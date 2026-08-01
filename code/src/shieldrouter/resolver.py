from __future__ import annotations


def resolve(safety, features, synthesis, exception_check=None) -> tuple[str, str, str]:
    if safety.verdict == "high_risk":
        return "mute", "scam", "hard safety risk"
    if exception_check is not None and exception_check.eligible_for_notify:
        return "notify", synthesis.message_type if synthesis.message_type != "unknown" else "urgent", exception_check.reason
    critical_direct = (
        synthesis.direct_mention
        and synthesis.urgency_level == "high"
        and synthesis.message_type not in {"promotion", "spam", "forward"}
    )
    if features.group_muted and synthesis.urgency_level == "high" and not (exception_check and exception_check.eligible_for_notify):
        return "digest", synthesis.message_type if synthesis.message_type != "unknown" else "urgent", "muted group queued without critical trusted exception"
    if (features.in_quiet_hours or features.relative_load >= 0.72) and synthesis.preliminary_action == "notify" and not critical_direct:
        return "digest", synthesis.message_type, "queued by quiet hours or notification load"
    if (
        safety.verdict == "safe"
        and critical_direct
        and (features.trust >= 0.38 or features.affinity >= 0.75)
    ):
        return "notify", synthesis.message_type if synthesis.message_type != "unknown" else "urgent", "trusted critical direct mention"
    if safety.verdict == "safe" and synthesis.direct_mention and synthesis.preliminary_action == "notify" and features.affinity >= 0.75:
        return "notify", synthesis.message_type if synthesis.message_type != "unknown" else "personal", "trusted direct response request"
    if safety.verdict == "safe" and synthesis.urgency_level == "high" and synthesis.preliminary_action == "notify" and features.trust >= 0.38:
        return "notify", synthesis.message_type if synthesis.message_type != "unknown" else "urgent", "trusted time-critical update"
    if features.promotion_opt_out and synthesis.message_type in {"promotion", "spam"}:
        return "mute", synthesis.message_type, "promotion opt-out or repeated dismissal"
    if features.fatigue >= 0.72 and synthesis.message_type in {"promotion", "forward", "spam", "business_update"}:
        return "mute", synthesis.message_type, "severe notification fatigue"
    if safety.verdict == "suspicious" and "chain_or_excessive_forwarding" in safety.signals and (features.repeated or features.fatigue >= 0.45 or features.group_muted):
        return "mute", synthesis.message_type if synthesis.message_type != "unknown" else safety.message_type, "repeated forwarding pattern"
    if safety.verdict == "suspicious" and safety.message_type == "spam" and features.fatigue >= 0.65:
        return "mute", "spam", "reported sender and repeated dismissal"
    if synthesis.urgency_level == "high":
        if features.in_quiet_hours or features.relative_load >= 0.72 or safety.verdict == "suspicious":
            return "digest", synthesis.message_type, "urgent but queued by quiet hours, load, or risk"
        return "notify", synthesis.message_type, "useful urgent content"
    if safety.verdict == "suspicious":
        return "digest", safety.message_type if safety.message_type != "unknown" else synthesis.message_type, "suspicious but not decisive"
    if synthesis.ambiguous:
        return "digest", synthesis.message_type, "ambiguous content"
    return "digest", synthesis.message_type, "safe non-urgent content"
