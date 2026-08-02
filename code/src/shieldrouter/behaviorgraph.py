from __future__ import annotations

from datetime import time

from .io import parse_bool, parse_datetime, parse_int
from .normalize import lower_text, tokenize
from .retrieval import highest_user_history_similarity
from .schemas import BehaviorFeatures, EvidenceCandidate


URGENT_WORDS = {
    "urgent",
    "asap",
    "immediately",
    "today",
    "now",
    "deadline",
    "eod",
    "leaving",
    "expire",
    "expires",
    "blocked",
    "wait",
    "needed",
    "need",
    "emergency",
    "minutes",
    "confirm",
    "scheduled",
    "appointment",
    "pickup",
    "consent",
    "timing",
    "review",
    "escalation",
    "threshold",
    "unwell",
    "clinic",
}
PROMO_WORDS = {"sale", "discount", "offer", "coupon", "deal", "flat", "cashback", "limited", "promo"}


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def _parse_window(window: str) -> tuple[time, time] | None:
    try:
        start_s, end_s = window.split("-", 1)
        sh, sm = [int(x) for x in start_s.split(":", 1)]
        eh, em = [int(x) for x in end_s.split(":", 1)]
        return time(sh, sm), time(eh, em)
    except Exception:
        return None


def in_quiet_hours(created_at: str, window: str) -> bool:
    dt = parse_datetime(created_at)
    parsed = _parse_window(window)
    if dt is None or parsed is None:
        return False
    current = dt.time()
    start, end = parsed
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def detect_direct_mention(row: dict[str, str]) -> bool:
    text = lower_text(row.get("message_text", ""))
    user_id = row.get("user_id", "").casefold()
    if user_id and f"@{user_id}" in text:
        return True
    if row.get("conversation_type") == "personal":
        return True
    phrases = [
        "can you",
        "need you",
        "your child",
        "your flat",
        "your account",
        "please reply",
        "pls reply",
        "reply once",
    ]
    if row.get("media_type") == "voice":
        phrases.extend(["please call", "call now"])
    return any(
        phrase in text
        for phrase in phrases
    )


def urgency_score(row: dict[str, str]) -> float:
    tokens = set(tokenize(row.get("message_text", "")))
    text = lower_text(row.get("message_text", ""))
    score = 0.0
    score += min(0.5, 0.1 * len(tokens & URGENT_WORDS))
    if detect_direct_mention(row):
        score += 0.25
    if any(x in text for x in ("15 mins", "20 mins", "before eod", "by 7", "expire today", "expires today", "in 20 minutes", "before the scheduled time", "before tomorrow morning", "before i confirm")):
        score += 0.25
    if row.get("media_type") == "voice" and any(x in text for x in ("call now", "please call now", "dad is unwell", "going to the clinic", "going to clinic")):
        score += 0.35
    if row.get("conversation_type") == "business" and any(x in text for x in ("expected to reach", "local hub today", "has been packed", "packed and", "appointment", "scheduled time", "prescription", "claim", "pickup details", "booking")):
        score += 0.45
    if row.get("conversation_type") == "group" and any(x in text for x in ("school circular", "field-trip", "pickup timing", "consent note", "bus is leaving", "water now", "motor room", "plumber")):
        score += 0.25
    if row.get("conversation_type") == "group" and any(x in text for x in ("school circular", "consent note", "timing and consent")):
        score += 0.15
    if row.get("conversation_type") == "group" and any(
        x in text for x in ("incident bridge", "payments are failing", "live users", "checkout error", "join the incident")
    ):
        score += 0.45
    return _bounded(score)


def novelty_score(row: dict[str, str], idx) -> tuple[float, float]:
    if not tokenize(row.get("message_text", "")):
        return 0.5, 0.0
    history = idx.history_by_user.get(row.get("user_id", ""), [])
    if not history:
        return 0.5, 0.0
    highest = highest_user_history_similarity(row, idx)
    return _bounded(1.0 - highest), highest


def transaction_strength(row: dict[str, str], ubh: dict[str, str]) -> tuple[bool, float]:
    if row.get("conversation_type") != "business" or not row.get("business_id") or not ubh:
        return False, 0.0
    known = lower_text(ubh.get("why_user_knows_account", ""))
    transaction_terms = {
        "order",
        "delivery",
        "booking",
        "payment",
        "bill",
        "wallet",
        "account",
        "appointment",
        "clinic",
        "pickup",
        "maintenance",
        "card",
        "utility",
        "travel",
    }
    matched_terms = sum(1 for term in transaction_terms if term in known)
    activity = parse_int(ubh.get("activity_count_180d"))
    opened = parse_int(ubh.get("messages_opened_30d"))
    replied = parse_int(ubh.get("messages_replied_30d"))
    dismissed = parse_int(ubh.get("messages_dismissed_30d"))
    score = 0.0
    if matched_terms:
        score += min(0.45, 0.18 * matched_terms)
    if any(term in known for term in ("recent", "active", "confirmed", "upcoming", "expected", "monthly", "frequent")):
        score += 0.18
    if ubh.get("last_activity_at"):
        score += 0.08
    if ubh.get("last_reply_at"):
        score += 0.08
    score += min(0.18, activity * 0.03)
    score += min(0.12, (opened + 2 * replied) * 0.015)
    score -= min(0.12, dismissed * 0.02)
    score = _bounded(score)
    return score >= 0.35, score


def forwarding_fatigue_contribution(row: dict[str, str], has_negative_context: bool = False) -> float:
    count = max(0, parse_int(row.get("forwarded_count")))
    if count == 0:
        return 0.0
    raw = min(0.30, count * 0.06)
    if count == 1:
        return round(raw, 4)
    if has_negative_context or count >= 5:
        return round(raw, 4)
    return round(min(raw, 0.12), 4)


def build_features(row: dict[str, str], idx, evidence: list[EvidenceCandidate], media_error: str = "") -> BehaviorFeatures:
    user = idx.users.get(row.get("user_id", ""), {})
    group = idx.groups.get(row.get("group_id", ""), {})
    membership = idx.memberships.get((row.get("group_id", ""), row.get("user_id", "")), {})
    business = idx.business_accounts.get(row.get("business_id", ""), {})
    ubh = idx.user_business.get((row.get("user_id", ""), row.get("business_id", "")), {})
    missing: list[str] = []
    for label, condition in [
        ("user", not user),
        ("group", row.get("group_id") and not group),
        ("membership", row.get("group_id") and not membership),
        ("business", row.get("business_id") and not business),
        ("user_business_history", row.get("business_id") and not ubh),
    ]:
        if condition:
            missing.append(label)

    opened = parse_int(user.get("messages_opened_30d"))
    replied = parse_int(user.get("messages_replied_30d"))
    dismissed = parse_int(user.get("notifications_dismissed_30d"))
    reported = parse_int(user.get("messages_reported_30d"))
    user_affinity = (opened + 2 * replied) / max(1, opened + replied + dismissed + reported)

    same_sender_history = sum(
        1
        for hist in idx.history_by_user.get(row.get("user_id", ""), [])
        if row.get("sender_user_id") and hist.get("sender_user_id") == row.get("sender_user_id")
    )
    trust = 0.2
    if row.get("conversation_type") == "personal":
        trust += 0.35 if same_sender_history else 0.08
    if membership.get("role") == "admin":
        trust += 0.2
    if group.get("group_type") in {"family", "school_group", "work", "society"}:
        trust += 0.12
    if business:
        trust += 0.28 if business.get("verified") == "1" else -0.1
        trust -= min(0.3, parse_int(business.get("user_reports_30d")) / 50)
    if ubh:
        trust += min(0.25, parse_int(ubh.get("activity_count_180d")) / 40)
    transaction_relationship, transaction_value = transaction_strength(row, ubh)
    if transaction_relationship:
        trust += min(0.12, transaction_value * 0.12)

    ubh_open = parse_int(ubh.get("messages_opened_30d"))
    ubh_reply = parse_int(ubh.get("messages_replied_30d"))
    ubh_dismiss = parse_int(ubh.get("messages_dismissed_30d"))
    group_read = parse_int(membership.get("messages_read_30d"))
    group_reply = parse_int(membership.get("replies_sent_30d"))
    group_dismiss = parse_int(membership.get("notifications_dismissed_30d"))
    affinity = _bounded(0.2 + user_affinity * 0.3 + (ubh_open + 2 * ubh_reply + group_read + 2 * group_reply) / max(1, 20 + ubh_dismiss + group_dismiss))

    promotion_opt_out = bool(ubh and (ubh.get("allows_promotions") == "0" or bool(ubh.get("promotions_opted_out_at"))))
    evidence_dismissed = 0
    evidence_engaged = 0
    for candidate in evidence:
        event = idx.events.get(candidate.message_id, {})
        if event.get("notification_dismissed") == "1" or event.get("muted_after_message") == "1" or event.get("message_reported") == "1":
            evidence_dismissed += 1
        if event.get("message_opened") == "1" or event.get("message_replied") == "1":
            evidence_engaged += 1
    looks_promotional = _looks_promotional(row)
    forwarding_fatigue = forwarding_fatigue_contribution(
        row,
        has_negative_context=bool(
            evidence_dismissed
            or group_dismiss
            or promotion_opt_out
            or looks_promotional
            or parse_int(row.get("forwarded_count")) >= 5
        ),
    )
    fatigue = _bounded(
        (dismissed / max(1, opened + dismissed + 10))
        + (ubh_dismiss / 12)
        + (group_dismiss / 18)
        + (0.35 if promotion_opt_out and looks_promotional else 0)
        + (0.28 if evidence_dismissed and looks_promotional else 0)
        + (0.18 if evidence_dismissed >= 2 and parse_int(row.get("forwarded_count")) >= 3 else 0)
        + forwarding_fatigue
        - (0.08 if evidence_engaged and not looks_promotional else 0)
    )

    daily = idx.daily_by_user.get(row.get("user_id", ""), [])
    if daily:
        avg_sent = sum(parse_int(r.get("notifications_sent")) for r in daily) / len(daily)
        avg_dismissed = sum(parse_int(r.get("notifications_dismissed")) for r in daily) / len(daily)
        relative_load = _bounded((avg_sent / 10) * 0.7 + (avg_dismissed / max(1, avg_sent)) * 0.3)
    else:
        relative_load = 0.0
        missing.append("daily_notification_summary")
    novelty, highest_similarity = novelty_score(row, idx)
    urgency = urgency_score(row)
    if transaction_relationship and any(
        phrase in lower_text(row.get("message_text", ""))
        for phrase in ("today", "tomorrow", "changed", "expected", "scheduled", "appointment", "pickup", "payment update", "booking", "delivery")
    ):
        urgency = _bounded(urgency + min(0.12, transaction_value * 0.12))

    return BehaviorFeatures(
        trust=_bounded(trust),
        affinity=affinity,
        fatigue=fatigue,
        novelty=novelty,
        highest_history_similarity=highest_similarity,
        transaction_relationship=transaction_relationship,
        transaction_strength=transaction_value,
        forwarding_fatigue=forwarding_fatigue,
        negative_evidence_count=evidence_dismissed,
        engaged_evidence_count=evidence_engaged,
        promotion_opt_out=promotion_opt_out,
        relationship_strength=_bounded((trust + affinity) / 2),
        group_muted=parse_bool(membership.get("group_muted_by_user")),
        group_role=membership.get("role", ""),
        sender_is_admin_context=membership.get("role") == "admin" or "admin" in lower_text(row.get("message_text", "")),
        in_quiet_hours=in_quiet_hours(row.get("created_at", ""), user.get("do_not_disturb_window", "")),
        relative_load=relative_load,
        urgency=urgency,
        direct_mention=detect_direct_mention(row),
        repeated=bool(evidence and evidence[0].score >= 0.45),
        missing_context=tuple(missing),
        media_available=bool(row.get("media_type") and not media_error),
        media_error=media_error,
    )


def _looks_promotional(row: dict[str, str]) -> bool:
    tokens = set(tokenize(row.get("message_text", "")))
    text = lower_text(row.get("message_text", ""))
    return bool(tokens & PROMO_WORDS) or any(
        phrase in text for phrase in ("reply stop", "unsubscribe", "50% off", "shopping offer", "cashback", "sale", "discount", "coupon", "deal")
    )
