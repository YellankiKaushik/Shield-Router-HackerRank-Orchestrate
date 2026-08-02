from argparse import Namespace
from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import cmd_run


ROOT = Path(__file__).resolve().parents[2]


def args(tmp_path, output, summary):
    return Namespace(dataset=str(ROOT / "dataset"), output=str(output), offline=True, online=False, local_voice=False, local_multimodal=False, cache_dir=str(tmp_path / "cache"), trace_errors=False, summary_json=str(summary))


def test_summary_json_creation_counts_and_sha(tmp_path):
    output = tmp_path / "out.csv"
    summary = tmp_path / "summary.json"
    assert cmd_run(args(tmp_path, output, summary)) == 0
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["rows"] == 110
    assert payload["unique_ids"] == 110
    assert payload["output_sha256"] == __import__("hashlib").sha256(output.read_bytes()).hexdigest()
    assert payload["provider_requests"] == 0


def test_summary_json_has_no_raw_sensitive_content(tmp_path):
    output = tmp_path / "out.csv"
    summary = tmp_path / "summary.json"
    cmd_run(args(tmp_path, output, summary))
    dumped = summary.read_text(encoding="utf-8").casefold()
    for forbidden in ("message_text", "visible_text", "transcript_text", "voice_transcript", "ocr_text", "api_key", "password"):
        assert forbidden not in dumped
    assert str(ROOT).casefold() not in dumped


def test_summary_write_failure_does_not_corrupt_output(tmp_path):
    output = tmp_path / "out.csv"
    summary_dir = tmp_path / "summary_dir"
    summary_dir.mkdir()
    with pytest.raises(Exception):
        cmd_run(args(tmp_path, output, summary_dir))
    assert output.exists()
    assert output.read_text(encoding="utf-8").startswith("message_id,action,message_type,reason,confidence,evidence_message_ids")
