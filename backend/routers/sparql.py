from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

import sparql_endpoint as sparql

router = APIRouter()


class SparqlBody(BaseModel):
    query: str


def _run(query: str) -> dict:
    if not query or not query.strip():
        raise HTTPException(400, "SPARQL 'query' must not be empty")
    try:
        columns, rows = sparql.run_query(query)
    except Exception as e:
        raise HTTPException(400, f"SPARQL error: {type(e).__name__}: {e}")
    return {"columns": columns, "rows": rows, "count": len(rows)}


@router.get("/sparql")
async def sparql_get(query: str = Query(..., description="A SPARQL 1.1 query (SELECT/ASK/CONSTRUCT)")):
    return _run(query)


@router.post("/sparql")
async def sparql_post(body: SparqlBody):
    return _run(body.query)


@router.get("/sparql/csv", response_class=PlainTextResponse)
async def sparql_csv(query: str = Query(..., description="A SPARQL 1.1 query (SELECT/ASK)")):
    if not query or not query.strip():
        raise HTTPException(400, "SPARQL 'query' must not be empty")
    try:
        csv_text = sparql.run_query_csv(query)
    except Exception as e:
        raise HTTPException(400, f"SPARQL error: {type(e).__name__}: {e}")
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sparql_results.csv"},
    )


@router.get("/sparql/schema")
async def sparql_schema():
    return {
        "prefixes": {"fair": str(sparql.FAIR), "ds": str(sparql.DS)},
        "predicates": [
            {"predicate": "fair:id", "description": "Dataset id (string)"},
            {"predicate": "fair:category", "description": "LOD sub-cloud category (string)"},
            {"predicate": "fair:repository", "description": "BLOD source repository, where known (string)"},
            {"predicate": "fair:fujiComposite / fair:faircheckerComposite / fair:kgheartbeatComposite",
             "description": "Each tool's composite FAIR score on the unified 0-1 scale (double)"},
            {"predicate": "fair:<tool>_F / _A / _I / _R (e.g. fair:fuji_F)",
             "description": "Each tool's per-dimension score (double)"},
            {"predicate": "fair:consensusScore", "description": "Cross-tool agreed-upon composite (double)"},
            {"predicate": "fair:consensusAgreement",
             "description": "\"high\" | \"medium\" | \"low\" | \"single_tool\" (string)"},
        ],
        "example_queries": sparql.EXAMPLE_QUERIES,
    }
