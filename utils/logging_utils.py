import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.path_utils import get_app_base_dir


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOGGER_INITIALIZED = False


def get_log_dir() -> Path:
    log_dir = get_app_base_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging() -> Path:
    global _LOGGER_INITIALIZED
    log_file = get_log_dir() / "bsimplehires.log"

    if _LOGGER_INITIALIZED:
        return log_file

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    _LOGGER_INITIALIZED = True
    return log_file


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
