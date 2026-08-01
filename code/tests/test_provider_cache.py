from pathlib import Path
import json
import urllib.error

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.provider import OpenRouterConfig, OpenRouterProvider, ProviderBudgetExceeded


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _provider(tmp_path, monkeypatch, **kwargs):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    return OpenRouterProvider(
        cache_dir=tmp_path,
        config=OpenRouterConfig(max_requests=kwargs.pop("max_requests", 35), max_retries=kwargs.pop("max_retries", 1), **kwargs),
    )


def _success_payload(model="free/model"):
    return {"model": model, "choices": [{"message": {"content": json.dumps({"ok": True})}}]}


def test_cache_hit_and_invalidation_without_network(tmp_path, monkeypatch):
    provider = _provider(tmp_path, monkeypatch)
    key1 = provider._preflight_key("task", {"a": 1}, provider.config.text_model, "", "p1", "s1")
    (provider.cache_dir / f"{key1}.json").write_text(
        json.dumps({"response": {"ok": True}, "actual_model": "free/model"}),
        encoding="utf-8",
    )
    assert provider.json_task("task", "instructions", {"a": 1}, prompt_version="p1", schema_version="s1") == {"ok": True}
    assert provider.stats.cache_hits == 1
    assert provider.stats.request_count == 0
    key2 = provider._preflight_key("task", {"a": 2}, provider.config.text_model, "", "p1", "s1")
    assert key1 != key2


def test_request_cap_enforced_before_network(tmp_path, monkeypatch):
    provider = _provider(tmp_path, monkeypatch, max_requests=0)
    called = False

    def fake_urlopen(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(ProviderBudgetExceeded):
        provider.json_task("task", "instructions", {"a": 1})
    assert called is False
    assert provider.stats.request_count == 0


def test_retry_accounting_for_429(tmp_path, monkeypatch):
    provider = _provider(tmp_path, monkeypatch, max_requests=3, max_retries=1)
    calls = {"n": 0}

    def fake_urlopen(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError("url", 429, "rate", {}, None)
        return _Response(_success_payload())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert provider.json_task("task", "instructions", {"a": 1}) == {"ok": True}
    assert provider.stats.request_count == 2
    assert provider.stats.retries == 1


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404])
def test_no_retry_for_auth_payment_or_bad_request_errors(tmp_path, monkeypatch, status):
    provider = _provider(tmp_path, monkeypatch, max_requests=3, max_retries=1)

    def fake_urlopen(*_args, **_kwargs):
        raise urllib.error.HTTPError("url", status, "nope", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(Exception):
        provider.json_task("task", "instructions", {"a": 1})
    assert provider.stats.request_count == 1
    assert provider.stats.retries == 0


def test_image_data_url_uses_base64_and_mime(tmp_path, monkeypatch):
    image = tmp_path / "poster.jpg"
    image.write_bytes(b"\xff\xd8fake")
    provider = _provider(tmp_path, monkeypatch)
    mime, data_url = provider.image_data_url(image)
    assert mime == "image/jpeg"
    assert data_url.startswith("data:image/jpeg;base64,")


def test_cache_hit_after_success_consumes_zero_requests(tmp_path, monkeypatch):
    provider = _provider(tmp_path, monkeypatch)

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: _Response(_success_payload("free/a")))
    assert provider.json_task("task", "instructions", {"a": 1}) == {"ok": True}
    assert provider.stats.request_count == 1
    before = provider.stats.request_count
    assert provider.json_task("task", "instructions", {"a": 1}) == {"ok": True}
    assert provider.stats.request_count == before
    assert provider.stats.cache_hits == 1
