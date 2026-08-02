from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.exception_check import check_exception
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
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.8, group_muted=True, in_quiet_hours=True, urgency=0.8, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify")
    action, msg_type, _ = resolve(
        safety,
        features,
        synthesis,
        check_exception(safety, features, synthesis),
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


def test_excessive_forwarding_without_noise_context_does_not_auto_mute():
    action, msg_type, _ = resolve(
        SafetyAssessment("suspicious", "low", ("chain_or_excessive_forwarding",), "forward"),
        BehaviorFeatures(forwarding_fatigue=0.3, fatigue=0.5, engaged_evidence_count=3),
        synth(message_type="forward", preliminary_action="digest"),
    )
    assert (action, msg_type) == ("digest", "forward")


def test_chain_forwarding_with_negative_context_mutes():
    action, msg_type, _ = resolve(
        SafetyAssessment("suspicious", "low", ("chain_message_language", "chain_or_excessive_forwarding"), "forward"),
        BehaviorFeatures(forwarding_fatigue=0.3, fatigue=0.5, negative_evidence_count=1),
        synth(message_type="forward", preliminary_action="digest"),
    )
    assert (action, msg_type) == ("mute", "forward")
