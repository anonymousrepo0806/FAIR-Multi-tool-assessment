from __future__ import annotations

import os
from typing import Optional

import pandas as pd
import requests

from . import realtime_fairness

API_URL = os.environ.get("KGHEARTBEAT_API_URL")
DEFAULT_TIMEOUT = int(os.environ.get("KGHEARTBEAT_TIMEOUT", "120"))
REALTIME_TIMEOUT = int(os.environ.get("KGHEARTBEAT_REALTIME_TIMEOUT", "20"))

_EXPORT_COLUMNS = [
    "F1-M", "F1-D", "F2a-M", "F2b-M", "F3-M",
    "A1.1-M", "A1.1-D", "A1.2",
    "I1-M", "I1-D", "I2", "I3-D",
    "R1.1", "R1.2", "R1.3-M", "R1.3-D",
]


def assess_live(url: str, api_url: str = API_URL, timeout: int = DEFAULT_TIMEOUT) -> dict:
    if not api_url:
        return {"error": "no KGHEARTBEAT_API_URL configured — no live endpoint to call"}
    try:
        resp = requests.post(api_url, json={"dataset_url": url}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"KGHeartBeat request failed: {e}"}
    except ValueError:
        return {"error": "KGHeartBeat returned a non-JSON response"}
    return data


def assess_from_export(
    dataset_id: str,
    export_csv: str,
    id_column: str = "KG id",
) -> dict:
    try:
        df = pd.read_csv(export_csv, low_memory=False)
    except (FileNotFoundError, OSError) as e:
        return {"error": f"could not read KGHeartBeat export: {e}"}

    if id_column not in df.columns:
        return {"error": f"export missing expected id column '{id_column}'"}

    match = df[df[id_column].astype(str).str.strip() == str(dataset_id).strip()]
    if match.empty:
        return {"error": f"'{dataset_id}' not found in KGHeartBeat export"}

    row = match.iloc[0]
    return {c: row[c] for c in _EXPORT_COLUMNS if c in df.columns}


def assess_realtime(url: str, timeout: int = REALTIME_TIMEOUT) -> dict:
    try:
        evaluator = realtime_fairness.RealtimeEvaluateFAIRness(url, timeout=timeout)
        return evaluator.run_flat()
    except Exception as e:
        return {"error": f"real-time FAIR probe failed: {type(e).__name__}: {e}"}


def assess(
    url: str,
    dataset_id: Optional[str] = None,
    export_csv: Optional[str] = None,
    id_column: str = "KG id",
    allow_realtime: bool = True,
) -> dict:
    if API_URL:
        result = assess_live(url)
        if "error" not in result:
            return result
    if export_csv and dataset_id:
        result = assess_from_export(dataset_id, export_csv, id_column)
        if "error" not in result:
            return result
    if allow_realtime:
        return assess_realtime(url)
    return {
        "error": (
            "KGHeartBeat was not assessed: no live endpoint configured "
            "(set KGHEARTBEAT_API_URL), no precomputed export supplied "
            "(pass --kgheartbeat-export together with a dataset id), and "
            "real-time probing was disabled."
        )
    }
