from pathlib import Path
import json
import os
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.indexes import build_indexes
from shieldrouter.io import load_dataset
from shieldrouter.retrieval import retrieve_evidence


ROOT = Path(__file__).resolve().parents[2]


def test_evidence_same_user_only():
    tables = load_dataset(ROOT / "dataset")
    idx = build_indexes(ROOT / "dataset", tables)
    row = tables["messages.csv"][0]
    evidence = retrieve_evidence(row, idx)
    history_user = {r["message_id"]: r["user_id"] for r in tables["message_history.csv"]}
    assert len(evidence) <= 5
    assert all(history_user[e.message_id] == row["user_id"] for e in evidence)


def test_checkout_asr_split_does_not_select_generic_check_invite():
    row = {
        "message_id": "incoming",
        "user_id": "u1",
        "conversation_type": "group",
        "group_id": "g1",
        "business_id": "",
        "sender_user_id": "s1",
        "message_text": "Check out error spiking again. Please join the incident bridge now. Payments are failing for live users.",
        "media_type": "voice",
        "media_id": "v1",
    }
    history = [
        {
            "message_id": "message_0001",
            "user_id": "u1",
            "conversation_type": "group",
            "group_id": "g1",
            "business_id": "",
            "sender_user_id": "s1",
            "message_text": "Checkout errors are spiking again. Please join the incident bridge now, payments are failing for live users.",
            "media_type": "",
            "media_id": "",
        },
        {
            "message_id": "message_0002",
            "user_id": "u1",
            "conversation_type": "group",
            "group_id": "g1",
            "business_id": "",
            "sender_user_id": "s1",
            "message_text": "Incident review invite attached. Please check the guest list and RSVP before standup.",
            "media_type": "image",
            "media_id": "img1",
        },
    ]
    events = {r["message_id"]: {"message_opened": "1", "message_replied": "1"} for r in history}
    idx = SimpleNamespace(history_by_user={"u1": history}, events=events)

    evidence = retrieve_evidence(row, idx)

    assert [e.message_id for e in evidence] == ["message_0001"]


def test_retrieve_evidence_stable_across_hash_seed_processes(tmp_path):
    script = tmp_path / "seed_check.py"
    script.write_text(
        f"""
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, {str((ROOT / 'code' / 'src').resolve())!r})
from shieldrouter.retrieval import retrieve_evidence

row = {{
    "message_id": "incoming",
    "user_id": "u1",
    "conversation_type": "group",
    "group_id": "g1",
    "business_id": "",
    "sender_user_id": "s1",
    "message_text": "alpha beta gamma delta",
    "media_type": "",
    "media_id": "",
}}
history = [
    {{"message_id": "message_0002", "user_id": "u1", "conversation_type": "group", "group_id": "g1", "business_id": "", "sender_user_id": "s1", "message_text": "alpha beta", "media_type": "", "media_id": ""}},
    {{"message_id": "message_0001", "user_id": "u1", "conversation_type": "group", "group_id": "g1", "business_id": "", "sender_user_id": "s1", "message_text": "alpha beta", "media_type": "", "media_id": ""}},
    {{"message_id": "message_0003", "user_id": "u1", "conversation_type": "group", "group_id": "g1", "business_id": "", "sender_user_id": "s1", "message_text": "alpha", "media_type": "", "media_id": ""}},
]
events = {{r["message_id"]: {{"message_opened": "1", "message_replied": "1"}} for r in history}}
idx = SimpleNamespace(history_by_user={{"u1": history}}, events=events)
print(json.dumps([(e.message_id, e.score) for e in retrieve_evidence(row, idx, limit=3)]))
""",
        encoding="utf-8",
    )
    outputs = []
    for seed in ("0", "1", "42", "12345"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        result = subprocess.check_output([sys.executable, str(script)], text=True, env=env)
        outputs.append(json.loads(result))

    assert outputs
    assert all(output == outputs[0] for output in outputs)
    assert [message_id for message_id, _score in outputs[0]][:2] == ["message_0001", "message_0002"]
