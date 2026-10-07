from __future__ import annotations

import os
import requests

DEFAULT_API_URL = os.environ.get("FUJI_API_URL", "http://localhost:1071/fuji/api/v1/evaluate")
DEFAULT_USER = os.environ.get("FUJI_USER", "marvel")
DEFAULT_PASSWORD = os.environ.get("FUJI_PASSWORD", "wonderwoman")
DEFAULT_TIMEOUT = int(os.environ.get("FUJI_TIMEOUT", "120"))


def _extract_summary_scores(summary: dict) -> dict:
    out = {}
    for key, value in summary.get("score_earned", {}).items():
        out[f"score_earned_{key.replace('.', '_')}"] = value
    return out


def assess(
    url: str,
    api_url: str = DEFAULT_API_URL,
    user: str = DEFAULT_USER,
    password: str = DEFAULT_PASSWORD,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    payload = {
        "object_identifier": url,
        "test_debug": False,
        "use_datacite": True,
        "use_crossref": True,
    }
    try:
        resp = requests.post(api_url, json=payload, auth=(user, password), timeout=timeout)
    except requests.exceptions.RequestException as e:
        return {"error": f"F-UJI request failed: {e}"}

    if resp.status_code != 200:
        return {"error": f"F-UJI returned HTTP {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"error": "F-UJI returned a non-JSON response"}

    if "summary" not in data:
        return {"error": "F-UJI response missing 'summary' (evaluation likely failed)"}

    flat = _extract_summary_scores(data["summary"])

    for metric in data.get("results", []):
        raw_id = metric.get("metric_identifier", "")
        metric_id = raw_id.replace("-", "_").replace(".", "_")
        score_block = metric.get("score", {})
        flat[f"{metric_id}_earned"] = score_block.get("earned", 0)
        for test_id, test_data in metric.get("metric_tests", {}).items():
            clean_id = test_id.replace("-", "_").replace(".", "_")
            test_score = test_data.get("metric_test_score", {})
            flat[f"{clean_id}_earned"] = test_score.get("earned", 0)

    flat["_full_response"] = data
    return flat


def check_server(api_url: str = DEFAULT_API_URL, timeout: int = 5) -> bool:
    ui_url = api_url.rsplit("/evaluate", 1)[0] + "/ui/"
    try:
        r = requests.get(ui_url, timeout=timeout)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False
