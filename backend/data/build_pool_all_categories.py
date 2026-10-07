from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent
BACKEND_DIR = DATA_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from mapping import unified_mapping_base as base

RAW_DIR = DATA_DIR / "raw"
EXISTING_BLOD_POOL = DATA_DIR / "pool_BLOD_1301.csv"
OUT_CSV = DATA_DIR / "pool_all_categories.csv"

NEW_CATEGORIES = {
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

TOOLS = ("fuji", "fairchecker", "kgheartbeat")
TOOL_SUFFIX = {"fuji": "fuji", "fairchecker": "fc", "kgheartbeat": "kgh"}

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


def _score_one_tool(tool: str, category: str, filename: str) -> dict:
    path = RAW_DIR / tool / filename
    out = {}
    if not path.exists():
        print(f"  [skip] {path} not found")
        return out
    df = pd.read_csv(path, low_memory=False)
    if tool == "kgheartbeat":
        df = df.rename(columns=KGHEARTBEAT_COLUMN_RENAME)
    id_col = "id" if "id" in df.columns else "KG id"
    if id_col not in df.columns:
        print(f"  [skip] {path} has no id column")
        return out
    for _, row in df.iterrows():
        kg_id = str(row[id_col]).strip()
        if not kg_id or kg_id.lower() == "nan":
            continue
        raw = row.to_dict()
        result = base.normalise_tool_output(tool, raw)
        out[kg_id] = {
            "F": result.dimension_scores.get("F"),
            "A": result.dimension_scores.get("A"),
            "I": result.dimension_scores.get("I"),
            "R": result.dimension_scores.get("R"),
            "composite": result.composite,
        }
    return out


def build_category(category: str, filename: str) -> pd.DataFrame:
    print(f"category: {category}")
    per_tool = {t: _score_one_tool(t, category, filename) for t in TOOLS}
    all_ids = sorted(set().union(*[set(d.keys()) for d in per_tool.values()]))
    rows = []
    for kg_id in all_ids:
        row = {"id": kg_id, "category": category}
        for tool in TOOLS:
            suf = TOOL_SUFFIX[tool]
            scores = per_tool[tool].get(kg_id, {})
            row[f"F_{suf}"] = scores.get("F")
            row[f"A_{suf}"] = scores.get("A")
            row[f"I_{suf}"] = scores.get("I")
            row[f"R_{suf}"] = scores.get("R")
            row[f"FAIR_{suf}"] = scores.get("composite")
        rows.append(row)
    print(f"  -> {len(rows)} KGs")
    return pd.DataFrame(rows)


def main():
    frames = []

    if EXISTING_BLOD_POOL.exists():
        blod = pd.read_csv(EXISTING_BLOD_POOL)
        blod["category"] = "blod"
        frames.append(blod)
        print(f"category: blod (from existing {EXISTING_BLOD_POOL.name})\n  -> {len(blod)} KGs")
    else:
        print(f"  [warn] {EXISTING_BLOD_POOL} not found; 'blod' category will be empty")

    for category, filename in NEW_CATEGORIES.items():
        frames.append(build_category(category, filename))

    combined = pd.concat(frames, ignore_index=True, sort=False)

    col_order = ["id", "category",
                 "F_fuji", "A_fuji", "I_fuji", "R_fuji",
                 "F_fc", "A_fc", "I_fc", "R_fc",
                 "F_kgh", "A_kgh", "I_kgh", "R_kgh",
                 "FAIR_fuji", "FAIR_fc", "FAIR_kgh"]
    combined = combined[[c for c in col_order if c in combined.columns]]
    combined.to_csv(OUT_CSV, index=False)
    print(f"\nwrote {OUT_CSV} ({len(combined)} rows total)")
    print(combined["category"].value_counts())


if __name__ == "__main__":
    main()
