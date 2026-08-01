from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.behaviorgraph import detect_direct_mention, in_quiet_hours


def test_quiet_hours_wraparound():
    assert in_quiet_hours("2026-07-30 22:19", "22:00-07:00")
    assert not in_quiet_hours("2026-07-30 12:19", "22:00-07:00")


def test_direct_mention_detects_user_id_and_request():
    assert detect_direct_mention({"message_text": "@u_010 can you join now", "user_id": "u_010", "conversation_type": "group"})
    assert detect_direct_mention({"message_text": "Can you reply once", "user_id": "u_010", "conversation_type": "group"})
