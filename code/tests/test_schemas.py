from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.schemas import ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES, OUTPUT_COLUMNS


def test_output_header_order():
    assert OUTPUT_COLUMNS == ["message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"]
    assert ALLOWED_ACTIONS == {"notify", "digest", "mute"}
    assert "scam" in ALLOWED_MESSAGE_TYPES
