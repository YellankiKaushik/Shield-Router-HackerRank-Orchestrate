from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.ai_models import MediaFacts, SynthesisModelOutput
from shieldrouter.online_ai import build_safety_payload
from shieldrouter.orchestrator import run
from shieldrouter.provider import ProviderStats


ROOT = Path(__file__).resolve().parents[2]


def test_prompt_templates_use_official_enums_only():
    combined = (ROOT / "code" / "prompts" / "safety_gate.md").read_text(encoding="utf-8") + "\n" + (ROOT / "code" / "prompts" / "synthesis.md").read_text(encoding="utf-8")
    assert "scam_or_risk" in combined
    assert "social" in combined
    assert "Never use" in combined
    assert "business_update" in combined


def test_safety_payload_excludes_personalization_fields_for_prompt():
    payload = build_safety_payload({"message_text": "Send OTP", "forwarded_count": "1"}, {"verified": "1"}, MediaFacts())
    dumped = str(payload.model_dump()).casefold()
    for forbidden in ("affinity", "fatigue", "promotion", "history", "dismissal"):
        assert forbidden not in dumped


def test_synthesis_output_rejects_non_official_enum():
    with pytest.raises(ValidationError):
        SynthesisModelOutput.model_validate(
            {
                "is_direct_mention": False,
                "deadline_and_urgency_facts": [],
                "urgency_level": "low",
                "message_type": "scam_or_risk",
                "recommended_preliminary_action": "digest",
                "selected_evidence_ids": [],
                "concise_grounded_reason": "bad enum",
                "ambiguity": False,
            }
        )


class FakeLocalMultimodalProvider:
    def __init__(self):
        self.stats = ProviderStats()

    def json_task(self, *_args, **_kwargs):
        raise AssertionError("local multimodal must not invoke provider prompts")

    def transcribe(self, *_args, **_kwargs):
        return "hello"

    def extract_image(self, *_args, **_kwargs):
        return MediaFacts(media_type="image", status="ok", visible_text="")


def test_local_multimodal_never_reads_prompt_templates(tmp_path, monkeypatch):
    original = Path.read_text

    def guard(self, *args, **kwargs):
        if "prompts" in self.parts:
            raise AssertionError("local multimodal must not read provider prompts")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guard)
    traces, summary = run(ROOT / "dataset", tmp_path / "out.csv", provider=FakeLocalMultimodalProvider(), local_multimodal=True)
    assert len(traces) == 110
    assert summary["provider"]["request_count"] == 0
