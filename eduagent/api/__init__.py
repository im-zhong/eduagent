from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from fastapi import FastAPI

__all__ = ["api"]

api: FastAPI

if TYPE_CHECKING:
    from .api import api as _fastapi_app

    api = _fastapi_app


def __getattr__(name: str) -> FastAPI:
    if name == "api":
        return import_module("eduagent.api.api").api
    raise AttributeError(name)
