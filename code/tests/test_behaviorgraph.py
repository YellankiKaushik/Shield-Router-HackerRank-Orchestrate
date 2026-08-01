from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.behaviorgraph import (
    build_features,
    detect_direct_mention,
    forwarding_fatigue_contribution,
    in_quiet_hours,
    novelty_score,
)
from shieldrouter.schemas import EvidenceCandidate


def test_quiet_hours_wraparound():
    assert in_quiet_hours("2026-07-30 22:19", "22:00-07:00")
    assert not in_quiet_hours("2026-07-30 12:19", "22:00-07:00")


def test_direct_mention_detects_user_id_and_request():
    assert detect_direct_mention({"message_text": "@u_010 can you join now", "user_id": "u_010", "conversation_type": "group"})
    assert detect_direct_mention({"message_text": "Can you reply once", "user_id": "u_010", "conversation_type": "group"})


def idx(**overrides):
    base = dict(
        users={"u1": {"messages_opened_30d": "3", "messages_replied_30d": "1", "notifications_dismissed_30d": "0", "messages_reported_30d": "0", "do_not_disturb_window": ""}},
        groups={},
        memberships={},
        business_accounts={},
        user_business={},
        history={},
        history_by_user={},
        events={},
        daily_by_user={"u1": [{"notifications_sent": "2", "notifications_dismissed": "0"}]},
        images={},
        voices={},
        dataset_dir=Path("."),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def row(**overrides):
    base = dict(
        message_id="m1",
        user_id="u1",
        conversation_type="personal",
        group_id="",
        business_id="",
        sender_user_id="s1",
        created_at="2026-07-30 10:00",
        message_text="Please confirm the pickup timing today",
        media_type="",
        media_id="",
        forwarded_count="0",
    )
    base.update(overrides)
    return base


def test_novelty_repeated_message_is_low():
    history = [dict(row(message_id="h1", message_text="Please confirm the pickup timing today"))]
    novelty, highest = novelty_score(row(), idx(history_by_user={"u1": history}))
    assert novelty <= 0.01
    assert highest >= 0.99


def test_novelty_semantically_similar_message_is_lower_than_novel():
    history = [dict(row(message_id="h1", message_text="Confirm pickup timing today please"))]
    similar, similarity = novelty_score(row(), idx(history_by_user={"u1": history}))
    novel, _ = novelty_score(row(message_text="Concert poster discount sale weekend"), idx(history_by_user={"u1": history}))
    assert 0 <= similar < novel <= 1
    assert similarity > 0.4


def test_novelty_novel_message_is_high():
    history = [dict(row(message_id="h1", message_text="Society water tanker update"))]
    novelty, highest = novelty_score(row(message_text="Concert poster discount sale weekend"), idx(history_by_user={"u1": history}))
    assert novelty == 1.0
    assert highest == 0.0


def test_novelty_no_user_history_is_neutral():
    novelty, highest = novelty_score(row(), idx(history_by_user={}))
    assert novelty == 0.5
    assert highest == 0.0


def test_novelty_empty_content_is_neutral():
    history = [dict(row(message_id="h1", message_text="Please confirm the pickup timing today"))]
    novelty, highest = novelty_score(row(message_text=""), idx(history_by_user={"u1": history}))
    assert novelty == 0.5
    assert highest == 0.0


def test_novelty_ignores_other_users_history():
    other_history = [dict(row(message_id="h1", user_id="u2", message_text="Please confirm the pickup timing today"))]
    novelty, highest = novelty_score(row(), idx(history_by_user={"u2": other_history}))
    assert novelty == 0.5
    assert highest == 0.0


def test_behaviorgraph_value_boundaries():
    features = build_features(row(), idx(), [])
    for value in (
        features.trust,
        features.affinity,
        features.fatigue,
        features.novelty,
        features.highest_history_similarity,
        features.transaction_strength,
        features.forwarding_fatigue,
        features.relationship_strength,
        features.relative_load,
        features.urgency,
    ):
        assert 0 <= value <= 1


def test_verified_business_without_history_is_not_transactional():
    features = build_features(
        row(conversation_type="business", business_id="biz", sender_user_id=""),
        idx(business_accounts={"biz": {"verified": "1", "user_reports_30d": "0"}}),
        [],
    )
    assert not features.transaction_relationship
    assert features.transaction_strength == 0.0


def test_recent_order_booking_payment_context_is_transactional():
    business_history = {("u1", "biz"): {"why_user_knows_account": "recent_card_payment", "last_activity_at": "2026-07-29 10:00", "activity_count_180d": "4", "messages_opened_30d": "3", "messages_replied_30d": "1", "messages_dismissed_30d": "0", "last_reply_at": "2026-07-29 10:05"}}
    features = build_features(row(conversation_type="business", business_id="biz", sender_user_id="", message_text="Your payment update is available today"), idx(user_business=business_history), [])
    assert features.transaction_relationship
    assert features.transaction_strength >= 0.35


def test_transaction_context_can_increase_trust_or_urgency():
    no_history = build_features(row(conversation_type="business", business_id="biz", sender_user_id="", message_text="Your booking changed today"), idx(), [])
    business_history = {("u1", "biz"): {"why_user_knows_account": "confirmed_travel_booking", "last_activity_at": "2026-07-29 10:00", "activity_count_180d": "5", "messages_opened_30d": "4", "messages_replied_30d": "1", "messages_dismissed_30d": "0", "last_reply_at": "2026-07-29 10:05"}}
    with_history = build_features(row(conversation_type="business", business_id="biz", sender_user_id="", message_text="Your booking changed today"), idx(user_business=business_history), [])
    assert with_history.transaction_relationship
    assert with_history.trust > no_history.trust or with_history.urgency > no_history.urgency


def test_transaction_context_is_user_specific():
    business_history = {("u2", "biz"): {"why_user_knows_account": "recent_card_payment", "last_activity_at": "2026-07-29 10:00", "activity_count_180d": "8", "messages_opened_30d": "5", "messages_replied_30d": "1", "messages_dismissed_30d": "0", "last_reply_at": "2026-07-29 10:05"}}
    features = build_features(row(conversation_type="business", business_id="biz", sender_user_id=""), idx(user_business=business_history), [])
    assert not features.transaction_relationship


def test_forwarding_fatigue_zero_one_moderate_heavy():
    assert forwarding_fatigue_contribution(row(forwarded_count="0")) == 0.0
    assert forwarding_fatigue_contribution(row(forwarded_count="1")) == 0.06
    assert forwarding_fatigue_contribution(row(forwarded_count="3")) == 0.12
    assert forwarding_fatigue_contribution(row(forwarded_count="5"), has_negative_context=True) == 0.30


def test_legitimate_forwarded_event_is_not_automatically_muted():
    features = build_features(row(conversation_type="group", message_text="School circular pickup timing and consent note", forwarded_count="2"), idx(), [])
    assert features.forwarding_fatigue == 0.12
    assert features.fatigue < 0.72


def test_chain_forwarding_with_negative_history_has_stronger_fatigue():
    evidence = [EvidenceCandidate("h1", 0.7, "u1")]
    events = {"h1": {"notification_dismissed": "1", "muted_after_message": "1", "message_reported": "0"}}
    features = build_features(row(message_text="Forward to ten people for good luck", forwarded_count="5"), idx(events=events), evidence)
    assert features.forwarding_fatigue == 0.30
    assert features.fatigue >= 0.30
