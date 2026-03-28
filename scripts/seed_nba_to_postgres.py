"""
Seed script — copies key NBA tables from local nba.sqlite into a Postgres database.

Usage:
    python scripts/seed_nba_to_postgres.py \
        --sqlite sample_dbs/sqlite/nba.sqlite \
        --postgres "postgresql://user:pass@host/dbname"

The script is idempotent: it drops and recreates each table on every run.
Skip play_by_play (13.5M rows) to stay within Render's 1 GB free tier.
"""

import argparse
import sqlite3
import re
import sys
import time

# Tables to migrate and optional row limit (None = all rows)
TABLES = {
    "team":               None,
    "team_details":       None,
    "team_history":       None,
    "player":             None,
    "common_player_info": None,
    "draft_history":      None,
    "draft_combine_stats": None,
    "game":               50_000,   # cap to ~50k most recent games
    "game_summary":       50_000,
    "game_info":          50_000,
    "line_score":         50_000,
    "officials":          50_000,
    "other_stats":        28_271,   # all rows — manageable
    # play_by_play skipped — 13.5M rows
}

# SQLite → Postgres type mapping
_TYPE_MAP = {
    "INTEGER": "BIGINT",
    "REAL":    "DOUBLE PRECISION",
    "TEXT":    "TEXT",
    "BLOB":    "BYTEA",
    "NUMERIC": "NUMERIC",
}


def _pg_type(sqlite_type: str) -> str:
    upper = sqlite_type.upper().strip()
    for k, v in _TYPE_MAP.items():
        if k in upper:
            return v
    return "TEXT"


def _sanitize(name: str) -> str:
    """Quote identifiers to avoid reserved-word clashes."""
    return f'"{name}"'


def migrate(sqlite_path: str, pg_url: str) -> None:
    try:
        import sqlalchemy
        from sqlalchemy import create_engine, text
    except ImportError:
        sys.exit("Run:  pip install sqlalchemy psycopg2-binary")

    print(f"Source : {sqlite_path}")
    print(f"Target : {pg_url}\n")

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row

    engine = create_engine(pg_url)

    for table, row_limit in TABLES.items():
        t0 = time.perf_counter()

        # --- get SQLite schema ---
        cols_info = src.execute(f"PRAGMA table_info(\"{table}\")").fetchall()
        if not cols_info:
            print(f"  SKIP  {table} (not found in SQLite)")
            continue

        col_defs = ", ".join(
            f"{_sanitize(c['name'])} {_pg_type(c['type'])}"
            for c in cols_info
        )

        with engine.begin() as pg:
            # Drop + recreate
            pg.execute(text(f"DROP TABLE IF EXISTS {_sanitize(table)} CASCADE"))
            pg.execute(text(f"CREATE TABLE {_sanitize(table)} ({col_defs})"))

        # --- fetch rows from SQLite ---
        limit_clause = f"LIMIT {row_limit}" if row_limit else ""
        rows = src.execute(
            f"SELECT * FROM \"{table}\" {limit_clause}"
        ).fetchall()

        if not rows:
            print(f"  EMPTY {table}")
            continue

        col_names = [c["name"] for c in cols_info]
        placeholders = ", ".join([":p" + str(i) for i in range(len(col_names))])
        insert_sql = (
            f"INSERT INTO {_sanitize(table)} "
            f"({', '.join(_sanitize(c) for c in col_names)}) "
            f"VALUES ({placeholders})"
        )

        # Batch insert in chunks of 1000
        CHUNK = 1_000
        with engine.begin() as pg:
            for i in range(0, len(rows), CHUNK):
                batch = rows[i : i + CHUNK]
                pg.execute(
                    text(insert_sql),
                    [{"p" + str(j): row[j] for j in range(len(col_names))} for row in batch],
                )

        elapsed = round(time.perf_counter() - t0, 1)
        print(f"  OK    {table:30s} {len(rows):>7,} rows  ({elapsed}s)")

    src.close()
    engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed NBA SQLite → Postgres")
    parser.add_argument("--sqlite",   required=True, help="Path to nba.sqlite")
    parser.add_argument("--postgres", required=True, help="Postgres connection URL")
    args = parser.parse_args()
    migrate(args.sqlite, args.postgres)
