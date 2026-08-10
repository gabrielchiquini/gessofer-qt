from __future__ import annotations

import os
from datetime import date, datetime
from typing import Set, Tuple

# ── Constants ────────────────────────────────────────────────────────────────

BACKUP_FILENAME_PATTERN: str = "db-%Y-%m-%d.db"

BACKUP_DIR_SUFFIX: str = "gessofer-app\\db-backup"


# ── Filename parsing ─────────────────────────────────────────────────────────

def parse_backup_filename(filename: str) -> date | None:
    """
    Extract the ``date`` object from a backup filename like ``db-2026-08-09.db``.

    Args:
        filename: e.g. ``"db-2026-08-09.db"``.

    Returns:
        The parsed :class:`date`, or ``None`` if the filename doesn't match the
        expected pattern.
    """
    try:
        if not filename.endswith(".db"):
            return None
        stripped = filename[:-3]  # remove ".db" suffix
        if not stripped.startswith("db-"):
            return None
        date_str = stripped[3:]  # remove "db-" prefix
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None


def get_backup_path(db_dir: str, backup_date: date) -> str:
    """
    Construct the full backup file path for a given date.

    Args:
        db_dir: The backup directory path.
        backup_date: The date to encode in the filename.

    Returns:
        e.g. ``C:\\Users\\...\\db-2026-08-09.db``.
    """
    return os.path.join(db_dir, f"db-{backup_date.strftime('%Y-%m-%d')}.db")


# ── Retention policy helpers ─────────────────────────────────────────────────

def classify_backup(age_days: int) -> str:
    """
    Classify a backup into its retention bucket based on age.

    Args:
        age_days: Number of days between today and the backup date.

    Returns:
        One of ``"daily"``, ``"weekly_1"``, ``"weekly_2"``, ``"monthly"``.
    """
    if age_days <= 10:
        return "daily"
    if age_days <= 20:
        return "weekly_1"
    if age_days <= 30:
        return "weekly_2"
    return "monthly"


def compute_retention_decision(
    backup_list: list[tuple[date, str]],
    today: date | None = None,
) -> tuple[set[str], set[str]]:
    """
    Given a list of ``(backup_date, file_path)`` tuples sorted by date
    descending, return ``(paths_to_keep, paths_to_delete)``.

    Retention policy:

    * **Daily** (0–10 days old): keep all.
    * **Weekly 1** (11–20 days): keep most recent only.
    * **Weekly 2** (21–30 days): keep most recent only.
    * **Monthly** (31+ days): keep most recent per calendar month.

    Args:
        backup_list: Sorted by date descending.
        today: Today's date (defaults to :func:`date.today`).

    Returns:
        ``(keep_paths, delete_paths)`` — two sets of file paths.
    """
    today = today or date.today()

    # Categorize each backup into a retention bucket
    buckets: dict[str, list[tuple[date, str]]] = {
        "daily": [],
        "weekly_1": [],
        "weekly_2": [],
        "monthly": [],
    }

    for backup_date, file_path in backup_list:
        age_days = (today - backup_date).days
        if age_days <= 10:
            buckets["daily"].append((backup_date, file_path))
        elif age_days <= 20:
            buckets["weekly_1"].append((backup_date, file_path))
        elif age_days <= 30:
            buckets["weekly_2"].append((backup_date, file_path))
        else:
            buckets["monthly"].append((backup_date, file_path))

    # Select which to keep
    keep_paths: set[str] = set()

    # Daily: keep all
    for _backup_date, fp in buckets["daily"]:
        keep_paths.add(fp)

    # Weekly ranges: keep most recent only (already sorted by date desc)
    for bucket_name in ("weekly_1", "weekly_2"):
        entries = buckets[bucket_name]
        if entries:
            keep_paths.add(entries[0][1])

    # Monthly: keep most recent per calendar month
    monthly_groups: dict[tuple[int, int], list[tuple[date, str]]] = {}
    for backup_date, file_path in buckets["monthly"]:
        key = (backup_date.year, backup_date.month)
        if key not in monthly_groups:
            monthly_groups[key] = []
        monthly_groups[key].append((backup_date, file_path))

    for _key, entries in monthly_groups.items():
        # entries are already sorted by date desc (inherited from backup_list)
        keep_paths.add(entries[0][1])

    # Everything not in keep_paths is deleted
    all_paths: set[str] = {fp for _backup_date, fp in backup_list}
    delete_paths: set[str] = all_paths - keep_paths

    return keep_paths, delete_paths


# ── Directory discovery ──────────────────────────────────────────────────────

def discover_backup_dir() -> str:
    """
    Resolve the backup directory path from ``%LOCALAPPDATA%``.

    Returns:
        e.g. ``C:\\Users\\...\\AppData\\Local\\gessofer-app\\db-backup``.
    """
    localappdata: str = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(localappdata, "gessofer-app", "db-backup")
