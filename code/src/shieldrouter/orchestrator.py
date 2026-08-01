from __future__ import annotations

from pathlib import Path

from .behaviorgraph import build_features
from .confidence import calibrate_confidence
from .fallback_synthesis import synthesize
from .indexes import build_indexes
from .io import DatasetError, load_dataset, safe_media_path
from .reason import build_reason
from .resolver import resolve
from .retrieval import retrieve_evidence
from .safety_rules import assess_safety
from .schemas import DecisionTrace, OUTPUT_COLUMNS, SafetyAssessment, Synthesis
from .validate import validate_output_rows


def media_error_for(row: dict[str, str], idx) -> str:
    media_type = row.get("media_type", "")
    media_id = row.get("media_id", "")
    if not media_type:
        return ""
    media_map = idx.images if media_type == "image" else idx.voices if media_type == "voice" else {}
    if media_id not in media_map:
        return f"missing_{media_type}_media_id"
    try:
        path = media_map[media_id]
        safe_media_path(idx.dataset_dir, str(path.relative_to(idx.dataset_dir)))
        if not path.exists():
            return f"missing_{media_type}_file"
    except Exception:
        return f"invalid_{media_type}_path"
    return ""


def process_message(row: dict[str, str], idx) -> DecisionTrace:
    errors: list[str] = []
    try:
        media_error = media_error_for(row, idx)
        if media_error:
            errors.append(media_error)
        business = idx.business_accounts.get(row.get("business_id", ""))
        safety = assess_safety(row, business)
        evidence = retrieve_evidence(row, idx)
        features = build_features(row, idx, evidence, media_error=media_error)
        synthesis = synthesize(row, safety, features)
        action, message_type, rule_reason = resolve(safety, features, synthesis)
        confidence = calibrate_confidence(action, safety, features, synthesis, evidence, errors)
        reason = build_reason(action, rule_reason, safety, features, synthesis, evidence)
        evidence_ids = [e.message_id for e in evidence]
        return DecisionTrace(row["message_id"], action, message_type, reason, confidence, evidence_ids, safety, features, synthesis, errors)
    except Exception as exc:
        errors.append(type(exc).__name__)
        safety = SafetyAssessment("suspicious", "low", ("row_processing_error",), "unknown")
        synthesis = Synthesis("low", False, "unknown", "digest", True, ("recoverable row error",))
        features = build_features(row, idx, [], media_error="row_processing_error")
        return DecisionTrace(
            row.get("message_id", ""),
            "digest",
            "unknown",
            "Recoverable processing error; conservative digest fallback",
            0.35,
            [],
            safety,
            features,
            synthesis,
            errors,
        )


def run(dataset_dir: Path, output_path: Path) -> tuple[list[DecisionTrace], dict[str, object]]:
    tables = load_dataset(dataset_dir)
    idx = build_indexes(dataset_dir, tables)
    traces = [process_message(row, idx) for row in tables["messages.csv"]]
    rows = [t.to_output_row() for t in traces]
    errors = validate_output_rows(tables["messages.csv"], tables["message_history.csv"], rows)
    if errors:
        raise DatasetError("Output validation failed before write: " + "; ".join(errors[:5]))
    from .io import write_csv

    write_csv(output_path, rows, OUTPUT_COLUMNS)
    return traces, summarize(traces)


def summarize(traces: list[DecisionTrace]) -> dict[str, object]:
    from collections import Counter

    confidences = [t.confidence for t in traces]
    return {
        "rows": len(traces),
        "unique_ids": len({t.message_id for t in traces}),
        "actions": dict(Counter(t.action for t in traces)),
        "message_types": dict(Counter(t.message_type for t in traces)),
        "confidence_min": min(confidences) if confidences else 0,
        "confidence_mean": sum(confidences) / len(confidences) if confidences else 0,
        "confidence_max": max(confidences) if confidences else 0,
        "evidence_usage_count": sum(1 for t in traces if t.evidence_message_ids),
        "fallback_error_count": sum(1 for t in traces if t.errors),
    }
