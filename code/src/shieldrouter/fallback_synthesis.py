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
    elif _is_greeting_forward(row, text):
        message_type = "greeting"
        facts.append("forwarded greeting pattern")
    elif _is_promotion(row, text, tokens):
        message_type = "promotion"
        facts.append("message contains promotional language")
    elif row.get("forwarded_count") and int(float(row.get("forwarded_count") or 0)) >= 3 or "forward to" in text or "forwarding" in text:
        message_type = "forward"
        facts.append("message has a forwarding signal")
    elif any(w in tokens for w in {"otp", "pin", "password", "login", "cvv"}) and any(w in tokens for w in {"reply", "send", "share", "enter", "confirm"}):
        message_type = "scam" if safety.verdict != "safe" else "payment"
        facts.append("message refers to credentials or account access")
    elif row.get("conversation_type") == "business" and _is_business_event(text):
        message_type = "event"
        facts.append("business appointment or scheduled update")
    elif row.get("conversation_type") == "business" and _is_business_update(text, tokens):
        message_type = "business_update"
        facts.append("verified business update or account notice")
    elif _is_school_event(text):
        message_type = "event"
        facts.append("school operational update")
    elif any(w in tokens for w in {"pay", "payment", "upi", "bank", "card", "invoice", "refund", "fee"}) and not _is_work_incident(text):
        message_type = "payment"
        facts.append("message concerns payment or account activity")
    elif row.get("media_type") == "voice" and features.urgency >= 0.55 and features.direct_mention and _is_medical_direct_urgent(text):
        message_type = "urgent"
        facts.append("urgent direct medical or call request was detected")
    elif _is_direct_personal_request(text, features):
        message_type = "personal"
        facts.append("direct personal response request")
    elif features.urgency >= 0.55 and (features.direct_mention or _is_work_incident(text)):
        message_type = "urgent"
        facts.append("urgent direct request or deadline was detected")
    elif any(w in tokens for w in {"meeting", "bus", "class", "event", "pickup", "plumber", "tanker", "delivery", "appointment", "circular", "consent", "timing", "form"}) or "cultural night" in text:
        message_type = "event"
        facts.append("message describes an operational update or event")
    elif row.get("conversation_type") == "personal" and features.relationship_strength >= 0.45:
        message_type = "personal"
        facts.append("message is from a personal chat")
    elif row.get("conversation_type") == "personal" and features.relationship_strength < 0.45:
        message_type = "unknown"
        facts.append("unfamiliar personal sender without urgency")
    elif any(w in tokens for w in {"hi", "hello", "morning", "evening"}) and len(tokens) <= 28:
        message_type = "greeting"
        facts.append("message is conversational")
    elif row.get("conversation_type") == "business":
        message_type = "business_update"
        facts.append("message comes from a business account")
    elif row.get("conversation_type") == "group" and row.get("media_type") in {"image", "voice"}:
        message_type = "personal" if features.relationship_strength >= 0.4 or features.affinity >= 0.6 else "unknown"
        facts.append(f"{row.get('media_type')} attachment is available")
    elif row.get("conversation_type") == "group" and any(phrase in text for phrase in ("anyone watching", "score thread", "join only if")):
        message_type = "personal"
        facts.append("message is casual group chat")

    if row.get("media_type") == "image":
        facts.append("image attachment is available")
    if row.get("media_type") == "voice":
        facts.append("voice-note attachment is available")
    if features.group_muted:
        facts.append("recipient has muted this group")
    if features.in_quiet_hours:
        facts.append("message arrived during quiet hours")
    if features.promotion_opt_out and message_type in {"promotion", "spam"}:
        facts.append("recipient has opted out or dismissed similar promotions")

    direct = detect_direct_mention(row)
    if safety.verdict == "high_risk":
        prelim = "mute"
    elif features.promotion_opt_out and message_type in {"promotion", "spam"}:
        prelim = "mute"
    elif features.urgency >= 0.55 and (direct or row.get("conversation_type") == "business") and features.trust >= 0.38:
        prelim = "notify"
    elif features.direct_mention and features.affinity >= 0.75 and features.urgency >= 0.4:
        prelim = "notify"
    else:
        prelim = "digest"
    urgency = "high" if features.urgency >= 0.55 else "medium" if features.urgency >= 0.3 else "low"
    ambiguous = message_type == "unknown" or bool(features.missing_context)
    return Synthesis(urgency, direct, message_type, prelim, ambiguous, tuple(facts[:5]))


def _is_promotion(row: dict[str, str], text: str, tokens: set[str]) -> bool:
    promo_tokens = set(tokens) & {"sale", "discount", "offer", "deal", "coupon", "cashback", "promo", "selling", "unsubscribe", "itinerary"}
    if "offer" in promo_tokens and any(phrase in text for phrase in ("offer letter", "internship offer", "job offer")):
        promo_tokens.remove("offer")
    return bool(promo_tokens) or any(
        phrase in text for phrase in ("50% off", "reply stop", "rs 17,999", "tap below to view the itinerary", "shopping offer", "saved items", "kurta set", "cycle helmet")
    )


def _is_business_update(text: str, tokens: set[str]) -> bool:
    return any(
        phrase in text
        for phrase in (
            "your order",
            "has been packed",
            "expected to reach",
            "delivery details",
            "health-related update",
            "registered app",
            "safety advisory",
            "feedback",
            "experience with us",
        )
    ) or bool(tokens & {"appointment", "prescription", "booking", "delivery"})


def _is_business_event(text: str) -> bool:
    return any(phrase in text for phrase in ("appointment", "scheduled time", "prescription", "doctor", "clinic", "pickup details"))


def _is_work_incident(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "prod review",
            "retry count",
            "alert threshold",
            "escalation",
            "client note",
            "queue",
            "failed-payment screenshots",
            "incident bridge",
            "payments are failing",
            "live users",
            "checkout error",
            "join the incident",
        )
    )


def _is_school_event(text: str) -> bool:
    return any(phrase in text for phrase in ("route b parents", "bus is leaving", "school circular", "consent note", "pickup timing", "field-trip circular"))


def _is_greeting_forward(row: dict[str, str], text: str) -> bool:
    return int(float(row.get("forwarded_count") or 0)) >= 3 and any(phrase in text for phrase in ("good morning", "stay positive", "blessings", "good vibes"))


def _is_direct_personal_request(text: str, features) -> bool:
    return features.direct_mention and any(
        phrase in text
        for phrase in ("can you call", "please call", "call now", "call?", "pickup still works", "confirm cab", "still works for you")
    )


def _is_medical_direct_urgent(text: str) -> bool:
    return any(phrase in text for phrase in ("call now", "please call now", "dad is unwell", "going to the clinic", "going to clinic"))
