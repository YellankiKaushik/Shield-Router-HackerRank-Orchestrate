from __future__ import annotations

from .behaviorgraph import detect_direct_mention
from .normalize import lower_text, tokenize
from .schemas import Synthesis


def synthesize(row: dict[str, str], safety, features) -> Synthesis:
    text = lower_text(row.get("message_text", ""))
    tokens = set(tokenize(text))
    facts: list[str] = []
    message_type = "unknown"
    if safety.message_type in {"scam", "spam"}:
        message_type = safety.message_type
        facts.append("safety rules found risky content")
    elif row.get("forwarded_count") and int(float(row.get("forwarded_count") or 0)) >= 3:
        message_type = "forward"
        facts.append("message has a forwarding signal")
    elif any(w in tokens for w in {"otp", "pin", "password", "login", "code", "cvv"}):
        message_type = "scam" if safety.verdict != "safe" else "payment"
        facts.append("message refers to credentials or account access")
    elif any(w in tokens for w in {"pay", "payment", "upi", "bank", "card", "invoice", "refund", "fee"}):
        message_type = "payment"
        facts.append("message concerns payment or account activity")
    elif any(w in tokens for w in {"sale", "discount", "offer", "deal", "coupon", "cashback", "promo"}):
        message_type = "promotion"
        facts.append("message contains promotional language")
    elif any(w in tokens for w in {"meeting", "bus", "class", "event", "pickup", "plumber", "tanker", "delivery", "appointment"}):
        message_type = "event"
        facts.append("message describes an operational update or event")
    elif any(w in tokens for w in {"hi", "hello", "morning", "evening", "checking"}):
        message_type = "greeting"
        facts.append("message is conversational")
    elif features.urgency >= 0.55:
        message_type = "urgent"
        facts.append("urgent wording or deadline was detected")
    elif row.get("conversation_type") == "business":
        message_type = "business_update"
        facts.append("message comes from a business account")
    elif row.get("conversation_type") == "personal":
        message_type = "personal"
        facts.append("message is from a personal chat")

    if row.get("media_type") == "image":
        facts.append("image attachment is available")
    if row.get("media_type") == "voice":
        facts.append("voice-note attachment is available")
    if features.group_muted:
        facts.append("recipient has muted this group")
    if features.in_quiet_hours:
        facts.append("message arrived during quiet hours")
    if features.promotion_opt_out:
        facts.append("recipient has opted out or dismissed similar promotions")

    direct = detect_direct_mention(row)
    if safety.verdict == "high_risk":
        prelim = "mute"
    elif features.promotion_opt_out and message_type == "promotion":
        prelim = "mute"
    elif features.urgency >= 0.55 and direct and features.trust >= 0.45:
        prelim = "notify"
    else:
        prelim = "digest"
    urgency = "high" if features.urgency >= 0.55 else "medium" if features.urgency >= 0.3 else "low"
    ambiguous = message_type == "unknown" or bool(features.missing_context)
    return Synthesis(urgency, direct, message_type, prelim, ambiguous, tuple(facts[:5]))
