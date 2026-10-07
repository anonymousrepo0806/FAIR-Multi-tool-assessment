from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

DATA_DIR = Path(__file__).parent / "data"
_POOL_CSV = DATA_DIR / "pool_all_categories.csv"
_LEGACY_BLOD_ONLY_CSV = DATA_DIR / "pool_BLOD_1301.csv"
_REPO_CSV = DATA_DIR / "kg_repository_map.csv"

_SCORE_COLUMNS = [
    "F_fuji", "A_fuji", "I_fuji", "R_fuji", "FAIR_fuji",
    "F_fc", "A_fc", "I_fc", "R_fc", "FAIR_fc",
    "F_kgh", "A_kgh", "I_kgh", "R_kgh", "FAIR_kgh",
]

_engine = None
_SessionLocal = None


def is_postgres_enabled() -> bool:
    return bool(DATABASE_URL)


def _psycopg2_url(url: str) -> str:


    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set -- Postgres is disabled")


        _engine = create_engine(_psycopg2_url(DATABASE_URL), poolclass=NullPool, future=True)
        _SessionLocal = sessionmaker(bind=_engine, future=True)
    return _engine


def ensure_schema() -> None:
    """Create the two corpus tables if they don't exist yet.

    Deliberately plain DDL rather than an ORM model + Alembic migration --
    the schema is a single append-mostly fact table plus a lookup table,
    both mirroring CSV files that ship in the image. A full migration
    framework would be a lot of ceremony for something this static; if the
    schema ever needs to evolve, Alembic is the natural next step.
    """
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS dataset_scores (
                id TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'blod',
                "F_fuji" DOUBLE PRECISION,
                "A_fuji" DOUBLE PRECISION,
                "I_fuji" DOUBLE PRECISION,
                "R_fuji" DOUBLE PRECISION,
                "FAIR_fuji" DOUBLE PRECISION,
                "F_fc" DOUBLE PRECISION,
                "A_fc" DOUBLE PRECISION,
                "I_fc" DOUBLE PRECISION,
                "R_fc" DOUBLE PRECISION,
                "FAIR_fc" DOUBLE PRECISION,
                "F_kgh" DOUBLE PRECISION,
                "A_kgh" DOUBLE PRECISION,
                "I_kgh" DOUBLE PRECISION,
                "R_kgh" DOUBLE PRECISION,
                "FAIR_kgh" DOUBLE PRECISION,
                PRIMARY KEY (id, category)
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS dataset_repository (
                id TEXT PRIMARY KEY,
                repository TEXT
            )
            """
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_dataset_scores_category "
            "ON dataset_scores (category)"
        ))


def _read_source_csvs() -> tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    pool_path = _POOL_CSV if _POOL_CSV.exists() else _LEGACY_BLOD_ONLY_CSV
    if not pool_path.exists():
        raise FileNotFoundError(f"Corpus data not found at {_POOL_CSV}")
    pool = pd.read_csv(pool_path)
    if "category" not in pool.columns:
        pool["category"] = "blod"
    repo = pd.read_csv(_REPO_CSV) if _REPO_CSV.exists() else None
    return pool, repo


def seed_from_csv_if_empty() -> int:
    """Load the baked-in CSV corpus into Postgres, but only the first time.

    Returns the number of rows inserted (0 if the tables were already
    populated -- a redeploy or restart is a no-op, not a re-import).
    """
    engine = get_engine()
    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM dataset_scores")).scalar_one()
    if existing:
        return 0

    pool, repo = _read_source_csvs()
    cols = ["id", "category"] + [c for c in _SCORE_COLUMNS if c in pool.columns]
    pool[cols].to_sql("dataset_scores", engine, if_exists="append", index=False, method="multi", chunksize=500)

    if repo is not None and "id" in repo.columns and "repository" in repo.columns:
        repo[["id", "repository"]].drop_duplicates(subset="id").to_sql(
            "dataset_repository", engine, if_exists="append", index=False, method="multi", chunksize=500
        )

    return len(pool)


def ensure_seeded() -> None:
    """Called once at startup when DATABASE_URL is set: create the schema
    and seed it from the CSV corpus if the database is empty."""
    ensure_schema()
    seed_from_csv_if_empty()


def insert_dataset_rows(rows: list[dict]) -> int:
    """Upsert newly-ingested rows into Postgres -- used by the monthly
    ingestion job (ingestion.py) after it assesses datasets discovered from
    the key-free catalogs. Each row needs at least 'id'; 'category' defaults
    to 'blod' and missing score columns are left NULL, matching how a
    partial CSV row behaves elsewhere in this app. Returns the number of
    rows written (0 if `rows` is empty or Postgres isn't enabled)."""
    if not rows or not is_postgres_enabled():
        return 0

    engine = get_engine()
    col_list = ", ".join(f'"{c}"' for c in _SCORE_COLUMNS)
    placeholders = ", ".join(f":{c}" for c in _SCORE_COLUMNS)
    set_clause = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in _SCORE_COLUMNS)

    with engine.begin() as conn:
        for row in rows:
            params = {"id": row["id"], "category": row.get("category") or "blod"}
            params.update({c: row.get(c) for c in _SCORE_COLUMNS})
            conn.execute(text(
                f"""
                INSERT INTO dataset_scores (id, category, {col_list})
                VALUES (:id, :category, {placeholders})
                ON CONFLICT (id, category) DO UPDATE SET {set_clause}
                """
            ), params)

            repository = row.get("repository")
            if repository:
                conn.execute(text(
                    """
                    INSERT INTO dataset_repository (id, repository)
                    VALUES (:id, :repository)
                    ON CONFLICT (id) DO UPDATE SET repository = EXCLUDED.repository
                    """
                ), {"id": row["id"], "repository": repository})

    return len(rows)


def load_dataframe_from_db() -> pd.DataFrame:
    """Read the full corpus back out of Postgres as a DataFrame with the
    exact same shape `corpus._load()` has always produced from the CSVs, so
    every downstream function (consensus, filtering, pagination) works
    unchanged regardless of which storage backend is active."""
    engine = get_engine()
    pool = pd.read_sql_table("dataset_scores", engine)
    try:
        repo = pd.read_sql_table("dataset_repository", engine)
        pool = pool.merge(repo, on="id", how="left")
    except Exception:
        pool["repository"] = None
    return pool
