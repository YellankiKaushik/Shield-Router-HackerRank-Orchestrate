from __future__ import annotations

from pathlib import Path

import re

from .ai_models import AdvisoryModelOutput
from .behaviorgraph import build_features
from .confidence import calibrate_confidence
from .exception_check import check_exception
from .fallback_synthesis import synthesize
from .indexes import build_indexes
from .io import DatasetError, load_routing_dataset, safe_media_path
from .media import extract_media
from .online_ai import merge_advisory_safety, merge_advisory_synthesis, request_advisory
from .provider import AIProvider
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


def _row_with_media_text(row: dict[str, str], media_facts) -> dict[str, str]:
    media_text = media_facts.combined_text()
    if not media_text:
        return row
    enriched = dict(row)
    enriched["message_text"] = (row.get("message_text", "") + " " + media_text).strip()
    return enriched


def process_message(
    row: dict[str, str],
    idx,
    provider: AIProvider | None = None,
    online: bool = False,
    enrich_external: bool = False,
) -> DecisionTrace:
    errors: list[str] = []
    try:
        media_facts = extract_media(row, idx, provider, online=online, enrich_external=enrich_external)
        enriched_row = _row_with_media_text(row, media_facts)
        media_error = media_error_for(row, idx)
        if media_error:
            errors.append(media_error)
        if media_facts.status == "failed":
            errors.append(media_facts.error or "media_extraction_failed")
        business = idx.business_accounts.get(row.get("business_id", ""))
        rule_safety = assess_safety(enriched_row, business)
        advisory: AdvisoryModelOutput | None = None
        if (
            online
            and provider is not None
            and enrich_external
            and row.get("media_type", "") != "image"
            and (row.get("media_type", "") != "voice" or media_facts.status == "ok")
            and rule_safety.verdict != "high_risk"
        ):
            try:
                advisory = request_advisory(provider, enriched_row, business, media_facts)
            except Exception as exc:
                errors.append(f"advisory_model_fallback:{type(exc).__name__}:{str(exc)[:160]}")
                provider.stats.fallbacks += 1
        safety = merge_advisory_safety(rule_safety, advisory)
        evidence = retrieve_evidence(enriched_row, idx)
        features = build_features(enriched_row, idx, evidence, media_error=media_error or media_facts.error)
        synthesis = synthesize(enriched_row, safety, features)
        if row.get("media_type", "") == "image" and media_facts.status == "ok":
            advisory = _advisory_from_image_media(media_facts)
            safety = merge_advisory_safety(safety, advisory)
            synthesis = merge_advisory_synthesis(synthesis, advisory, safety)
        else:
            synthesis = merge_advisory_synthesis(synthesis, advisory, safety)
        exception = check_exception(safety, features, synthesis)
        action, message_type, rule_reason = resolve(safety, features, synthesis, exception)
        confidence = calibrate_confidence(action, safety, features, synthesis, evidence, errors)
        reason = build_reason(action, rule_reason, safety, features, synthesis, evidence)
        evidence_ids = [e.message_id for e in evidence]
        return DecisionTrace(row["message_id"], action, message_type, reason, confidence, evidence_ids, safety, features, synthesis, errors, media_facts, exception)
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


def run(
    dataset_dir: Path,
    output_path: Path,
    provider: AIProvider | None = None,
    online: bool = False,
    local_voice: bool = False,
    local_multimodal: bool = False,
) -> tuple[list[DecisionTrace], dict[str, object]]:
    tables = load_routing_dataset(dataset_dir)
    idx = build_indexes(dataset_dir, tables)
    if (local_voice or local_multimodal) and provider is not None:
        traces = [
            process_message(row, idx, provider=provider, online=True, enrich_external=False)
            for row in tables["messages.csv"]
        ]
    elif online and provider is not None:
        offline_traces = [process_message(row, idx) for row in tables["messages.csv"]]
        selected = select_external_enrichment_rows(tables["messages.csv"], offline_traces, getattr(getattr(provider, "config", None), "max_non_image_text_requests", 12))
        traces = [
            process_message(row, idx, provider=provider, online=True, enrich_external=row["message_id"] in selected)
            for row in tables["messages.csv"]
        ]
    else:
        traces = [process_message(row, idx, provider=provider, online=online) for row in tables["messages.csv"]]
    rows = [t.to_output_row() for t in traces]
    errors = validate_output_rows(tables["messages.csv"], tables["message_history.csv"], rows)
    if errors:
        raise DatasetError("Output validation failed before write: " + "; ".join(errors[:5]))
    from .io import write_csv

    write_csv(output_path, rows, OUTPUT_COLUMNS)
    summary = summarize(traces)
    if provider is not None:
        summary["provider"] = provider.stats.summary()
    return traces, summary


def _advisory_from_image_media(media: object) -> AdvisoryModelOutput:
    facts = getattr(media, "local_image_facts", None)
    credential_requests: list[str] = []
    if getattr(facts, "credential_request_language", False):
        credential_requests.append("visible credential or sensitive-code request")
    suspicious_domains = [
        signal.split(":", 1)[1]
        for signal in getattr(media, "suspicious_visual_signals", [])
        if signal.startswith("suspicious_domain:")
    ]
    prompt_injection = "prompt_injection" in getattr(media, "suspicious_visual_signals", [])
    payment_pressure = "payment_pressure" in getattr(media, "suspicious_visual_signals", [])
    risk_level = "none"
    if prompt_injection or (credential_requests and (getattr(facts, "urgent_language", False) or getattr(facts, "payment_language", False))):
        risk_level = "high"
    elif getattr(media, "suspicious_visual_signals", []):
        risk_level = "medium"
    best_type = "unknown"
    if risk_level == "high":
        best_type = "scam"
    elif getattr(facts, "layout_type", "") == "low_text_image":
        best_type = "unknown"
    elif _looks_like_safety_advisory(getattr(media, "visible_text", "")):
        best_type = "business_update"
    elif getattr(facts, "promotion_language", False):
        best_type = "promotion"
    elif getattr(facts, "payment_language", False):
        best_type = "payment"
    elif getattr(facts, "deadline_language", False) or getattr(facts, "detected_dates", []):
        best_type = "event"
    elif getattr(facts, "layout_type", "") == "document":
        best_type = "event"
    urgency = "high" if getattr(facts, "urgent_language", False) or getattr(facts, "deadline_language", False) else "medium" if getattr(facts, "detected_dates", []) else "low"
    return AdvisoryModelOutput(
        visible_image_text=getattr(media, "visible_text", ""),
        image_scene_or_poster_facts=list(getattr(media, "scene_or_poster_facts", [])),
        qr_presence=bool(getattr(media, "qr_code_present", False)),
        prices_payments=list(getattr(media, "price_or_payment_information", [])),
        dates_deadlines=list(getattr(media, "dates_and_deadlines", [])),
        credential_or_sensitive_data_requests=credential_requests,
        suspicious_domains=suspicious_domains,
        prompt_injection_detected=prompt_injection,
        risk_level=risk_level,
        urgency_level=urgency,
        best_official_message_type=best_type,
        ambiguity=getattr(facts, "layout_type", "") in {"low_text_image", "unknown"} or payment_pressure,
        concise_grounded_semantic_facts=list(getattr(media, "scene_or_poster_facts", []))[:4],
    )


def _looks_like_safety_advisory(text: str) -> bool:
    low = (text or "").casefold()
    return any(phrase in low for phrase in ("scammer", "scammers", "secure banking", "moohbandrakho", "do not share otp", "never ask for otp"))


def select_external_enrichment_rows(rows: list[dict[str, str]], offline_traces: list[DecisionTrace], max_text: int = 12) -> set[str]:
    selected: set[str] = {r["message_id"] for r in rows if r.get("media_type") == "image"}
    trace_by_id = {t.message_id: t for t in offline_traces}
    text_candidates: list[tuple[tuple[int, int, float, int, str], str]] = []
    voice_candidates: list[tuple[tuple[int, int, float, int, str], str]] = []
    for row in rows:
        trace = trace_by_id[row["message_id"]]
        media_type = row.get("media_type", "")
        if media_type == "text":
            media_type = ""
        eligible = _needs_text_enrichment(row, trace)
        if media_type == "" and eligible:
            text_candidates.append((_priority(row, trace), row["message_id"]))
        elif media_type == "voice" and trace.synthesis.ambiguous:
            voice_candidates.append((_priority(row, trace), row["message_id"]))
    for _priority_key, message_id in sorted(text_candidates)[:max_text]:
        selected.add(message_id)
    for _priority_key, message_id in sorted(voice_candidates):
        selected.add(message_id)
    return selected


def _needs_text_enrichment(row: dict[str, str], trace: DecisionTrace) -> bool:
    if row.get("media_type"):
        return False
    return (
        trace.confidence < 0.70
        or trace.message_type == "unknown"
        or trace.synthesis.ambiguous
        or _safety_context_disagree(trace)
        or _deadline_or_direct_unresolved(row, trace)
    )


def _safety_context_disagree(trace: DecisionTrace) -> bool:
    return trace.safety.verdict == "suspicious" and trace.features.trust >= 0.6


def _deadline_or_direct_unresolved(row: dict[str, str], trace: DecisionTrace) -> bool:
    text = row.get("message_text", "").casefold()
    has_deadline = bool(re.search(r"\b(today|tonight|tomorrow|deadline|by \d{1,2}|before \d{1,2}|urgent|asap|eod)\b", text))
    has_direct = bool(re.search(r"\b(you|kaushik|please|can you|call me|reply|confirm)\b", text))
    return (has_deadline or has_direct) and (trace.synthesis.ambiguous or trace.confidence < 0.78)


def _priority(row: dict[str, str], trace: DecisionTrace) -> tuple[int, int, float, int, str]:
    text = row.get("message_text", "").casefold()
    safety_terms = bool(re.search(r"\b(otp|password|login|payment|upi|qr|refund|verify|blocked|suspend|http|www\.)\b", text))
    missed_notify = trace.action != "notify" and (trace.synthesis.urgency_level == "high" or trace.synthesis.direct_mention)
    unknown = trace.message_type == "unknown"
    return (-int(safety_terms or trace.safety.verdict != "safe"), -int(missed_notify), trace.confidence, -int(unknown), row["message_id"])


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
