from __future__ import annotations

import logging
import os
import shutil
from datetime import date

from backend.database.connection import discover_database_path
from backend.errors import BackupError
from backend.utils.backup import (
    compute_retention_decision,
    parse_backup_filename,
)

_logger: logging.Logger = logging.getLogger(__name__)


class BackupService:
    """
    Creates daily SQLite database backups and enforces a tiered retention policy.

    This service operates purely on the filesystem — it does not depend on the
    database Engine, Session, or any ORM entity.

    Attributes:
        _backup_dir: Path to the directory where backup files are stored.
    """

    def __init__(self, backup_dir: str) -> None:
        """
        Initialize the backup service.

        Args:
            backup_dir: Absolute path to the backup directory. The directory is
                created if it does not exist.
        """
        self._backup_dir: str = backup_dir
        os.makedirs(self._backup_dir, exist_ok=True)

    def create_backup(self) -> str:
        """
        Copy the SQLite database file to the backup directory with today's date.

        If a backup for today already exists, it is overwritten.

        Args:
            db_path: Absolute path to the active ``main.db`` file.

        Returns:
            The absolute path to the created backup file (e.g.
            ``C:\\Users\\...\\db-2026-08-09.db``).

        Raises:
            BackupError: If ``db_path`` does not exist or is not a file.
        """
        db_path = discover_database_path()
        if not os.path.isfile(db_path):
            raise BackupError(f"Arquivo de banco de dados não encontrado: {db_path}")

        today_iso: str = date.today().strftime("%Y-%m-%d")
        backup_filename: str = f"db-{today_iso}.db"
        backup_file_path: str = os.path.join(self._backup_dir, backup_filename)

        shutil.copy2(db_path, backup_file_path)
        _logger.info("Backup criado: %s", backup_file_path)

        return backup_file_path

    def prune_backups(self, today: date | None = None) -> None:
        """
        Remove backup files that exceed the retention policy.

        Args:
            today: Optional date used as "today" for age calculations.
                Defaults to :func:`date.today` when not provided. Useful for
                testing with a fixed date.

        Retention policy:

        * Daily (0–10 days old): keep all.
        * Weekly 1 (11–20 days): keep most recent only.
        * Weekly 2 (21–30 days): keep most recent only.
        * Monthly (31+ days): keep most recent per calendar month.

        Individual file deletions that fail are logged but do not abort the
        entire pruning pass.
        """
        backup_entries: list[tuple[date, str]] = []

        try:
            for filename in os.listdir(self._backup_dir):
                if not filename.endswith(".db"):
                    continue
                backup_date = parse_backup_filename(filename)
                if backup_date is None:
                    continue
                file_path: str = os.path.join(self._backup_dir, filename)
                backup_entries.append((backup_date, file_path))
        except OSError as exc:
            _logger.error(f"Não foi possível listar backups: {exc}", exc_info=True)
            return

        # Sort by date descending (newest first)
        backup_entries.sort(key=lambda entry: entry[0], reverse=True)

        if not backup_entries:
            return

        _, delete_paths = compute_retention_decision(backup_entries, today)

        for file_path in delete_paths:
            try:
                os.remove(file_path)
                _logger.info("Backup removido (política de retenção): %s", file_path)
            except OSError as exc:
                _logger.warning("Não foi possível remover %s: %s", file_path, exc)

    def get_backup_dir(self) -> str:
        """
        Return the backup directory path.

        Returns:
            The backup directory path (``self._backup_dir``).
        """
        return self._backup_dir
