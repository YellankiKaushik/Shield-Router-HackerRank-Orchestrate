from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.resolver import resolve
from shieldrouter.schemas import BehaviorFeatures, SafetyAssessment, Synthesis


def synth(**kwargs):
    base = dict(urgency_level="low", direct_mention=False, message_type="personal", preliminary_action="digest", ambiguous=False)
    base.update(kwargs)
    return Synthesis(**base)


def test_high_risk_mutes_even_when_trusted():
    action, msg_type, _ = resolve(
        SafetyAssessment("high_risk", "high", ("credential_request",), "scam"),
        BehaviorFeatures(trust=1, affinity=1, urgency=1, direct_mention=True),
        synth(urgency_level="high", direct_mention=True, preliminary_action="notify"),
    )
    assert (action, msg_type) == ("mute", "scam")


def test_muted_group_trusted_urgent_direct_mention_notifies():
    action, msg_type, _ = resolve(
        SafetyAssessment("safe", "none"),
        BehaviorFeatures(trust=0.8, group_muted=True, in_quiet_hours=True, urgency=0.8, direct_mention=True),
        synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify"),
    )
    assert (action, msg_type) == ("notify", "urgent")


def test_promotion_opt_out_mutes():
    action, msg_type, _ = resolve(
        SafetyAssessment("safe", "none"),
        BehaviorFeatures(promotion_opt_out=True, fatigue=0.8),
        synth(message_type="promotion", preliminary_action="mute"),
    )
    assert (action, msg_type) == ("mute", "promotion")


def test_quiet_hours_soft_downgrade_to_digest():
    action, _, _ = resolve(
        SafetyAssessment("safe", "none"),
        BehaviorFeatures(trust=0.3, in_quiet_hours=True, urgency=0.8, direct_mention=False),
        synth(urgency_level="high", direct_mention=False, message_type="event", preliminary_action="notify"),
    )
    assert action == "digest"


def test_critical_trusted_direct_urgency_overrides_quiet_hours():
    action, _, _ = resolve(
        SafetyAssessment("safe", "none"),
        BehaviorFeatures(trust=0.7, in_quiet_hours=True, urgency=0.8, direct_mention=True),
        synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify"),
    )
    assert action == "notify"
