from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shieldrouter.io import DatasetError, load_dataset, safe_media_path, validate_dataset


ROOT = Path(__file__).resolve().parents[2]


def test_real_dataset_validates():
    tables = load_dataset(ROOT / "dataset")
    assert validate_dataset(ROOT / "dataset", tables) == []


def test_media_path_escape_rejected():
    try:
        safe_media_path(ROOT / "dataset", "../secret.txt")
    except DatasetError as exc:
        assert "escapes" in str(exc)
    else:
        raise AssertionError("expected DatasetError")
