from pathlib import Path
import sys

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
