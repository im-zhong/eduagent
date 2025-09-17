from pathlib import Path

from eduagent.defs import defs


def test_defs() -> None:
    assert defs.pathes.log_dir == Path("logs")
    # make sure log_dir is created
    assert defs.pathes.log_dir.exists()
