from __future__ import annotations

import json
import os
from typing import Optional

try:
    from google import genai
except ImportError:
    genai = None

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

SECTION_HEADERS = [
    "## Overall FAIR Compliance",
    "## Strengths",
    "## Weaknesses",
    "## Tool Disagreement",
    "## Recommendations",
]

_PROMPT_TEMPLATE = """\
You are explaining an automated multi-tool FAIR assessment result to a data
publisher who is not a FAIR expert. Use ONLY the numbers given below -- never
invent a score. If a tool's data is missing, say so plainly rather than
guessing.

Consensus result (mapped, 0-1 scale, higher is better):
{consensus_json}

Per-tool results (native = the tool's own score in its own units; mapped =
normalised onto the shared 0-1 scale used for the consensus above):
{tool_results_json}

Write your response as markdown with EXACTLY these five sections, in this
exact order, using these exact headers:

## Overall FAIR Compliance
(2-3 sentences: where this resource stands overall, referencing the actual
consensus.overall number and the agreement level.)

## Strengths
(Bullet list: dimensions where tools scored high AND agreed with each other.
If none, say so explicitly rather than omitting the section.)

## Weaknesses
(Bullet list: dimensions where scores were low, referencing the actual
dimension score. Be concrete about what a low score in that dimension means
practically for someone trying to reuse this resource.)

## Tool Disagreement
(1-2 sentences per dimension where agreement is "medium" or "low": name the
dimension, the range between tools, and one plausible reason two FAIR tools
might disagree on the same nominal principle, e.g. different tools check
different specific things under the same principle name. If agreement is
"high" or "insufficient_data" throughout, say so plainly.)

## Recommendations
(2-4 concrete, actionable steps prioritised by which would move the
lowest-scoring dimension the most. Avoid generic FAIR advice -- tie each
recommendation to the specific weak dimension found above.)
"""


def build_prompt(consensus: dict, tool_results: dict) -> str:
    return _PROMPT_TEMPLATE.format(
        consensus_json=json.dumps(consensus, indent=2),
        tool_results_json=json.dumps(tool_results, indent=2),
    )


def explain(
    consensus: dict,
    tool_results: dict,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    if genai is None:
        return "## Overall FAIR Compliance\n\n*Explanation unavailable: `google-genai` package is not installed on the server.*"

    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return "## Overall FAIR Compliance\n\n*Explanation unavailable: no Gemini API key configured (set GEMINI_API_KEY).*"

    client = genai.Client(api_key=key)
    prompt = build_prompt(consensus, tool_results)

    try:
        response = client.models.generate_content(model=model, contents=prompt)
        text = (response.text or "").strip()
        if not text:
            return "## Overall FAIR Compliance\n\n*Explanation generation failed: the model returned an empty response.*"
        missing = [h for h in SECTION_HEADERS if h not in text]
        if missing:
            text += f"\n\n*(Note: response may be missing expected section(s): {', '.join(missing)})*"
        return text
    except Exception as e:
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        message_lower = str(e).lower()
        if status == 429 or "quota" in message_lower or "resource_exhausted" in message_lower:
            return (
                "## Overall FAIR Compliance\n\n"
                "*AI explanations are temporarily unavailable: the Gemini account "
                "connected to this server has hit its API quota/billing limit. Check "
                "the account at aistudio.google.com and try again -- this is a "
                "billing/quota issue on the connected account, not a problem with the "
                "FAIR assessment itself.*"
            )
        if status == 401 or status == 403 or "api key not valid" in message_lower or "permission_denied" in message_lower:
            return (
                "## Overall FAIR Compliance\n\n"
                "*AI explanations are unavailable: the server's Gemini API key is "
                "missing or invalid. Check the GEMINI_API_KEY configuration.*"
            )
        return f"## Overall FAIR Compliance\n\n*Explanation generation failed: {e}*"
