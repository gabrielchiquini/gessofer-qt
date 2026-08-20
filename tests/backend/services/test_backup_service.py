from __future__ import annotations

import os
import shutil
import tempfile
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from backend.errors import BackupError
from backend.services.backup_service import BackupService
from backend.utils.backup import (
    BACKUP_DIR_SUFFIX,
    classify_backup,
    compute_retention_decision,
    discover_backup_dir,
    get_backup_path,
    parse_backup_filename,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_backup_dir(tmp_path: pytest.TempPathFactory) -> str:
    """Return a temporary directory for backup files."""
    return str(tmp_path)


@pytest.fixture()
def sample_db(tmp_path: pytest.TempPathFactory) -> str:
    """Return a temporary file simulating a database."""
    db_file = tmp_path / "main.db"
    db_file.write_bytes(b"fake sqlite database content")
    return str(db_file)


# ── parse_backup_filename ────────────────────────────────────────────────────


class TestParseBackupFilename:
    def test_valid_filename(self) -> None:
        result = parse_backup_filename("db-2026-08-09.db")
        assert result == date(2026, 8, 9)

    def test_valid_filename_leading_zero(self) -> None:
        result = parse_backup_filename("db-2026-01-01.db")
        assert result == date(2026, 1, 1)

    def test_invalid_prefix(self) -> None:
        result = parse_backup_filename("random-file.db")
        assert result is None

    def test_missing_extension(self) -> None:
        result = parse_backup_filename("db-2026-08-09")
        assert result is None

    def test_invalid_date(self) -> None:
        result = parse_backup_filename("db-2026-13-45.db")
        assert result is None

    def test_empty_string(self) -> None:
        result = parse_backup_filename("")
        assert result is None


# ── get_backup_path ──────────────────────────────────────────────────────────


class TestGetBackupPath:
    def test_path_construction(self) -> None:
        path = get_backup_path("/backups", date(2026, 8, 9))
        assert path == os.path.join("/backups", "db-2026-08-09.db")

    def test_path_with_trailing_slash(self) -> None:
        path = get_backup_path("/backups/", date(2026, 1, 1))
        expected = "/backups/db-2026-01-01.db"
        assert path == expected


# ── classify_backup ──────────────────────────────────────────────────────────


class TestClassifyBackup:
    def test_daily_zero_days(self) -> None:
        assert classify_backup(0) == "daily"

    def test_daily_edge(self) -> None:
        assert classify_backup(10) == "daily"

    def test_weekly_1_start(self) -> None:
        assert classify_backup(11) == "weekly_1"

    def test_weekly_1_end(self) -> None:
        assert classify_backup(20) == "weekly_1"

    def test_weekly_2_start(self) -> None:
        assert classify_backup(21) == "weekly_2"

    def test_weekly_2_end(self) -> None:
        assert classify_backup(30) == "weekly_2"

    def test_monthly_start(self) -> None:
        assert classify_backup(31) == "monthly"

    def test_monthly_far_future(self) -> None:
        assert classify_backup(365) == "monthly"


# ── compute_retention_decision ───────────────────────────────────────────────


class TestComputeRetentionDecision:
    def _make_entries(
        self, days_ago_list: list[int], today: date | None = None
    ) -> list[tuple[date, str]]:
        """Helper to create (date, filepath) tuples."""
        today = today or date.today()
        entries: list[tuple[date, str]] = []
        for days_ago in sorted(days_ago_list, reverse=True):
            backup_date = today - timedelta(days=days_ago)
            filepath = f"/backups/db-{backup_date.isoformat()}.db"
            entries.append((backup_date, filepath))
        return entries

    def test_daily_keeps_all(self) -> None:
        """All backups within 10 days should be kept."""
        days = list(range(11))  # 0 through 10
        today = date(2026, 8, 9)
        entries = self._make_entries(days, today)
        keep, delete = compute_retention_decision(entries, today)
        assert len(delete) == 0
        assert len(keep) == 11

    def test_weekly_1_keeps_only_most_recent(self) -> None:
        """Only the most recent backup in D-11..D-20 should be kept."""
        today = date(2026, 8, 9)
        entries = self._make_entries([11, 15, 20], today)
        keep, delete = compute_retention_decision(entries, today)
        assert len(keep) == 1
        assert len(delete) == 2

    def test_weekly_2_keeps_only_most_recent(self) -> None:
        """Only the most recent backup in D-21..D-30 should be kept."""
        today = date(2026, 8, 9)
        entries = self._make_entries([21, 25, 30], today)
        keep, delete = compute_retention_decision(entries, today)
        assert len(keep) == 1
        assert len(delete) == 2

    def test_monthly_keeps_one_per_calendar_month(self) -> None:
        """Two backups in the same calendar month → keep only the newest."""
        today = date(2026, 8, 9)
        # Two backups in June 2026
        entries = [
            (date(2026, 6, 20), "/backups/db-2026-06-20.db"),
            (date(2026, 6, 10), "/backups/db-2026-06-10.db"),
            # One backup in May 2026
            (date(2026, 5, 15), "/backups/db-2026-05-15.db"),
        ]
        keep, delete = compute_retention_decision(entries, today)
        # June: keep 20th, delete 10th. May: keep 15th.
        assert len(keep) == 2
        assert len(delete) == 1

    def test_empty_list(self) -> None:
        """No backups → nothing to delete."""
        today = date(2026, 8, 9)
        keep, delete = compute_retention_decision([], today)
        assert len(keep) == 0
        assert len(delete) == 0

    def test_full_scenario(self) -> None:
        """Full retention scenario matching the plan's example."""
        today = date(2026, 8, 9)
        entries = [
            (date(2026, 8, 9), "/backups/db-2026-08-09.db"),  # daily
            (date(2026, 8, 8), "/backups/db-2026-08-08.db"),  # daily
            (date(2026, 8, 5), "/backups/db-2026-08-05.db"),  # daily
            (date(2026, 8, 1), "/backups/db-2026-08-01.db"),  # daily
            (date(2026, 7, 28), "/backups/db-2026-07-28.db"),  # weekly_1
            (date(2026, 7, 22), "/backups/db-2026-07-22.db"),  # weekly_1
            (date(2026, 7, 15), "/backups/db-2026-07-15.db"),  # weekly_2
            (date(2026, 7, 10), "/backups/db-2026-07-10.db"),  # weekly_2
            (date(2026, 6, 20), "/backups/db-2026-06-20.db"),  # monthly (Jun)
            (date(2026, 5, 15), "/backups/db-2026-05-15.db"),  # monthly (May)
            (date(2026, 4, 10), "/backups/db-2026-04-10.db"),  # monthly (Apr)
        ]
        keep, delete = compute_retention_decision(entries, today)
        # Expected keeps: 4 daily + 1 weekly_1 (Jul 28) + 1 weekly_2 (Jul 15) + 3 monthly (Jun, May, Apr) = 9
        # Expected deletes: Jul 22, Jul 10 = 2
        assert len(keep) == 9
        assert len(delete) == 2


# ── discover_backup_dir ──────────────────────────────────────────────────────


class TestDiscoverBackupDir:
    def test_path_contains_suffix(self) -> None:
        with patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\test"}):
            result = discover_backup_dir()
        assert "gessofer-app" in result
        assert "db-backup" in result

    def test_returns_absolute_path(self) -> None:
        with patch.dict(os.environ, {"LOCALAPPDATA": os.path.join("C:", os.sep, "Users", "test")}):
            result = discover_backup_dir()
        assert os.path.isabs(result)


# ── BackupService.create_backup ─────────────────────────────────────────────


class TestBackupServiceCreateBackup:
    def test_creates_backup_file(
        self, tmp_backup_dir: str, sample_db: str
    ) -> None:
        service = BackupService(backup_dir=tmp_backup_dir)
        result = service.create_backup(sample_db)
        assert os.path.isfile(result)
        assert result.endswith(".db")

    def test_backup_content_matches_source(
        self, tmp_backup_dir: str, sample_db: str
    ) -> None:
        service = BackupService(backup_dir=tmp_backup_dir)
        service.create_backup(sample_db)
        backup_file = os.path.join(tmp_backup_dir, os.path.basename(
            [f for f in os.listdir(tmp_backup_dir) if f.endswith(".db")][0]
        ))
        with open(sample_db, "rb") as f:
            original = f.read()
        with open(backup_file, "rb") as f:
            backed_up = f.read()
        assert original == backed_up

    def test_overwrites_today_backup(
        self, tmp_backup_dir: str, sample_db: str
    ) -> None:
        service = BackupService(backup_dir=tmp_backup_dir)
        # First backup
        path1 = service.create_backup(sample_db)
        mtime1 = os.path.getmtime(path1)

        # Wait a moment and backup again
        import time
        time.sleep(0.1)
        path2 = service.create_backup(sample_db)
        mtime2 = os.path.getmtime(path2)

        assert path1 == path2
        assert mtime2 >= mtime1

    def test_raises_on_missing_db(
        self, tmp_backup_dir: str
    ) -> None:
        service = BackupService(backup_dir=tmp_backup_dir)
        with pytest.raises(BackupError, match="Arquivo de banco de dados não encontrado"):
            service.create_backup("/nonexistent/path/main.db")


# ── BackupService.prune_backups ─────────────────────────────────────────────


class TestBackupServicePruneBackups:
    def _seed_backups(
        self,
        backup_dir: str,
        days_ago_list: list[int],
        today: date | None = None,
    ) -> None:
        """Create dummy backup files for the given days ago."""
        today = today or date.today()
        for days_ago in days_ago_list:
            backup_date = today - timedelta(days=days_ago)
            filename = f"db-{backup_date.isoformat()}.db"
            filepath = os.path.join(backup_dir, filename)
            with open(filepath, "wb") as f:
                f.write(b"fake backup")

    def test_prune_keeps_daily(self, tmp_backup_dir: str) -> None:
        today = date(2026, 8, 9)
        self._seed_backups(tmp_backup_dir, list(range(11)), today)
        service = BackupService(backup_dir=tmp_backup_dir)
        service.prune_backups(today)
        remaining = [f for f in os.listdir(tmp_backup_dir) if f.endswith(".db")]
        assert len(remaining) == 11

    def test_prune_keeps_one_per_weekly_range(self, tmp_backup_dir: str) -> None:
        today = date(2026, 8, 9)
        self._seed_backups(tmp_backup_dir, [11, 15, 20], today)
        service = BackupService(backup_dir=tmp_backup_dir)
        service.prune_backups(today)
        remaining = [f for f in os.listdir(tmp_backup_dir) if f.endswith(".db")]
        assert len(remaining) == 1

    def test_prune_keeps_one_per_month(self, tmp_backup_dir: str) -> None:
        today = date(2026, 8, 9)
        # Two backups in June 2026
        self._seed_backups(tmp_backup_dir, [50, 55], today)
        service = BackupService(backup_dir=tmp_backup_dir)
        service.prune_backups()
        remaining = [f for f in os.listdir(tmp_backup_dir) if f.endswith(".db")]
        assert len(remaining) == 1

    def test_prune_ignores_non_matching_files(self, tmp_backup_dir: str) -> None:
        """Files that don't match db-YYYY-MM-DD.db should be left alone."""
        today = date(2026, 8, 9)
        self._seed_backups(tmp_backup_dir, [0], today)
        # Add a non-matching file
        other = os.path.join(tmp_backup_dir, "random-file.db")
        with open(other, "wb") as f:
            f.write(b"not a backup")
        service = BackupService(backup_dir=tmp_backup_dir)
        service.prune_backups()
        remaining = os.listdir(tmp_backup_dir)
        assert len(remaining) == 2  # backup + random-file.db

    def test_prune_empty_dir(self, tmp_backup_dir: str) -> None:
        service = BackupService(backup_dir=tmp_backup_dir)
        service.prune_backups()  # Should not raise


# ── BackupService.get_backup_dir ────────────────────────────────────────────


class TestBackupServiceGetBackupDir:
    def test_returns_dir_path(self, tmp_backup_dir: str) -> None:
        service = BackupService(backup_dir=tmp_backup_dir)
        assert service.get_backup_dir() == tmp_backup_dir
