from __future__ import annotations

from typing import Optional

from . import unified_mapping_base as base


def _fuji_native(raw: dict) -> dict:
    if "error" in raw:
        return {"error": raw["error"]}
    keys = {
        "F": "score_earned_F", "A": "score_earned_A",
        "I": "score_earned_I", "R": "score_earned_R",
        "FAIR": "score_earned_FAIR",
    }
    out = {}
    for dim, key in keys.items():
        if key in raw and raw[key] is not None:
            try:
                out[dim] = float(raw[key])
            except (TypeError, ValueError):
                pass
    if not out:
        return {"error": "F-UJI native scores not present in response"}
    return out


def _fairchecker_native(raw: dict) -> dict:
    if "error" in raw:
        return {"error": raw["error"]}
    out = {}
    for dim in ("F", "A", "I", "R"):
        key = f"total_{dim}"
        if key in raw and raw[key] is not None:
            out[dim] = raw[key]
    if "score_total" in raw and raw["score_total"] is not None:
        out["FAIR"] = raw["score_total"]
    if not out:
        return {"error": "FAIR-Checker native scores not present in response"}
    return out


def _kgheartbeat_native(raw: dict) -> dict:
    if "error" in raw:
        return {"error": raw["error"]}
    out = {}
    for dim in ("F", "A", "I", "R", "FAIR"):
        for key in (dim, dim.lower(), f"score_{dim}", f"{dim}_score"):
            if key in raw and raw[key] is not None:
                try:
                    out[dim] = float(raw[key])
                except (TypeError, ValueError):
                    pass
                break
    if not out:
        return {"note": "KGHeartBeat response contains only raw metrics; "
                         "no distinct native composite reported. See 'mapped' instead."}
    return out


_NATIVE_EXTRACTORS = {
    "fuji": _fuji_native,
    "fairchecker": _fairchecker_native,
    "kgheartbeat": _kgheartbeat_native,
}


def normalise(tool: str, raw: dict) -> dict:
    key = tool.lower().replace(" ", "").replace("-", "")
    extractor = _NATIVE_EXTRACTORS.get(key)
    native = extractor(raw) if extractor else {"error": f"unknown tool '{tool}'"}

    mapped_obj = base.normalise_tool_output(tool, raw)
    if "error" in raw and mapped_obj.error is None:
        mapped_obj.error = raw["error"]

    mapped = {
        "composite": mapped_obj.composite,
        "dimension_scores": mapped_obj.dimension_scores,
        "principle_scores": mapped_obj.principle_scores,
        "metric_scores": mapped_obj.metric_scores,
        "metric_definitions": mapped_obj.metric_definitions,
        "error": mapped_obj.error,
    }

    return {"native": native, "mapped": mapped}
