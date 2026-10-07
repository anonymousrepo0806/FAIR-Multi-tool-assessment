from __future__ import annotations

import asyncio
import io
import json
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from mapping import unified_mapping
from aggregation import consensus as consensus_mod
from tools import fuji_client, fairchecker_client, kgheartbeat_client
from dataset_url_guard import check_dataset_url, check_dataset_url_with_ai, InvalidDatasetUrlError

router = APIRouter()


class AssessResponse(BaseModel):
    input: dict
    tool_results: dict
    consensus: dict


def _parse_uploaded_file(filename: str, content: bytes) -> list[dict]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
        id_col = "id" if "id" in df.columns else df.columns[0]
        url_col = "url" if "url" in df.columns else id_col
        out = []
        for _, row in df.iterrows():
            rid = str(row[id_col]).strip()
            rurl = str(row[url_col]).strip()
            if rid and rid.lower() != "nan":
                out.append({"id": rid, "url": rurl})
        return out
    if lower.endswith(".json"):
        data = json.loads(content.decode("utf-8"))
        out = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    out.append({"id": item, "url": item})
                elif isinstance(item, dict):
                    rid = str(item.get("id") or item.get("url") or "").strip()
                    rurl = str(item.get("url") or item.get("id") or "").strip()
                    if rid:
                        out.append({"id": rid, "url": rurl})
        return out
    raise HTTPException(400, f"Unsupported file type: {filename}. Use .csv or .json.")


async def _run_all_tools(
    url: str,
    dataset_id: str,
    run_fuji: bool = True,
    run_fairchecker: bool = True,
    run_kgheartbeat: bool = True,
    fuji_api_url: Optional[str] = None,
    kgheartbeat_export_csv: Optional[str] = None,
    kgheartbeat_id_column: str = "KG id",
) -> dict:
    tasks = {}

    if run_fuji:
        kwargs = {"api_url": fuji_api_url} if fuji_api_url else {}
        tasks["fuji"] = asyncio.to_thread(fuji_client.assess, url, **kwargs)
    if run_fairchecker:
        tasks["fairchecker"] = asyncio.to_thread(fairchecker_client.assess, url)
    if run_kgheartbeat:
        tasks["kgheartbeat"] = asyncio.to_thread(
            kgheartbeat_client.assess, url,
            dataset_id=dataset_id,
            export_csv=kgheartbeat_export_csv,
            id_column=kgheartbeat_id_column,
        )

    names = list(tasks.keys())
    raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    raw_by_tool = {}
    for name, res in zip(names, raw_results):
        if isinstance(res, Exception):
            raw_by_tool[name] = {"error": f"{type(res).__name__}: {res}"}
        else:
            raw_by_tool[name] = res

    tool_results = {}
    mapped_by_tool = {}
    for tool, raw in raw_by_tool.items():
        norm = unified_mapping.normalise(tool, raw)
        tool_results[tool] = norm
        mapped_by_tool[tool] = norm["mapped"]

    consensus = consensus_mod.compute_consensus(mapped_by_tool)

    return {"tool_results": tool_results, "consensus": consensus}


@router.post("/assess", response_model=AssessResponse)
async def assess(
    input_type: str = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    run_fuji: bool = Form(True),
    run_fairchecker: bool = Form(True),
    run_kgheartbeat: bool = Form(True),
    fuji_api_url: Optional[str] = Form(None),
    kgheartbeat_id_column: str = Form("KG id"),
):
    if input_type not in ("file", "url"):
        raise HTTPException(400, "input_type must be 'file' or 'url'")

    if input_type == "url":
        if not url or not url.strip():
            raise HTTPException(400, "url is required when input_type='url'")
        target_id, target_url = url.strip(), url.strip()
        try:
            await asyncio.to_thread(check_dataset_url_with_ai, target_url)
        except InvalidDatasetUrlError as e:
            raise HTTPException(400, str(e))
        input_echo = {"type": "url", "value": url.strip()}
    else:
        if file is None:
            raise HTTPException(400, "file is required when input_type='file'")
        content = await file.read()
        resources = _parse_uploaded_file(file.filename, content)
        if not resources:
            raise HTTPException(400, "No resources found in the uploaded file")
        target_id, target_url = resources[0]["id"], resources[0]["url"]
        try:
            await asyncio.to_thread(check_dataset_url_with_ai, target_url)
        except InvalidDatasetUrlError as e:
            raise HTTPException(400, f"First resource in file ({target_id}): {e}")
        input_echo = {"type": "file", "value": file.filename, "resources_found": len(resources)}

    result = await _run_all_tools(
        target_url, target_id,
        run_fuji=run_fuji, run_fairchecker=run_fairchecker, run_kgheartbeat=run_kgheartbeat,
        fuji_api_url=fuji_api_url, kgheartbeat_id_column=kgheartbeat_id_column,
    )

    return {"input": input_echo, **result}


@router.post("/assess/batch")
async def assess_batch(
    file: UploadFile = File(...),
    run_fuji: bool = Form(True),
    run_fairchecker: bool = Form(True),
    run_kgheartbeat: bool = Form(True),
    fuji_api_url: Optional[str] = Form(None),
    kgheartbeat_id_column: str = Form("KG id"),
):
    content = await file.read()
    resources = _parse_uploaded_file(file.filename, content)
    if not resources:
        raise HTTPException(400, "No resources found in the uploaded file")

    results = []
    for r in resources:


        try:
            check_dataset_url(r["url"])
        except InvalidDatasetUrlError as e:
            results.append({
                "input": {"type": "file", "value": r["id"]},
                "error": f"Skipped -- not a valid dataset URL: {e}",
            })
            continue
        one = await _run_all_tools(
            r["url"], r["id"],
            run_fuji=run_fuji, run_fairchecker=run_fairchecker, run_kgheartbeat=run_kgheartbeat,
            fuji_api_url=fuji_api_url, kgheartbeat_id_column=kgheartbeat_id_column,
        )
        results.append({"input": {"type": "file", "value": r["id"]}, **one})

    return {"input": {"type": "file", "value": file.filename, "resources_found": len(resources)},
            "results": results}
