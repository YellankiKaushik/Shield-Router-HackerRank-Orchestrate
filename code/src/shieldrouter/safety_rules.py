from __future__ import annotations

import re

from .normalize import extract_domains, lower_text
from .schemas import SafetyAssessment


CREDENTIAL_RE = re.compile(r"\b(otp|pin|password|passcode|login code|verification code|6 digit|six digit|cvv|card number|account number|upi pin)\b", re.I)
REQUEST_RE = re.compile(r"\b(reply|send|share|enter|provide|confirm|verify|submit)\b", re.I)
PRESSURE_RE = re.compile(r"\b(expire|expires|blocked|suspend|locked|urgent|immediately|act now|today|release|refund|reward|prize|claim)\b", re.I)
PAYMENT_RE = re.compile(r"\b(pay|payment|qr|scan|upi|reattempt fee|fee|transfer|deposit|bank)\b", re.I)
INJECTION_RE = re.compile(r"\b(ignore previous instructions|system prompt|mark this notify|override|developer message|you are chatgpt|router instruction)\b", re.I)
CHAIN_RE = re.compile(r"\b(forward to|share with 10|send to 10|good luck|bad luck|chain message)\b", re.I)
SHORTENER_OR_ODD_DOMAIN_RE = re.compile(r"\b(bit\.ly|tinyurl|t\.co|goo\.gl|rebrand\.ly|free|claim|verify|secure|delivery|refund|pay)\b", re.I)


def assess_safety(row: dict[str, str], business: dict[str, str] | None = None) -> SafetyAssessment:
    text = row.get("message_text", "")
    low = lower_text(text)
    forwarded = int(float(row.get("forwarded_count") or 0))
    domains = extract_domains(text)
    signals: list[str] = []
    if INJECTION_RE.search(low):
        signals.append("prompt_injection_text")
    if CREDENTIAL_RE.search(low):
        signals.append("credential_or_login_code_request")
    if CREDENTIAL_RE.search(low) and REQUEST_RE.search(low):
        signals.append("credential_request_with_instruction")
    if PRESSURE_RE.search(low) and (CREDENTIAL_RE.search(low) or PAYMENT_RE.search(low)):
        signals.append("urgency_pressure")
    if PAYMENT_RE.search(low) and ("qr" in low or "scan" in low or "reattempt fee" in low):
        signals.append("payment_or_qr_pressure")
    if CHAIN_RE.search(low) or forwarded >= 5:
        signals.append("chain_or_excessive_forwarding")
    if domains:
        official = (business or {}).get("official_domain", "").casefold()
        used = (business or {}).get("domain_used_by_sender", "").casefold()
        for domain in domains:
            if SHORTENER_OR_ODD_DOMAIN_RE.search(domain):
                signals.append(f"suspicious_domain:{domain}")
            if official and domain not in {official, used} and not domain.endswith("." + official):
                signals.append(f"mismatched_domain:{domain}")
    if business:
        verified = business.get("verified", "") == "1"
        reports = int(float(business.get("user_reports_30d") or 0))
        if not verified and any(word in low for word in ("bank", "account", "card", "payment", "refund")):
            signals.append("unverified_financial_sender")
        if reports >= 15:
            signals.append("sender_report_history")

    high = any(
        s in signals
        for s in (
            "credential_request_with_instruction",
            "prompt_injection_text",
            "payment_or_qr_pressure",
            "unverified_financial_sender",
        )
    ) and any("credential" in s or "payment" in s or "domain" in s or "injection" in s for s in signals)
    if high or any(s.startswith("mismatched_domain") for s in signals) and ("credential" in " ".join(signals) or PRESSURE_RE.search(low)):
        return SafetyAssessment("high_risk", "high", tuple(dict.fromkeys(signals)), "scam")
    if signals:
        msg_type = "spam" if "chain_or_excessive_forwarding" in signals else "scam"
        return SafetyAssessment("suspicious", "low", tuple(dict.fromkeys(signals)), msg_type)
    return SafetyAssessment("safe", "none", (), "unknown")
