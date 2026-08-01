from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Iterable


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


def classification_metrics(expected: list[str], predicted: list[str], classes: Iterable[str]) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for cls in classes:
        tp = sum(1 for e, p in zip(expected, predicted) if e == cls and p == cls)
        fp = sum(1 for e, p in zip(expected, predicted) if e != cls and p == cls)
        fn = sum(1 for e, p in zip(expected, predicted) if e == cls and p != cls)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        result[cls] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return result


def macro_f1(metrics: dict[str, dict[str, float | int]]) -> float:
    return round(sum(float(v["f1"]) for v in metrics.values()) / len(metrics), 4) if metrics else 0.0


def confusion(expected: list[str], predicted: list[str]) -> dict[str, int]:
    return {f"{e}->{p}": n for (e, p), n in sorted(Counter(zip(expected, predicted)).items())}


def confidence_stats(rows: list[dict[str, str]]) -> dict[str, float]:
    values = [float(r["confidence"]) for r in rows]
    return {
        "min": round(min(values), 4) if values else 0.0,
        "mean": round(sum(values) / len(values), 4) if values else 0.0,
        "max": round(max(values), 4) if values else 0.0,
    }
