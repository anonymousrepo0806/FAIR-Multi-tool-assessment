"""SPARQL endpoints, website and BLOD page for each corpus dataset, read directly
from the BLOD catalogue file data/BLOD.json (the enriched BLOD export, whose
records carry `sparql`, `website`, `fair_page` and `also_available_at`).

Corpus ids are matched to BLOD records case-insensitively ("bao" -> "BAO"); for
the blod category a punctuation-insensitive match is tried as a fallback
("ido;_vido;_cido" -> "IDO, VIDO, CIDO"). Datasets in other LOD sub-clouds are
only matched on an exact (case-insensitive) id.

SPARQL endpoints are also taken from data/kghb_sparql_endpoints.csv, extracted
from a KGHeartBeat analysis snapshot by data/build_kghb_endpoints.py. That file
covers every LOD sub-cloud, not just BLOD, and records whether KGHeartBeat found
each endpoint online on the snapshot date. Each endpoint returned here carries:
  url, title, description, sources (["BLOD"], ["KGHeartBeat"] or both),
  check ("online" | "offline" | "unreachable" | None if never checked), checked_on

Replace either file and restart the backend (or call invalidate()) to refresh.
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Optional

BLOD_JSON = Path(os.environ.get("BLOD_JSON_PATH", Path(__file__).parent / "data" / "BLOD.json"))
KGHB_CSV = Path(os.environ.get("KGHB_ENDPOINTS_PATH", Path(__file__).parent / "data" / "kghb_sparql_endpoints.csv"))
KGHB_META = Path(os.environ.get("KGHB_METADATA_PATH", Path(__file__).parent / "data" / "kghb_metadata.csv"))

EMPTY = {"title": None, "website": None, "blod_page": None, "sparql_endpoints": [], "also_available_at": []}

_by_lower: Optional[dict] = None
_by_norm: dict = {}
_kghb_lower: dict = {}
_kghb_norm: dict = {}
_meta_lower: dict = {}
_cache: dict = {}
_text_cache: dict = {}


def _norm(text) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


def _real_url(u) -> bool:
    return isinstance(u, str) and u.strip().startswith(("http://", "https://")) and " " not in u.strip()


def _links_for(rec: dict) -> dict:
    endpoints, seen = [], set()
    for ep in rec.get("sparql") or []:
        if not isinstance(ep, dict) or not _real_url(ep.get("access_url")):
            continue
        url = ep["access_url"].strip()
        if url.rstrip("/") in seen:
            continue
        seen.add(url.rstrip("/"))
        endpoints.append({
            "url": url,
            "title": (ep.get("title") or "").strip(),
            "description": (ep.get("description") or "").strip(),
            "sources": ["BLOD"],
            "check": None,
            "checked_on": None,
        })
    sites = [{"site": s["site"], "url": s["url"].strip()}
             for s in rec.get("also_available_at") or []
             if isinstance(s, dict) and s.get("site") and _real_url(s.get("url"))]
    website = (rec.get("website") or "").strip()
    return {
        "title": (rec.get("title") or "").strip() or None,
        "website": website if _real_url(website) else None,
        "blod_page": rec.get("fair_page") if _real_url(rec.get("fair_page")) else None,
        "sparql_endpoints": endpoints,
        "also_available_at": sites,
    }


def _url_key(url: str) -> str:
    return re.sub(r"^https?://", "", url.strip().lower()).rstrip("/")


def _load() -> dict:
    global _by_lower, _by_norm, _kghb_lower, _kghb_norm, _meta_lower
    if _by_lower is None:
        _by_lower, _by_norm, _kghb_lower, _kghb_norm, _meta_lower = {}, {}, {}, {}, {}
        if KGHB_META.exists():
            with KGHB_META.open(encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    _meta_lower.setdefault(r["id"].strip().lower(),
                                           {"name": r.get("name") or "", "description": r.get("description") or ""})
        if KGHB_CSV.exists():
            with KGHB_CSV.open(encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    ep = {"url": r["endpoint_url"].strip(), "check": r.get("status") or None,
                          "checked_on": r.get("checked_on") or None}
                    _kghb_lower.setdefault(r["id"].strip().lower(), []).append(ep)
                    _kghb_norm.setdefault(_norm(r["id"]), []).append(ep)
        if BLOD_JSON.exists():
            records = json.loads(BLOD_JSON.read_text(encoding="utf-8"))
            for rec in records:
                for key in {rec.get("_id"), rec.get("identifier")} - {None, ""}:
                    _by_lower.setdefault(str(key).strip().lower(), rec)
                    _by_norm.setdefault(_norm(key), rec)
        else:
            print(f"[dataset_links] {BLOD_JSON} not found -- no SPARQL endpoints or links will be shown")
    return _by_lower


def invalidate() -> None:
    global _by_lower
    _by_lower = None
    _cache.clear()
    _text_cache.clear()


def topic_text(dataset_id: str, category: Optional[str] = None) -> str:
    """Lower-cased searchable text for a dataset: id, title, description and
    keywords from BLOD.json, plus the name and description KGHeartBeat records.
    Used for topic search in /federated/select."""
    by_lower = _load()
    cat = category or "blod"
    key = (cat, dataset_id)
    if key not in _text_cache:
        low = str(dataset_id).strip().lower()
        parts = [str(dataset_id)]
        rec = by_lower.get(low)
        if rec is None and cat == "blod":
            rec = _by_norm.get(_norm(dataset_id))
        if rec is not None:
            desc = rec.get("description")
            if isinstance(desc, dict):
                desc = " ".join(str(v) for v in desc.values())
            parts += [rec.get("title") or "", desc or "", " ".join(rec.get("keywords") or [])]
        meta = _meta_lower.get(low)
        if meta:
            parts += [meta["name"], meta["description"]]
        _text_cache[key] = " ".join(p for p in parts if p).lower()
    return _text_cache[key]


def get(dataset_id: str, category: Optional[str] = None) -> dict:
    by_lower = _load()
    cat = category or "blod"
    key = (cat, dataset_id)
    if key not in _cache:
        rec = by_lower.get(str(dataset_id).strip().lower())
        if rec is None and cat == "blod":
            rec = _by_norm.get(_norm(dataset_id))
        links = _links_for(rec) if rec is not None else {**EMPTY, "sparql_endpoints": []}

        kghb = _kghb_lower.get(str(dataset_id).strip().lower())
        if kghb is None and cat == "blod":
            kghb = _kghb_norm.get(_norm(dataset_id))
        by_url = {_url_key(e["url"]): e for e in links["sparql_endpoints"]}
        for k in kghb or []:
            existing = by_url.get(_url_key(k["url"]))
            if existing is not None:
                existing["sources"] = existing["sources"] + ["KGHeartBeat"]
                existing["check"], existing["checked_on"] = k["check"], k["checked_on"]
            else:
                ep = {"url": k["url"], "title": "", "description": "", "sources": ["KGHeartBeat"],
                      "check": k["check"], "checked_on": k["checked_on"]}
                links["sparql_endpoints"].append(ep)
                by_url[_url_key(k["url"])] = ep
        # endpoints KGHeartBeat found online first
        links["sparql_endpoints"].sort(key=lambda e: {"online": 0, None: 1}.get(e["check"], 2))
        _cache[key] = links
    return _cache[key]


def endpoint_urls(dataset_id: str, category: Optional[str] = None) -> list[str]:
    return [e["url"] for e in get(dataset_id, category)["sparql_endpoints"]]
