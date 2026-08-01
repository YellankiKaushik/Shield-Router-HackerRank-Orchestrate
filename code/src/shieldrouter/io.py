from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .schemas import CONVERSATION_TYPES, DATASET_HEADERS, MEDIA_TYPES, ROUTING_TABLES


class DatasetError(ValueError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{k: (v if v is not None else "") for k, v in row.items()} for row in reader]


def read_headers(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def write_csv(path: Path, rows: Iterable[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def load_dataset(dataset_dir: Path, filenames: Iterable[str] | None = None) -> dict[str, list[dict[str, str]]]:
    dataset_dir = dataset_dir.resolve()
    tables: dict[str, list[dict[str, str]]] = {}
    for filename in (filenames or DATASET_HEADERS.keys()):
        path = dataset_dir / filename
        if not path.exists():
            raise DatasetError(f"Missing required dataset file: {filename}")
        headers = read_headers(path)
        expected = DATASET_HEADERS[filename]
        if headers != expected:
            raise DatasetError(f"{filename} headers mismatch: expected {expected}, got {headers}")
        tables[filename] = read_csv(path)
    return tables


def load_routing_dataset(dataset_dir: Path) -> dict[str, list[dict[str, str]]]:
    return load_dataset(dataset_dir, ROUTING_TABLES)


def parse_int(value: object, default: int = 0) -> int:
    try:
        text = str(value).strip()
        return default if text == "" else int(float(text))
    except (TypeError, ValueError):
        return default


def parse_bool(value: object) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def parse_datetime(value: object) -> datetime | None:
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def validate_unique(rows: list[dict[str, str]], key: str, name: str) -> list[str]:
    seen: set[str] = set()
    errors: list[str] = []
    for row in rows:
        value = row.get(key, "")
        if not value:
            errors.append(f"{name} has blank {key}")
        elif value in seen:
            errors.append(f"{name} duplicate {key}: {value}")
        seen.add(value)
    return errors


def safe_media_path(dataset_dir: Path, rel_path: str) -> Path:
    root = dataset_dir.resolve()
    candidate = (root / rel_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise DatasetError(f"Media path escapes dataset directory: {rel_path}")
    return candidate


def validate_dataset(dataset_dir: Path, tables: dict[str, list[dict[str, str]]] | None = None) -> list[str]:
    dataset_dir = dataset_dir.resolve()
    tables = tables or load_dataset(dataset_dir)
    errors: list[str] = []
    for name, key in [
        ("messages.csv", "message_id"),
        ("sample_messages.csv", "message_id"),
        ("users.csv", "user_id"),
        ("groups.csv", "group_id"),
        ("business_accounts.csv", "business_id"),
        ("message_history.csv", "message_id"),
        ("message_events.csv", "message_id"),
        ("images.csv", "image_id"),
        ("voice_notes.csv", "voice_note_id"),
    ]:
        errors.extend(validate_unique(tables[name], key, name))

    users = {r["user_id"] for r in tables["users.csv"]}
    groups = {r["group_id"] for r in tables["groups.csv"]}
    businesses = {r["business_id"] for r in tables["business_accounts.csv"]}
    images = {r["image_id"]: r["file_path"] for r in tables["images.csv"]}
    voices = {r["voice_note_id"]: r["file_path"] for r in tables["voice_notes.csv"]}

    for media_name, media_map in [("image", images), ("voice", voices)]:
        for media_id, rel_path in media_map.items():
            try:
                path = safe_media_path(dataset_dir, rel_path)
            except DatasetError as exc:
                errors.append(str(exc))
                continue
            if not path.exists():
                errors.append(f"{media_name} media file missing for {media_id}: {rel_path}")

    for name in ("messages.csv", "message_history.csv"):
        for row in tables[name]:
            mid = row["message_id"]
            if row["conversation_type"] not in CONVERSATION_TYPES:
                errors.append(f"{name}:{mid} invalid conversation_type={row['conversation_type']}")
            if row["media_type"] not in MEDIA_TYPES:
                errors.append(f"{name}:{mid} invalid media_type={row['media_type']}")
            if parse_datetime(row["created_at"]) is None:
                errors.append(f"{name}:{mid} invalid created_at={row['created_at']}")
            if row["user_id"] and row["user_id"] not in users:
                errors.append(f"{name}:{mid} unknown user_id={row['user_id']}")
            if row["group_id"] and row["group_id"] not in groups:
                errors.append(f"{name}:{mid} unknown group_id={row['group_id']}")
            if row["business_id"] and row["business_id"] not in businesses:
                errors.append(f"{name}:{mid} unknown business_id={row['business_id']}")
            if row["media_type"] == "image" and row["media_id"] and row["media_id"] not in images:
                errors.append(f"{name}:{mid} unknown image media_id={row['media_id']}")
            if row["media_type"] == "voice" and row["media_id"] and row["media_id"] not in voices:
                errors.append(f"{name}:{mid} unknown voice media_id={row['media_id']}")
    return errors
