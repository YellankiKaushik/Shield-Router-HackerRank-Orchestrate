from __future__ import annotations


def build_reason(action: str, rule_reason: str, safety, features, synthesis, evidence: list) -> str:
    bits: list[str] = []
    if safety.verdict == "high_risk":
        bits.append("Safety override")
        if safety.signals:
            bits.append(", ".join(safety.signals[:2]).replace("_", " "))
    elif rule_reason:
        bits.append(rule_reason)
    bits.extend(synthesis.facts[:3])
    if evidence:
        bits.append(f"similar prior message {evidence[0].message_id}")
    if features.media_error:
        bits.append("media reference issue handled conservatively")
    text = "; ".join(dict.fromkeys(b for b in bits if b))
    if not text:
        text = f"{action} selected by deterministic context rules"
    text = text[:220].rstrip(" ;,.")
    return text
