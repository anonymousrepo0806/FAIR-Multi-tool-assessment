from __future__ import annotations

from fastapi import APIRouter

from mapping import unified_mapping_base as base

router = APIRouter()

TOOL_LABELS = {
    "fuji": "F-UJI",
    "fairchecker": "FAIR-Checker",
    "kgheartbeat": "KGHeartBeat",
}


def _table_by_principle(metrics: dict) -> dict:
    out: dict[str, list] = {p: [] for p in base.PRINCIPLES}
    for column, (principle, attainable) in metrics.items():
        out.setdefault(principle, []).append({"column": column, "attainable": attainable})
    return out


@router.get("/mapping/reference")
async def mapping_reference():
    tools = {
        "fuji": _table_by_principle(base.FUJI_METRICS),
        "fairchecker": _table_by_principle(base.FAIRCHECKER_METRICS),
        "kgheartbeat": _table_by_principle(base.KGHEARTBEAT_METRICS),
    }
    return {
        "principles": base.PRINCIPLES,
        "dimensions": base.DIMENSIONS,
        "dimension_of": base.DIMENSION_OF,
        "tool_labels": TOOL_LABELS,
        "tools": tools,
        "kgheartbeat_metric_definitions": base.KGHEARTBEAT_METRIC_DEFINITIONS,
    }
