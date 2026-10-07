from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
_CSV = DATA_DIR / "checloud_fair_scores.csv"

_COLUMN_MAP = {
    "KG id": "id",
    "KG name": "name",
    "KG SPARQL endpoint": "sparql_endpoint",
    "RDF dump link": "rdf_dump_link",
    "F1-M Unique and persistent ID": "F1-M",
    "F1-D URIs dereferenceability": "F1-D",
    "F2a-M - Metadata availability via standard primary sources": "F2a-M",
    "F2b-M Metadata availability for all the attributes covered in the FAIR score computation": "F2b-M",
    "F3-M Data referrable via a DOI": "F3-M",
    "F4-M Metadata registered in a searchable engine": "F4-M",
    "F score": "F",
    "A1-D Working access point(s)": "A1-D",
    "A1-M Metadata availability via working primary sources": "A1-M",
    "A1.2 Authentication & HTTPS support": "A1.2",
    "A2-M Registered in search engines": "A2-M",
    "A score": "A",
    "I1-D Standard & open representation format": "I1-D",
    "I1-M Metadata are described with VoID/DCAT predicates": "I1-M",
    "I2 Use of FAIR vocabularies": "I2",
    "I3-D Degree of connection": "I3-D",
    "I score": "I",
    "R1.1 Machine- or human-readable license retrievable via any primary source": "R1.1",
    "R1.2 Publisher information, such as authors, contributors, publishers, and sources": "R1.2",
    "R1.3-D Data organized in a standardized way": "R1.3-D",
    "R1.3-M Metadata are described with VoID/DCAT predicates": "R1.3-M",
    "R score": "R",
    "FAIR score": "fair_score",
}

_df: Optional[pd.DataFrame] = None


def _load() -> pd.DataFrame:
    global _df
    if _df is not None:
        return _df
    if not _CSV.exists():
        raise FileNotFoundError(f"CheCLOUD data not found at {_CSV}")
    raw = pd.read_csv(_CSV)
    raw = raw.rename(columns=_COLUMN_MAP)
    raw["normalized_fair_score"] = raw["fair_score"] / 4.0
    _df = raw
    return _df


def _row_to_summary(row: pd.Series) -> dict:
    return {
        "id": row["id"],
        "name": row.get("name"),
        "sparql_endpoint": row.get("sparql_endpoint") if pd.notna(row.get("sparql_endpoint")) else None,
        "dimension_scores": {
            "F": float(row["F"]) if pd.notna(row.get("F")) else None,
            "A": float(row["A"]) if pd.notna(row.get("A")) else None,
            "I": float(row["I"]) if pd.notna(row.get("I")) else None,
            "R": float(row["R"]) if pd.notna(row.get("R")) else None,
        },
        "fair_score": float(row["fair_score"]) if pd.notna(row.get("fair_score")) else None,
        "normalized_fair_score": float(row["normalized_fair_score"]) if pd.notna(row.get("normalized_fair_score")) else None,
        "tool": "KGHeartBeat only",
    }


def summary() -> dict:
    df = _load()
    valid = df[df["normalized_fair_score"].notna()]
    return {
        "total_datasets": len(df),
        "mean_normalized_fair_score": round(valid["normalized_fair_score"].mean(), 4) if len(valid) else None,
        "tool": "KGHeartBeat only (no F-UJI/FAIR-Checker comparison for this corpus)",
        "score_scale_note": "fair_score is CheCLOUD's own 0-4 sum of F+A+I+R; "
                             "normalized_fair_score divides by 4 for comparability "
                             "with BLOD's 0-1 composite scale.",
    }


def list_datasets(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    sort_desc: bool = True,
) -> dict:
    df = _load()
    if search:
        df = df[df["id"].astype(str).str.contains(search, case=False, na=False)
                 | df["name"].astype(str).str.contains(search, case=False, na=False)]

    df = df.sort_values("normalized_fair_score", ascending=not sort_desc, na_position="last")

    total = len(df)
    start = (page - 1) * page_size
    page_df = df.iloc[start:start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "results": [_row_to_summary(row) for _, row in page_df.iterrows()],
    }


def dataset_detail(dataset_id: str) -> Optional[dict]:
    df = _load()
    match = df[df["id"] == dataset_id]
    if match.empty:
        return None
    row = match.iloc[0]
    detail = _row_to_summary(row)
    metric_cols = ["F1-M", "F1-D", "F2a-M", "F2b-M", "F3-M", "F4-M",
                   "A1-D", "A1-M", "A1.2", "A2-M",
                   "I1-D", "I1-M", "I2", "I3-D",
                   "R1.1", "R1.2", "R1.3-D", "R1.3-M"]
    detail["metric_scores"] = {
        c: float(row[c]) for c in metric_cols if c in row.index and pd.notna(row[c])
    }
    return detail
