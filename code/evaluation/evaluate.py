from __future__ import annotations

import csv
from pathlib import Path


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate_sample(predictions: list[dict[str, str]], sample_rows: list[dict[str, str]]) -> dict[str, object]:
    by_id = {r["message_id"]: r for r in predictions}
    labeled = [r for r in sample_rows if r["message_id"] in by_id]
    action_correct = sum(1 for r in labeled if by_id[r["message_id"]]["action"] == r["action"])
    type_correct = sum(1 for r in labeled if by_id[r["message_id"]]["message_type"] == r["message_type"])
    total = len(labeled)
    return {
        "matched_sample_rows": total,
        "action_accuracy": action_correct / total if total else None,
        "message_type_accuracy": type_correct / total if total else None,
    }
