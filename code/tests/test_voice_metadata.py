from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.media import derive_voice_metadata, extract_media
from shieldrouter.provider import ProviderError, ProviderStats


class VoiceProvider:
    def __init__(self, transcript="", fail=False):
        self.transcript = transcript
        self.fail = fail
        self.stats = ProviderStats()

    def transcribe(self, _path):
        if self.fail:
            raise ProviderError("missing model")
        return self.transcript


def voice_idx(tmp_path):
    audio = tmp_path / "dataset" / "media" / "audio" / "note.mp3"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"audio")
    return SimpleNamespace(dataset_dir=(tmp_path / "dataset").resolve(), voices={"vn": audio.resolve()}, images={}, business_accounts={})


def voice_row():
    return {"media_type": "voice", "media_id": "vn"}


@pytest.mark.parametrize(
    ("text", "tone", "pressure"),
    [
        ("Please call now, dad is unwell and going to the clinic.", "urgent", False),
        ("Emergency, join the incident bridge right now.", "urgent", False),
        ("Your airport pickup update is informational, nothing urgent.", "calm", False),
        ("Hi, good morning.", "neutral", False),
        ("Your account will be blocked today, pay now otherwise access stops.", "urgent", True),
        ("Reply with the 6 digit login code you received.", "urgent", True),
        ("", "unknown", False),
        ("à²¨à²®à²¸à³à²¤à³†, appointment today confirm madi", "urgent", False),
    ],
)
def test_transcript_derived_voice_tone_and_pressure(text, tone, pressure):
    detected_tone, detected_pressure = derive_voice_metadata(text)
    assert detected_tone == tone
    assert detected_pressure is pressure


def test_failed_transcription_has_unknown_tone(tmp_path):
    facts = extract_media(voice_row(), voice_idx(tmp_path), VoiceProvider(fail=True), online=True)
    assert facts.status == "failed"
    assert facts.detected_tone == "unknown"
    assert not facts.detected_pressure_language


def test_voice_metadata_preserves_multilingual_transcript(tmp_path):
    transcript = "à²¨à²®à²¸à³à²¤à³†, appointment today confirm madi"
    facts = extract_media(voice_row(), voice_idx(tmp_path), VoiceProvider(transcript), online=True)
    assert facts.transcript == transcript
    assert facts.detected_tone == "urgent"


def test_voice_metadata_is_deterministic_for_same_transcript(tmp_path):
    transcript = "Please call now"
    first = extract_media(voice_row(), voice_idx(tmp_path), VoiceProvider(transcript), online=True)
    second = extract_media(voice_row(), voice_idx(tmp_path), VoiceProvider(transcript), online=True)
    assert first.detected_tone == second.detected_tone
    assert first.detected_pressure_language == second.detected_pressure_language
