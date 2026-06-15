"""
utils/logger.py – structured logging configuration.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from config import config


def setup_logging() -> None:
    Path(config.log_file).parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    # Console
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # Rotating file
    fh = logging.handlers.RotatingFileHandler(
        config.log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Silence noisy libraries
    for lib in ("aiogram", "aiosqlite", "asyncio"):
        logging.getLogger(lib).setLevel(logging.WARNING)
