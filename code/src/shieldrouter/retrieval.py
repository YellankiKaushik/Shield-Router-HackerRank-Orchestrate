from __future__ import annotations

import math
from collections import Counter

from .normalize import tokenize
from .schemas import EvidenceCandidate


def _tf(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def _cosine(a: Counter[str], b: Counter[str], idf: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    num = sum(a[t] * b[t] * idf.get(t, 1.0) ** 2 for t in common)
    da = math.sqrt(sum((v * idf.get(t, 1.0)) ** 2 for t, v in a.items()))
    db = math.sqrt(sum((v * idf.get(t, 1.0)) ** 2 for t, v in b.items()))
    return 0.0 if da == 0 or db == 0 else num / (da * db)


def retrieve_evidence(row: dict[str, str], idx, limit: int = 5, threshold: float = 0.08) -> list[EvidenceCandidate]:
    history = idx.history_by_user.get(row.get("user_id", ""), [])
    if not history:
        return []
    docs = [tokenize(r.get("message_text", "")) for r in history]
    df: Counter[str] = Counter()
    for tokens in docs:
        df.update(set(tokens))
    idf = {t: math.log((1 + len(docs)) / (1 + n)) + 1 for t, n in df.items()}
    query = _tf(tokenize(row.get("message_text", "")))
    scored: list[EvidenceCandidate] = []
    for hist, tokens in zip(history, docs):
        score = _cosine(query, _tf(tokens), idf)
        if row.get("sender_user_id") and hist.get("sender_user_id") == row.get("sender_user_id"):
            score += 0.08
        if row.get("group_id") and hist.get("group_id") == row.get("group_id"):
            score += 0.08
        if row.get("business_id") and hist.get("business_id") == row.get("business_id"):
            score += 0.1
        if hist.get("conversation_type") == row.get("conversation_type"):
            score += 0.03
        event = idx.events.get(hist["message_id"], {})
        if event.get("message_reported") == "1" or event.get("muted_after_message") == "1":
            score += 0.03
        if score >= threshold:
            scored.append(EvidenceCandidate(hist["message_id"], round(score, 4), hist["user_id"]))
    scored.sort(key=lambda c: (-c.score, c.message_id))
    return scored[:limit]
