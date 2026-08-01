from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.indexes import build_indexes
from shieldrouter.io import load_dataset
from shieldrouter.orchestrator import process_message, run
from shieldrouter.validate import validate_output_rows


ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def test_full_output_contract_and_ids(tmp_path):
    output = tmp_path / "out.csv"
    traces, _ = run(ROOT / "dataset", output)
    tables = load_dataset(ROOT / "dataset")
    rows = []
    import csv

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert validate_output_rows(tables["messages.csv"], tables["message_history.csv"], rows) == []
    assert len(rows) == len(tables["messages.csv"])
    assert len({r["message_id"] for r in rows}) == len(rows)
    assert all(0 <= t.confidence <= 1 for t in traces)


def test_same_promotional_content_routes_differently_for_history():
    tables = load_dataset(ROOT / "dataset")
    idx = build_indexes(ROOT / "dataset", tables)
    base = {
        "message_id": "x",
        "conversation_type": "business",
        "group_id": "",
        "business_id": "business_003",
        "sender_user_id": "",
        "created_at": "2026-07-30 10:00",
        "message_text": "Flash sale offer today with discount coupon",
        "media_type": "",
        "media_id": "",
        "forwarded_count": "0",
    }
    muted = process_message(dict(base, user_id="u_001"), idx)
    allowed = process_message(dict(base, user_id="u_002"), idx)
    assert muted.action == "mute"
    assert allowed.action == "digest"


def test_missing_context_and_invalid_media_do_not_drop_row():
    tables = load_dataset(ROOT / "dataset")
    idx = build_indexes(ROOT / "dataset", tables)
    row = {
        "message_id": "missing_ctx",
        "user_id": "u_missing",
        "conversation_type": "business",
        "group_id": "",
        "business_id": "business_missing",
        "sender_user_id": "",
        "created_at": "2026-07-30 10:00",
        "message_text": "",
        "media_type": "image",
        "media_id": "img_missing",
        "forwarded_count": "0",
    }
    trace = process_message(row, idx)
    assert trace.message_id == "missing_ctx"
    assert trace.action in {"digest", "mute", "notify"}
    assert trace.errors


def test_repeated_identical_cli_run_is_byte_identical(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    cmd1 = [PYTHON, str(ROOT / "code" / "main.py"), "run", "--dataset", str(ROOT / "dataset"), "--output", str(first), "--offline"]
    cmd2 = [PYTHON, str(ROOT / "code" / "main.py"), "run", "--dataset", str(ROOT / "dataset"), "--output", str(second), "--offline"]
    subprocess.run(cmd1, check=True, capture_output=True, text=True)
    subprocess.run(cmd2, check=True, capture_output=True, text=True)
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(second.read_bytes()).hexdigest()
