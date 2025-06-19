from __future__ import annotations

import os
import sys

import loguru

loguru.logger.remove()

if os.environ.get("LOGGER_FORMAT", "text") == "text":
    logger_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    loguru.logger.add(sys.stdout, format=logger_format)
else:
    logger_format = "{time} {level} {message}"
    loguru.logger.add(sys.stdout, serialize=True, format=logger_format)


def get_logger() -> loguru.Logger:
    return loguru.logger


class Logger:
    def __init__(self):
        self.logger = get_logger()

    def info(self, msg: str) -> None:
        self.logger.opt(depth=1).info(msg)

    def debug(self, msg: str) -> None:
        self.logger.opt(depth=1).debug(msg)

    def error(self, msg: str) -> None:
        self.logger.opt(depth=1).error(msg)

    def warn(self, msg: str) -> None:
        self.logger.opt(depth=1).warning(msg)

logger = Logger()