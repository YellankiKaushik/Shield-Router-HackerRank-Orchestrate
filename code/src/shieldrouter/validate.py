from __future__ import annotations

from .schemas import ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES, OUTPUT_COLUMNS


def validate_output_rows(
    messages: list[dict[str, str]],
    history: list[dict[str, str]],
    rows: list[dict[str, object]],
) -> list[str]:
    errors: list[str] = []
    input_ids = [r["message_id"] for r in messages]
    output_ids = [str(r.get("message_id", "")) for r in rows]
    if len(rows) != len(messages):
        errors.append(f"row count mismatch input={len(messages)} output={len(rows)}")
    if set(output_ids) != set(input_ids):
        errors.append("output ID set does not match input messages")
    if len(output_ids) != len(set(output_ids)):
        errors.append("duplicate output message_id")
    history_user = {r["message_id"]: r["user_id"] for r in history}
    input_user = {r["message_id"]: r["user_id"] for r in messages}
    for row in rows:
        keys = list(row.keys())
        if keys != OUTPUT_COLUMNS:
            errors.append(f"{row.get('message_id', '<unknown>')} output columns out of order")
            break
        mid = str(row.get("message_id", ""))
        action = str(row.get("action", ""))
        msg_type = str(row.get("message_type", ""))
        reason = str(row.get("reason", "")).strip()
        if action not in ALLOWED_ACTIONS:
            errors.append(f"{mid} invalid action={action}")
        if msg_type not in ALLOWED_MESSAGE_TYPES:
            errors.append(f"{mid} invalid message_type={msg_type}")
        if not reason:
            errors.append(f"{mid} empty reason")
        try:
            conf = float(row.get("confidence", ""))
            if not 0 <= conf <= 1:
                errors.append(f"{mid} confidence out of range")
        except (TypeError, ValueError):
            errors.append(f"{mid} confidence not numeric")
        evidence = str(row.get("evidence_message_ids", ""))
        if evidence == "none":
            continue
        if not evidence:
            errors.append(f"{mid} empty evidence")
            continue
        for eid in evidence.split(";"):
            if eid not in history_user:
                errors.append(f"{mid} evidence id absent from history: {eid}")
            elif history_user[eid] != input_user.get(mid):
                errors.append(f"{mid} evidence belongs to another user: {eid}")
    return errors
