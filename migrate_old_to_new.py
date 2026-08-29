#!/usr/bin/env python3
"""
Migration script: Tauri (old) database → PySide6 (new) database.

Migrates data from the old Tauri SQLite database (tables: nota, produtos,
expenses) into the new PySide6 database (tables: ORDER, PRODUCT, EXPENSE).

Usage:
    python migrate_old_to_new.py <old_db_path> <new_db_path>

If paths are not provided, the script will prompt the user.
"""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

# Add src/ to sys.path so we can import normalize_text from the project.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from backend.utils.text import normalize_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def real_to_cents(value: float) -> int:
    """Convert a REAL currency value (e.g. 12.34) to integer cents (1234)."""
    return round(value * 100)


def parse_sqlite_date(value: str | None) -> date | None:
    """Parse a DATE column value (YYYY-MM-DD) into a Python date object."""
    if value is None:
        return None
    return date.fromisoformat(str(value))


def parse_sqlite_datetime(value: str | None) -> datetime | None:
    """Parse a DATETIME column value into a Python datetime object."""
    if value is None:
        return None
    # SQLite may store as ISO string or as integer (unix timestamp).
    val = str(value)
    return datetime.strptime(val, "%Y-%m-%d %H:%M:%S.%f %z")


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------

def migrate(old_db: str, new_db: str) -> None:
    """Run the full migration from old_db to new_db."""

    # ---- Validate inputs ---------------------------------------------------
    old_path = Path(old_db)
    new_path = Path(new_db)

    if not old_path.exists():
        print(f"ERROR: Old database not found: {old_db}")
        sys.exit(1)

    if not new_path.exists():
        print(f"ERROR: New database not found: {new_db}")
        sys.exit(1)

    # ---- Connect to databases ----------------------------------------------
    old_conn = sqlite3.connect(str(old_path))
    old_conn.row_factory = sqlite3.Row
    new_conn = sqlite3.connect(str(new_path))
    new_conn.execute("PRAGMA foreign_keys = ON")

    try:
        new_conn.execute("DELETE FROM EXPENSE")
        new_conn.execute("DELETE FROM PRODUCT")
        new_conn.execute('DELETE FROM "ORDER"')
        mappings = _migrate_orders(old_conn, new_conn)
        _migrate_products(old_conn, new_conn, mappings)
        _migrate_expenses(old_conn, new_conn)

        new_conn.commit()

        print("Migration completed successfully.")
    except Exception as exc:
        new_conn.rollback()
        print(f"ERROR: Migration failed — {exc}")
        raise
    finally:
        old_conn.close()
        new_conn.close()


def _migrate_orders(old_conn: sqlite3.Connection, new_conn: sqlite3.Connection) -> dict[int, str]:
    """
    Migrate rows from old 'nota' table to new 'ORDER' table.

    Returns a dict mapping old nota.id → new order UUID.
    """
    cursor = old_conn.execute("SELECT * FROM nota ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("WARNING: No rows found in 'nota' table.")
        return {}

    print(f"Migrating {len(rows)} row(s) from 'nota' → 'ORDER' ...")

    old_to_new_uuid: dict[int, str] = {}

    for row in rows:
        old_id = row["id"]
        new_id = str(uuid.uuid4())

        fornecedor = row["fornecedor"]
        data = row["data"][0:10]
        chave_nfe = row["chaveNFE"]
        frete = real_to_cents(row["frete"]) if row["frete"] is not None else 0
        descarga = real_to_cents(row["descarga"]) if row["descarga"] is not None else 0
        created_at = parse_sqlite_datetime(row["createdAt"])
        updated_at = parse_sqlite_datetime(row["updatedAt"])

        # Default timestamps if missing
        if created_at is None:
            created_at = datetime.now()
        if updated_at is None:
            updated_at = created_at

        new_conn.execute(
            """
            INSERT INTO "ORDER" (
                ID, DATE, SUPPLIER, SUPPLIER_NORMALIZED, NFE_KEY,
                FREIGHT, UNLOADING, CREATED_AT, UPDATED_AT
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                data,
                fornecedor,
                normalize_text(fornecedor),
                chave_nfe,
                frete,
                descarga,
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
                updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

        old_to_new_uuid[old_id] = new_id

    print(f"  → {len(old_to_new_uuid)} order(s) migrated.")
    return old_to_new_uuid


def _migrate_products(
        old_conn: sqlite3.Connection,
        new_conn: sqlite3.Connection,
        old_to_new_uuid: dict[int, str],
) -> None:
    """
    Migrate rows from old 'produtos' table to new 'PRODUCT' table.

    Computes inverse freight distribution for the PRICE column.
    """
    cursor = old_conn.execute("SELECT * FROM produtos ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("WARNING: No rows found in 'produtos' table.")
        return

    # Group products by old nota.id (FK) for freight distribution.
    products_by_order: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        fk = row["fkNota"]
        products_by_order.setdefault(fk, []).append(row)

    print(f"Migrating {len(rows)} row(s) from 'produtos' → 'PRODUCT' ...")

    migrated = 0

    for old_nota_id, product_rows in products_by_order.items():
        new_order_uuid = old_to_new_uuid.get(old_nota_id)
        if new_order_uuid is None:
            raise RuntimeError(
                f"  WARNING: produto row fkNota={old_nota_id} references nota.id not found in old database — skipping.")

            # Pre-compute freight distribution for this order.
        order_total_cents = sum(
            real_to_cents(pr["precoTotal"]) for pr in product_rows
        )
        frete_cursor = old_conn.execute(
            "SELECT frete, descarga FROM nota WHERE id = ?", (old_nota_id,)
        )
        nota_row = frete_cursor.fetchone()
        frete_total = (
                real_to_cents(nota_row["frete"] if nota_row["frete"] is not None else 0)
                + real_to_cents(nota_row["descarga"] if nota_row["descarga"] is not None else 0)
        )

        # Compute ratio for inverse freight distribution.
        ratio: float | None = None
        if order_total_cents > 0 and frete_total >= 0 and (order_total_cents - frete_total) > 0:
            ratio = order_total_cents / (order_total_cents - frete_total)

        for ordinal, pr in enumerate(product_rows, start=1):
            new_id = str(uuid.uuid4())

            preco_unit = real_to_cents(pr["precoUnitario"])

            # Compute PRICE using inverse freight distribution.
            if ratio is not None:
                price = round(preco_unit / ratio)
            else:
                price = preco_unit  # no freight applied

            preco_total = price * int(pr["quantidade"])
            created_at = parse_sqlite_datetime(pr["createdAt"])
            updated_at = parse_sqlite_datetime(pr["updatedAt"])

            if created_at is None:
                created_at = datetime.now()
            if updated_at is None:
                updated_at = created_at

            nome = pr["nome"]

            new_conn.execute(
                """
                INSERT INTO PRODUCT (
                    ID, NAME, NAME_NORMALIZED, QUANTITY, PRICE,
                    PRICE_WITH_FREIGHT, TOTAL_PRICE, ORDER_ID,
                    ITEM_ORDINAL, CREATED_AT, UPDATED_AT
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id,
                    nome,
                    normalize_text(nome),
                    int(pr["quantidade"]),
                    price,
                    preco_unit,
                    preco_total,
                    new_order_uuid,
                    ordinal,
                    created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            migrated += 1

    print(f"  → {migrated} product(s) migrated.")


def _migrate_expenses(
        old_conn: sqlite3.Connection,
        new_conn: sqlite3.Connection,
) -> None:
    """Migrate rows from old 'expenses' table to new 'EXPENSE' table."""
    cursor = old_conn.execute("SELECT * FROM expenses ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("WARNING: No rows found in 'expenses' table.")
        return

    print(f"Migrating {len(rows)} row(s) from 'expenses' → 'EXPENSE' ...")

    migrated = 0

    for row in rows:
        new_id = row["id"]  # keep old integer ID as primary key

        month = int(row["month"])
        year = int(row["year"])
        month_str = f"{year:04d}-{month:02d}"

        description = row["name"]
        value = real_to_cents(row["value"]) if row["value"] is not None else 0
        created_at = parse_sqlite_datetime(row["createdAt"])
        updated_at = parse_sqlite_datetime(row["updatedAt"])

        if created_at is None:
            created_at = datetime.now()
        if updated_at is None:
            updated_at = created_at

        new_conn.execute(
            """
            INSERT INTO EXPENSE (ID, MONTH, DESCRIPTION, VALUE, CREATED_AT, UPDATED_AT)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                month_str,
                description,
                value,
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
                updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        migrated += 1

    print(f"  → {migrated} expense(s) migrated.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _prompt_path(label: str, default: str) -> str:
    """Prompt user for a file path, falling back to *default*."""
    value = input(f"{label} [{default}]: ").strip()
    return value if value else default


def main() -> None:
    if len(sys.argv) >= 3:
        old_db = sys.argv[1]
        new_db = sys.argv[2]
    else:
        raise RuntimeError("Usage: python migrate_old_to_new.py <old_db_path> <new_db_path>")

    print(f"Old database: {old_db}")
    print(f"New database: {new_db}")
    print()

    migrate(old_db, new_db)


if __name__ == "__main__":
    main()
