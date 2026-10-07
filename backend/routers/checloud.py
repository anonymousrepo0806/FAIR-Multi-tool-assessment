from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

import checloud as cc

router = APIRouter()


@router.get("/checloud/summary")
async def checloud_summary():
    return cc.summary()


@router.get("/checloud/datasets")
async def checloud_datasets(
    search: Optional[str] = Query(None),
    sort_desc: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    return cc.list_datasets(search=search, page=page, page_size=page_size, sort_desc=sort_desc)


@router.get("/checloud/datasets/{dataset_id}")
async def checloud_dataset_detail(dataset_id: str):
    detail = cc.dataset_detail(dataset_id)
    if detail is None:
        raise HTTPException(404, f"'{dataset_id}' not found in CheCLOUD")
    return detail
