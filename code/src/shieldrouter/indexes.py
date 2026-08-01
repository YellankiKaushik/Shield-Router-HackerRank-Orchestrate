from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .io import safe_media_path


@dataclass
class Indexes:
    dataset_dir: Path
    users: dict[str, dict[str, str]]
    groups: dict[str, dict[str, str]]
    memberships: dict[tuple[str, str], dict[str, str]]
    business_accounts: dict[str, dict[str, str]]
    user_business: dict[tuple[str, str], dict[str, str]]
    history: dict[str, dict[str, str]]
    history_by_user: dict[str, list[dict[str, str]]]
    events: dict[str, dict[str, str]]
    daily_by_user: dict[str, list[dict[str, str]]]
    images: dict[str, Path]
    voices: dict[str, Path]


def build_indexes(dataset_dir: Path, tables: dict[str, list[dict[str, str]]]) -> Indexes:
    history_by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in tables["message_history.csv"]:
        history_by_user[row["user_id"]].append(row)
    daily_by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in tables["daily_notification_summary.csv"]:
        daily_by_user[row["user_id"]].append(row)
    return Indexes(
        dataset_dir=dataset_dir.resolve(),
        users={r["user_id"]: r for r in tables["users.csv"]},
        groups={r["group_id"]: r for r in tables["groups.csv"]},
        memberships={(r["group_id"], r["user_id"]): r for r in tables["group_members.csv"]},
        business_accounts={r["business_id"]: r for r in tables["business_accounts.csv"]},
        user_business={(r["user_id"], r["business_id"]): r for r in tables["user_business_history.csv"]},
        history={r["message_id"]: r for r in tables["message_history.csv"]},
        history_by_user=dict(history_by_user),
        events={r["message_id"]: r for r in tables["message_events.csv"]},
        daily_by_user=dict(daily_by_user),
        images={r["image_id"]: safe_media_path(dataset_dir, r["file_path"]) for r in tables["images.csv"]},
        voices={r["voice_note_id"]: safe_media_path(dataset_dir, r["file_path"]) for r in tables["voice_notes.csv"]},
    )
