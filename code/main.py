from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from shieldrouter.indexes import build_indexes
from shieldrouter.io import DatasetError, load_dataset, read_csv, validate_dataset
from shieldrouter.orchestrator import process_message, run, summarize
from shieldrouter.schemas import OUTPUT_COLUMNS
from shieldrouter.validate import validate_output_rows


def cmd_validate_input(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset)
    tables = load_dataset(dataset)
    errors = validate_dataset(dataset, tables)
    if errors:
        print("INPUT VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"INPUT VALIDATION OK: {len(tables['messages.csv'])} messages")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    traces, summary = run(Path(args.dataset), Path(args.output))
    print("RUN OK")
    print_summary(summary)
    if args.trace_errors:
        for trace in traces:
            if trace.errors:
                print(f"{trace.message_id}: {','.join(trace.errors)}")
    return 0


def cmd_validate_output(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset)
    tables = load_dataset(dataset)
    rows = read_csv(Path(args.output))
    errors = validate_output_rows(tables["messages.csv"], tables["message_history.csv"], rows)
    if errors:
        print("OUTPUT VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OUTPUT VALIDATION OK: {len(rows)} rows")
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset)
    tables = load_dataset(dataset)
    idx = build_indexes(dataset, tables)
    row = next((r for r in tables["messages.csv"] if r["message_id"] == args.message_id), None)
    if row is None:
        print(f"Unknown message_id: {args.message_id}")
        return 1
    trace = process_message(row, idx)
    payload = {
        "output": trace.to_output_row(),
        "safety": {
            "verdict": trace.safety.verdict,
            "risk_level": trace.safety.risk_level,
            "signals": list(trace.safety.signals),
        },
        "features": trace.features.__dict__,
        "synthesis": trace.synthesis.__dict__,
        "errors": trace.errors,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


def print_summary(summary: dict[str, object]) -> None:
    for key in [
        "rows",
        "unique_ids",
        "actions",
        "message_types",
        "confidence_min",
        "confidence_mean",
        "confidence_max",
        "evidence_usage_count",
        "fallback_error_count",
    ]:
        print(f"{key}: {summary[key]}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ShieldRouter offline notification router")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate-input")
    p.add_argument("--dataset", required=True)
    p.set_defaults(func=cmd_validate_input)
    p = sub.add_parser("run")
    p.add_argument("--dataset", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--offline", action="store_true", help="Accepted for evaluator compatibility; offline is the only implemented mode.")
    p.add_argument("--trace-errors", action="store_true")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("validate-output")
    p.add_argument("--dataset", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_validate_output)
    p = sub.add_parser("trace")
    p.add_argument("--dataset", required=True)
    p.add_argument("--message-id", required=True)
    p.add_argument("--offline", action="store_true")
    p.set_defaults(func=cmd_trace)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except DatasetError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
