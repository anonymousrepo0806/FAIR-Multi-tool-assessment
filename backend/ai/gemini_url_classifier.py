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

DEFAULT_MODEL = os.environ.get("GEMINI_URL_CLASSIFIER_MODEL") or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

_PROMPT_TEMPLATE = """\
You are a strict gatekeeper deciding whether a URL points to a reusable
*dataset resource* -- a knowledge graph, ontology, SPARQL/API endpoint, RDF/
data file, database record, or a specific entity/item page in a linked-data
repository -- as opposed to a non-dataset page such as: a search engine, a
social network, a generic company/product homepage, a news article or blog
post, a software repository's README/landing page (not a data release), an
academic paper or preprint (even if it describes a dataset -- the paper
itself is not the dataset), documentation, or any other informational page.

Judge only from the URL string itself -- its domain and path -- using your
general knowledge of what that site/URL pattern usually serves. Do not fetch
anything. When genuinely unsure, lean towards is_dataset=true for domains
that are plausibly data repositories, and lean towards false only when the
URL clearly matches a non-dataset pattern above.

URL: {url}

Respond with ONLY a JSON object, no other text:
{{"is_dataset": true or false, "reasoning": "<one short sentence>"}}
"""


def build_prompt(url: str) -> str:
    return _PROMPT_TEMPLATE.format(url=url)


def classify_dataset_url(
    url: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Ask Gemini whether `url` looks like a dataset resource.

    Returns {"is_dataset": True/False/None, "reasoning": <str or None>,
    "error": <str or None>}. `is_dataset` is None whenever the model
    couldn't be reached (no package, no key, quota hit, bad response, etc.)
    -- callers should treat None as "inconclusive" and fail open (same
    graceful-degradation pattern as this app's other optional Gemini
    integrations: explanations and dataset categorization), since this AI
    check is a second-opinion layer on top of the static blocklist in
    dataset_url_guard.py, not the only gate.
    """
    if genai is None:
        return {"is_dataset": None, "reasoning": None,
                "error": "google-genai package not installed"}

    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return {"is_dataset": None, "reasoning": None,
                "error": "no Gemini API key configured (set GEMINI_API_KEY)"}

    client = genai.Client(api_key=key)
    prompt = build_prompt(url)

    try:
        config = (
            genai_types.GenerateContentConfig(response_mime_type="application/json")
            if genai_types is not None else None
        )
        response = client.models.generate_content(model=model, contents=prompt, config=config)
        text = (response.text or "").strip()
        if not text:
            return {"is_dataset": None, "reasoning": None, "error": "empty response from Gemini"}

        parsed = json.loads(text)
        is_dataset = parsed.get("is_dataset")
        if not isinstance(is_dataset, bool):
            return {"is_dataset": None, "reasoning": parsed.get("reasoning"),
                     "error": "Gemini response did not include a boolean is_dataset"}
        return {"is_dataset": is_dataset, "reasoning": parsed.get("reasoning"), "error": None}

    except json.JSONDecodeError:
        return {"is_dataset": None, "reasoning": None, "error": "Gemini response was not valid JSON"}
    except Exception as e:
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        message_lower = str(e).lower()
        if status == 429 or "quota" in message_lower or "resource_exhausted" in message_lower:
            return {"is_dataset": None, "reasoning": None, "error": "Gemini quota/billing limit hit"}
        if status in (401, 403) or "api key not valid" in message_lower or "permission_denied" in message_lower:
            return {"is_dataset": None, "reasoning": None, "error": "Gemini API key missing or invalid"}
        return {"is_dataset": None, "reasoning": None, "error": f"{type(e).__name__}: {e}"}
