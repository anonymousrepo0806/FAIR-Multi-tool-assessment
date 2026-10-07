from __future__ import annotations

DIMENSIONS = ["F", "A", "I", "R"]

HIGH_AGREEMENT_MAX_RANGE = 0.15
MEDIUM_AGREEMENT_MAX_RANGE = 0.35


def _agreement_label(value_range: float) -> str:
    if value_range < HIGH_AGREEMENT_MAX_RANGE:
        return "high"
    if value_range < MEDIUM_AGREEMENT_MAX_RANGE:
        return "medium"
    return "low"


def compute_consensus(mapped_by_tool: dict[str, dict]) -> dict:
    usable = {
        tool: m for tool, m in mapped_by_tool.items()
        if not m.get("error") and m.get("composite") is not None
    }
    missing = [t for t in mapped_by_tool if t not in usable]

    if not usable:
        return {
            "overall": None,
            "by_dimension": {},
            "agreement": "insufficient_data",
            "agreement_by_dimension": {},
            "tools_used": [],
            "tools_missing": missing,
            "range_by_dimension": {},
            "composite_range": None,
            "note": "No tool produced a usable mapped score.",
        }

    by_dimension = {}
    range_by_dimension = {}
    agreement_by_dimension = {}
    for d in DIMENSIONS:
        vals = [m["dimension_scores"][d] for m in usable.values() if d in m.get("dimension_scores", {})]
        if vals:
            by_dimension[d] = round(sum(vals) / len(vals), 4)
            r = round(max(vals) - min(vals), 4)
            range_by_dimension[d] = r
            agreement_by_dimension[d] = _agreement_label(r) if len(vals) > 1 else "single_tool"

    composites = [m["composite"] for m in usable.values()]
    overall = round(sum(composites) / len(composites), 4)
    composite_range = round(max(composites) - min(composites), 4) if len(composites) > 1 else 0.0
    overall_agreement = _agreement_label(composite_range) if len(composites) > 1 else "single_tool"

    return {
        "overall": overall,
        "by_dimension": by_dimension,
        "agreement": overall_agreement,
        "agreement_by_dimension": agreement_by_dimension,
        "tools_used": list(usable.keys()),
        "tools_missing": missing,
        "range_by_dimension": range_by_dimension,
        "composite_range": composite_range,
    }
