from __future__ import annotations

from fastapi import APIRouter

import ingestion
from ai import gemini_categorizer

router = APIRouter()


@router.get("/ingestion/sources")
async def ingestion_sources():
    return {
        "key_free_sources": ingestion.KEY_FREE_SOURCES,
        "excluded_sources": [
            {"name": "BioPortal", "reason": "requires a free API key (BIOPORTAL_API_KEY)"},
            {"name": "Kaggle", "reason": "requires account credentials (KAGGLE_USERNAME/KAGGLE_KEY)"},
        ],
        "categorization": {
            "method": "Gemini (falls back to direct LOD Cloud domain metadata "
                       "when unambiguous, and to a generic category if Gemini "
                       "is unavailable/unconfigured)",
            "categories": gemini_categorizer.CATEGORIES,
        },
    }

