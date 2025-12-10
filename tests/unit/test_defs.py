from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from eduagent.defs import defs


def test_defs() -> None:
    assert defs.pathes.log_dir == Path("logs")
    # make sure log_dir is created
    assert defs.pathes.log_dir.exists()


def test_uploads_dir_env_override(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    override = tmp_path / "custom" / "uploads"
    monkeypatch.setenv("EDUAGENT_UPLOADS_DIR", str(override))
    uploads_dir = defs.pathes.uploads_dir
    assert uploads_dir == override
    assert uploads_dir.exists()
