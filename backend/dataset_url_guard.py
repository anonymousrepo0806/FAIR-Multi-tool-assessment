
from __future__ import annotations

from urllib.parse import urlparse
from typing import Optional

from ai import gemini_url_classifier


ALWAYS_BLOCKED_DOMAINS = {
    "google.com", "www.google.com",
    "bing.com", "www.bing.com",
    "yahoo.com", "www.yahoo.com",
    "duckduckgo.com",
    "facebook.com", "www.facebook.com",
    "instagram.com", "www.instagram.com",
    "twitter.com", "x.com",
    "linkedin.com", "www.linkedin.com",
    "tiktok.com", "www.tiktok.com",
    "youtube.com", "www.youtube.com", "youtu.be",
    "reddit.com", "www.reddit.com",
    "amazon.com", "www.amazon.com",
    "netflix.com",
    "example.com", "example.org", "example.net",

    "arxiv.org", "www.arxiv.org",
    "biorxiv.org", "www.biorxiv.org",
    "medrxiv.org", "www.medrxiv.org",
    "researchgate.net", "www.researchgate.net",
    "semanticscholar.org", "www.semanticscholar.org",
    "scholar.google.com",
    "dl.acm.org",
    "ieeexplore.ieee.org",
    "sciencedirect.com", "www.sciencedirect.com",
    "link.springer.com",
    "pubmed.ncbi.nlm.nih.gov",
    "mdpi.com", "www.mdpi.com", "https://www.hackerrank.com/",
    "https://docs.google.com/",
}


HOMEPAGE_ONLY_DOMAINS = {
    "wikidata.org", "www.wikidata.org",
    "wikipedia.org", "www.wikipedia.org", "en.wikipedia.org",
    "github.com", "www.github.com",
    "dbpedia.org", "www.dbpedia.org",
    "data.gov",
    "europa.eu", "data.europa.eu",
}


GENERIC_PATHS = {"", "/", "/about", "/about-us", "/contact", "/help",
                 "/documentation", "/docs", "/home", "/index", "/index.html"}


class InvalidDatasetUrlError(ValueError):
    """Raised when a submitted URL is not an acceptable dataset URL."""


def _netloc_without_port(netloc: str) -> str:
    return netloc.split(":")[0].lower()


def check_dataset_url(url: str) -> None:
    """Raise InvalidDatasetUrlError if `url` is not an acceptable dataset URL.

    Call this before invoking any FAIR assessment tool. It never mutates or
    normalises the URL -- it only validates.
    """
    if not url or not url.strip():
        raise InvalidDatasetUrlError("A dataset URL is required.")

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise InvalidDatasetUrlError(f"Could not parse URL: {e}") from None

    if parsed.scheme not in ("http", "https"):
        raise InvalidDatasetUrlError(
            "Only http:// or https:// URLs are accepted for assessment."
        )

    if not parsed.netloc:
        raise InvalidDatasetUrlError("The URL must include a domain.")

    domain = _netloc_without_port(parsed.netloc)
    path = (parsed.path or "").rstrip("/").lower() or "/"

    if domain in ALWAYS_BLOCKED_DOMAINS:
        raise InvalidDatasetUrlError(
            f"'{domain}' is a generic web service or paper/publication "
            "repository, not a dataset host -- please submit the URL of a "
            "specific dataset, ontology, SPARQL endpoint, or knowledge-graph "
            "resource instead."
        )

    if domain in HOMEPAGE_ONLY_DOMAINS and path in ("", "/"):
        raise InvalidDatasetUrlError(
            f"'{url}' looks like the homepage of {domain}, not a specific "
            "dataset. Link directly to the dataset/entity/resource page "
            f"(e.g. a specific item, repo, or ontology on {domain}), not the "
            "site's root."
        )

    if path in GENERIC_PATHS and domain not in HOMEPAGE_ONLY_DOMAINS:


        if path not in ("", "/"):
            raise InvalidDatasetUrlError(
                f"'{url}' looks like an informational page ('{parsed.path}'), "
                "not a dataset resource. Please submit a link to the dataset "
                "itself."
            )


def check_dataset_url_with_ai(
    url: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[dict]:
    """Run the fast static check_dataset_url() first, then -- only if that
    passes and a Gemini API key is configured -- ask an LLM for a second
    opinion on whether the URL really looks like a dataset resource.

    This catches cases the static blocklist can't anticipate (an unknown
    blog, a company marketing page, a software project's README, etc. that
    isn't on any blocklist but obviously isn't a dataset either), without
    having to hand-enumerate every non-dataset site on the internet.

    Returns the AI classifier's result dict (see gemini_url_classifier) for
    visibility/logging, or None if the AI layer was skipped (no API key
    configured, or the package isn't installed) -- in which case the static
    check above is the only gate, same graceful-degradation pattern as this
    app's other optional Gemini integrations. Raises InvalidDatasetUrlError
    if either the static check fails, or the AI check comes back with a
    confident "not a dataset" verdict. A model error/timeout/quota hit
    (is_dataset=None) fails open -- it never blocks a request just because
    the AI layer was unreachable.
    """
    check_dataset_url(url)

    result = gemini_url_classifier.classify_dataset_url(
        url, api_key=api_key, **({"model": model} if model else {})
    )

    if result["is_dataset"] is False:
        reason = result.get("reasoning") or "it doesn't look like a dataset resource"
        raise InvalidDatasetUrlError(
            f"'{url}' was flagged as not a dataset URL ({reason}). If this is "
            "a genuine dataset, ontology, or knowledge-graph resource, please "
            "double-check the link or use a more specific URL."
        )

    return result
