from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DATASET_HEADERS: dict[str, list[str]] = {
    "messages.csv": [
        "message_id",
        "user_id",
        "conversation_type",
        "group_id",
        "business_id",
        "sender_user_id",
        "created_at",
        "message_text",
        "media_type",
        "media_id",
        "forwarded_count",
    ],
    "sample_messages.csv": [
        "message_id",
        "user_id",
        "conversation_type",
        "group_id",
        "business_id",
        "sender_user_id",
        "created_at",
        "message_text",
        "media_type",
        "media_id",
        "forwarded_count",
        "action",
        "message_type",
        "reason",
        "confidence",
        "evidence_message_ids",
    ],
    "users.csv": [
        "user_id",
        "do_not_disturb_window",
        "messages_opened_30d",
        "messages_replied_30d",
        "notifications_dismissed_30d",
        "messages_reported_30d",
    ],
    "groups.csv": [
        "group_id",
        "group_name",
        "group_type",
        "member_count",
        "admin_count",
        "created_at",
        "messages_30d",
    ],
    "group_members.csv": [
        "group_id",
        "user_id",
        "role",
        "joined_at",
        "messages_sent_30d",
        "messages_read_30d",
        "replies_sent_30d",
        "notifications_dismissed_30d",
        "group_muted_by_user",
    ],
    "business_accounts.csv": [
        "business_id",
        "display_name",
        "brand_name",
        "category",
        "verified",
        "official_domain",
        "domain_used_by_sender",
        "account_age_days",
        "messages_sent_30d",
        "user_reports_30d",
        "domain_used_by_sender_age_days",
    ],
    "user_business_history.csv": [
        "user_id",
        "business_id",
        "why_user_knows_account",
        "last_activity_at",
        "allows_promotions",
        "promotions_opted_out_at",
        "activity_count_180d",
        "messages_opened_30d",
        "messages_dismissed_30d",
        "messages_replied_30d",
        "last_reply_at",
    ],
    "message_history.csv": [
        "message_id",
        "user_id",
        "conversation_type",
        "group_id",
        "business_id",
        "sender_user_id",
        "created_at",
        "message_text",
        "media_type",
        "media_id",
        "forwarded_count",
    ],
    "message_events.csv": [
        "user_id",
        "message_id",
        "message_opened",
        "message_replied",
        "reaction_time_minutes",
        "notification_dismissed",
        "muted_after_message",
        "message_reported",
    ],
    "images.csv": ["image_id", "file_path"],
    "voice_notes.csv": ["voice_note_id", "file_path"],
    "daily_notification_summary.csv": [
        "user_id",
        "date",
        "notifications_sent",
        "notifications_dismissed",
    ],
    "output.csv": [
        "message_id",
        "action",
        "message_type",
        "reason",
        "confidence",
        "evidence_message_ids",
    ],
}

OUTPUT_COLUMNS = DATASET_HEADERS["output.csv"]
ROUTING_TABLES = [
    name
    for name in DATASET_HEADERS
    if name not in {"sample_messages.csv", "output.csv"}
]
ALLOWED_ACTIONS = {"notify", "digest", "mute"}
ALLOWED_MESSAGE_TYPES = {
    "personal",
    "urgent",
    "event",
    "payment",
    "business_update",
    "promotion",
    "greeting",
    "forward",
    "spam",
    "scam",
    "unknown",
}
CONVERSATION_TYPES = {"personal", "group", "business"}
MEDIA_TYPES = {"", "image", "voice"}


@dataclass(frozen=True)
class SafetyAssessment:
    verdict: str
    risk_level: str
    signals: tuple[str, ...] = ()
    message_type: str = "unknown"


@dataclass(frozen=True)
class BehaviorFeatures:
    trust: float = 0.0
    affinity: float = 0.0
    fatigue: float = 0.0
    promotion_opt_out: bool = False
    relationship_strength: float = 0.0
    group_muted: bool = False
    group_role: str = ""
    sender_is_admin_context: bool = False
    in_quiet_hours: bool = False
    relative_load: float = 0.0
    urgency: float = 0.0
    direct_mention: bool = False
    repeated: bool = False
    missing_context: tuple[str, ...] = ()
    media_available: bool = False
    media_error: str = ""


@dataclass(frozen=True)
class EvidenceCandidate:
    message_id: str
    score: float
    user_id: str


@dataclass(frozen=True)
class Synthesis:
    urgency_level: str
    direct_mention: bool
    message_type: str
    preliminary_action: str
    ambiguous: bool
    facts: tuple[str, ...] = ()


@dataclass
class DecisionTrace:
    message_id: str
    action: str
    message_type: str
    reason: str
    confidence: float
    evidence_message_ids: list[str]
    safety: SafetyAssessment
    features: BehaviorFeatures
    synthesis: Synthesis
    errors: list[str] = field(default_factory=list)
    media_facts: Any | None = None

    def to_output_row(self) -> dict[str, Any]:
        evidence = ";".join(self.evidence_message_ids) if self.evidence_message_ids else "none"
        return {
            "message_id": self.message_id,
            "action": self.action,
            "message_type": self.message_type,
            "reason": self.reason,
            "confidence": f"{max(0.0, min(1.0, self.confidence)):.2f}",
            "evidence_message_ids": evidence,
        }
