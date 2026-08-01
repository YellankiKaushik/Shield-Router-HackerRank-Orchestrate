from argparse import Namespace
from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import cmd_prepare_models, make_provider
from shieldrouter.provider import LocalVoiceProvider


ROOT = Path(__file__).resolve().parents[2]


def test_local_voice_provider_ignores_openrouter_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "not-openrouter")
    args = Namespace(local_voice=True, online=False, cache_dir=str(tmp_path))
    provider = make_provider(args)
    assert isinstance(provider, LocalVoiceProvider)
    assert provider.stats.request_count == 0


def test_prepare_models_initializes_required_local_models(monkeypatch, capsys):
    created = {"rapidocr": 0, "whisper": []}

    class FakeRapidOCR:
        def __init__(self):
            created["rapidocr"] += 1

    class FakeWhisperModel:
        def __init__(self, model_name, **kwargs):
            created["whisper"].append((model_name, kwargs))

    hf_home = Path.home() / ".cache" / "shieldrouter-test-hf"
    rapidocr_init = hf_home / "rapidocr" / "__init__.py"
    monkeypatch.setenv("HF_HOME", str(hf_home))
    monkeypatch.setenv("LOCAL_WHISPER_MODEL", "tiny")
    monkeypatch.setitem(sys.modules, "rapidocr", types.SimpleNamespace(RapidOCR=FakeRapidOCR, __file__=str(rapidocr_init)))
    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisperModel))

    assert cmd_prepare_models(Namespace(whisper_model=None)) == 0

    out = capsys.readouterr().out
    assert "MODEL PREPARATION OK" in out
    assert "Faster-Whisper model: tiny" in out
    assert created["rapidocr"] == 1
    assert created["whisper"] == [("tiny", {"device": "cpu", "compute_type": "int8", "local_files_only": False})]


def test_prepare_models_refuses_repo_local_model_cache(monkeypatch, capsys):
    monkeypatch.setenv("HF_HOME", str(ROOT / ".tmp" / "hf-cache"))

    assert cmd_prepare_models(Namespace(whisper_model="tiny")) == 1

    out = capsys.readouterr().out
    assert "inside the repository" in out
