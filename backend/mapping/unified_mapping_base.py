from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

DIMENSION_OF = {
    "F1": "F", "F2": "F", "F3": "F",
    "A1": "A", "A1.2": "A",
    "I1": "I", "I2": "I", "I3": "I",
    "R1.1": "R", "R1.2": "R", "R1.3": "R",
}
PRINCIPLES = ["F1", "F2", "F3", "A1", "A1.2", "I1", "I2", "I3", "R1.1", "R1.2", "R1.3"]
DIMENSIONS = ["F", "A", "I", "R"]

FUJI_METRICS = {
    "FsF_F1_01MD_earned": ("F1", 1),
    "FsF_F1_02MD_earned": ("F1", 1),
    "FsF_F2_01M_earned":  ("F2", 2),
    "FsF_F3_01M_earned":  ("F3", 1),
    "FsF_A1_02MD_earned": ("A1", 1),
    "FsF_A1_1_01MD_earned": ("A1", 1),
    "FsF_A1_2_01MD_earned": ("A1.2", 1),
    "FsF_I1_01M_earned":  ("I1", 1),
    "FsF_I2_01M_earned":  ("I2", 1),
    "FsF_I3_01M_earned":  ("I3", 1),
    "FsF_R1_1_01M_earned": ("R1.1", 1),
    "FsF_R1_2_01M_earned": ("R1.2", 1),
    "FsF_R1_3_01M_earned": ("R1.3", 1),
    "FsF_R1_3_02D_earned": ("R1.3", 1),
}

FAIRCHECKER_METRICS = {
    "score_F1A": ("F1", 2),
    "score_F1B": ("F1", 2),
    "score_F2A": ("F2", 2),
    "score_F2B": ("F2", 2),
    "score_A1.1": ("A1", 2),
    "score_A1.2": ("A1.2", 2),
    "score_I1": ("I1", 2),
    "score_I2": ("I2", 2),
    "score_I3": ("I3", 2),
    "score_R1.1": ("R1.1", 2),
    "score_R1.2": ("R1.2", 2),
    "score_R1.3": ("R1.3", 2),
}

KGHEARTBEAT_METRICS = {
    "F1-M": ("F1", 1), "F1-D": ("F1", 1),
    "F2a-M": ("F2", 1), "F2b-M": ("F2", 1),
    "F3-M": ("F3", 1),
    "A1.1-M": ("A1", 1), "A1.1-D": ("A1", 1),
    "A1.2": ("A1.2", 1),
    "I1-M": ("I1", 1), "I1-D": ("I1", 1),
    "I2": ("I2", 1),
    "I3-D": ("I3", 1),
    "R1.1": ("R1.1", 1),
    "R1.2": ("R1.2", 1),
    "R1.3-M": ("R1.3", 1), "R1.3-D": ("R1.3", 1),
}

KGHEARTBEAT_METRIC_DEFINITIONS = {
    "F1-M": "Binary: 1 if the dataset is registered in a search engine that "
            "provides a persistent DOI, else 0.",
    "F1-D": "Ratio: |dereferenceable URIs| / |sampled URIs|, sampled at "
            "|U_g| = 5000.",
    "F2a-M": "Binary: 1 if metadata is available via a standard primary "
             "source (SPARQL endpoint, searchable engine, or VoID/DCAT), else 0.",
    "F2b-M": "Ratio: |covered required metadata attributes| / |required "
             "metadata attributes|.",
    "F3-M": "Binary: 1 if metadata attaches a DOI (or DOIs) to the data, else 0.",
    "A1.1-D": "Ternary: 1 if an operational SPARQL endpoint or accessible "
              "data dump is found; 0.5 if merely accessible; 0 otherwise.",
    "A1.1-M": "Binary: 1 if the primary sources found for F2a-M contain "
              "metadata, else 0.",
    "A1.2": "Binary: 1 if authentication/HTTPS support can be discovered "
            "via SPARQL, else 0.",
    "I1-D": "Binary: 1 if the data uses a standard/open representation "
            "format (valid media type, or OWL/RDF(S)), else 0.",
    "I1-M": "Binary: 1 if metadata is published according to VoID/DCAT "
            "specifications, else 0.",
    "I2": "Ratio: (# vocabularies recognised as FAIR) / (# total "
          "vocabularies used).",
    "I3-D": "Binary: 1 if the data contains a link to another dataset, else 0.",
    "R1.1": "Binary: 1 if a license is explicitly reported, else 0.",
    "R1.2": "Binary: 1 if publisher details are explicitly reported, else 0.",
    "R1.3-D": "Binary: 1 if data is organised in a standard way (SPARQL "
              "endpoint, valid data dump, or OWL/RDFS), else 0.",
    "R1.3-M": "Binary: same definition and value as I1-M (VoID/DCAT "
              "description present).",
}

FUJI_METRIC_DEFINITIONS = {
    "FsF_F1_01MD_earned": "Binary (0/1): the resource is assigned a globally unique identifier "
                           "(e.g. DOI, Handle, URL) that unambiguously identifies it.",
    "FsF_F1_02MD_earned": "Binary (0/1): that identifier is persistent -- resolves reliably over "
                           "time via a recognised PID scheme rather than a plain URL.",
    "FsF_F2_01M_earned": "0-2 points: structured, machine-readable metadata describing the "
                          "resource is available, scored on how rich/complete it is.",
    "FsF_F3_01M_earned": "Binary (0/1): the metadata explicitly includes/links the identifier of "
                          "the data it describes.",
    "FsF_A1_02MD_earned": "Binary (0/1): metadata specifies the access protocol/procedure used to "
                           "retrieve the data.",
    "FsF_A1_1_01MD_earned": "Binary (0/1): the data (and/or its metadata) is retrievable via a "
                             "standardised, open communication protocol (e.g. HTTP(S), SPARQL).",
    "FsF_A1_2_01MD_earned": "Binary (0/1): metadata specifies any access restrictions, "
                             "authentication or licence requirements needed to access the data.",
    "FsF_I1_01M_earned": "Binary (0/1): metadata uses a formal, machine-interpretable knowledge "
                          "representation language (e.g. RDF, RDFS/OWL).",
    "FsF_I2_01M_earned": "Binary (0/1): metadata uses vocabularies/ontologies that themselves "
                          "follow FAIR principles (resolvable, documented terms).",
    "FsF_I3_01M_earned": "Binary (0/1): metadata includes qualified references/links to other "
                          "related resources.",
    "FsF_R1_1_01M_earned": "Binary (0/1): a clear, accessible usage licence is specified for the "
                            "data.",
    "FsF_R1_2_01M_earned": "Binary (0/1): metadata includes detailed provenance information (e.g. "
                            "source, authorship, processing history).",
    "FsF_R1_3_01M_earned": "Binary (0/1): metadata conforms to a recognised, domain-relevant "
                            "community standard/schema.",
    "FsF_R1_3_02D_earned": "Binary (0/1): the data itself is provided in a format that follows a "
                            "recognised community standard.",
}

FAIRCHECKER_METRIC_DEFINITIONS = {
    "score_F1A": "Ordinal 0-2: whether the resource has a globally unique identifier.",
    "score_F1B": "Ordinal 0-2: whether that identifier is persistent.",
    "score_F2A": "Ordinal 0-2: whether the resource has structured, machine-readable metadata.",
    "score_F2B": "Ordinal 0-2: richness/completeness of that descriptive metadata.",
    "score_A1.1": "Ordinal 0-2: whether the resource is retrievable via a standardised, open, "
                  "free access protocol.",
    "score_A1.2": "Ordinal 0-2: whether the access protocol supports authentication/"
                  "authorisation where the resource needs it.",
    "score_I1": "Ordinal 0-2: whether the resource uses a formal, accessible, shared knowledge "
                "representation (RDF).",
    "score_I2": "Ordinal 0-2: whether the vocabularies/ontologies used themselves follow FAIR "
                "principles.",
    "score_I3": "Ordinal 0-2: whether the resource includes qualified references to other "
                "resources.",
    "score_R1.1": "Ordinal 0-2: whether a clear and accessible data usage licence is provided.",
    "score_R1.2": "Ordinal 0-2: whether detailed provenance metadata is provided.",
    "score_R1.3": "Ordinal 0-2: whether the resource meets domain-relevant community standards.",
}

TOOL_METRICS = {
    "fuji": FUJI_METRICS,
    "faircheker": FAIRCHECKER_METRICS,
    "fairchecker": FAIRCHECKER_METRICS,
    "kgheartbeat": KGHEARTBEAT_METRICS,
}


@dataclass
class ToolResult:
    tool: str
    metric_scores: dict = field(default_factory=dict)
    metric_definitions: dict = field(default_factory=dict)
    principle_scores: dict = field(default_factory=dict)
    dimension_scores: dict = field(default_factory=dict)
    composite: Optional[float] = None
    raw: dict = field(default_factory=dict)
    error: Optional[str] = None


def get_metric_definition(tool: str, metric: str) -> Optional[str]:
    key = tool.lower().replace(" ", "").replace("-", "")
    if key == "kgheartbeat":
        return KGHEARTBEAT_METRIC_DEFINITIONS.get(metric)
    if key == "fuji":
        return FUJI_METRIC_DEFINITIONS.get(metric)
    if key in ("fairchecker", "faircheker"):
        return FAIRCHECKER_METRIC_DEFINITIONS.get(metric)
    return None


def normalise_tool_output(tool: str, raw: dict) -> ToolResult:
    key = tool.lower().replace(" ", "").replace("-", "")
    metrics = TOOL_METRICS.get(key)
    if metrics is None:
        return ToolResult(tool=tool, raw=raw, error=f"unknown tool '{tool}'")

    result = ToolResult(tool=tool, raw=raw)

    for col, (principle, attainable) in metrics.items():
        if col not in raw or raw[col] is None:
            continue
        try:
            earned = float(raw[col])
        except (TypeError, ValueError):
            continue
        s = max(0.0, min(1.0, earned / attainable)) if attainable else 0.0
        result.metric_scores[col] = s
        definition = get_metric_definition(tool, col)
        if definition:
            result.metric_definitions[col] = definition

    by_principle: dict[str, list[float]] = {p: [] for p in PRINCIPLES}
    for col, s in result.metric_scores.items():
        principle, _ = metrics[col]
        by_principle[principle].append(s)
    for p, vals in by_principle.items():
        if vals:
            result.principle_scores[p] = sum(vals) / len(vals)

    by_dim: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    for p, s in result.principle_scores.items():
        by_dim[DIMENSION_OF[p]].append(s)
    for d, vals in by_dim.items():
        if vals:
            result.dimension_scores[d] = sum(vals) / len(vals)

    dim_vals = list(result.dimension_scores.values())
    if dim_vals:
        result.composite = sum(dim_vals) / len(dim_vals)

    return result


def aggregate_across_tools(results: list[ToolResult]) -> dict:
    ok = [r for r in results if r.error is None and r.composite is not None]
    if not ok:
        return {"tools_used": [], "note": "No tool produced a usable score."}

    out = {"tools_used": [r.tool for r in ok]}

    for d in DIMENSIONS:
        vals = [r.dimension_scores[d] for r in ok if d in r.dimension_scores]
        if vals:
            out[f"dimension_{d}_mean"] = round(sum(vals) / len(vals), 4)
            out[f"dimension_{d}_min"] = round(min(vals), 4)
            out[f"dimension_{d}_max"] = round(max(vals), 4)
            out[f"dimension_{d}_range"] = round(max(vals) - min(vals), 4)

    composites = [r.composite for r in ok]
    out["composite_mean"] = round(sum(composites) / len(composites), 4)
    out["composite_min"] = round(min(composites), 4)
    out["composite_max"] = round(max(composites), 4)
    out["composite_range"] = round(max(composites) - min(composites), 4)
    out["composite_agreement"] = (
        "high" if out["composite_range"] < 0.15 else
        "moderate" if out["composite_range"] < 0.35 else
        "low"
    )
    return out
