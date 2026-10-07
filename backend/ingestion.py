from __future__ import annotations

import csv
import io
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import db
import discovery
import graphdb_client
import sparql_endpoint
from ai import gemini_categorizer
from routers.assess import _run_all_tools
from routers.corpus import TOOL_COLUMNS, append_rows_to_csv, invalidate as invalidate_corpus_cache

logger = logging.getLogger("ingestion")

DATA_DIR = Path(__file__).parent / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


_MAX_NEW_PER_RUN = int(os.environ.get("INGESTION_MAX_NEW_PER_RUN", "0") or 0)


KEY_FREE_SOURCES = ["obo-foundry", "ols", "lod-cloud", "github"]


def _str(v) -> str:
    """Coerce a metadata field that might be a plain string, a list of
    strings, or a {lang: text} dict (all of which show up across these
    catalogs) into one plain string for the classifier prompt."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v.get("en") or next(iter(v.values()), "") if v else ""
    if isinstance(v, list):
        return " ".join(_str(x) for x in v)
    return str(v)


_LOD_DOMAIN_TO_CATEGORY = {
    "cross_domain": "cross-domain",
    "geography": "geography",
    "government": "government",
    "linguistics": "linguistic",
    "media": "media",
    "publications": "publications",
    "social_networking": "social-networking",
    "user_generated": "user-generated",
}


def _candidates_from_obo_foundry() -> list[dict]:
    try:
        data = discovery.fetch_obo_foundry_catalog(limit=100_000)
    except Exception as e:
        logger.warning("OBO Foundry discovery failed: %s: %s", type(e).__name__, e)
        return []
    out = []
    for o in data.get("sample", []):
        oid = o.get("id")


        url = o.get("ontology_purl") or o.get("homepage")
        if not oid or not url:
            continue
        out.append({
            "id": f"obo-{oid}", "url": url, "category": "cross-domain", "repository": "OBO Foundry",
            "title": _str(o.get("title")), "description": _str(o.get("description")),
            "domain_hint": _str(o.get("domain")),
        })
    return out


def _candidates_from_ols() -> list[dict]:
    try:
        entries = discovery.fetch_ols_catalog_all()
    except Exception as e:
        logger.warning("OLS discovery failed: %s: %s", type(e).__name__, e)
        return []
    out = []
    for o in entries:
        oid = o.get("id")
        url = o.get("file_location") or o.get("homepage")
        if not oid or not url:
            continue
        out.append({
            "id": f"ols-{oid}", "url": url, "category": "cross-domain", "repository": "OLS",
            "title": _str(o.get("title")), "description": _str(o.get("description")),
        })
    return out


def _candidates_from_lod_cloud() -> list[dict]:
    try:
        data = discovery.fetch_lod_cloud_full()
    except Exception as e:
        logger.warning("LOD Cloud discovery failed: %s: %s", type(e).__name__, e)
        return []
    out = []
    for ds_id, meta in (data.get("items") or {}).items():
        meta = meta or {}


        url = (
            meta.get("landingPage")
            or meta.get("sparql")
            or meta.get("homepage")
            or meta.get("uri")
        )
        if not url:
            continue
        domain = _str(meta.get("domain")).strip().lower().replace("-", "_")
        out.append({
            "id": f"lodcloud-{ds_id}", "url": url,
            "category": _LOD_DOMAIN_TO_CATEGORY.get(domain, "cross-domain"),
            "repository": "LOD Cloud",
            "title": _str(meta.get("title")), "description": _str(meta.get("description")),
            "domain_hint": domain,


            "needs_classification": domain not in _LOD_DOMAIN_TO_CATEGORY,
        })
    return out


def _candidates_from_github() -> list[dict]:
    try:
        repos = discovery.search_github_repos_all(
            "topic:knowledge-graph topic:linked-data OR topic:rdf OR topic:fair-data"
        )
    except Exception as e:
        logger.warning("GitHub discovery failed: %s: %s", type(e).__name__, e)
        return []
    out = []
    for r in repos:
        full_name, url = r.get("full_name"), (r.get("homepage") or r.get("html_url"))
        if not full_name or not url:
            continue
        out.append({
            "id": f"github-{full_name.replace('/', '-')}", "url": url,
            "category": "cross-domain", "repository": "GitHub",
            "title": full_name, "description": _str(r.get("description")),
        })
    return out


_SOURCE_FUNCS = {
    "obo-foundry": _candidates_from_obo_foundry,
    "ols": _candidates_from_ols,
    "lod-cloud": _candidates_from_lod_cloud,
    "github": _candidates_from_github,
}


def discover_candidates(sources: Optional[list[str]] = None) -> list[dict]:
    """Pull candidate datasets from every key-free source (or a subset, via
    `sources`), tagging each with which source found it. A failure in one
    source (network error, catalog format drift, etc.) is logged and
    skipped rather than aborting the whole discovery pass -- matches this
    app's existing pattern in routers/snapshots.py's /snapshots/live-catalogs."""
    wanted = sources or KEY_FREE_SOURCES
    candidates = []
    for name in wanted:
        fn = _SOURCE_FUNCS.get(name)
        if fn is None:
            continue
        found = fn()
        logger.info("discovery: %s -> %d candidate(s)", name, len(found))
        candidates.extend(found)
    return candidates


def _existing_ids() -> set:
    from routers.corpus import _load
    df = _load()
    return set(df["id"].astype(str))


def filter_new(candidates: list[dict]) -> list[dict]:
    """Drop candidates already present in the corpus and de-duplicate
    within this run's own results (the same dataset can surface from more
    than one source)."""
    existing = _existing_ids()
    seen = set()
    out = []
    for c in candidates:
        if not c.get("id") or not c.get("url"):
            continue
        if c["id"] in existing or c["id"] in seen:
            continue
        seen.add(c["id"])
        out.append(c)
    return out


def classify_candidates(candidates: list[dict]) -> dict:
    """Resolve each new candidate's final corpus category, tagging BLOD
    (biomedical/health) data as "blod" and everything else into whichever
    existing category actually fits -- the automated version of this
    project's own BLOD/CHe-CLOUD research methodology (manual annotation +
    a GPT-4o-mini classifier over title/description; see the uploaded
    Blod/src/lodcloud_filter.py), with Gemini standing in for GPT-4o-mini.

    A LOD Cloud entry whose own metadata already gives an unambiguous
    domain (government, geography, media, etc.) skips the LLM call
    entirely and uses that directly -- mirrors the original pipeline's
    layered approach of trusting structured metadata before falling back
    to an LLM, and only spending a Gemini call where metadata alone can't
    decide (notably: every "life_sciences"-domain entry and every
    non-LOD-Cloud source, since those registries carry no domain field of
    their own and easily mix in non-biomedical ontologies/repos).

    Mutates and returns `candidates` with "category" resolved; also adds
    "category_source" ("metadata" or "gemini") and, when Gemini ran,
    "category_reasoning" -- useful for the ingestion snapshot's audit trail.
    """
    counts = {"metadata": 0, "gemini": 0, "gemini_fallback": 0}
    for c in candidates:
        if not c.get("needs_classification", True):

            c["category_source"] = "metadata"
            counts["metadata"] += 1
            continue

        result = gemini_categorizer.categorize(
            dataset_id=c["id"],
            title=c.get("title", ""),
            description=c.get("description", ""),
            default_category=c.get("category") or "cross-domain",
        )
        c["category"] = result["category"]
        c["category_reasoning"] = result.get("reasoning")
        if result.get("error"):
            c["category_source"] = "fallback"
            c["category_error"] = result["error"]
            counts["gemini_fallback"] += 1
        else:
            c["category_source"] = "gemini"
            counts["gemini"] += 1

    logger.info("classification: %d via metadata, %d via Gemini, %d fell back "
                "(Gemini unavailable/failed, used source default)",
                counts["metadata"], counts["gemini"], counts["gemini_fallback"])
    return counts


def _tool_results_to_row(candidate: dict, tool_results: dict) -> dict:
    row = {"id": candidate["id"], "category": candidate["category"], "repository": candidate.get("repository")}
    for tool, cols in TOOL_COLUMNS.items():
        mapped = (tool_results.get(tool) or {}).get("mapped") or {}
        row[cols["composite"]] = mapped.get("composite")
        dims = mapped.get("dimension_scores") or {}
        for d in ("F", "A", "I", "R"):
            row[cols[d]] = dims.get(d)
    return row


async def assess_candidate(candidate: dict) -> dict:
    """Run the same three-tool assessment /assess uses for a manually
    submitted URL, against one discovered candidate, and shape the result
    as a corpus row."""
    result = await _run_all_tools(candidate["url"], candidate["id"])
    return _tool_results_to_row(candidate, result["tool_results"])


async def run_monthly_ingestion(now: Optional[datetime] = None) -> dict:
    """The monthly job: discover datasets from every key-free source, keep
    only the ones not already in the corpus, assess each with F-UJI +
    FAIR-Checker + KGHeartBeat, and write the results into every storage
    backend that's active (CSV always; Postgres and/or GraphDB too when
    configured) -- then archive what happened as a snapshot, same as the
    existing monthly corpus snapshot.
    """
    now = now or datetime.now(timezone.utc)
    started = now.isoformat()

    candidates = discover_candidates()
    new_candidates = filter_new(candidates)
    if _MAX_NEW_PER_RUN and len(new_candidates) > _MAX_NEW_PER_RUN:
        logger.info("ingestion: capping %d new candidates to %d (INGESTION_MAX_NEW_PER_RUN)",
                    len(new_candidates), _MAX_NEW_PER_RUN)
        new_candidates = new_candidates[:_MAX_NEW_PER_RUN]

    classification_counts = classify_candidates(new_candidates)

    rows: list[dict] = []
    errors: list[dict] = []
    for candidate in new_candidates:
        try:
            rows.append(await assess_candidate(candidate))
        except Exception as e:
            errors.append({"id": candidate["id"], "url": candidate["url"], "error": f"{type(e).__name__}: {e}"})
            logger.warning("ingestion: assessment failed for %s: %s", candidate["id"], e)

    written_csv = append_rows_to_csv(rows)
    if rows:
        invalidate_corpus_cache()
        sparql_endpoint.invalidate()

    written_pg = 0
    if rows and db.is_postgres_enabled():
        try:
            written_pg = db.insert_dataset_rows(rows)
        except Exception as e:
            logger.warning("ingestion: Postgres write failed: %s: %s", type(e).__name__, e)

    written_graphdb = 0
    if rows and graphdb_client.is_enabled():
        try:
            written_graphdb = graphdb_client.add_rows(rows)
        except Exception as e:
            logger.warning("ingestion: GraphDB write failed: %s: %s", type(e).__name__, e)

    summary = {
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "sources_queried": KEY_FREE_SOURCES,
        "candidates_found": len(candidates),
        "new_candidates": len(new_candidates),
        "categorized_by_metadata": classification_counts["metadata"],
        "categorized_by_gemini": classification_counts["gemini"],
        "categorized_by_fallback": classification_counts["gemini_fallback"],
        "category_breakdown": {
            cat: sum(1 for c in new_candidates if c.get("category") == cat)
            for cat in sorted({c.get("category") for c in new_candidates})
        },
        "assessed": len(rows),
        "failed": len(errors),
        "written_csv_rows": written_csv,
        "written_postgres_rows": written_pg,
        "written_graphdb_triples": written_graphdb,
        "errors": errors,
    }

    _write_ingestion_snapshot(rows, new_candidates, summary, now)
    return summary


def _write_ingestion_snapshot(rows: list[dict], candidates: list[dict], summary: dict, now: datetime) -> Path:
    date_str = now.strftime("%Y-%m-%d")
    zip_path = SNAPSHOTS_DIR / f"ingestion_{date_str}.zip"

    csv_buf = io.StringIO()
    if rows:
        fieldnames = ["id", "category", "repository"] + [
            col for cols in TOOL_COLUMNS.values() for col in cols.values()
        ]
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


    audit_buf = io.StringIO()
    if candidates:
        writer = csv.DictWriter(audit_buf, fieldnames=[
            "id", "title", "category", "category_source", "category_reasoning",
        ])
        writer.writeheader()
        for c in candidates:
            writer.writerow({
                "id": c.get("id"), "title": c.get("title"), "category": c.get("category"),
                "category_source": c.get("category_source"),
                "category_reasoning": c.get("category_reasoning"),
            })

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"newly_added_{date_str}.csv", csv_buf.getvalue())
        zf.writestr(f"categorization_audit_{date_str}.csv", audit_buf.getvalue())
        zf.writestr("manifest.json", json.dumps(summary, indent=2))

    return zip_path
