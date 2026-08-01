from __future__ import annotations


def resolve(safety, features, synthesis) -> tuple[str, str, str]:
    if safety.verdict == "high_risk":
        return "mute", "scam", "hard safety risk"
    if (
        safety.verdict == "safe"
        and synthesis.direct_mention
        and synthesis.urgency_level == "high"
        and features.trust >= 0.45
    ):
        return "notify", synthesis.message_type if synthesis.message_type != "unknown" else "urgent", "trusted critical direct mention"
    if features.promotion_opt_out and synthesis.message_type == "promotion":
        return "mute", "promotion", "promotion opt-out or repeated dismissal"
    if features.fatigue >= 0.72 and synthesis.message_type in {"promotion", "forward", "spam", "business_update"}:
        return "mute", synthesis.message_type, "severe notification fatigue"
    if synthesis.urgency_level == "high":
        if features.in_quiet_hours or features.relative_load >= 0.72 or safety.verdict == "suspicious":
            return "digest", synthesis.message_type, "urgent but queued by quiet hours, load, or risk"
        return "notify", synthesis.message_type, "useful urgent content"
    if safety.verdict == "suspicious":
        return "digest", safety.message_type if safety.message_type != "unknown" else synthesis.message_type, "suspicious but not decisive"
    if synthesis.ambiguous:
        return "digest", synthesis.message_type, "ambiguous content"
    return "digest", synthesis.message_type, "safe non-urgent content"
