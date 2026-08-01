from argparse import Namespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import make_provider
from shieldrouter.provider import LocalVoiceProvider


def test_local_voice_provider_ignores_openrouter_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "not-openrouter")
    args = Namespace(local_voice=True, online=False, cache_dir=str(tmp_path))
    provider = make_provider(args)
    assert isinstance(provider, LocalVoiceProvider)
    assert provider.stats.request_count == 0
