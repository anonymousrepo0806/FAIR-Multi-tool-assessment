from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

import db
from aggregation import consensus as consensus_mod
from mapping import unified_mapping

router = APIRouter()

KGHEARTBEAT_COLUMN_RENAME = {
    "F1-M Unique and persistent ID": "F1-M",
    "F1-D URIs dereferenceability": "F1-D",
    "F2a-M - Metadata availability via standard primary sources": "F2a-M",
    "F2b-M Metadata availability for all the attributes covered in the FAIR score computation": "F2b-M",
    "F3-M Data referrable via a DOI": "F3-M",
    "A1-D Working access point(s)": "A1.1-D",
    "A1-M Metadata availability via working primary sources": "A1.1-M",
    "A1.2 Authentication & HTTPS support": "A1.2",
    "R1.1 Machine- or human-readable license retrievable via any primary source": "R1.1",
    "R1.2 Publisher information such as authors-contributors-publishers and sources": "R1.2",
    "R1.3-D Data organized in a standardized way": "R1.3-D",
    "R1.3-M Metadata are described with VoID/DCAT predicates": "R1.3-M",
    "I1-D Standard & open representation format": "I1-D",
    "I1-M Metadata are described with VoID/DCAT predicates": "I1-M",
    "I2 Use of FAIR vocabularies": "I2",
    "I3-D Degree of connection": "I3-D",
}

DATA_DIR = Path(__file__).parent.parent / "data"
_POOL_CSV = DATA_DIR / "pool_all_categories.csv"
_LEGACY_BLOD_ONLY_CSV = DATA_DIR / "pool_BLOD_1301.csv"
_REPO_CSV = DATA_DIR / "kg_repository_map.csv"
_RAW_DIR = DATA_DIR / "raw"

CATEGORY_RAW_FILE = {
    "blod": "BLOD.csv",
    "che-cloud": "che-cloud.csv",
    "life-sciences": "life-sciences.csv",
    "linguistic": "linguistic.csv",
    "government": "government.csv",
    "publications": "publications.csv",
    "social-networking": "social-networking.csv",
    "cross-domain": "cross-domain.csv",
    "user-generated": "user-generated.csv",
    "geography": "geography.csv",
    "media": "media.csv",
}

TOOL_COLUMNS = {
    "fuji": {"F": "F_fuji", "A": "A_fuji", "I": "I_fuji", "R": "R_fuji", "composite": "FAIR_fuji"},
    "fairchecker": {"F": "F_fc", "A": "A_fc", "I": "I_fc", "R": "R_fc", "composite": "FAIR_fc"},
    "kgheartbeat": {"F": "F_kgh", "A": "A_kgh", "I": "I_kgh", "R": "R_kgh", "composite": "FAIR_kgh"},
}

_df: Optional[pd.DataFrame] = None
_raw_cache: dict = {}


def _load() -> pd.DataFrame:
    global _df
    if _df is not None:
        return _df

    if db.is_postgres_enabled():
        try:
            _df = db.load_dataframe_from_db()
            return _df
        except Exception:


            pass

    pool_path = _POOL_CSV if _POOL_CSV.exists() else _LEGACY_BLOD_ONLY_CSV
    if not pool_path.exists():
        raise HTTPException(500, f"Corpus data not found at {_POOL_CSV}")
    pool = pd.read_csv(pool_path)
    if "category" not in pool.columns:
        pool["category"] = "blod"
    if _REPO_CSV.exists():
        repo = pd.read_csv(_REPO_CSV)
        pool = pool.merge(repo, on="id", how="left")
    else:
        pool["repository"] = None
    _df = pool
    return _df


def invalidate() -> None:
    """Drop the cached in-memory DataFrame so the next call to _load()
    re-reads current storage -- called after the monthly ingestion job
    (ingestion.py) appends newly-discovered, newly-assessed datasets."""
    global _df
    _df = None


def append_rows_to_csv(rows: list[dict]) -> int:
    """Append newly-ingested rows to the CSV corpus files, so the CSV path
    stays a complete, self-sufficient mirror of the corpus even when
    Postgres/GraphDB are also enabled (ingestion.py writes to all
    configured backends, not just one). Returns the number of rows written
    (0 if `rows` is empty)."""
    if not rows:
        return 0

    pool_path = _POOL_CSV if _POOL_CSV.exists() else _LEGACY_BLOD_ONLY_CSV
    existing_pool = pd.read_csv(pool_path) if pool_path.exists() else pd.DataFrame()
    score_cols = [
        "F_fuji", "A_fuji", "I_fuji", "R_fuji", "FAIR_fuji",
        "F_fc", "A_fc", "I_fc", "R_fc", "FAIR_fc",
        "F_kgh", "A_kgh", "I_kgh", "R_kgh", "FAIR_kgh",
    ]
    new_pool_rows = pd.DataFrame([
        {"id": r["id"], "category": r.get("category") or "blod",
         **{c: r.get(c) for c in score_cols}}
        for r in rows
    ]).astype({c: "float64" for c in score_cols})
    if not existing_pool.empty:


        new_pool_rows = new_pool_rows.reindex(columns=existing_pool.columns)
    combined = pd.concat([existing_pool, new_pool_rows], ignore_index=True)
    combined.to_csv(_POOL_CSV, index=False)

    repo_rows = [{"id": r["id"], "repository": r["repository"]} for r in rows if r.get("repository")]
    if repo_rows:
        existing_repo = pd.read_csv(_REPO_CSV) if _REPO_CSV.exists() else pd.DataFrame(columns=["id", "repository"])
        combined_repo = pd.concat([existing_repo, pd.DataFrame(repo_rows)], ignore_index=True)
        combined_repo = combined_repo.drop_duplicates(subset="id", keep="last")
        combined_repo.to_csv(_REPO_CSV, index=False)

    return len(rows)


def _load_raw(tool: str, category: str) -> Optional[pd.DataFrame]:
    key = (tool, category)
    if key in _raw_cache:
        return _raw_cache[key]
    filename = CATEGORY_RAW_FILE.get(category)
    if not filename:
        _raw_cache[key] = None
        return None
    path = _RAW_DIR / tool / filename
    if not path.exists():
        _raw_cache[key] = None
        return None
    df = pd.read_csv(path, low_memory=False)
    if tool == "kgheartbeat":
        df = df.rename(columns=KGHEARTBEAT_COLUMN_RENAME)
    id_col = "id" if "id" in df.columns else "KG id"
    df = df.set_index(df[id_col].astype(str).str.strip())
    _raw_cache[key] = df
    return df


def _row_to_mapped_by_tool(row: pd.Series) -> dict:
    out = {}
    for tool, cols in TOOL_COLUMNS.items():
        composite = row.get(cols["composite"])
        if pd.isna(composite):
            out[tool] = {"error": "no score for this tool"}
            continue
        out[tool] = {
            "composite": float(composite),
            "dimension_scores": {
                d: float(row[cols[d]]) for d in ("F", "A", "I", "R") if not pd.isna(row.get(cols[d]))
            },
            "error": None,
        }
    return out


def _row_to_summary(row: pd.Series) -> dict:
    mapped_by_tool = _row_to_mapped_by_tool(row)
    cons = consensus_mod.compute_consensus(mapped_by_tool)
    return {
        "id": row["id"],
        "category": row.get("category") if pd.notna(row.get("category")) else None,
        "repository": row.get("repository") if pd.notna(row.get("repository")) else None,
        "tool_composites": {t: m.get("composite") for t, m in mapped_by_tool.items()},
        "consensus": cons,
    }


@router.get("/corpus/categories")
async def corpus_categories():
    df = _load()
    counts = df["category"].fillna("blod").value_counts().to_dict()
    return {"categories": [{"category": c, "count": n} for c, n in sorted(counts.items())]}


@router.get("/corpus/summary")
async def corpus_summary(category: Optional[str] = Query(None, description="Restrict to one category")):
    df = _load()
    if category:
        df = df[df["category"] == category]
        if df.empty:
            raise HTTPException(404, f"Unknown or empty category '{category}'")

    repo_counts = (
        df["repository"].fillna("Unknown").value_counts().to_dict() if "repository" in df.columns else {}
    )
    category_counts = df["category"].fillna("blod").value_counts().to_dict()
    composites = []
    for _, row in df.iterrows():
        cons = consensus_mod.compute_consensus(_row_to_mapped_by_tool(row))
        if cons.get("overall") is not None:
            composites.append(cons["overall"])

    return {
        "total_datasets": len(df),
        "category_breakdown": category_counts,
        "repository_breakdown": repo_counts,
        "mean_consensus_composite": round(sum(composites) / len(composites), 4) if composites else None,
        "tools": list(TOOL_COLUMNS.keys()),
    }


@router.get("/corpus/datasets")
async def corpus_datasets(
    search: Optional[str] = Query(None, description="Filter by id substring (case-insensitive)"),
    category: Optional[str] = Query(None, description="Filter by LOD sub-cloud category (see /corpus/categories)"),
    repository: Optional[str] = Query(None, description="Filter by exact repository name"),
    min_consensus: Optional[float] = Query(None, ge=0, le=1),
    max_consensus: Optional[float] = Query(None, ge=0, le=1),
    sort_by: str = Query("id", pattern="^(id|consensus)$"),
    sort_desc: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    df = _load()

    if search:
        df = df[df["id"].str.contains(search, case=False, na=False)]
    if category:
        df = df[df["category"] == category]
    if repository:
        df = df[df["repository"] == repository]

    rows = [_row_to_summary(row) for _, row in df.iterrows()]

    if min_consensus is not None:
        rows = [r for r in rows if r["consensus"].get("overall") is not None and r["consensus"]["overall"] >= min_consensus]
    if max_consensus is not None:
        rows = [r for r in rows if r["consensus"].get("overall") is not None and r["consensus"]["overall"] <= max_consensus]

    if sort_by == "consensus":
        rows.sort(key=lambda r: (r["consensus"].get("overall") is None, r["consensus"].get("overall") or 0), reverse=sort_desc)
    else:
        rows.sort(key=lambda r: r["id"], reverse=sort_desc)

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "results": page_rows,
    }


def _dataset_url_for(dataset_id: str, category: str) -> Optional[str]:
    for tool in ("fuji", "fairchecker", "kgheartbeat"):
        raw = _load_raw(tool, category)
        if raw is not None and dataset_id in raw.index:
            for col in ("url", "Dataset URL", "processed_url"):
                if col in raw.columns:
                    val = raw.loc[dataset_id, col]
                    if isinstance(val, pd.Series):
                        val = val.iloc[0]
                    if pd.notna(val):
                        return str(val)
    return None


@router.get("/corpus/datasets/{dataset_id}")
async def corpus_dataset_detail(
    dataset_id: str,
    category: Optional[str] = Query(
        None, description="Disambiguates dataset ids that recur across categories "
                           "(e.g. 'dbpedia' appears in several categories) -- pass "
                           "the category from the row you're expanding. Falls back "
                           "to an arbitrary matching row if omitted."
    ),
):
    df = _load()
    match = df[df["id"] == dataset_id]
    if match.empty:
        raise HTTPException(404, f"'{dataset_id}' not found in the precomputed corpus")

    if category:
        scoped = match[match["category"] == category]
        if not scoped.empty:
            match = scoped

    row = match.iloc[0]
    category = row.get("category") if pd.notna(row.get("category")) else "blod"

    tool_results = {}
    for tool in TOOL_COLUMNS:
        raw_df = _load_raw(tool, category)
        raw_row = None
        if raw_df is not None and dataset_id in raw_df.index:
            hit = raw_df.loc[dataset_id]
            raw_row = hit.iloc[0].to_dict() if isinstance(hit, pd.DataFrame) else hit.to_dict()
        if raw_row is not None:
            tool_results[tool] = unified_mapping.normalise(tool, raw_row)
        else:
            fallback = _row_to_mapped_by_tool(row)[tool]
            tool_results[tool] = {"native": {}, "mapped": fallback}

    mapped_by_tool = {t: r["mapped"] for t, r in tool_results.items()}
    cons = consensus_mod.compute_consensus(mapped_by_tool)

    return {
        "input": {"type": "corpus", "value": dataset_id},
        "category": category,
        "repository": row.get("repository") if pd.notna(row.get("repository")) else None,
        "dataset_url": _dataset_url_for(dataset_id, category),
        "tool_results": tool_results,
        "consensus": cons,
    }
