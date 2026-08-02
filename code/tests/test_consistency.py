from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.consistency import validate_and_repair_reason
from shieldrouter.schemas import BehaviorFeatures, EvidenceCandidate, SafetyAssessment, Synthesis


def synth(**kwargs):
    base = dict(urgency_level="low", direct_mention=False, message_type="personal", preliminary_action="digest", ambiguous=False)
    base.update(kwargs)
    return Synthesis(**base)


def test_high_risk_notify_contradiction_is_repaired():
    result = validate_and_repair_reason(
        action="notify",
        message_type="scam",
        reason="Safety override; credential request",
        safety=SafetyAssessment("high_risk", "high", ("credential_request",), "scam"),
        features=BehaviorFeatures(),
        synthesis=synth(message_type="scam"),
        evidence=[],
        resolver_rule="bad",
    )
    assert result.reason_repaired
    assert "high_risk_notify_contradiction" in result.detected_issue


def test_unselected_evidence_reference_is_reported():
    result = validate_and_repair_reason(
        action="digest",
        message_type="personal",
        reason="safe non-urgent content; similar prior message message_9999",
        safety=SafetyAssessment("safe", "none"),
        features=BehaviorFeatures(),
        synthesis=synth(),
        evidence=[EvidenceCandidate("message_0001", 0.5, "u1")],
        resolver_rule="safe non-urgent content",
    )
    assert result.reason_repaired
    assert "unselected_evidence_reference:message_9999" in result.detected_issue
    assert "message_0001" in result.final_reason


def test_repeated_dismissal_claim_requires_negative_selected_evidence():
    result = validate_and_repair_reason(
        action="mute",
        message_type="promotion",
        reason="promotion opt-out or repeated dismissal",
        safety=SafetyAssessment("safe", "none"),
        features=BehaviorFeatures(promotion_opt_out=False),
        synthesis=synth(message_type="promotion"),
        evidence=[EvidenceCandidate("message_0001", 0.5, "u1")],
        resolver_rule="promotion opt-out or repeated dismissal",
        events={"message_0001": {"message_opened": "1", "notification_dismissed": "0", "muted_after_message": "0", "message_reported": "0"}},
    )
    assert result.reason_repaired
    assert "repeated_dismissal_claim_without_evidence" in result.detected_issue


def test_grounded_reason_passes_without_repair():
    result = validate_and_repair_reason(
        action="digest",
        message_type="event",
        reason="safe non-urgent content; message describes an operational update or event; similar prior message message_0001",
        safety=SafetyAssessment("safe", "none"),
        features=BehaviorFeatures(),
        synthesis=synth(message_type="event", facts=("message describes an operational update or event",)),
        evidence=[EvidenceCandidate("message_0001", 0.5, "u1")],
        resolver_rule="safe non-urgent content",
    )
    assert result.consistency_status == "ok"
    assert not result.reason_repaired
