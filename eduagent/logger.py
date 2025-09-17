# logger
# https://loguru.readthedocs.io/en/stable/overview.html

from logging import Logger

from loguru import logger as loguru_logger

from eduagent.defs import defs


def new_logger() -> Logger:
    # 普通日志，每天切分，保留 7 天
    loguru_logger.add(
        sink=defs.pathes.log_dir / "eduagent_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    )

    # 错误日志单独记录，每天切分，保留 30 天
    loguru_logger.add(
        sink=defs.pathes.log_dir / "eduagent_error_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    )

    return loguru_logger  # type: ignore


logger: Logger = new_logger()
