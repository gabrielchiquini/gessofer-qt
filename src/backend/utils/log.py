from __future__ import annotations

import logging
import os
from datetime import date
from typing import Literal

# ── Constants ────────────────────────────────────────────────────────────────

_LOG_FORMAT: str = "{asctime} | {levelname:<8} | {name:<12} | {message}"
_LOG_STYLE: Literal["%", "{", "$"] = "{"


# ── Directory discovery ──────────────────────────────────────────────────────

def discover_log_dir() -> str:
    """
    Resolve the log directory path from ``%LOCALAPPDATA%``.

    Returns:
        e.g. ``C:\\Users\\...\\AppData\\Local\\gessofer-app\\logs``.
        Falls back to ``"logs"`` (relative to CWD) if ``LOCALAPPDATA`` is
        unset or empty.
    """
    localappdata: str = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        return os.path.join(localappdata, "gessofer-app", "logs")
    return "logs"


# ── Log file setup ───────────────────────────────────────────────────────────

_handler_installed: bool = False


def setup_log() -> None:
    """
    Attach a :class:`logging.FileHandler` to the root logger so that all
    Python logging (including Qt messages) is written to a daily log file.

    The log file is named ``log-YYYY-MM-DD.log`` inside the directory
    returned by :func:`discover_log_dir`.  If the file already exists it is
    opened in **append** mode.  The log directory is created automatically
    if it does not exist.

    If the log file cannot be created (permission denied, disk full, etc.)
    the function logs an error to stderr and returns silently — the
    application must still start.

    This function is idempotent: calling it a second time is a no-op.
    """

    global _handler_installed
    if _handler_installed:
        return

    logging.basicConfig(
        level=logging.DEBUG,
        style=_LOG_STYLE,
        format=_LOG_FORMAT
    )
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    try:
        log_dir: str = discover_log_dir()
        os.makedirs(log_dir, exist_ok=True)

        log_file: str = os.path.join(
            log_dir,
            f"log-{date.today().strftime('%Y-%m-%d')}.log",
        )

        handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, style=_LOG_STYLE))

        logging.getLogger().addHandler(handler)
        _handler_installed = True
    except (OSError, PermissionError) as exc:
        # At this point only console logging is available (basicConfig has
        # already run in main.py), so this error goes to stderr only.
        logging.error("Falha ao configurar log em arquivo: %s", exc)
