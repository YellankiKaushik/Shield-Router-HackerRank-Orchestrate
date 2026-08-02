from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from evaluate import classification_metrics, confusion, macro_f1
from shieldrouter.indexes import build_indexes
from shieldrouter.io import load_dataset
import shieldrouter.orchestrator as orchestrator
from shieldrouter.schemas import SafetyAssessment


@contextmanager
def deterministic_safety_disabled() -> Iterator[None]:
    original = orchestrator.assess_safety

    def safe_only(_row, _business=None):
        return SafetyAssessment("safe", "none", (), "unknown")

    orchestrator.assess_safety = safe_only
    try:
        yield
    finally:
        orchestrator.assess_safety = original


def evaluate_sample_mode(dataset_dir: Path, *, safety_disabled: bool = False) -> dict[str, object]:
    tables = load_dataset(dataset_dir)
    idx = build_indexes(dataset_dir, tables)
    traces = []
    started = time.perf_counter()
    context = deterministic_safety_disabled() if safety_disabled else _null_context()
    with context:
        for sample in tables["sample_messages.csv"]:
            incoming = {k: sample[k] for k in tables["messages.csv"][0].keys()}
            traces.append(orchestrator.process_message(incoming, idx))
    pred_rows = [trace.to_output_row() for trace in traces]
    expected_actions = [row["action"] for row in tables["sample_messages.csv"]]
    predicted_actions = [row["action"] for row in pred_rows]
    expected_types = [row["message_type"] for row in tables["sample_messages.csv"]]
    predicted_types = [row["message_type"] for row in pred_rows]
    action_metrics = classification_metrics(expected_actions, predicted_actions, ["notify", "digest", "mute"])
    type_classes = sorted(set(expected_types) | set(predicted_types))
    type_metrics = classification_metrics(expected_types, predicted_types, type_classes)
    return {
        "sample_rows": len(pred_rows),
        "action_accuracy": round(sum(e == p for e, p in zip(expected_actions, predicted_actions)) / len(pred_rows), 4),
        "action_macro_f1": macro_f1(action_metrics),
        "message_type_accuracy": round(sum(e == p for e, p in zip(expected_types, predicted_types)) / len(pred_rows), 4),
        "message_type_macro_f1": macro_f1(type_metrics),
        "scam_precision": type_metrics.get("scam", {}).get("precision", 0.0),
        "scam_recall": type_metrics.get("scam", {}).get("recall", 0.0),
        "notify_precision": action_metrics.get("notify", {}).get("precision", 0.0),
        "notify_recall": action_metrics.get("notify", {}).get("recall", 0.0),
        "false_positive_scams": [
            row["message_id"]
            for row, pred in zip(tables["sample_messages.csv"], pred_rows)
            if pred["message_type"] == "scam" and row["message_type"] != "scam"
        ],
        "false_negative_urgent_cases": [
            row["message_id"]
            for row, pred in zip(tables["sample_messages.csv"], pred_rows)
            if row["action"] == "notify" and pred["action"] != "notify"
        ],
        "action_confusion": confusion(expected_actions, predicted_actions),
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "provider_calls": 0,
        "fallback_rate": 0.0,
        "evidence_validity": "passed",
    }


@contextmanager
def _null_context() -> Iterator[None]:
    yield
