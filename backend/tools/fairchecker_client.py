from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse

import requests

from mapping.unified_mapping_base import FAIRCHECKER_METRICS, DIMENSION_OF

API_URL = os.environ.get("FAIRCHECKER_API_URL", "https://fair-checker.france-bioinformatique.fr")
DEFAULT_TIMEOUT = int(os.environ.get("FAIRCHECKER_TIMEOUT", "60"))

BLOCKED_DOMAINS = {"thermofisher.com", "wikipedia.org", "github.com", "example.com"}
BLOCKED_PATHS = {"/about", "/contact", "/documentation", "/help"}

_session = requests.Session()
_session.headers.update({"Accept": "application/json"})


def _is_assessable(url: str) -> bool:
    try:
        p = urlparse(url)
        if any(d in p.netloc for d in BLOCKED_DOMAINS):
            return False
        if any(p.path.lower().startswith(bp) for bp in BLOCKED_PATHS):
            return False
        return True
    except Exception:
        return False


def _preprocess_url(url: str) -> Optional[str]:
    try:
        url = str(url).strip()
        if not _is_assessable(url):
            return None
        p = urlparse(url)
        if "bio2rdf.org" in p.netloc and p.path.count("/") >= 2:
            ds = p.path.strip("/").split("/")[-1]
            return f"http://download.bio2rdf.org/release/3/{ds}/{ds}.nt"
        if "ontobee.org" in p.netloc:
            return "http://sparql.hegroup.org/sparql"
        if "bioportal.bioontology.org" in p.netloc:
            return f"http://data.bioontology.org/ontologies/{p.path.split('/')[-1]}"
        return url
    except Exception:
        return None


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def assess(url: str, api_url: str = API_URL, timeout: int = DEFAULT_TIMEOUT) -> dict:
    processed = _preprocess_url(url)
    if not processed:
        return {"error": "URL was filtered out (blocked domain/path)"}

    try:
        resp = _session.get(
            f"{api_url}/api/check/legacy/metrics_all",
            params={"url": processed},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"error": "FAIR-Checker request timed out"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"FAIR-Checker returned HTTP {e.response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"FAIR-Checker request failed: {e}"}
    except ValueError:
        return {"error": "FAIR-Checker returned a non-JSON response"}

    if not isinstance(data, list):
        return {"error": "Unexpected FAIR-Checker response shape", "raw_response": str(data)[:500]}

    flat = {"processed_url": processed}
    all_scores = []
    for item in data:
        metric = item.get("metric", "").strip()
        score = _safe_float(item.get("score"))
        if metric:
            flat[f"score_{metric}"] = score
            flat[f"recommendation_{metric}"] = item.get("recommendation", "")
            flat[f"comment_{metric}"] = item.get("comment", "")
        if score is not None:
            all_scores.append(score)

    if all_scores:
        flat["score_total"] = sum(all_scores)
        flat["score_avg"] = round(sum(all_scores) / len(all_scores), 3)
        flat["metrics_evaluated"] = len(all_scores)

    by_dimension: dict[str, float] = {}
    for col, (principle, _attainable) in FAIRCHECKER_METRICS.items():
        val = flat.get(col)
        if val is None:
            continue
        dim = DIMENSION_OF.get(principle)
        if dim is None:
            continue
        by_dimension[dim] = by_dimension.get(dim, 0.0) + val
    for dim in ("F", "A", "I", "R"):
        if dim in by_dimension:
            flat[f"total_{dim}"] = by_dimension[dim]

    return flat
