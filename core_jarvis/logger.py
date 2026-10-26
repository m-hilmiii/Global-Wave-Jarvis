"""
JARVIS Centralized Logging Engine
Provides structured, thread-safe, rotating file and console logging across all Jarvis modules.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "jarvis.log"

_CONFIGURED = False
_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_central_logging(default_level: int = logging.INFO) -> None:
    """Configures root logger with console and rotating file handler."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(default_level)

    # Formatter
    formatter = logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT)

    # 1. Console Handler (UTF-8 safe stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(default_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler (10 MB max, 5 backups)
    try:
        file_handler = RotatingFileHandler(
            str(LOG_FILE),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(default_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"[JARVIS Logger] Failed to initialize file handler: {e}\n")

    # Suppress overly chatty 3rd-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Returns a named logger, ensuring central logging configuration is initialized."""
    if not _CONFIGURED:
        setup_central_logging()
    return logging.getLogger(name or "jarvis")
