"""Source selection for federated querying.

GET /federated/select returns the SPARQL endpoints of corpus datasets that meet
a FAIR-score threshold, best first, so a federated query engine (for example a
federated RAG pipeline building retrieval context from live knowledge graphs)
can pick which endpoints to query.

Selection is driven by the FAIR score: datasets below `min_fair_score` (and
below any per-principle minimum, min_f / min_a / min_i / min_r) are dropped,
and results are ranked by FAIR score, highest first. `keywords` only narrows
the candidates to a topic (title, description or keywords mention it); it never
changes the order.

Each endpoint is returned once, under its highest-scoring dataset: several
datasets share one endpoint (e.g. the Bio2RDF or Ontobee stores), and querying
the same endpoint twice would only duplicate results.
"""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

import dataset_links
from routers.corpus import _load, _row_to_summary

router = APIRouter()


def _term_pattern(term: str) -> re.Pattern:
    """Whole-word match, tolerant of a plural 's' (drug -> drugs)."""
    words = [re.escape(w) for w in term.lower().split()]
    return re.compile(r"\b" + r"\s+".join(words) + r"s?\b")

SCORE_FIELDS = ("consensus", "fuji", "fairchecker", "kgheartbeat")


def _dimension_scores(row, summary, score: str) -> dict:
    """F/A/I/R scores for the chosen score: the cross-tool consensus per
    principle, or one tool's own per-principle scores."""
    if score == "consensus":
        return dict(summary["consensus"].get("by_dimension") or {})
    from routers.corpus import TOOL_COLUMNS
    cols = TOOL_COLUMNS[score]
    return {d: (float(row[cols[d]]) if pd.notna(row.get(cols[d])) else None) for d in ("F", "A", "I", "R")}


def _url_key(url: str) -> str:
    return re.sub(r"^https?://", "", url.strip().lower()).rstrip("/")


@router.get("/federated/select")
async def federated_select(
    min_fair_score: float = Query(0.6, ge=0, le=1, description="Minimum FAIR score (0-1)"),
    category: Optional[str] = Query(
        None, description="LOD sub-cloud(s), comma-separated, e.g. 'life-sciences,blod'. Omit for all."),
    limit: int = Query(2, ge=1, le=500, description="Maximum number of endpoints to return"),
    require_sparql: bool = Query(True, description="Only datasets with a SPARQL endpoint (always true here)"),
    status: str = Query(
        "online", pattern="^(online|any)$",
        description="'online' = only endpoints KGHeartBeat found online at its last check; 'any' = all known"),
    score: str = Query(
        "consensus", pattern="^(consensus|fuji|fairchecker|kgheartbeat)$",
        description="Which score min_fair_score applies to and results are ranked by"),
    keywords: Optional[str] = Query(
        None, description="Topic terms, comma-separated (e.g. 'drug,adverse event,disease'). "
                          "Matched as whole words in each dataset's title, description and keywords."),
    match: str = Query("any", pattern="^(any|all)$",
                       description="'any' = at least one term must match; 'all' = every term must match"),
    min_f: Optional[float] = Query(None, ge=0, le=1, description="Minimum Findability score"),
    min_a: Optional[float] = Query(None, ge=0, le=1, description="Minimum Accessibility score"),
    min_i: Optional[float] = Query(None, ge=0, le=1, description="Minimum Interoperability score"),
    min_r: Optional[float] = Query(None, ge=0, le=1, description="Minimum Reusability score"),
):
    df = _load()
    if category:
        cats = [c.strip() for c in category.split(",") if c.strip()]
        df = df[df["category"].isin(cats)]
        if df.empty:
            raise HTTPException(404, f"No datasets in category '{category}' (see /corpus/categories)")

    terms = [t.strip() for t in (keywords or "").split(",") if t.strip()]
    patterns = [(t, _term_pattern(t)) for t in terms]

    best: dict[str, dict] = {}
    for _, row in df.iterrows():
        cat = row.get("category") if pd.notna(row.get("category")) else "blod"
        links = dataset_links.get(row["id"], cat)
        if not links["sparql_endpoints"]:
            continue
        matched = []
        if patterns:
            text = dataset_links.topic_text(row["id"], cat)
            matched = [t for t, pat in patterns if pat.search(text)]
            if not matched or (match == "all" and len(matched) < len(patterns)):
                continue
        summary = _row_to_summary(row)
        fair = (summary["consensus"].get("overall") if score == "consensus"
                else summary["tool_composites"].get(score))
        if fair is None or fair < min_fair_score:
            continue
        dims = _dimension_scores(row, summary, score)
        if any(m is not None and (dims.get(d) is None or dims[d] < m)
               for d, m in (("F", min_f), ("A", min_a), ("I", min_i), ("R", min_r))):
            continue
        for ep in links["sparql_endpoints"]:
            if status == "online" and ep.get("check") != "online":
                continue
            key = _url_key(ep["url"])
            if key in best and best[key]["fair_score"] >= fair:
                continue
            best[key] = {
                "id": row["id"],
                "title": links["title"],
                "category": cat,
                "fair_score": round(float(fair), 4),
                "score_used": score,
                "fair_by_principle": {d: (round(float(v), 4) if v is not None else None) for d, v in dims.items()},
                "tool_scores": summary["tool_composites"],
                "agreement": summary["consensus"].get("agreement"),
                "sparql_endpoint": ep["url"],
                "endpoint_status": ep.get("check"),
                "endpoint_checked_on": ep.get("checked_on"),
                "matched_keywords": matched,
            }

    results = sorted(best.values(), key=lambda r: (-r["fair_score"], r["id"].lower()))
    return {
        "query": {"min_fair_score": min_fair_score, "category": category, "limit": limit,
                  "status": status, "score": score, "keywords": terms, "match": match,
                  "min_f": min_f, "min_a": min_a, "min_i": min_i, "min_r": min_r},
        "candidates": len(results),
        "results": results[:limit],
    }
