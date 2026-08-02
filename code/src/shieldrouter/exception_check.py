from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExceptionCheckResult:
    eligible_for_notify: bool
    direct_mention: bool
    critical_urgency: bool
    trusted_context: bool
    group_muted: bool
    blocked_by_safety: bool
    reason: str


def check_exception(safety, features, synthesis) -> ExceptionCheckResult:
    blocked_by_safety = safety.verdict == "high_risk"
    group_muted = bool(features.group_muted)
    direct_mention = bool(features.direct_mention or synthesis.direct_mention)
    trusted_context = bool(
        features.trust >= 0.50
        or features.affinity >= 0.75
        or features.relationship_strength >= 0.65
        or (features.transaction_relationship and features.transaction_strength >= 0.35)
    )
    marketing_or_chain = synthesis.message_type in {"promotion", "spam", "forward"}
    critical_urgency = bool(
        synthesis.urgency_level == "high"
        and features.urgency >= 0.55
        and not marketing_or_chain
    )
    eligible = bool(
        group_muted
        and direct_mention
        and critical_urgency
        and trusted_context
        and not blocked_by_safety
    )
    if blocked_by_safety:
        reason = "blocked_by_safety"
    elif not group_muted:
        reason = "not_required_non_muted_group"
    elif not direct_mention:
        reason = "muted_group_without_direct_mention"
    elif not critical_urgency:
        reason = "muted_group_without_critical_urgency"
    elif not trusted_context:
        reason = "muted_group_without_trusted_context"
    else:
        reason = "trusted critical direct mention"
    return ExceptionCheckResult(
        eligible_for_notify=eligible,
        direct_mention=direct_mention,
        critical_urgency=critical_urgency,
        trusted_context=trusted_context,
        group_muted=group_muted,
        blocked_by_safety=blocked_by_safety,
        reason=reason,
    )
