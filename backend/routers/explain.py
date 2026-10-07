from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ai import gemini_explainer

router = APIRouter()


class ExplainRequest(BaseModel):
    consensus: dict
    tool_results: dict = {}
    gemini_api_key: Optional[str] = None


class ExplainResponse(BaseModel):
    explanation: str


@router.post("/explain", response_model=ExplainResponse)
async def explain(req: ExplainRequest):
    text = gemini_explainer.explain(
        consensus=req.consensus,
        tool_results=req.tool_results,
        api_key=req.gemini_api_key,
    )
    return {"explanation": text}
