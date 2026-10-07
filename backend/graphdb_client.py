from __future__ import annotations

import os
from typing import Optional

import requests

GRAPHDB_SPARQL_URL = os.environ.get("GRAPHDB_SPARQL_URL", "").strip().rstrip("/")
GRAPHDB_UPDATE_URL = os.environ.get("GRAPHDB_UPDATE_URL", "").strip().rstrip("/") or (
    f"{GRAPHDB_SPARQL_URL}/statements" if GRAPHDB_SPARQL_URL else ""
)

_TIMEOUT = float(os.environ.get("GRAPHDB_TIMEOUT_SECONDS", "15"))


def is_enabled() -> bool:
    return bool(GRAPHDB_SPARQL_URL)


def _ask(query: str) -> bool:
    resp = requests.get(
        GRAPHDB_SPARQL_URL,
        params={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return bool(resp.json().get("boolean"))


def _has_any_triples() -> bool:
    return _ask("ASK { ?s ?p ?o }")


def ensure_seeded(force: bool = False) -> int:
    """Push the corpus into the GraphDB repository over the standard SPARQL
    1.1 Graph Store / RDF4J statements endpoint, but only if it's currently
    empty (or `force`). Returns the number of triples pushed (0 if skipped
    because the repository already has data -- a restart isn't a re-import).

    Deferred import of build_graph to avoid a circular import: sparql_endpoint
    imports this module to decide whether to route queries here.
    """
    if not is_enabled():
        raise RuntimeError("GRAPHDB_SPARQL_URL is not set -- GraphDB is disabled")
    if not force and _has_any_triples():
        return 0

    from sparql_endpoint import build_graph

    g = build_graph()
    nt = g.serialize(format="nt")
    if isinstance(nt, str):
        nt = nt.encode("utf-8")

    resp = requests.post(
        GRAPHDB_UPDATE_URL,
        data=nt,
        headers={"Content-Type": "application/n-triples"},
        timeout=max(_TIMEOUT, 60),
    )
    resp.raise_for_status()
    return len(g)


def add_rows(rows) -> int:
    """Incrementally push just the given rows (a DataFrame or list of
    row-like mappings) to GraphDB, without touching what's already there --
    used by the monthly ingestion job so adding N new datasets doesn't
    require re-uploading the whole corpus. Returns the number of triples
    sent (0 if `rows` is empty or GraphDB isn't enabled)."""
    if not is_enabled():
        return 0

    from sparql_endpoint import graph_for_rows

    g = graph_for_rows(rows)
    if len(g) == 0:
        return 0

    nt = g.serialize(format="nt")
    if isinstance(nt, str):
        nt = nt.encode("utf-8")

    resp = requests.post(
        GRAPHDB_UPDATE_URL,
        data=nt,
        headers={"Content-Type": "application/n-triples"},
        timeout=max(_TIMEOUT, 60),
    )
    resp.raise_for_status()
    return len(g)


def run_query(query: str) -> tuple[list[str], list[list[str]]]:
    """Run a SPARQL query against the remote GraphDB repository over the
    standard SPARQL 1.1 Protocol (SPARQL-results+JSON), returning the same
    (columns, rows) shape as sparql_endpoint.run_query()'s in-memory path,
    so routers/sparql.py doesn't need to know which backend answered it."""
    resp = requests.post(
        GRAPHDB_SPARQL_URL,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()

    if "boolean" in payload:
        return ["ask"], [["true" if payload["boolean"] else "false"]]

    columns = payload.get("head", {}).get("vars", [])
    rows = []
    for binding in payload.get("results", {}).get("bindings", []):
        rows.append([binding[c]["value"] if c in binding else "" for c in columns])
    return columns, rows
