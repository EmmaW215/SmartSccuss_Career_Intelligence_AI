"""
GPU Server Logging Configuration

- Dual output: console (colorized) + file (structured)
- RotatingFileHandler to prevent log bloat (10MB x 5 files = 50MB max)
- Structured format: timestamp | level | service | message | extras
- Suppresses noisy third-party loggers
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# Defaults
LOG_DIR = os.environ.get(
    "GPU_LOG_DIR",
    os.path.dirname(os.path.dirname(__file__)),  # gpu-server/
)
LOG_FILE = os.path.join(LOG_DIR, "gpu_server.log")
LOG_LEVEL = os.environ.get("GPU_LOG_LEVEL", "INFO").upper()
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
BACKUP_COUNT = 5              # keep 5 rotated files


def setup_logging() -> logging.Logger:
    """
    Configure and return the root 'gpu' logger.

    Call once at server startup (in lifespan or top of main.py).
    Each service module should use:
        import logging
        logger = logging.getLogger("gpu.<service_name>")
    """
    root_logger = logging.getLogger("gpu")

    # Avoid duplicate handlers if called twice
    if root_logger.handlers:
        return root_logger

    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # ---- Formatter ----
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # ---- File handler (rotating) ----
    os.makedirs(LOG_DIR, exist_ok=True)
    fh = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)  # capture everything to file
    fh.setFormatter(file_fmt)
    root_logger.addHandler(fh)

    # ---- Console handler ----
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    ch.setFormatter(console_fmt)
    root_logger.addHandler(ch)

    # ---- Suppress noisy third-party loggers ----
    for noisy in (
        "uvicorn.access",
        "uvicorn.error",
        "httpcore",
        "httpx",
        "chromadb",
        "sentence_transformers",
        "TTS",
        "numba",
        "matplotlib",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root_logger.info(
        "Logging initialized — file=%s level=%s max=%dMB x %d",
        LOG_FILE, LOG_LEVEL, MAX_BYTES // (1024 * 1024), BACKUP_COUNT,
    )
    return root_logger
