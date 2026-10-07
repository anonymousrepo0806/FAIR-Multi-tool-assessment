from __future__ import annotations

import json
import os
from typing import Optional

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

DEFAULT_MODEL = os.environ.get("GEMINI_CATEGORIZER_MODEL") or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


CATEGORIES = {
    "blod": "Biomedical / health-related Linked Open Data: ontologies, "
            "knowledge graphs or datasets about diseases, drugs, genes, "
            "clinical data, biomedical terminology, or health informatics.",
    "life-sciences": "Life-sciences data that is NOT specifically biomedical "
                      "or health-related -- e.g. general biology, agriculture, "
                      "ecology, taxonomy, or species data with no clinical/"
                      "health/disease/drug focus.",
    "che-cloud": "Cultural heritage: museums, art, archaeology, historical "
                 "artifacts, monuments, or heritage collections (tangible, "
                 "intangible, or natural heritage).",
    "linguistic": "Language resources: lexicons, thesauri, linguistic "
                   "ontologies, corpora, or terminology databases.",
    "government": "Government or public-sector open data (official "
                   "statistics, administrative data, public records).",
    "publications": "Scholarly publications or bibliographic metadata "
                     "(papers, citations, authors, journals).",
    "social-networking": "Social network or social media data.",
    "cross-domain": "General-purpose, multi-domain reference data spanning "
                     "many topics at once (e.g. DBpedia/Wikidata-style "
                     "encyclopedic knowledge graphs).",
    "user-generated": "User-generated content platforms (reviews, wikis, "
                       "crowdsourced data) not better described by another "
                       "category above.",
    "geography": "Geographic or geospatial data (places, boundaries, maps, "
                  "coordinates).",
    "media": "Media data: music, film, broadcasting, or other audiovisual "
              "content.",
}

_PROMPT_TEMPLATE = """\
You are categorizing a dataset discovered in a Linked Open Data registry
into exactly one of this project's fixed corpus categories, based only on
its title and description below. Never invent facts not implied by the text.

Categories (pick exactly one id):
{categories_json}

A dataset is "blod" ONLY if it is specifically biomedical/health-related --
diseases, drugs, genes, clinical data, biomedical ontologies/terminology,
or health informatics. General biology/agriculture/ecology without a
health/clinical focus is "life-sciences", not "blod". When genuinely
unsure between two close categories, prefer the more specific one.

Dataset:
  id: {dataset_id}
  title: {title}
  description: {description}

Respond with ONLY a JSON object, no other text:
{{"category": "<one of: {category_ids}>", "reasoning": "<one short sentence>"}}
"""


def build_prompt(dataset_id: str, title: str, description: str) -> str:
    return _PROMPT_TEMPLATE.format(
        categories_json=json.dumps(CATEGORIES, indent=2),
        dataset_id=dataset_id,
        title=title or "(no title given)",
        description=(description or "(no description given)")[:2000],
        category_ids=", ".join(CATEGORIES.keys()),
    )


def categorize(
    dataset_id: str,
    title: str = "",
    description: str = "",
    default_category: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Classify one discovered dataset into this app's fixed category set
    using Gemini, the same way this project's own BLOD/CHe-CLOUD research
    used GPT-4o-mini to decide a dataset's domain from its title and
    description (see Blod/src/lodcloud_filter.py's filter_with_gpt()).

    Returns {"category": <slug>, "reasoning": <str>, "error": <str or None>}.
    On any failure (no package, no key, bad response, network error), falls
    back to `default_category` (or "cross-domain" if that's also unset) and
    reports why in "error" -- callers decide whether that's good enough,
    same graceful-degradation pattern as the rest of this app's optional
    integrations (Postgres, GraphDB, Gemini explanations).
    """
    fallback = default_category or "cross-domain"

    if genai is None:
        return {"category": fallback, "reasoning": None,
                "error": "google-genai package not installed"}

    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return {"category": fallback, "reasoning": None,
                "error": "no Gemini API key configured (set GEMINI_API_KEY)"}

    client = genai.Client(api_key=key)
    prompt = build_prompt(dataset_id, title, description)

    try:
        config = (
            genai_types.GenerateContentConfig(response_mime_type="application/json")
            if genai_types is not None else None
        )
        response = client.models.generate_content(model=model, contents=prompt, config=config)
        text = (response.text or "").strip()
        if not text:
            return {"category": fallback, "reasoning": None, "error": "empty response from Gemini"}

        parsed = json.loads(text)
        category = parsed.get("category")
        if category not in CATEGORIES:
            return {"category": fallback, "reasoning": parsed.get("reasoning"),
                    "error": f"Gemini returned an unknown category '{category}'"}
        return {"category": category, "reasoning": parsed.get("reasoning"), "error": None}

    except json.JSONDecodeError:
        return {"category": fallback, "reasoning": None,
                "error": "Gemini response was not valid JSON"}
    except Exception as e:
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        message_lower = str(e).lower()
        if status == 429 or "quota" in message_lower or "resource_exhausted" in message_lower:
            return {"category": fallback, "reasoning": None,
                    "error": "Gemini quota/billing limit hit"}
        if status in (401, 403) or "api key not valid" in message_lower or "permission_denied" in message_lower:
            return {"category": fallback, "reasoning": None,
                    "error": "Gemini API key missing or invalid"}
        return {"category": fallback, "reasoning": None, "error": f"{type(e).__name__}: {e}"}
