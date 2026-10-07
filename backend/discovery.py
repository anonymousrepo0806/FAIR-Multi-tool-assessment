from __future__ import annotations

import os
from typing import Optional

import requests

_TIMEOUT = 20
_UA = "fair-multi-assessor/1.0 (research tool; contact via repository issues)"


def fetch_ols_catalog(page_size: int = 20) -> dict:
    resp = requests.get(
        "https://www.ebi.ac.uk/ols4/api/ontologies",
        params={"size": page_size},
        headers={"User-Agent": _UA},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    ontologies = data.get("_embedded", {}).get("ontologies", [])
    return {
        "source": "OLS",
        "total": data.get("page", {}).get("totalElements"),
        "sample": [
            {
                "id": o.get("ontologyId"),
                "title": o.get("config", {}).get("title"),
                "description": o.get("config", {}).get("description"),
                "homepage": o.get("config", {}).get("homepage"),
                "numberOfTerms": o.get("numberOfTerms"),
            }
            for o in ontologies
        ],
    }


def fetch_obo_foundry_catalog(limit: int = 20) -> dict:
    resp = requests.get(
        "https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/"
        "master/registry/ontologies.jsonld",
        headers={"User-Agent": _UA},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    ontologies = data.get("ontologies", [])
    return {
        "source": "OBO Foundry",
        "total": len(ontologies),
        "sample": [
            {
                "id": o.get("id"),
                "title": o.get("title"),
                "description": o.get("description"),
                "homepage": o.get("homepage"),


                "ontology_purl": o.get("ontology_purl"),
                "domain": o.get("domain"),
                "status": o.get("activity_status"),
            }
            for o in ontologies[:limit]
        ],
    }


def query_wikidata(sparql: str) -> dict:
    resp = requests.get(
        "https://query.wikidata.org/sparql",
        params={"query": sparql, "format": "json"},
        headers={"User-Agent": _UA, "Accept": "application/sparql-results+json"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "source": "Wikidata",
        "vars": data.get("head", {}).get("vars", []),
        "rows": data.get("results", {}).get("bindings", []),
    }


def fetch_wikidata_biomedical_kg_count() -> dict:
    sparql = """
    SELECT (COUNT(?item) AS ?count) WHERE {
      ?item wdt:P31/wdt:P279* wd:Q56111686 .
    }
    """
    return query_wikidata(sparql)


def fetch_ncbi_esearch(db: str, term: str, retmax: int = 20, api_key: Optional[str] = None) -> dict:
    params = {"db": db, "term": term, "retmode": "json", "retmax": retmax}
    key = api_key or os.environ.get("NCBI_API_KEY")
    if key:
        params["api_key"] = key
    resp = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params=params,
        headers={"User-Agent": _UA},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    result = resp.json().get("esearchresult", {})
    return {
        "source": "NCBI",
        "db": db,
        "total": result.get("count"),
        "sample_ids": result.get("idlist", []),
    }


def query_ontobee(sparql: str) -> dict:
    resp = requests.get(
        "http://sparql.hegroup.org/sparql",
        params={"query": sparql, "format": "json"},
        headers={"User-Agent": _UA, "Accept": "application/sparql-results+json"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "source": "Ontobee",
        "vars": data.get("head", {}).get("vars", []),
        "rows": data.get("results", {}).get("bindings", []),
    }


def search_github_repos(query: str, per_page: int = 20, token: Optional[str] = None) -> dict:
    headers = {"User-Agent": _UA, "Accept": "application/vnd.github+json"}
    tok = token or os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    resp = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": query, "per_page": per_page},
        headers=headers,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "source": "GitHub",
        "total": data.get("total_count"),
        "sample": [
            {"full_name": r.get("full_name"), "url": r.get("html_url"), "description": r.get("description")}
            for r in data.get("items", [])
        ],
    }


_LOD_CLOUD_DATA_URL = "https://lod-cloud.net/lod-data.json"


def fetch_lod_cloud_catalog(limit: int = 20) -> dict:
    import urllib.robotparser

    parser = urllib.robotparser.RobotFileParser()
    parser.set_url("https://lod-cloud.net/robots.txt")
    parser.read()

    if not parser.can_fetch(_UA, _LOD_CLOUD_DATA_URL):
        raise PermissionError(
            "lod-cloud.net/robots.txt disallows fetching lod-data.json for "
            f"this user-agent ({_UA!r}). Not working around it."
        )

    resp = requests.get(_LOD_CLOUD_DATA_URL, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    items = list(data.items()) if isinstance(data, dict) else []
    return {
        "source": "LOD Cloud",
        "total": len(items),
        "sample": [
            {
                "id": ds_id,
                "title": (meta or {}).get("title"),
                "description": (meta or {}).get("description"),
                "domain": (meta or {}).get("domain"),
            }
            for ds_id, meta in items[:limit]
        ],
    }


def fetch_checloud_catalog() -> dict:
    raise NotImplementedError(
        "Live per-id CheCLOUD/KGHeartBeat lookup: see this function's "
        "docstring. Use fetch_checloud_live_fairness(id) below instead -- "
        "this stub is kept only so callers expecting fetch_checloud_catalog() "
        "get a clear pointer to the right function."
    )


def fetch_checloud_live_fairness(dataset_id: str) -> dict:
    key_mapping = {
        "f1M": "F1-M Unique and persistent ID",
        "f1D": "F1-D URIs dereferenceability",
        "f2aM": "F2a-M - Metadata availability via standard primary sources",
        "f2bM": "F2b-M Metadata availability for all the attributes covered in the FAIR score computation",
        "f3M": "F3-M Data referrable via a DOI",
        "f4M": "F4-M Metadata registered in a searchable engine",
        "f_score": "F score",
        "a1D": "A1-D Working access point(s)",
        "a1M": "A1-M Metadata availability via working primary sources",
        "a1_2": "A1.2 Authentication & HTTPS support",
        "a2M": "A2-M Registered in search engines",
        "a_score": "A score",
        "r1_1": "R1.1 Machine- or human-readable license retrievable via any primary source",
        "r1_2": "R1.2 Publisher information, such as authors, contributors, publishers, and sources",
        "r1_3D": "R1.3-D Data organized in a standardized way",
        "r1_3M": "R1.3-M Metadata are described with VoID/DCAT predicates",
        "r_score": "R score",
        "i1D": "I1-D Standard & open representation format",
        "i1M": "I1-M Metadata are described with VoID/DCAT predicates",
        "i2": "I2 Use of FAIR vocabularies",
        "i3D": "I3-D Degree of connection",
        "i_score": "I score",
        "fair_score": "FAIR score",
        "analysis_date": "analysis_date",
    }
    base = os.environ.get("KGHEARTBEAT_FAIRNESS_URL", "").rstrip("/")
    if not base:
        raise NotImplementedError(
            "Set KGHEARTBEAT_FAIRNESS_URL to KGHeartBeat's public fairness API base URL "
            "(the endpoint ending in /kgheartbeat-api/fairness) to enable live lookups."
        )
    resp = requests.get(
        f"{base}/{dataset_id}",
        headers={"User-Agent": _UA},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    raw = resp.json()
    return {"source": "CheCLOUD/KGHeartBeat (live)", "id": dataset_id,
            "data": {key_mapping.get(k, k): v for k, v in raw.items()}}


def fetch_bioportal_catalog(api_key: Optional[str] = None) -> dict:
    key = api_key or os.environ.get("BIOPORTAL_API_KEY")
    if not key:
        raise NotImplementedError(
            "BioPortal requires an API key (free at bioontology.org/account). "
            "Set BIOPORTAL_API_KEY or pass api_key= to use this function."
        )
    resp = requests.get(
        "https://data.bioontology.org/ontologies",
        headers={"Authorization": f"apikey token={key}", "User-Agent": _UA},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "source": "BioPortal",
        "total": len(data),
        "sample": [{"acronym": o.get("acronym"), "name": o.get("name")} for o in data[:20]],
    }


def fetch_kaggle_catalog(username: Optional[str] = None, key: Optional[str] = None) -> dict:
    u = username or os.environ.get("KAGGLE_USERNAME")
    k = key or os.environ.get("KAGGLE_KEY")
    if not (u and k):
        raise NotImplementedError(
            "Kaggle requires account credentials (KAGGLE_USERNAME + KAGGLE_KEY, "
            "from kaggle.com/settings/account, or the kaggle Python package's "
            "own credential file)."
        )
    raise NotImplementedError(
        "Credentials given, but the Kaggle API call itself was not "
        "implemented/tested this session -- wire in the `kaggle` package's "
        "datasets_list() here."
    )


def fetch_ols_catalog_all(page_size: int = 200, max_pages: int = 20) -> list[dict]:
    """Paginate through the full OLS ontology catalog (fetch_ols_catalog()
    above only returns one page, sized for a quick preview). No API key --
    OLS4 is a fully open EBI service. max_pages is a safety cap (OLS has
    on the order of a few hundred ontologies, well under page_size*max_pages
    at the defaults)."""
    out = []
    for page in range(max_pages):
        resp = requests.get(
            "https://www.ebi.ac.uk/ols4/api/ontologies",
            params={"size": page_size, "page": page},
            headers={"User-Agent": _UA},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        ontologies = data.get("_embedded", {}).get("ontologies", [])
        if not ontologies:
            break
        for o in ontologies:
            cfg = o.get("config", {}) or {}
            out.append({
                "id": o.get("ontologyId"),
                "title": cfg.get("title"),
                "description": cfg.get("description"),
                "homepage": cfg.get("homepage"),
                "file_location": cfg.get("fileLocation"),
            })
        total_pages = data.get("page", {}).get("totalPages")
        if total_pages is not None and page + 1 >= total_pages:
            break
    return out


def fetch_lod_cloud_full() -> dict:
    """Like fetch_lod_cloud_catalog() but returns every entry's full raw
    metadata dict rather than a size-limited, field-trimmed preview --
    lod-data.json is one flat JSON file (not paginated), so "full" costs no
    extra requests over the preview version. Still honors robots.txt."""
    import urllib.robotparser

    parser = urllib.robotparser.RobotFileParser()
    parser.set_url("https://lod-cloud.net/robots.txt")
    parser.read()

    if not parser.can_fetch(_UA, _LOD_CLOUD_DATA_URL):
        raise PermissionError(
            "lod-cloud.net/robots.txt disallows fetching lod-data.json for "
            f"this user-agent ({_UA!r}). Not working around it."
        )

    resp = requests.get(_LOD_CLOUD_DATA_URL, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    items = data if isinstance(data, dict) else {}
    return {"source": "LOD Cloud", "total": len(items), "items": items}


def search_github_repos_all(query: str, max_pages: int = 3, per_page: int = 100,
                             token: Optional[str] = None) -> list[dict]:
    """Paginate GitHub code search up to `max_pages` (default 300 repos).
    No token required -- unauthenticated search works, just rate-limited to
    10 req/min, which is why this is capped rather than exhausting GitHub's
    own 1000-result search ceiling every run."""
    headers = {"User-Agent": _UA, "Accept": "application/vnd.github+json"}
    tok = token or os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"

    out = []
    for page in range(1, max_pages + 1):
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "per_page": per_page, "page": page},
            headers=headers,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            break
        for r in items:
            out.append({
                "full_name": r.get("full_name"),
                "html_url": r.get("html_url"),
                "homepage": r.get("homepage"),
                "description": r.get("description"),
            })
        if len(items) < per_page:
            break
    return out


def query_ontobee_ontology_list() -> list[dict]:
    """Best-effort discovery of Ontobee's ontology list via its SPARQL
    endpoint. Ontobee has no documented flat "list all ontologies" REST
    endpoint, so this queries for distinct named graphs, which is how
    Ontobee organizes one ontology per graph -- confirmed against Ontobee's
    own SPARQL documentation, not against a live response (see this
    project's snapshots.list_sources(): this endpoint returned HTTP 403
    from this development sandbox specifically; unconfirmed from a real
    deployment with normal internet access)."""
    sparql = "SELECT DISTINCT ?graph WHERE { GRAPH ?graph { ?s ?p ?o } } LIMIT 1000"
    data = query_ontobee(sparql)
    out = []
    for row in data.get("rows", []):
        graph_uri = row.get("graph", {}).get("value")
        if graph_uri:
            out.append({"id": graph_uri.rstrip("/").rsplit("/", 1)[-1], "url": graph_uri})
    return out


def fetch_bio2rdf_catalog() -> dict:
    raise NotImplementedError(
        "Bio2RDF's per-dataset URL convention is already used elsewhere in "
        "this codebase (fairchecker_client.py), but a catalog LISTING "
        "endpoint was not confirmed this session."
    )
