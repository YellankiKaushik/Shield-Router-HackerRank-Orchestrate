from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .schemas import ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MediaFacts(StrictModel):
    media_type: Literal["none", "image", "voice"] = "none"
    status: Literal["not_applicable", "ok", "failed"] = "not_applicable"
    visible_text: str = ""
    transcript: str = ""
    scene_or_poster_facts: list[str] = Field(default_factory=list)
    qr_code_present: bool = False
    price_or_payment_information: list[str] = Field(default_factory=list)
    dates_and_deadlines: list[str] = Field(default_factory=list)
    suspicious_visual_signals: list[str] = Field(default_factory=list)
    error: str = ""
    cache_hit: bool = False

    def combined_text(self) -> str:
        parts = [self.visible_text, self.transcript, " ".join(self.scene_or_poster_facts), " ".join(self.dates_and_deadlines)]
        return " ".join(p for p in parts if p).strip()


class AdvisoryModelOutput(StrictModel):
    visible_image_text: str = ""
    image_scene_or_poster_facts: list[str] = Field(default_factory=list)
    qr_presence: bool = False
    prices_payments: list[str] = Field(default_factory=list)
    dates_deadlines: list[str] = Field(default_factory=list)
    credential_or_sensitive_data_requests: list[str] = Field(default_factory=list)
    suspicious_domains: list[str] = Field(default_factory=list)
    prompt_injection_detected: bool = False
    risk_level: Literal["none", "low", "medium", "high"] = "none"
    urgency_level: Literal["low", "medium", "high"] = "low"
    direct_mention: bool = False
    best_official_message_type: str = "unknown"
    ambiguity: bool = False
    concise_grounded_semantic_facts: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("best_official_message_type")
    @classmethod
    def valid_message_type(cls, value: str) -> str:
        if value not in ALLOWED_MESSAGE_TYPES:
            raise ValueError(f"invalid message_type={value}")
        return value


class SafetyPayload(StrictModel):
    message_text: str
    media_facts: MediaFacts
    forwarded_count: int
    sender_legitimacy: dict[str, str | int | bool]
    domains: list[str]


class SafetyModelOutput(StrictModel):
    risk_level: Literal["none", "low", "high"]
    verdict: Literal["safe", "suspicious", "high_risk"]
    detected_safety_signals: list[str] = Field(default_factory=list)
    requested_sensitive_data_types: list[str] = Field(default_factory=list)
    suspicious_domains: list[str] = Field(default_factory=list)
    prompt_injection: bool = False


class EvidencePayloadCandidate(StrictModel):
    message_id: str
    score: float
    text_excerpt: str


class SynthesisPayload(StrictModel):
    normalized_message_content: str
    media_facts: MediaFacts
    safety_result: SafetyModelOutput
    behavior_features: dict[str, float | bool | str | list[str]]
    context: dict[str, str | int | bool]
    evidence_candidates: list[EvidencePayloadCandidate]


class SynthesisModelOutput(StrictModel):
    is_direct_mention: bool
    deadline_and_urgency_facts: list[str] = Field(default_factory=list)
    urgency_level: Literal["low", "medium", "high"]
    message_type: str
    recommended_preliminary_action: str
    selected_evidence_ids: list[str] = Field(default_factory=list)
    concise_grounded_reason: str
    ambiguity: bool = False

    @field_validator("message_type")
    @classmethod
    def valid_message_type(cls, value: str) -> str:
        if value not in ALLOWED_MESSAGE_TYPES:
            raise ValueError(f"invalid message_type={value}")
        return value

    @field_validator("recommended_preliminary_action")
    @classmethod
    def valid_action(cls, value: str) -> str:
        if value not in ALLOWED_ACTIONS:
            raise ValueError(f"invalid action={value}")
        return value
