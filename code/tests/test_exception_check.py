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


def test_high_risk_direct_mention_is_blocked():
    safety = SafetyAssessment("high_risk", "high", ("credential_request",), "scam")
    features = BehaviorFeatures(trust=1, affinity=1, group_muted=True, urgency=1, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert exception.blocked_by_safety
    assert not exception.eligible_for_notify
    assert resolve(safety, features, synthesis, exception)[:2] == ("mute", "scam")


def test_trusted_urgent_direct_mention_in_muted_group_is_exception_eligible():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.8, group_muted=True, urgency=0.8, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert exception.eligible_for_notify
    assert resolve(safety, features, synthesis, exception)[0] == "notify"


def test_untrusted_urgent_message_in_muted_group_is_not_exception_eligible():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.2, affinity=0.1, group_muted=True, urgency=0.8, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert not exception.eligible_for_notify
    assert resolve(safety, features, synthesis, exception)[0] == "digest"


def test_ordinary_direct_personal_message_does_not_need_group_exception():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.7, affinity=0.8, group_muted=False, urgency=0.45, direct_mention=True)
    synthesis = synth(urgency_level="medium", direct_mention=True, message_type="personal", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert exception.reason == "not_required_non_muted_group"
    assert not exception.eligible_for_notify
    assert resolve(safety, features, synthesis, exception)[0] == "notify"


def test_promotional_act_now_language_does_not_trigger_exception():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.9, affinity=0.9, group_muted=True, urgency=0.8, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="promotion", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert not exception.critical_urgency
    assert not exception.eligible_for_notify
    assert resolve(safety, features, synthesis, exception)[0] == "digest"


def test_quiet_hours_critical_exception_can_notify():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.8, group_muted=True, in_quiet_hours=True, urgency=0.8, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert exception.eligible_for_notify
    assert resolve(safety, features, synthesis, exception)[0] == "notify"


def test_quiet_hours_noncritical_message_downgrades():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.8, group_muted=False, in_quiet_hours=True, urgency=0.4, direct_mention=True)
    synthesis = synth(urgency_level="medium", direct_mention=True, message_type="personal", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert not exception.eligible_for_notify
    action, _, _ = resolve(safety, features, synthesis, exception)
    assert action == "digest"


def test_missing_group_context_does_not_require_exception():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.7, urgency=0.8, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert exception.reason == "not_required_non_muted_group"
    assert not exception.eligible_for_notify


def test_non_muted_group_does_not_require_exception():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.7, group_muted=False, urgency=0.8, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert exception.reason == "not_required_non_muted_group"
    assert not exception.eligible_for_notify


def test_exception_check_is_deterministic():
    safety = SafetyAssessment("safe", "none")
    features = BehaviorFeatures(trust=0.7, group_muted=True, urgency=0.8, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="urgent", preliminary_action="notify")
    assert check_exception(safety, features, synthesis) == check_exception(safety, features, synthesis)


def test_transaction_context_cannot_override_high_risk():
    safety = SafetyAssessment("high_risk", "high", ("payment_or_qr_pressure",), "scam")
    features = BehaviorFeatures(transaction_relationship=True, transaction_strength=1, trust=1, group_muted=True, urgency=1, direct_mention=True)
    synthesis = synth(urgency_level="high", direct_mention=True, message_type="payment", preliminary_action="notify")
    exception = check_exception(safety, features, synthesis)
    assert not exception.eligible_for_notify
    assert resolve(safety, features, synthesis, exception)[:2] == ("mute", "scam")
