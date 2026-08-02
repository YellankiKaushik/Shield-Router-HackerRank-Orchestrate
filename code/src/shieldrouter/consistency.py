from __future__ import annotations

import re
from dataclasses import dataclass


EVIDENCE_RE = re.compile(r"\bmessage_\d+\b")


@dataclass(frozen=True)
class ConsistencyResult:
    consistency_status: str
    detected_issue: tuple[str, ...] = ()
    supporting_facts: tuple[str, ...] = ()
    reason_repaired: bool = False
    final_reason: str = ""


def validate_and_repair_reason(
    *,
    action: str,
    message_type: str,
    reason: str,
    safety,
    features,
    synthesis,
    evidence: list,
    resolver_rule: str,
    events: dict[str, dict[str, str]] | None = None,
) -> ConsistencyResult:
    selected_ids = [e.message_id for e in evidence]
    selected_set = set(selected_ids)
    events = events or {}
    issues: list[str] = []
    supporting: list[str] = [
        f"safety={safety.verdict}",
        f"resolver={resolver_rule}",
        f"type={message_type}",
        f"action={action}",
    ]

    lower = reason.casefold()
    if safety.verdict == "high_risk" and action == "notify":
        issues.append("high_risk_notify_contradiction")
    if features.promotion_opt_out and "promotion opt-out" in lower and action == "notify":
        issues.append("promotion_opt_out_notify_contradiction")
    if "trusted critical" in lower and action == "mute" and safety.verdict != "high_risk":
        issues.append("trusted_critical_reason_muted_without_safety")
    if "quiet hours" in lower and not features.in_quiet_hours and not (
        ("load" in lower and features.relative_load >= 0.72) or ("risk" in lower and safety.verdict == "suspicious")
    ):
        issues.append("quiet_hours_claim_without_quiet_hours")
    if "transaction" in lower and not features.transaction_relationship:
        issues.append("transaction_claim_without_relationship")
    if "verified" in lower and features.trust < 0.38 and not features.transaction_relationship:
        issues.append("verified_claim_without_trust_context")
    if "repeated dismissal" in lower and not _selected_evidence_has_negative_reaction(selected_ids, events):
        issues.append("repeated_dismissal_claim_without_evidence")

    for evidence_id in EVIDENCE_RE.findall(reason):
        if evidence_id not in selected_set:
            issues.append(f"unselected_evidence_reference:{evidence_id}")

    claimed_type = _claimed_message_type(lower)
    if claimed_type and not _type_claim_compatible(claimed_type, message_type, lower, synthesis):
        issues.append(f"message_type_reason_mismatch:{claimed_type}->{message_type}")

    final_reason = reason
    repaired = False
    if issues:
        final_reason = _grounded_reason(action, resolver_rule, safety, synthesis, selected_ids)
        repaired = True
        repaired_issues = [
            issue
            for issue in _post_repair_issues(final_reason, action, message_type, safety, features, selected_set)
            if issue not in issues
        ]
        issues.extend(repaired_issues)

    status = "ok" if not issues else "repaired" if repaired and not _post_repair_issues(final_reason, action, message_type, safety, features, selected_set) else "error"
    return ConsistencyResult(status, tuple(dict.fromkeys(issues)), tuple(dict.fromkeys(supporting)), repaired, final_reason)


def _selected_evidence_has_negative_reaction(selected_ids: list[str], events: dict[str, dict[str, str]]) -> bool:
    for evidence_id in selected_ids:
        event = events.get(evidence_id, {})
        if event.get("notification_dismissed") == "1" or event.get("muted_after_message") == "1" or event.get("message_reported") == "1":
            return True
    return False


def _claimed_message_type(lower_reason: str) -> str:
    claims = [
        ("promotion", ("promotion", "promotional")),
        ("forward", ("forwarded", "forwarding")),
        ("payment", ("payment", "invoice", "upi", "qr")),
        ("event", ("event", "appointment", "scheduled", "meeting", "poster")),
        ("greeting", ("greeting", "conversational")),
        ("business_update", ("business update", "account notice")),
        ("scam", ("scam", "credential", "login code", "safety override")),
        ("spam", ("spam", "reported sender")),
    ]
    for message_type, needles in claims:
        if any(needle in lower_reason for needle in needles):
            return message_type
    return ""


def _grounded_reason(action: str, resolver_rule: str, safety, synthesis, selected_ids: list[str]) -> str:
    bits: list[str] = []
    if safety.verdict == "high_risk":
        bits.append("Safety override")
        if safety.signals:
            bits.append(", ".join(safety.signals[:2]).replace("_", " "))
    else:
        bits.append(resolver_rule or f"{action} selected by deterministic resolver")
    bits.extend(synthesis.facts[:3])
    if selected_ids:
        bits.append(f"similar prior message {selected_ids[0]}")
    text = "; ".join(dict.fromkeys(b for b in bits if b))
    return (text or f"{action} selected by deterministic context rules")[:220].rstrip(" ;,.")


def _post_repair_issues(final_reason: str, action: str, message_type: str, safety, features, selected_set: set[str]) -> list[str]:
    lower = final_reason.casefold()
    issues: list[str] = []
    if safety.verdict == "high_risk" and action == "notify":
        issues.append("high_risk_notify_contradiction")
    if "quiet hours" in lower and not features.in_quiet_hours and not (
        ("load" in lower and features.relative_load >= 0.72) or ("risk" in lower and safety.verdict == "suspicious")
    ):
        issues.append("quiet_hours_claim_without_quiet_hours")
    for evidence_id in EVIDENCE_RE.findall(final_reason):
        if evidence_id not in selected_set:
            issues.append(f"unselected_evidence_reference:{evidence_id}")
    claimed_type = _claimed_message_type(lower)
    if claimed_type and not _type_claim_compatible(claimed_type, message_type, lower, None):
        issues.append(f"message_type_reason_mismatch:{claimed_type}->{message_type}")
    return issues


def _type_claim_compatible(claimed_type: str, message_type: str, lower_reason: str, synthesis) -> bool:
    if claimed_type == message_type:
        return True
    if message_type == "scam" and claimed_type in {"payment", "spam"}:
        return True
    facts = " ".join(getattr(synthesis, "facts", ()) or ()).casefold()
    if claimed_type == "forward" and message_type == "greeting" and ("forwarded greeting pattern" in lower_reason or "forwarded greeting pattern" in facts):
        return True
    return False
