from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


URL_RE = re.compile(r"https?://[^\s)>\]]+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?")
TOKEN_RE = re.compile(r"[\w@#]+", re.UNICODE)


def normalize_text(value: str | None) -> str:
    value = "" if value is None else str(value)
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", value).strip()


def lower_text(value: str | None) -> str:
    return normalize_text(value).casefold()


def extract_urls(text: str) -> list[str]:
    return [m.group(0).strip(".,;:") for m in URL_RE.finditer(text or "")]


def extract_domains(text: str) -> list[str]:
    domains: list[str] = []
    for url in extract_urls(text):
        candidate = url if "://" in url else f"https://{url}"
        parsed = urlparse(candidate)
        domain = (parsed.netloc or parsed.path.split("/", 1)[0]).casefold()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def tokenize(text: str) -> list[str]:
    return [t.casefold() for t in TOKEN_RE.findall(normalize_text(text)) if len(t) > 1]
