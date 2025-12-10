from __future__ import annotations

from pathlib import Path


def _find_repo_root(anchor: Path) -> Path:
    for parent in anchor.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    msg = "Unable to locate project root from tests directory"
    raise RuntimeError(msg)


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
DOCS_PATH = REPO_ROOT / "docs"


def docs_file(*parts: str) -> Path:
    path = DOCS_PATH.joinpath(*parts)
    if not path.exists():
        msg = f"Documentation artifact not found: {path}"
        raise FileNotFoundError(msg)
    return path


__all__ = ["DOCS_PATH", "REPO_ROOT", "docs_file"]
