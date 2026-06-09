"""
TRINKER - Logging Setup
Configures rotating file + console logging for the entire application.
All modules import `logger` from here.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from .config import APP_DIRS


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """
    Initialize and return the root application logger.
    Creates a rotating file handler (max 5MB, 3 backups) and a console handler.

    Args:
        level: Logging level (default: DEBUG for development).

    Returns:
        Configured logger instance named 'trinker'.
    """
    log_dir = APP_DIRS.user_log_dir
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / "trinker.log"

    log = logging.getLogger("trinker")
    log.setLevel(level)

    # Avoid adding duplicate handlers if setup_logging is called multiple times
    if log.handlers:
        return log

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler — keeps logs between sessions
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    # Console handler — shows INFO and above in the terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    log.addHandler(file_handler)
    log.addHandler(console_handler)

    log.info("TRINKER logging initialized. Log file: %s", log_path)
    return log


# Module-level singleton — import this everywhere: from src.core.logger import logger
logger = setup_logging()
