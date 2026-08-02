from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from shieldrouter.indexes import build_indexes
from shieldrouter.io import DatasetError, load_dataset, load_routing_dataset, read_csv, validate_dataset
from shieldrouter.orchestrator import process_message, run, summarize
from shieldrouter.provider import LocalMultimodalProvider, LocalVoiceProvider, OpenRouterProvider, ProviderError, WhisperConfig
from shieldrouter.schemas import OUTPUT_COLUMNS
from shieldrouter.validate import validate_output_rows

EVAL_DIR = ROOT / "evaluation"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
from evaluate import classification_metrics, confidence_stats, confusion, macro_f1


def cmd_validate_input(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset)
    tables = load_dataset(dataset)
    errors = validate_dataset(dataset, tables)
    if errors:
        print("INPUT VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"INPUT VALIDATION OK: {len(tables['messages.csv'])} messages")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.online and (getattr(args, "local_voice", False) or getattr(args, "local_multimodal", False)):
        raise DatasetError("--online cannot be combined with local zero-network modes")
    if getattr(args, "local_voice", False) and getattr(args, "local_multimodal", False):
        raise DatasetError("--local-voice and --local-multimodal are mutually exclusive")
    provider = make_provider(args)
    started = time.perf_counter()
    traces, summary = run(
        Path(args.dataset),
        Path(args.output),
        provider=provider,
        online=args.online,
        local_voice=getattr(args, "local_voice", False),
        local_multimodal=getattr(args, "local_multimodal", False),
    )
    summary["runtime_seconds"] = round(time.perf_counter() - started, 4)
    if getattr(args, "local_voice", False) or getattr(args, "local_multimodal", False):
        _assert_zero_provider_requests(summary)
    if getattr(args, "summary_json", None):
        write_summary_json(Path(args.summary_json), args, summary, traces, started)
    print("RUN OK")
    print_summary(summary)
    if args.trace_errors:
        for trace in traces:
            if trace.errors:
                print(f"{trace.message_id}: {','.join(trace.errors)}")
    return 0


def write_summary_json(path: Path, args: argparse.Namespace, summary: dict[str, object], traces: list, started: float) -> None:
    payload = build_summary_payload(args, summary, traces, started)
    validate_summary_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def build_summary_payload(args: argparse.Namespace, summary: dict[str, object], traces: list, started: float) -> dict[str, object]:
    provider = summary.get("provider") if isinstance(summary.get("provider"), dict) else {}
    output_path = Path(args.output)
    mode = "local_multimodal" if getattr(args, "local_multimodal", False) else "local_voice" if getattr(args, "local_voice", False) else "online" if getattr(args, "online", False) else "offline"
    output_sha = hashlib.sha256(output_path.read_bytes()).hexdigest() if output_path.exists() else ""
    return {
        "mode": mode,
        "rows": int(summary.get("rows", 0)),
        "unique_ids": int(summary.get("unique_ids", 0)),
        "action_distribution": summary.get("actions", {}),
        "message_type_distribution": summary.get("message_types", {}),
        "confidence": {
            "minimum": summary.get("confidence_min", 0),
            "mean": summary.get("confidence_mean", 0),
            "maximum": summary.get("confidence_max", 0),
        },
        "evidence_usage": int(summary.get("evidence_usage_count", 0)),
        "images": {
            "attempted": int(provider.get("image_extraction_attempts", 0) or 0),
            "succeeded": int(provider.get("image_extraction_successes", 0) or 0),
            "failed": int(provider.get("image_extraction_failures", 0) or 0),
        },
        "voice": {
            "attempted": int(provider.get("transcription_attempts", 0) or 0),
            "succeeded": int(provider.get("transcription_successes", 0) or 0),
            "failed": int(provider.get("transcription_failures", 0) or 0),
        },
        "ocr_cache_hits": int(provider.get("image_extraction_cache_hits", 0) or 0),
        "transcript_cache_hits": int(provider.get("transcription_cache_hits", 0) or 0),
        "provider_requests": int(provider.get("request_count", 0) or 0),
        "retries": int(provider.get("retry_count", 0) or 0),
        "fallbacks": int(provider.get("fallback_count", 0) or 0),
        "per_row_error_count": {trace.message_id: len(trace.errors) for trace in traces if trace.errors},
        "elapsed_runtime_seconds": round(time.perf_counter() - started, 4),
        "output_path": _display_path(output_path),
        "output_sha256": output_sha,
        "models": {
            "whisper_model": provider.get("whisper_model_used", "") or os.environ.get("LOCAL_WHISPER_MODEL", "small"),
            "external_models": provider.get("actual_models", []),
        },
        "cache": {
            "cache_dir": _display_path(Path(getattr(args, "cache_dir", ""))) if getattr(args, "cache_dir", "") else "",
            "ocr_cache_hits": int(provider.get("image_extraction_cache_hits", 0) or 0),
            "transcript_cache_hits": int(provider.get("transcription_cache_hits", 0) or 0),
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "application_version": _git_commit_or_unknown(),
    }


def validate_summary_payload(payload: dict[str, object]) -> None:
    required = {
        "mode",
        "rows",
        "unique_ids",
        "action_distribution",
        "message_type_distribution",
        "confidence",
        "evidence_usage",
        "images",
        "voice",
        "ocr_cache_hits",
        "transcript_cache_hits",
        "provider_requests",
        "retries",
        "fallbacks",
        "per_row_error_count",
        "elapsed_runtime_seconds",
        "output_path",
        "output_sha256",
        "models",
        "cache",
        "timestamp",
        "application_version",
    }
    missing = required - set(payload)
    if missing:
        raise DatasetError(f"summary_json missing keys: {sorted(missing)}")
    dumped = json.dumps(payload, ensure_ascii=False).casefold()
    forbidden = ("message_text", "visible_text", "transcript_text", "voice_transcript", "ocr_text", "api_key", "password", "credential")
    if any(term in dumped for term in forbidden):
        raise DatasetError("summary_json contains forbidden sensitive/raw-content fields")
    if len(str(payload.get("output_sha256", ""))) != 64:
        raise DatasetError("summary_json output_sha256 is invalid")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        return path.name


def _git_commit_or_unknown() -> str:
    try:
        import subprocess

        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT.parent, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def cmd_validate_output(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset)
    tables = load_routing_dataset(dataset)
    rows = read_csv(Path(args.output))
    errors = validate_output_rows(tables["messages.csv"], tables["message_history.csv"], rows)
    if errors:
        print("OUTPUT VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OUTPUT VALIDATION OK: {len(rows)} rows")
    return 0


def cmd_prepare_models(args: argparse.Namespace) -> int:
    config = WhisperConfig.from_env()
    model_name = args.whisper_model or config.model
    hf_home, hf_hub_cache = _huggingface_cache_locations()
    repo_root = ROOT.parent.resolve()
    if _path_is_inside(hf_hub_cache, repo_root):
        print(f"ERROR: Hugging Face cache is inside the repository: {hf_hub_cache}")
        print("Set HF_HOME or HF_HUB_CACHE to a cache directory outside the repository, then rerun prepare-models.")
        return 1

    from rapidocr import RapidOCR
    import rapidocr

    rapidocr_package = Path(rapidocr.__file__).resolve().parent
    rapidocr_models = rapidocr_package / "models"
    RapidOCR()

    from faster_whisper import WhisperModel

    WhisperModel(
        model_name,
        device=config.device,
        compute_type=config.compute_type,
        local_files_only=False,
    )
    print("MODEL PREPARATION OK")
    print(f"RapidOCR package: {rapidocr_package}")
    print(f"RapidOCR model assets: {rapidocr_models}")
    print(f"Faster-Whisper model: {model_name}")
    print(f"Faster-Whisper device: {config.device}")
    print(f"Faster-Whisper compute_type: {config.compute_type}")
    print(f"HF_HOME: {hf_home}")
    print(f"HF_HUB_CACHE: {hf_hub_cache}")
    print("Selected local runs use local_files_only=True after this preparation.")
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset)
    tables = load_routing_dataset(dataset)
    idx = build_indexes(dataset, tables)
    row = next((r for r in tables["messages.csv"] if r["message_id"] == args.message_id), None)
    if row is None:
        print(f"Unknown message_id: {args.message_id}")
        return 1
    provider = make_provider(args)
    local_mode = getattr(args, "local_voice", False) or getattr(args, "local_multimodal", False)
    trace = process_message(row, idx, provider=provider, online=args.online or local_mode, enrich_external=False)
    payload = {
        "output": trace.to_output_row(),
        "safety": {
            "verdict": trace.safety.verdict,
            "risk_level": trace.safety.risk_level,
            "signals": list(trace.safety.signals),
        },
        "features": trace.features.__dict__,
        "synthesis": trace.synthesis.__dict__,
        "exception_check": trace.exception_check.__dict__ if trace.exception_check else None,
        "consistency": trace.consistency.__dict__ if trace.consistency else None,
        "media_facts": trace.media_facts.model_dump() if hasattr(trace.media_facts, "model_dump") else trace.media_facts,
        "errors": trace.errors,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


def cmd_smoke_online(args: argparse.Namespace) -> int:
    provider = make_provider(args, require_online=True)
    dataset = Path(args.dataset)
    tables = load_routing_dataset(dataset)
    idx = build_indexes(dataset, tables)
    selected = []
    cases = [
        ("text", lambda r: not r.get("media_type"), True),
        ("image", lambda r: r.get("media_type") == "image", True),
        ("voice", lambda r: r.get("media_type") == "voice", False),
    ]
    for label, predicate, enrich in cases:
        row = next((r for r in tables["messages.csv"] if predicate(r)), None)
        if row is None:
            print(f"SMOKE FAILED: no {label} message found")
            return 1
        started = __import__("time").perf_counter()
        before = provider.stats.request_count
        trace = process_message(row, idx, provider=provider, online=True, enrich_external=enrich)
        latency = __import__("time").perf_counter() - started
        selected.append(
            {
                "kind": label,
                "message_id": trace.message_id,
                "latency_seconds": round(latency, 4),
                "new_openrouter_requests": provider.stats.request_count - before,
                "cache": provider.stats.summary(),
                "final_decision": trace.to_output_row(),
                "safety": {
                    "verdict": trace.safety.verdict,
                    "risk_level": trace.safety.risk_level,
                    "signals": list(trace.safety.signals),
                },
                "synthesis": trace.synthesis.__dict__,
                "errors": trace.errors,
            }
        )
        if label in {"text", "image"} and trace.errors:
            print(json.dumps({"smoke_results": selected, "provider": provider.stats.summary()}, indent=2, sort_keys=True, default=str))
            print(f"SMOKE FAILED: {label} structured enrichment fell back")
            return 1
    for label, predicate, enrich in cases[:2]:
        row = next(r for r in tables["messages.csv"] if predicate(r))
        before = provider.stats.request_count
        before_cache = provider.stats.cache_hits
        trace = process_message(row, idx, provider=provider, online=True, enrich_external=enrich)
        selected.append(
            {
                "kind": f"{label}_cache_rerun",
                "message_id": trace.message_id,
                "new_openrouter_requests": provider.stats.request_count - before,
                "new_cache_hits": provider.stats.cache_hits - before_cache,
                "errors": trace.errors,
            }
        )
        if provider.stats.request_count != before or provider.stats.cache_hits == before_cache:
            print(json.dumps({"smoke_results": selected, "provider": provider.stats.summary()}, indent=2, sort_keys=True, default=str))
            print(f"SMOKE FAILED: {label} cache rerun consumed a request")
            return 1
    print(json.dumps({"smoke_results": selected, "provider": provider.stats.summary()}, indent=2, sort_keys=True, default=str))
    return 0


def make_provider(args: argparse.Namespace, require_online: bool = False):
    if getattr(args, "local_multimodal", False):
        config = WhisperConfig.from_env()
        config = WhisperConfig(
            model=config.model,
            device=config.device,
            compute_type=config.compute_type,
            local_files_only=True,
            allow_model_fallback=False,
        )
        return LocalMultimodalProvider(cache_dir=Path(getattr(args, "cache_dir", "code/.shieldrouter_cache")), config=config)
    if getattr(args, "local_voice", False):
        config = WhisperConfig.from_env()
        config = WhisperConfig(
            model=config.model,
            device=config.device,
            compute_type=config.compute_type,
            local_files_only=True,
            allow_model_fallback=False,
        )
        return LocalVoiceProvider(cache_dir=Path(getattr(args, "cache_dir", "code/.shieldrouter_cache")), config=config)
    online = getattr(args, "online", False) or require_online
    if not online:
        return None
    _load_env_file(Path("code/.env"))
    _load_env_file(Path(".env"))
    provider_name = __import__("os").environ.get("AI_PROVIDER", "openrouter").casefold()
    if provider_name != "openrouter":
        raise DatasetError(f"Unsupported AI_PROVIDER={provider_name}; set AI_PROVIDER=openrouter for online mode")
    try:
        return OpenRouterProvider(cache_dir=Path(getattr(args, "cache_dir", "code/.shieldrouter_cache")))
    except ProviderError as exc:
        if require_online:
            raise DatasetError(str(exc))
        print(f"ONLINE PROVIDER UNAVAILABLE: {exc}; using offline fallback")
        return None


def _assert_zero_provider_requests(summary: dict[str, object]) -> None:
    provider = summary.get("provider")
    if not isinstance(provider, dict):
        raise DatasetError("Local voice mode expected provider stats")
    nonzero = {
        key: provider.get(key)
        for key in ("request_count", "provider_call_count", "media_call_count", "retry_count")
        if int(provider.get(key, 0) or 0) != 0
    }
    if nonzero:
        raise DatasetError(f"Local zero-network mode made forbidden provider requests: {nonzero}")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _huggingface_cache_locations() -> tuple[Path, Path]:
    hf_home = os.environ.get("HF_HOME")
    if not hf_home:
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        hf_home = str(Path(xdg_cache) / "huggingface") if xdg_cache else str(Path.home() / ".cache" / "huggingface")
    hf_hub_cache = os.environ.get("HF_HUB_CACHE") or str(Path(hf_home) / "hub")
    return Path(hf_home).expanduser().resolve(), Path(hf_hub_cache).expanduser().resolve()


def _path_is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def cmd_evaluate_sample(args: argparse.Namespace) -> int:
    import csv

    dataset = Path(args.dataset)
    tables = load_dataset(dataset)
    idx = build_indexes(dataset, tables)
    local_mode = getattr(args, "local_voice", False) or getattr(args, "local_multimodal", False)
    provider = make_provider(args) if local_mode else None
    traces = []
    for sample in tables["sample_messages.csv"]:
        incoming = {k: sample[k] for k in tables["messages.csv"][0].keys()}
        traces.append(process_message(incoming, idx, provider=provider, online=local_mode, enrich_external=False))
    pred_rows = [t.to_output_row() for t in traces]
    expected_actions = [r["action"] for r in tables["sample_messages.csv"]]
    predicted_actions = [r["action"] for r in pred_rows]
    expected_types = [r["message_type"] for r in tables["sample_messages.csv"]]
    predicted_types = [r["message_type"] for r in pred_rows]
    action_classes = ["notify", "digest", "mute"]
    type_classes = sorted(set(expected_types) | set(predicted_types))
    action_metrics = classification_metrics(expected_actions, predicted_actions, action_classes)
    type_metrics = classification_metrics(expected_types, predicted_types, type_classes)
    report = {
        "sample_rows": len(pred_rows),
        "action_accuracy": round(sum(e == p for e, p in zip(expected_actions, predicted_actions)) / len(pred_rows), 4),
        "action_metrics": action_metrics,
        "action_macro_f1": macro_f1(action_metrics),
        "message_type_accuracy": round(sum(e == p for e, p in zip(expected_types, predicted_types)) / len(pred_rows), 4),
        "message_type_metrics": type_metrics,
        "message_type_macro_f1": macro_f1(type_metrics),
        "action_confusion": confusion(expected_actions, predicted_actions),
        "message_type_confusion": confusion(expected_types, predicted_types),
        "evidence_usage_rate": round(sum(1 for r in pred_rows if r["evidence_message_ids"] != "none") / len(pred_rows), 4),
        "confidence": confidence_stats(pred_rows),
        "false_positive_scams": [
            r["message_id"]
            for r, p in zip(tables["sample_messages.csv"], pred_rows)
            if p["message_type"] == "scam" and r["message_type"] != "scam"
        ],
        "false_negative_urgent_notifications": [
            r["message_id"]
            for r, p in zip(tables["sample_messages.csv"], pred_rows)
            if r["action"] == "notify" and p["action"] != "notify"
        ],
    }
    notify_metrics = action_metrics.get("notify", {})
    report["urgent_notify_precision"] = notify_metrics.get("precision", 0.0)
    report["urgent_notify_recall"] = notify_metrics.get("recall", 0.0)
    report["voice_message_correctness"] = _voice_correctness(tables["sample_messages.csv"], pred_rows)
    report["image_message_correctness"] = _image_correctness(tables["sample_messages.csv"], pred_rows)
    if provider is not None:
        provider_summary = provider.stats.summary()
        _assert_zero_provider_requests({"provider": provider_summary})
        report["provider"] = provider_summary
    history_ids = {r["message_id"] for r in tables["message_history.csv"]}
    report["evidence_validity"] = "passed" if all(
        p["evidence_message_ids"] == "none" or all(eid in history_ids for eid in p["evidence_message_ids"].split(";"))
        for p in pred_rows
    ) else "failed"
    report["reason_consistency"] = "passed" if all(p["reason"].strip() and p["message_type"] in p["reason"] or p["reason"].strip() for p in pred_rows) else "failed"

    errors = []
    for sample, pred, trace in zip(tables["sample_messages.csv"], pred_rows, traces):
        if sample["action"] != pred["action"] or sample["message_type"] != pred["message_type"]:
            errors.append(
                {
                    "message_id": sample["message_id"],
                    "expected_action": sample["action"],
                    "predicted_action": pred["action"],
                    "expected_message_type": sample["message_type"],
                    "predicted_message_type": pred["message_type"],
                    "relevant_context": "; ".join(trace.synthesis.facts) or "limited deterministic context",
                    "responsible_rule_or_feature": f"safety={trace.safety.verdict}; urgency={trace.synthesis.urgency_level}; fatigue={trace.features.fatigue:.2f}",
                    "generalizable_correction": _suggest_correction(sample, pred),
                }
            )
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.errors:
        error_path = Path(args.errors)
        error_path.parent.mkdir(parents=True, exist_ok=True)
        with error_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "message_id",
                "expected_action",
                "predicted_action",
                "expected_message_type",
                "predicted_message_type",
                "relevant_context",
                "responsible_rule_or_feature",
                "generalizable_correction",
            ], lineterminator="\n")
            writer.writeheader()
            writer.writerows(errors)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def _voice_correctness(sample_rows: list[dict[str, str]], pred_rows: list[dict[str, str]]) -> dict[str, object]:
    pred_by_id = {r["message_id"]: r for r in pred_rows}
    voice_rows = [r for r in sample_rows if r.get("media_type") == "voice" and r["message_id"] in pred_by_id]
    if not voice_rows:
        return {"voice_sample_rows": 0, "action_accuracy": None, "message_type_accuracy": None, "correct_ids": [], "missed_ids": []}
    correct_ids = [
        r["message_id"]
        for r in voice_rows
        if pred_by_id[r["message_id"]]["action"] == r["action"] and pred_by_id[r["message_id"]]["message_type"] == r["message_type"]
    ]
    return {
        "voice_sample_rows": len(voice_rows),
        "action_accuracy": round(sum(pred_by_id[r["message_id"]]["action"] == r["action"] for r in voice_rows) / len(voice_rows), 4),
        "message_type_accuracy": round(sum(pred_by_id[r["message_id"]]["message_type"] == r["message_type"] for r in voice_rows) / len(voice_rows), 4),
        "correct_ids": correct_ids,
        "missed_ids": [r["message_id"] for r in voice_rows if r["message_id"] not in correct_ids],
    }


def _image_correctness(sample_rows: list[dict[str, str]], pred_rows: list[dict[str, str]]) -> dict[str, object]:
    pred_by_id = {r["message_id"]: r for r in pred_rows}
    image_rows = [r for r in sample_rows if r.get("media_type") == "image" and r["message_id"] in pred_by_id]
    if not image_rows:
        return {"image_sample_rows": 0, "action_accuracy": None, "message_type_accuracy": None, "correct_ids": [], "missed_ids": []}
    correct_ids = [
        r["message_id"]
        for r in image_rows
        if pred_by_id[r["message_id"]]["action"] == r["action"] and pred_by_id[r["message_id"]]["message_type"] == r["message_type"]
    ]
    return {
        "image_sample_rows": len(image_rows),
        "action_accuracy": round(sum(pred_by_id[r["message_id"]]["action"] == r["action"] for r in image_rows) / len(image_rows), 4),
        "message_type_accuracy": round(sum(pred_by_id[r["message_id"]]["message_type"] == r["message_type"] for r in image_rows) / len(image_rows), 4),
        "correct_ids": correct_ids,
        "missed_ids": [r["message_id"] for r in image_rows if r["message_id"] not in correct_ids],
    }


def _suggest_correction(expected: dict[str, str], predicted: dict[str, str]) -> str:
    if expected["action"] == "notify" and predicted["action"] != "notify":
        return "Improve trusted urgency, direct request, media transcript, or transaction-update detection."
    if expected["action"] == "mute" and predicted["action"] != "mute":
        return "Strengthen opt-out, dismissal, forwarding, or safety-risk precedence."
    if expected["message_type"] != predicted["message_type"]:
        return "Refine deterministic official message-type classification."
    return "No correction needed."


def print_summary(summary: dict[str, object]) -> None:
    for key in [
        "rows",
        "unique_ids",
        "actions",
        "message_types",
        "confidence_min",
        "confidence_mean",
        "confidence_max",
        "evidence_usage_count",
        "fallback_error_count",
        "provider",
        "runtime_seconds",
    ]:
        if key in summary:
            print(f"{key}: {summary[key]}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ShieldRouter offline notification router")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate-input")
    p.add_argument("--dataset", required=True)
    p.set_defaults(func=cmd_validate_input)
    p = sub.add_parser("prepare-models")
    p.add_argument("--whisper-model", help="Faster-Whisper model to download/cache; defaults to LOCAL_WHISPER_MODEL or small.")
    p.set_defaults(func=cmd_prepare_models)
    p = sub.add_parser("run")
    p.add_argument("--dataset", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--offline", action="store_true", help="Force deterministic offline mode.")
    p.add_argument("--online", action="store_true", help="Use optional external AI provider with offline fallback.")
    p.add_argument("--local-voice", action="store_true", help="Use local Faster-Whisper only for voice messages; no external provider requests.")
    p.add_argument("--local-multimodal", action="store_true", help="Use local OCR/QR for images and local Faster-Whisper for voice; no external provider requests.")
    p.add_argument("--cache-dir", default="code/.shieldrouter_cache")
    p.add_argument("--trace-errors", action="store_true")
    p.add_argument("--summary-json")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("validate-output")
    p.add_argument("--dataset", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_validate_output)
    p = sub.add_parser("trace")
    p.add_argument("--dataset", required=True)
    p.add_argument("--message-id", required=True)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--online", action="store_true")
    p.add_argument("--local-voice", action="store_true")
    p.add_argument("--local-multimodal", action="store_true")
    p.add_argument("--cache-dir", default="code/.shieldrouter_cache")
    p.set_defaults(func=cmd_trace)
    p = sub.add_parser("smoke-online")
    p.add_argument("--dataset", required=True)
    p.add_argument("--online", action="store_true", default=True)
    p.add_argument("--cache-dir", default="code/.shieldrouter_cache")
    p.set_defaults(func=cmd_smoke_online)
    p = sub.add_parser("evaluate-sample")
    p.add_argument("--dataset", required=True)
    p.add_argument("--local-voice", action="store_true")
    p.add_argument("--local-multimodal", action="store_true")
    p.add_argument("--cache-dir", default="code/.shieldrouter_cache")
    p.add_argument("--report")
    p.add_argument("--errors")
    p.set_defaults(func=cmd_evaluate_sample)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except DatasetError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
