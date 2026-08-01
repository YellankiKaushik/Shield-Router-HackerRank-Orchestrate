from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any

from .ai_models import LocalImageFacts, MediaFacts
from .io import DatasetError, safe_media_path
from .normalize import extract_domains, extract_urls


LOCAL_IMAGE_SCHEMA_VERSION = "local_image_facts_v1"
LOCAL_IMAGE_PREPROCESSING_VERSION = "pillow_cv2_decode_v1"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}

PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
PRICE_RE = re.compile(r"(?:rs\.?|inr|usd|aed|\u20b9|\$)\s?\d[\d,]*(?:\.\d{1,2})?|\d[\d,]*(?:\.\d{1,2})?\s?(?:rs|inr|usd|aed)", re.I)
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{1,2}\s?(?:jan|feb|mar|apr|may|jun|june|jul|july|aug|sep|sept|oct|nov|dec)[a-z]*"
    r"|(?:today|tomorrow|tonight|midnight|eod|evening|morning)|(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?)\b",
    re.I,
)
DEADLINE_RE = re.compile(r"\b(deadline|last date|closes?|close|before|by\s+\d|expires?|valid till|midnight|eod|today|tomorrow|tonight)\b", re.I)
PAYMENT_RE = re.compile(r"\b(qr|upi|scan|pay|payment|wallet|bank|card|refund|token|deposit|fee|receipt|invoice)\b", re.I)
CREDENTIAL_RE = re.compile(r"\b(otp|pin|password|passcode|login code|verification code|cvv|card details|wallet details|share pickup code)\b", re.I)
URGENT_RE = re.compile(r"\b(urgent|immediately|act now|last chance|final few|blocks?|blocked|locks?|locked|today|tonight|asap|before midnight)\b", re.I)
PROMO_RE = re.compile(r"\b(sale|discount|offer|cashback|coupon|deal|book now|limited|prime day|off|shopping benefit|unsubscribe)\b", re.I)
INJECTION_RE = re.compile(r"\b(ignore previous instructions|system prompt|developer message|mark this notify|override|you are chatgpt|router instruction)\b", re.I)
CHAIN_RE = re.compile(r"\b(forward to|share with 10|send to 10|good luck|bad luck|blessings)\b", re.I)
SUSPICIOUS_DOMAIN_RE = re.compile(r"\b(bit\.ly|tinyurl|t\.co|goo\.gl|rebrand\.ly|free|claim|verify|secure|refund|pay)\b", re.I)


class LocalImageExtractor:
    def __init__(self, cache_dir: Path, stats: Any | None = None) -> None:
        self.cache_dir = cache_dir / "local_images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stats = stats
        self._ocr_engine: Any | None = None
        self.ocr_engine_version = _package_version("rapidocr")

    def extract(self, row: dict[str, str], idx) -> MediaFacts:
        facts = self.extract_facts(row, idx)
        status = "ok" if facts.valid_media else "failed"
        scene_facts = _scene_facts(facts)
        return MediaFacts(
            media_type="image",
            status=status,
            visible_text=facts.visible_text,
            scene_or_poster_facts=scene_facts,
            qr_code_present=facts.contains_qr,
            price_or_payment_information=facts.detected_prices,
            dates_and_deadlines=facts.detected_dates,
            suspicious_visual_signals=facts.suspicious_visual_signals,
            local_image_facts=facts,
            error=facts.extraction_error,
        )

    def extract_facts(self, row: dict[str, str], idx) -> LocalImageFacts:
        _bump(self.stats, "image_extraction_attempts")
        try:
            image_path = self._resolve_image_path(row, idx)
            data = image_path.read_bytes()
            if len(data) > MAX_IMAGE_BYTES:
                raise DatasetError("image_file_too_large")
            media_sha = hashlib.sha256(data).hexdigest()
            cache_path = self._cache_path(media_sha)
            if cache_path.exists():
                _bump(self.stats, "image_extraction_cache_hits")
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                facts = LocalImageFacts.model_validate(cached["facts"])
                if facts.valid_media:
                    _bump(self.stats, "image_extraction_successes")
                    if facts.contains_qr:
                        _bump(self.stats, "qr_codes_detected")
                else:
                    _bump(self.stats, "image_extraction_failures")
                return facts
            facts = self._extract_uncached(data)
            self._write_cache(cache_path, media_sha, facts)
            if facts.valid_media:
                _bump(self.stats, "image_extraction_successes")
                if facts.contains_qr:
                    _bump(self.stats, "qr_codes_detected")
            else:
                _bump(self.stats, "image_extraction_failures")
            return facts
        except Exception as exc:
            _bump(self.stats, "image_extraction_failures")
            return LocalImageFacts(valid_media=False, layout_type="unknown", extraction_error=_sanitize_error(exc))

    def _resolve_image_path(self, row: dict[str, str], idx) -> Path:
        if row.get("media_type") != "image":
            raise DatasetError("not_image_media")
        media_id = row.get("media_id", "")
        if not media_id or media_id not in idx.images:
            raise DatasetError("missing_image_media")
        path = idx.images[media_id]
        root = idx.dataset_dir.resolve()
        try:
            rel = path.resolve().relative_to(root)
        except ValueError as exc:
            raise DatasetError("image_path_escapes_dataset") from exc
        safe = safe_media_path(root, str(rel))
        if not safe.exists() or not safe.is_file():
            raise DatasetError("missing_image_file")
        resolved = safe.resolve()
        if root != resolved and root not in resolved.parents:
            raise DatasetError("image_symlink_escapes_dataset")
        return resolved

    def _extract_uncached(self, data: bytes) -> LocalImageFacts:
        image, width, height, mime_type = _decode_with_pillow(data)
        cv_image = _decode_with_cv2(data)
        decoded_qr_text, contains_qr = _detect_qr(cv_image)
        lines, scores = self._run_ocr(cv_image)
        visible_text = "\n".join(lines).strip()
        all_text = "\n".join(part for part in (visible_text, decoded_qr_text) if part)
        urls = extract_urls(all_text)
        domains = extract_domains(all_text)
        signals = _suspicious_signals(all_text, contains_qr, domains)
        mean_confidence = round(sum(scores) / len(scores), 4) if scores else 0.0
        facts = LocalImageFacts(
            valid_media=True,
            visible_text=visible_text,
            ocr_lines=lines,
            mean_ocr_confidence=mean_confidence,
            image_width=width,
            image_height=height,
            mime_type=mime_type,
            contains_qr=contains_qr,
            decoded_qr_text=decoded_qr_text,
            detected_urls=urls,
            detected_domains=domains,
            detected_phone_numbers=_unique(PHONE_RE.findall(all_text)),
            detected_prices=_unique(m.group(0).strip() for m in PRICE_RE.finditer(all_text)),
            detected_dates=_unique(m.group(0).strip() for m in DATE_RE.finditer(all_text)),
            deadline_language=bool(DEADLINE_RE.search(all_text)),
            payment_language=bool(PAYMENT_RE.search(all_text)) or contains_qr,
            credential_request_language=bool(CREDENTIAL_RE.search(all_text)),
            urgent_language=bool(URGENT_RE.search(all_text)),
            promotion_language=bool(PROMO_RE.search(all_text)),
            prompt_injection_language=bool(INJECTION_RE.search(all_text)),
            suspicious_visual_signals=signals,
            layout_type=_layout_type(width, height, lines, all_text, contains_qr),
        )
        image.close()
        return facts

    def _run_ocr(self, cv_image: Any) -> tuple[list[str], list[float]]:
        if self._ocr_engine is None:
            from rapidocr import RapidOCR

            self._ocr_engine = RapidOCR()
        result = self._ocr_engine(cv_image)
        return _ordered_ocr_lines(result)

    def _cache_path(self, media_sha: str) -> Path:
        key = {
            "media_sha256": media_sha,
            "ocr_engine": "rapidocr",
            "ocr_engine_version": self.ocr_engine_version,
            "schema_version": LOCAL_IMAGE_SCHEMA_VERSION,
            "preprocessing_version": LOCAL_IMAGE_PREPROCESSING_VERSION,
        }
        digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _write_cache(self, path: Path, media_sha: str, facts: LocalImageFacts) -> None:
        payload = {
            "media_sha256": media_sha,
            "ocr_engine": "rapidocr",
            "ocr_engine_version": self.ocr_engine_version,
            "schema_version": LOCAL_IMAGE_SCHEMA_VERSION,
            "preprocessing_version": LOCAL_IMAGE_PREPROCESSING_VERSION,
            "facts": facts.model_dump(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")


def _decode_with_pillow(data: bytes):
    try:
        from PIL import Image

        with Image.open(BytesIO(data)) as probe:
            probe.verify()
        image = Image.open(BytesIO(data))
        image.load()
        fmt = (image.format or "").upper()
        if fmt not in SUPPORTED_FORMATS:
            raise DatasetError(f"unsupported_image_type:{fmt or 'unknown'}")
        mime_type = Image.MIME.get(fmt, f"image/{fmt.casefold()}")
        width, height = image.size
        return image, int(width), int(height), mime_type
    except DatasetError:
        raise
    except Exception as exc:
        raise DatasetError(f"invalid_image_bytes:{type(exc).__name__}") from exc


def _decode_with_cv2(data: bytes):
    try:
        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise DatasetError("opencv_decode_failed")
        return image
    except DatasetError:
        raise
    except Exception as exc:
        raise DatasetError(f"opencv_decode_failed:{type(exc).__name__}") from exc


def _detect_qr(cv_image: Any) -> tuple[str, bool]:
    import cv2

    detector = cv2.QRCodeDetector()
    decoded_values: list[str] = []
    contains_qr = False
    try:
        ok, decoded_info, points, _straight = detector.detectAndDecodeMulti(cv_image)
        if ok or points is not None:
            contains_qr = True
        decoded_values.extend(str(x) for x in decoded_info or [] if str(x).strip())
    except Exception:
        pass
    if not decoded_values:
        try:
            decoded, points, _straight = detector.detectAndDecode(cv_image)
            contains_qr = contains_qr or points is not None or bool(decoded)
            if decoded:
                decoded_values.append(str(decoded))
        except Exception:
            pass
    return "\n".join(_unique(decoded_values)), contains_qr


def _ordered_ocr_lines(result: Any) -> tuple[list[str], list[float]]:
    txts = _as_list(getattr(result, "txts", None))
    scores = [float(s) for s in _as_list(getattr(result, "scores", None))]
    boxes = _as_list(getattr(result, "boxes", None))
    if not txts and isinstance(result, (list, tuple)):
        parsed: list[tuple[Any, str, float]] = []
        for item in result:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                box = item[0]
                text = str(item[1][0] if isinstance(item[1], (list, tuple)) else item[1])
                score = float(item[1][1]) if isinstance(item[1], (list, tuple)) and len(item[1]) > 1 else 0.0
                parsed.append((box, text, score))
        boxes = [p[0] for p in parsed]
        txts = [p[1] for p in parsed]
        scores = [p[2] for p in parsed]
    entries = []
    for i, text in enumerate(txts):
        clean = str(text).strip()
        if not clean:
            continue
        box = boxes[i] if i < len(boxes) else None
        score = scores[i] if i < len(scores) else 0.0
        entries.append((_box_key(box, i), clean, score))
    entries.sort(key=lambda item: item[0])
    return [e[1] for e in entries], [e[2] for e in entries]


def _box_key(box: Any, fallback: int) -> tuple[int, int, int]:
    try:
        points = list(box)
        xs = [float(p[0]) for p in points]
        ys = [float(p[1]) for p in points]
        return (round(min(ys) / 12), round(min(xs) / 12), fallback)
    except Exception:
        return (fallback, 0, fallback)


def _suspicious_signals(text: str, contains_qr: bool, domains: list[str]) -> list[str]:
    signals: list[str] = []
    if INJECTION_RE.search(text):
        signals.append("prompt_injection")
    if CREDENTIAL_RE.search(text):
        signals.append("credential_request_language")
    if contains_qr and PAYMENT_RE.search(text):
        signals.append("payment_qr_language")
    elif contains_qr:
        signals.append("qr_code_present")
    if PAYMENT_RE.search(text) and URGENT_RE.search(text):
        signals.append("payment_pressure")
    if CHAIN_RE.search(text):
        signals.append("chain_forwarding_language")
    for domain in domains:
        if SUSPICIOUS_DOMAIN_RE.search(domain):
            signals.append(f"suspicious_domain:{domain}")
    return _unique(signals)


def _layout_type(width: int, height: int, lines: list[str], text: str, contains_qr: bool) -> str:
    low = text.casefold()
    if len(lines) == 0 and not contains_qr:
        return "low_text_image"
    if len(lines) >= 14 and height >= width:
        return "document"
    if any(term in low for term in ("organizer", "going?", "guests", "meeting notes", "home - edit")):
        return "screenshot"
    if len(lines) >= 2 or contains_qr:
        return "text_poster"
    return "low_text_image"


def _scene_facts(facts: LocalImageFacts) -> list[str]:
    result: list[str] = []
    if facts.contains_qr:
        result.append("QR code is present")
    if facts.layout_type == "low_text_image":
        result.append("low-information image; OCR found little or no visible text")
    elif facts.layout_type != "unknown":
        result.append(f"image layout appears to be {facts.layout_type}")
    for flag, label in [
        (facts.deadline_language, "visible text contains deadline language"),
        (facts.payment_language, "visible text contains payment language"),
        (facts.credential_request_language, "visible text requests credentials or sensitive codes"),
        (facts.urgent_language, "visible text contains urgency language"),
        (facts.promotion_language, "visible text contains promotional language"),
        (facts.prompt_injection_language, "visible text contains prompt-injection language"),
    ]:
        if flag:
            result.append(label)
    return result[:8]


def _sanitize_error(exc: Exception) -> str:
    text = str(exc) or type(exc).__name__
    text = re.sub(r"[A-Za-z]:\\[^\s]+", "[path]", text)
    text = re.sub(r"[/\\][^\s]+", "[path]", text)
    return f"{type(exc).__name__}:{text}"[:160]


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    try:
        return list(value)
    except TypeError:
        return []


def _bump(stats: Any | None, attr: str) -> None:
    if stats is None:
        return
    setattr(stats, attr, int(getattr(stats, attr, 0)) + 1)
