from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def configure_logging(log_dir: str | Path = "data/logs", verbose: bool = False) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if verbose else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    )
    logger.add(
        Path(log_dir) / "autoapply.log",
        rotation="5 MB",
        retention=5,
        level="DEBUG",
        enqueue=True,
        serialize=True,
    )
