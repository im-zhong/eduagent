# logger
# https://loguru.readthedocs.io/en/stable/overview.html
from __future__ import annotations

from loguru import Logger
from loguru import logger as loguru_logger

from eduagent.defs import defs


def new_logger() -> Logger:
    """Configure base sinks for application logging."""

    loguru_logger.add(
        sink=defs.pathes.log_dir / "eduagent_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        level="INFO",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    )
    loguru_logger.add(
        sink=defs.pathes.log_dir / "eduagent_error_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="ERROR",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    )
    return loguru_logger


_APP_LOGGER: Logger = new_logger()


def get_logger(name: str | None = None, **context: object) -> Logger:
    """Return the configured application logger bound with optional context."""

    bound = _APP_LOGGER
    if name:
        bound = bound.bind(module=name)
    if context:
        bound = bound.bind(**context)
    return bound


logger: Logger = _APP_LOGGER
