from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

import checloud
from aggregation import consensus as consensus_mod
from routers.corpus import TOOL_COLUMNS, _row_to_mapped_by_tool

DATA_DIR = Path(__file__).parent / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

_POOL_CSV = DATA_DIR / "pool_BLOD_1301.csv"
_REPO_CSV = DATA_DIR / "kg_repository_map.csv"


def list_sources() -> list[dict]:
    return [
        {
            "name": "BLOD",
            "status": "connected_full",
            "description": "Biomedical LOD corpus, spanning LOD Cloud, GitHub, "
                            "BioPortal, Wikidata, Bio2RDF, Kaggle, OLS, Ontobee, "
                            "OBO Foundry, and NCBI (repository membership as "
                            "recorded when the corpus was assembled). Every entry "
                            "carries full F-UJI/FAIR-Checker/KGHeartBeat scores.",
        },
        {
            "name": "OLS",
            "status": "connected_catalog",
            "description": "EMBL-EBI Ontology Lookup Service, ebi.ac.uk/ols4/api/ontologies "
                            "-- endpoint and response shape confirmed real via an independent "
                            "tool, but calling it from this development sandbox returned HTTP "
                            "403 (likely sandbox-IP-specific; unconfirmed from a real "
                            "deployment). See discovery.py.",
        },
        {
            "name": "OBO Foundry",
            "status": "connected_catalog",
            "description": "OBO Foundry registry, raw.githubusercontent.com/OBOFoundry/"
                            "OBOFoundry.github.io -- fully verified end-to-end, including a "
                            "live call from this codebase (267 ontologies returned).",
        },
        {
            "name": "Wikidata",
            "status": "connected_catalog",
            "description": "Wikidata Query Service SPARQL endpoint, "
                            "query.wikidata.org/sparql -- confirmed real via documentation, "
                            "not fetched live this session; any specific catalog query needs "
                            "the caller to supply the SPARQL, since Wikidata has no single "
                            "flat 'list of biomedical KGs' endpoint.",
        },
        {
            "name": "NCBI",
            "status": "connected_catalog",
            "description": "NCBI E-utilities, eutils.ncbi.nlm.nih.gov -- endpoint confirmed "
                            "real via documentation, but calling it from this development "
                            "sandbox returned HTTP 403 (likely sandbox-IP-specific; "
                            "unconfirmed from a real deployment). See discovery.py.",
        },
        {
            "name": "Ontobee",
            "status": "connected_catalog",
            "description": "Ontobee SPARQL endpoint, sparql.hegroup.org/sparql -- already "
                            "used elsewhere in this codebase for FAIR-Checker URL rewriting, "
                            "but calling it from this development sandbox returned HTTP 403 "
                            "(likely sandbox-IP-specific; unconfirmed from a real deployment).",
        },
        {
            "name": "GitHub",
            "status": "connected_catalog",
            "description": "GitHub Search API, api.github.com/search/repositories -- fully "
                            "verified end-to-end, including a live call from this codebase.",
        },
        {
            "name": "CheCLOUD",
            "status": "connected_full",
            "description": "Cultural heritage LOD cloud, "
                            "a related LOD sub-cloud -- 190 "
                            "knowledge graphs with real, verified FAIR scores, included in "
                            "snapshots. Assessed by KGHeartBeat ALONE (per its own published "
                            "methodology, not three tools like BLOD), so its consensus is "
                            "correctly reported as \"single_tool\" agreement, not cross-tool. "
                            "A genuinely live per-dataset REST endpoint also exists "
                            "(KGHeartBeat's public fairness API, confirmed "
                            "in CheCLOUD's own backend source) but is not wired up here -- "
                            "the static CSV above is what's actually loaded.",
        },
        {
            "name": "BioPortal",
            "status": "not_connected",
            "description": "Requires a free API key (bioontology.org/account). Set "
                            "BIOPORTAL_API_KEY to enable -- see discovery.py.",
        },
        {
            "name": "Kaggle",
            "status": "not_connected",
            "description": "Requires account credentials (KAGGLE_USERNAME + KAGGLE_KEY). "
                            "See discovery.py.",
        },
        {
            "name": "LOD Cloud",
            "status": "connected_catalog",
            "description": "The real data source (lod-cloud.net/lod-data.json) is "
                            "documented and implemented in discovery.py, which checks "
                            "lod-cloud.net/robots.txt LIVE before every fetch and refuses "
                            "(PermissionError) rather than working around it if that file "
                            "disallows the request. Neither outcome of that live check was "
                            "confirmed from this project's development environments -- "
                            "lod-cloud.net wasn't reachable from either one -- so this is "
                            "implemented-and-believed-correct, unconfirmed end-to-end, same "
                            "as OLS/NCBI/Ontobee. See GET /snapshots/live-catalogs.",
        },
        {
            "name": "Bio2RDF",
            "status": "not_connected",
            "description": "Per-dataset URL convention already used elsewhere in this "
                            "codebase, but no catalog LISTING endpoint was confirmed. "
                            "See discovery.py.",
        },
    ]


def _load_blod() -> pd.DataFrame:
    pool = pd.read_csv(_POOL_CSV)
    if _REPO_CSV.exists():
        repo = pd.read_csv(_REPO_CSV)
        pool = pool.merge(repo, on="id", how="left")
    else:
        pool["repository"] = None
    return pool


def _snapshot_rows() -> list[dict]:
    rows = []
    df = _load_blod()
    for _, row in df.iterrows():
        mapped_by_tool = _row_to_mapped_by_tool(row)
        cons = consensus_mod.compute_consensus(mapped_by_tool)
        rows.append({
            "source": "BLOD",
            "id": row["id"],
            "repository": row.get("repository") if pd.notna(row.get("repository")) else "",
            "fuji_composite": mapped_by_tool.get("fuji", {}).get("composite"),
            "fairchecker_composite": mapped_by_tool.get("fairchecker", {}).get("composite"),
            "kgheartbeat_composite": mapped_by_tool.get("kgheartbeat", {}).get("composite"),
            "consensus_overall": cons.get("overall"),
            "consensus_agreement": cons.get("agreement"),
        })

    try:
        checloud_datasets = checloud.list_datasets(page=1, page_size=10_000)["results"]
    except FileNotFoundError:
        checloud_datasets = []
    for d in checloud_datasets:
        rows.append({
            "source": "CheCLOUD",
            "id": d["id"],
            "repository": "CheCLOUD",
            "fuji_composite": None,
            "fairchecker_composite": None,
            "kgheartbeat_composite": d["normalized_fair_score"],
            "consensus_overall": d["normalized_fair_score"],
            "consensus_agreement": "single_tool",
        })

    return rows


def create_snapshot(now: Optional[datetime] = None) -> Path:
    now = now or datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    zip_path = SNAPSHOTS_DIR / f"{date_str}.zip"

    rows = _snapshot_rows()
    connected_full = [s["name"] for s in list_sources() if s["status"] == "connected_full"]
    connected_catalog = [s["name"] for s in list_sources() if s["status"] == "connected_catalog"]

    csv_buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(csv_buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "created_at": now.isoformat(),
        "sources_included_full_assessment": connected_full,
        "sources_included_catalog_only": connected_catalog,
        "sources_not_connected": [
            s["name"] for s in list_sources() if s["status"] == "not_connected"
        ],
        "total_datasets": len(rows),
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"assessment_{date_str}.csv", csv_buf.getvalue())
        zf.writestr("manifest.json", _to_json(manifest))

    return zip_path


def _to_json(obj: dict) -> str:
    import json
    return json.dumps(obj, indent=2)


def list_snapshots() -> list[dict]:
    out = []
    for p in sorted(SNAPSHOTS_DIR.glob("*.zip"), reverse=True):
        stat = p.stat()
        out.append({
            "filename": p.name,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return out


def get_snapshot_path(filename: str) -> Optional[Path]:
    candidate = SNAPSHOTS_DIR / filename
    if candidate.parent != SNAPSHOTS_DIR:
        return None
    if not candidate.is_file():
        return None
    return candidate
