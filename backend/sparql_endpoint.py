from __future__ import annotations

import csv
import io
from typing import Optional

import pandas as pd
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

import graphdb_client
from aggregation import consensus as consensus_mod
from routers.corpus import _load, _row_to_mapped_by_tool

FAIR = Namespace("https://fair-multi-assessor.local/schema#")
DS = Namespace("https://fair-multi-assessor.local/dataset/")

_graph: Optional[Graph] = None


def _slug(text: str) -> str:
    return str(text).strip().replace(" ", "_")


def _dataset_uri(dataset_id: str, category: str) -> URIRef:
    return DS[f"{_slug(category)}/{_slug(dataset_id)}"]


def _add_dataset_triples(g: Graph, row) -> None:
    """Emit one dataset's triples into `g`. Shared by build_graph() (the
    full in-memory rebuild) and graphdb_client.add_rows() (the incremental
    push used by the monthly ingestion job), so the two never drift apart."""
    category = row.get("category") if pd.notna(row.get("category")) else "blod"
    dataset_id = row["id"]
    uri = _dataset_uri(dataset_id, category)

    g.add((uri, RDF.type, FAIR.Dataset))
    g.add((uri, FAIR.id, Literal(dataset_id)))
    g.add((uri, FAIR.category, Literal(category)))

    repository = row.get("repository")
    if pd.notna(repository):
        g.add((uri, FAIR.repository, Literal(repository)))

    mapped_by_tool = _row_to_mapped_by_tool(row)
    for tool, mapped in mapped_by_tool.items():
        if mapped.get("composite") is not None:
            g.add((uri, FAIR[f"{tool}Composite"], Literal(float(mapped["composite"]), datatype=XSD.double)))
        for dim, val in (mapped.get("dimension_scores") or {}).items():
            g.add((uri, FAIR[f"{tool}_{dim}"], Literal(float(val), datatype=XSD.double)))

    cons = consensus_mod.compute_consensus(mapped_by_tool)
    if cons.get("overall") is not None:
        g.add((uri, FAIR.consensusScore, Literal(float(cons["overall"]), datatype=XSD.double)))
    if cons.get("agreement"):
        g.add((uri, FAIR.consensusAgreement, Literal(cons["agreement"])))


def graph_for_rows(rows) -> Graph:
    """Build a standalone graph for just the given rows (a DataFrame or a
    list of row-like mappings) -- used to push only the newly-ingested
    datasets to GraphDB instead of re-serializing the whole corpus."""
    g = Graph()
    g.bind("fair", FAIR)
    g.bind("ds", DS)
    iterator = (row for _, row in rows.iterrows()) if hasattr(rows, "iterrows") else iter(rows)
    for row in iterator:
        _add_dataset_triples(g, row)
    return g


def invalidate() -> None:
    """Drop the cached in-memory graph so the next query rebuilds it from
    the current corpus -- called after the monthly ingestion job appends
    new datasets, same idea as corpus._df being reset."""
    global _graph
    _graph = None


def build_graph(force: bool = False) -> Graph:
    global _graph
    if _graph is not None and not force:
        return _graph

    g = Graph()
    g.bind("fair", FAIR)
    g.bind("ds", DS)

    df = _load()
    for _, row in df.iterrows():
        _add_dataset_triples(g, row)

    _graph = g
    return g


def run_query(query: str) -> tuple[list[str], list[list[str]]]:
    if graphdb_client.is_enabled():
        try:
            return graphdb_client.run_query(query)
        except Exception:


            pass

    g = build_graph()
    result = g.query(query)

    if result.type == "ASK":
        return ["ask"], [["true" if result.askAnswer else "false"]]

    columns = [str(v) for v in (result.vars or [])]
    rows = []
    for binding in result:
        rows.append(["" if v is None else str(v) for v in binding])
    return columns, rows


def run_query_csv(query: str) -> str:
    columns, rows = run_query(query)
    buf = io.StringIO()
    writer = csv.writer(buf)
    if columns:
        writer.writerow(columns)
    writer.writerows(rows)
    return buf.getvalue()


EXAMPLE_QUERIES = [
    {
        "label": "Top 20 by consensus score",
        "query": (
            "PREFIX fair: <https://fair-multi-assessor.local/schema#>\n"
            "SELECT ?id ?category ?consensusScore WHERE {\n"
            "  ?ds fair:id ?id ; fair:category ?category ; fair:consensusScore ?consensusScore .\n"
            "}\n"
            "ORDER BY DESC(?consensusScore)\n"
            "LIMIT 20"
        ),
    },
    {
        "label": "High KGHeartBeat, low FAIR-Checker (biggest disagreement)",
        "query": (
            "PREFIX fair: <https://fair-multi-assessor.local/schema#>\n"
            "SELECT ?id ?category ?kgheartbeatComposite ?faircheckerComposite WHERE {\n"
            "  ?ds fair:id ?id ; fair:category ?category ;\n"
            "      fair:kgheartbeatComposite ?kgheartbeatComposite ;\n"
            "      fair:faircheckerComposite ?faircheckerComposite .\n"
            "  FILTER(?kgheartbeatComposite > 0.8 && ?faircheckerComposite < 0.5)\n"
            "}\n"
            "ORDER BY DESC(?kgheartbeatComposite)"
        ),
    },
    {
        "label": "Count datasets per category",
        "query": (
            "PREFIX fair: <https://fair-multi-assessor.local/schema#>\n"
            "SELECT ?category (COUNT(?ds) AS ?count) WHERE {\n"
            "  ?ds fair:category ?category .\n"
            "}\n"
            "GROUP BY ?category\n"
            "ORDER BY DESC(?count)"
        ),
    },
    {
        "label": "All BLOD datasets via the BioPortal repository",
        "query": (
            "PREFIX fair: <https://fair-multi-assessor.local/schema#>\n"
            "SELECT ?id ?consensusScore WHERE {\n"
            "  ?ds fair:id ?id ; fair:repository \"BioPortal\" ; fair:consensusScore ?consensusScore .\n"
            "}\n"
            "ORDER BY DESC(?consensusScore)"
        ),
    },
]
