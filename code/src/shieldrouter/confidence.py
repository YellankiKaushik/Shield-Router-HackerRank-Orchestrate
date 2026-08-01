from __future__ import annotations


def calibrate_confidence(action: str, safety, features, synthesis, evidence: list, errors: list[str]) -> float:
    score = 0.48
    if safety.verdict == "high_risk":
        score += 0.25
    elif safety.verdict == "safe":
        score += 0.08
    if synthesis.preliminary_action == action:
        score += 0.1
    if synthesis.urgency_level in {"high", "low"}:
        score += 0.05
    if evidence:
        score += min(0.08, evidence[0].score * 0.08)
    if features.trust >= 0.65 or features.fatigue >= 0.72 or features.promotion_opt_out:
        score += 0.05
    if features.media_available:
        score += 0.03
    if synthesis.ambiguous:
        score -= 0.08
    if features.missing_context:
        score -= min(0.08, 0.02 * len(features.missing_context))
    if features.media_error:
        score -= 0.04
    if errors:
        score -= 0.08
    return round(max(0.2, min(0.95, score)), 4)
