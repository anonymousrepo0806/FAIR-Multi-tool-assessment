from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from rdflib import Graph, URIRef
from rdflib.util import guess_format

DEFAULT_TIMEOUT = 12
USER_AGENT = "FAIR-Multi-Assessor/1.0 (+realtime FAIR probe)"

RDF_ACCEPT_TYPES = [
    ("text/turtle", "turtle"),
    ("application/rdf+xml", "xml"),
    ("application/ld+json", "json-ld"),
    ("application/n-triples", "nt"),
    ("text/n3", "n3"),
]

KNOWN_VOCAB_NAMESPACES = {
    "http://xmlns.com/foaf/0.1/": "FOAF",
    "http://purl.org/dc/terms/": "Dublin Core Terms",
    "http://purl.org/dc/elements/1.1/": "Dublin Core",
    "http://www.w3.org/2004/02/skos/core#": "SKOS",
    "http://www.w3.org/ns/dcat#": "DCAT",
    "http://rdfs.org/ns/void#": "VoID",
    "http://schema.org/": "schema.org",
    "https://schema.org/": "schema.org",
    "http://www.w3.org/2002/07/owl#": "OWL",
    "http://www.w3.org/2000/01/rdf-schema#": "RDFS",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "RDF",
    "http://www.w3.org/2006/vcard/ns#": "vCard",
    "http://purl.org/vocab/vann/": "VANN",
    "http://creativecommons.org/ns#": "Creative Commons",
}

LICENSE_PREDICATES = [
    "http://purl.org/dc/terms/license",
    "http://purl.org/dc/elements/1.1/rights",
    "http://www.w3.org/ns/dcat#license",
    "http://creativecommons.org/ns#license",
    "http://schema.org/license",
    "https://schema.org/license",
]

PUBLISHER_PREDICATES = [
    "http://purl.org/dc/terms/publisher",
    "http://purl.org/dc/elements/1.1/publisher",
    "http://schema.org/publisher",
    "https://schema.org/publisher",
]

SAMEAS_PREDICATES = ["http://www.w3.org/2002/07/owl#sameAs"]
SKOS_PREDICATES = [
    "http://www.w3.org/2004/02/skos/core#exactMatch",
    "http://www.w3.org/2004/02/skos/core#closeMatch",
    "http://www.w3.org/2004/02/skos/core#mappingRelation",
]

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


@dataclass
class _Extra:
    KGid: str = ""
    endpointUrl: str = ""
    urlVoid: str = ""
    voidAvailability: str = "-"
    metadataMediaType: list = field(default_factory=list)
    commonMediaType: bool = False


@dataclass
class _Availability:
    uriDef: float = 0.0
    RDFDumpM: int = 0
    sparqlEndpoint: str = "-"


@dataclass
class _Licensing:
    licenseMetadata = False
    licenseQuery: str = "-"
    licenseHR = False


@dataclass
class _Verifiability:
    vocabularies: list = field(default_factory=list)


@dataclass
class _Interlinking:
    degreeConnection: int = 0
    sameAs: int = 0
    skosMapping: int = 0


@dataclass
class _Security:
    useHTTPS: bool = False
    requiresAuth: bool = False


@dataclass
class LiveKGQuality:
    extra: _Extra = field(default_factory=_Extra)
    availability: _Availability = field(default_factory=_Availability)
    licensing: _Licensing = field(default_factory=_Licensing)
    verifiability: _Verifiability = field(default_factory=_Verifiability)
    interlinking: _Interlinking = field(default_factory=_Interlinking)
    security: _Security = field(default_factory=_Security)
    probe_notes: list = field(default_factory=list)


class LiveKGProbe:

    def __init__(self, url: str, timeout: int = DEFAULT_TIMEOUT):
        self.url = url.strip()
        self.timeout = timeout
        self.session = _session()
        self.notes: list = []


    def collect(self) -> LiveKGQuality:
        q = LiveKGQuality()
        q.extra.KGid = self.url
        q.security.useHTTPS = urlparse(self.url).scheme == "https"

        base_resp, base_graph, negotiated = self._negotiate_and_fetch(self.url)
        q.availability.uriDef = 1.0 if base_resp is not None and base_resp.status_code == 200 else 0.0
        q.extra.metadataMediaType = negotiated
        q.extra.commonMediaType = any(
            ct in {"text/turtle", "application/rdf+xml", "application/ld+json",
                   "application/n-triples", "text/n3"}
            for ct in negotiated
        )
        if base_resp is not None and base_resp.status_code in (401, 403):
            q.security.requiresAuth = True

        endpoint = self._find_sparql_endpoint()
        if endpoint:
            q.extra.endpointUrl = endpoint
            q.availability.sparqlEndpoint = "Available"

        void_url, void_found_in_graph = self._find_void()
        if void_url:
            q.extra.urlVoid = void_url
            q.extra.voidAvailability = "VoID file available"
        elif void_found_in_graph:
            q.extra.voidAvailability = "VoID file available"

        q.availability.RDFDumpM = 1 if self._find_dump_link(base_resp) else 0

        graph = base_graph
        if graph is None and void_url:
            _, graph, _ = self._negotiate_and_fetch(void_url)

        if graph is not None and len(graph) > 0:
            self._extract_license(graph, q)
            self._extract_publisher(graph, q)
            self._extract_vocabularies(graph, q)
            self._extract_interlinking(graph, q)
        else:
            self._extract_license_html_fallback(base_resp, q)

        q.probe_notes.extend(self.notes)
        return q


    def _get(self, url: str, accept: Optional[str] = None):
        headers = {"Accept": accept} if accept else {}
        try:
            return self.session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
        except requests.exceptions.RequestException as e:
            self.notes.append(f"GET {url} failed: {e}")
            return None

    def _negotiate_and_fetch(self, url: str):
        negotiated = []
        graph = None
        best_resp = None
        for mime, fmt in RDF_ACCEPT_TYPES:
            resp = self._get(url, accept=mime)
            if resp is None:
                continue
            if resp.status_code == 200:
                served_ct = resp.headers.get("Content-Type", "").split(";")[0].strip()
                negotiated.append(served_ct or mime)
                if graph is None:
                    g = Graph()
                    try:
                        parse_fmt = fmt if (served_ct in ("", mime) or mime in served_ct) else (
                            guess_format(url) or fmt
                        )
                        g.parse(data=resp.text, format=parse_fmt)
                        graph = g
                    except Exception as e:
                        self.notes.append(f"could not parse response from {url} as {fmt}: {e}")
            if best_resp is None:
                best_resp = resp
            time.sleep(0)

        if graph is None:
            plain = self._get(url)
            if plain is not None:
                if best_resp is None:
                    best_resp = plain
                ct = plain.headers.get("Content-Type", "")
                if plain.status_code == 200 and ("rdf" in ct or "turtle" in ct or "n-triples" in ct):
                    g = Graph()
                    try:
                        g.parse(data=plain.text, format=guess_format(url) or "turtle")
                        graph = g
                        negotiated.append(ct.split(";")[0].strip())
                    except Exception as e:
                        self.notes.append(f"plain GET parse failed: {e}")
        return best_resp, graph, negotiated


    def _looks_like_sparql_endpoint(self, url: str) -> bool:
        return bool(re.search(r"sparql", url, re.IGNORECASE))

    def _sparql_ask(self, endpoint: str) -> bool:
        try:
            resp = self.session.get(
                endpoint,
                params={"query": "ASK { ?s ?p ?o }"},
                headers={"Accept": "application/sparql-results+json, application/json"},
                timeout=self.timeout,
            )
            return resp.status_code == 200
        except requests.exceptions.RequestException as e:
            self.notes.append(f"SPARQL ASK against {endpoint} failed: {e}")
            return False

    def _find_sparql_endpoint(self) -> Optional[str]:
        candidates = []
        if self._looks_like_sparql_endpoint(self.url):
            candidates.append(self.url)
        parsed = urlparse(self.url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        for path in ("/sparql", "/sparql-endpoint", "/query", "/sparql/query"):
            candidates.append(urljoin(base, path))
        for c in candidates:
            if self._sparql_ask(c):
                return c
        return None


    def _find_void(self):
        parsed = urlparse(self.url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        candidates = [
            urljoin(self.url if self.url.endswith("/") else self.url + "/", "void.ttl"),
            urljoin(base, "/.well-known/void"),
            urljoin(base, "/void.ttl"),
            urljoin(base, "/void"),
        ]
        for c in candidates:
            resp = self._get(c, accept="text/turtle, application/rdf+xml")
            if resp is not None and resp.status_code == 200:
                ct = resp.headers.get("Content-Type", "")
                if "html" not in ct:
                    return c, True
        return None, False

    def _find_dump_link(self, base_resp) -> bool:
        if base_resp is None or base_resp.text is None:
            return False
        return bool(re.search(r'href=["\'][^"\']+\.(nt|ttl|rdf|n3|nq)(\.gz|\.bz2)?["\']',
                               base_resp.text, re.IGNORECASE))


    def _extract_license(self, graph: Graph, q: LiveKGQuality) -> None:
        for pred in LICENSE_PREDICATES:
            for _, _, o in graph.triples((None, URIRef(pred), None)):
                q.licensing.licenseMetadata = True
                q.licensing.licenseQuery = str(o)
                return

    def _extract_license_html_fallback(self, resp, q: LiveKGQuality) -> None:
        if resp is None or not resp.text:
            return
        m = re.search(r'<link[^>]+rel=["\']license["\'][^>]+href=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
        if m:
            q.licensing.licenseHR = True
            q.licensing.licenseQuery = m.group(1)

    def _extract_publisher(self, graph: Graph, q: LiveKGQuality) -> None:
        for pred in PUBLISHER_PREDICATES:
            if next(graph.triples((None, URIRef(pred), None)), None) is not None:
                self.notes.append("publisher metadata found via RDF triple")
                q.probe_notes.append("has_publisher_info=1")
                return
        q.probe_notes.append("has_publisher_info=0")

    def _extract_vocabularies(self, graph: Graph, q: LiveKGQuality) -> None:
        used = set()
        for prefix, ns in graph.namespaces():
            ns = str(ns)
            for known_ns, label in KNOWN_VOCAB_NAMESPACES.items():
                if ns.startswith(known_ns) or known_ns.startswith(ns):
                    used.add(label)
        q.verifiability.vocabularies = sorted(used)

    def _extract_interlinking(self, graph: Graph, q: LiveKGQuality) -> None:
        same_as = sum(1 for _ in graph.triples((None, URIRef(SAMEAS_PREDICATES[0]), None)))
        skos = sum(
            1
            for pred in SKOS_PREDICATES
            for _ in graph.triples((None, URIRef(pred), None))
        )
        q.interlinking.sameAs = same_as
        q.interlinking.skosMapping = skos
        q.interlinking.degreeConnection = same_as + skos


def check_publisher_info_live(q: LiveKGQuality) -> int:
    return 1 if "has_publisher_info=1" in q.probe_notes else 0


def check_at_least_sparql_on_live(endpoint_url: str, probe: LiveKGProbe) -> int:
    if not endpoint_url:
        return 0
    return 1 if probe._sparql_ask(endpoint_url) else 0


def find_search_engine_from_keywords_live(_url: str) -> int:
    return 0


def check_if_fair_vocabs_live(vocab_list) -> float:
    return 1.0 if vocab_list else 0.0


def check_void_dcat_live(endpoint_url: str, probe: LiveKGProbe) -> bool:
    if not endpoint_url:
        return False
    ask = ("ASK { { ?s a <http://rdfs.org/ns/void#Dataset> } "
           "UNION { ?s a <http://www.w3.org/ns/dcat#Dataset> } }")
    try:
        resp = probe.session.get(
            endpoint_url,
            params={"query": ask},
            headers={"Accept": "application/sparql-results+json, application/json"},
            timeout=probe.timeout,
        )
        return resp.status_code == 200 and '"boolean": true' in resp.text.replace(" ", "")
    except requests.exceptions.RequestException:
        return False


def find_doi_live(url: str, resp, session: requests.Session, timeout: int) -> Optional[str]:
    doi = None
    if resp is not None and resp.text:
        m = re.search(
            r'(?:citation_doi|DC\.identifier|dc\.identifier)["\']?\s*(?:content|=)\s*["\']?\s*'
            r'(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)',
            resp.text, re.IGNORECASE,
        )
        if not m:
            m = DOI_RE.search(resp.text)
        if m:
            doi = m.group(1) if m.lastindex else m.group(0)
            doi = doi.rstrip(').,;"\'<')
    if not doi:
        return None
    try:
        check = session.head(f"https://doi.org/{doi}", timeout=timeout, allow_redirects=True)
        if check.status_code >= 400:
            check = session.get(f"https://doi.org/{doi}", timeout=timeout, allow_redirects=True)
        if check.status_code < 400:
            return doi
    except requests.exceptions.RequestException:
        pass
    return None


def check_findable_live(url: str, doi: Optional[str]) -> bool:
    return bool(doi)


class FAIRness:

    def __init__(self):
        self.f1M = self.f1D = self.f2aM = self.f2bM = self.f3M = self.f4M = 0
        self.f_score = 0
        self.a1D = self.a1M = self.a1_2 = self.a2M = 0
        self.a_score = 0
        self.r1_1 = self.r1_2 = self.r1_3D = self.r1_3M = 0
        self.r_score = 0
        self.i1D = self.i1M = self.i2 = self.i3D = 0
        self.i_score = 0
        self.fair_score = 0

    def as_dict(self):
        return {
            "findability": {
                "F1-M": self.f1M, "F1-D": self.f1D, "F2a-M": self.f2aM,
                "F2b-M": self.f2bM, "F3-M": self.f3M, "F4-M": self.f4M,
                "score": self.f_score,
            },
            "accessibility": {
                "A1-D": self.a1D, "A1-M": self.a1M, "A1.2": self.a1_2,
                "A2-M": self.a2M, "score": self.a_score,
            },
            "reusability": {
                "R1.1": self.r1_1, "R1.2": self.r1_2, "R1.3-D": self.r1_3D,
                "R1.3-M": self.r1_3M, "score": self.r_score,
            },
            "interoperability": {
                "I1-D": self.i1D, "I1-M": self.i1M, "I2": self.i2, "I3-D": self.i3D,
                "score": self.i_score,
            },
            "fair_score": self.fair_score,
        }

    def as_flat_kgheartbeat_columns(self) -> dict:
        return {
            "F1-M": self.f1M, "F1-D": self.f1D,
            "F2a-M": self.f2aM, "F2b-M": self.f2bM,
            "F3-M": self.f3M,
            "A1.1-D": self.a1D, "A1.1-M": self.a1M, "A1.2": self.a1_2,
            "I1-D": self.i1D, "I1-M": self.i1M, "I2": self.i2, "I3-D": self.i3D,
            "R1.1": self.r1_1, "R1.2": self.r1_2,
            "R1.3-D": self.r1_3D, "R1.3-M": self.r1_3M,
            "F": self.f_score, "A": self.a_score,
            "I": self.i_score, "R": self.r_score,
            "FAIR": self.fair_score,
        }


class RealtimeEvaluateFAIRness:

    def __init__(self, url: str, timeout: int = DEFAULT_TIMEOUT):
        self.url = url
        self.probe = LiveKGProbe(url, timeout=timeout)
        self.kg_quality = self.probe.collect()
        self.fairness = FAIRness()

        base_resp, _, _ = self.probe._negotiate_and_fetch(url)
        self.doi = find_doi_live(url, base_resp, self.probe.session, timeout)
        self.available_on_search_engine = check_findable_live(url, self.doi)


    def evaluate_findability(self):
        available_on_search_engine = self.available_on_search_engine
        doi_indication = 1 if self.doi else 0
        self.fairness.f1M = 1 if available_on_search_engine or doi_indication else 0
        try:
            uriDef = float(self.kg_quality.availability.uriDef)
            self.fairness.f1D = uriDef
        except ValueError:
            self.fairness.f1D = 0
        sparql_indication = 1 if self.kg_quality.extra.endpointUrl != '' else 0
        void_indication = 1 if self.kg_quality.extra.urlVoid != '' else 0
        self.fairness.f2aM = 1 if sparql_indication or void_indication else 0
        dump_indication = 1 if self.kg_quality.availability.RDFDumpM in [1, "1"] else 0
        verifiability_info = check_publisher_info_live(self.kg_quality)
        mediatype_indication = 1 if len(self.kg_quality.extra.metadataMediaType) > 0 else 0
        license = 1 if (
            self.kg_quality.licensing.licenseMetadata not in [False, 'False', '', '-', '[]']
        ) or (
            self.kg_quality.licensing.licenseQuery != '-' and len(self.kg_quality.licensing.licenseQuery) > 0
        ) else 0
        vocabs = 1 if self.kg_quality.verifiability.vocabularies not in ['-', '', '[]'] and len(
            self.kg_quality.verifiability.vocabularies) > 0 else 0
        if available_on_search_engine:
            links = 1 if (
                self.kg_quality.interlinking.degreeConnection != '-'
                and isinstance(self.kg_quality.interlinking.degreeConnection, int)
                and int(self.kg_quality.interlinking.degreeConnection) > 0
            ) else 0
        else:
            links = 1 if (
                (self.kg_quality.interlinking.sameAs not in ['-', '0', ''] and int(self.kg_quality.interlinking.sameAs) > 0) or
                (self.kg_quality.interlinking.skosMapping not in ['-', '0', ''] and int(self.kg_quality.interlinking.skosMapping) > 0)
            ) else 0
        self.fairness.f2bM = round(
            (sparql_indication + doi_indication + dump_indication + verifiability_info +
             mediatype_indication + license + vocabs + links + void_indication) / 9, 2)
        self.fairness.f3M = doi_indication
        self.fairness.f4M = 1 if available_on_search_engine else find_search_engine_from_keywords_live(self.kg_quality.extra.KGid)
        self.fairness.f_score = round(
            (self.fairness.f1M + self.fairness.f1D + self.fairness.f2aM +
             self.fairness.f2bM + self.fairness.f3M + self.fairness.f4M) / 6, 2)

    def evaluate_availability(self):
        sparql_availability = 1 if self.kg_quality.availability.sparqlEndpoint == 'Available' else 0
        dump_availability = 1 if self.kg_quality.availability.RDFDumpM in [1, "1"] else 0
        sparql_or_dump = 1 if sparql_availability == 1 or dump_availability == 1 else 0
        sparql_on_not_interop = check_at_least_sparql_on_live(self.kg_quality.extra.endpointUrl, self.probe)
        self.fairness.a1D = 1 if sparql_or_dump == 1 else 0.5 if sparql_or_dump == 0 and sparql_on_not_interop == 1 else 0
        available_on_search_engine = self.available_on_search_engine
        if available_on_search_engine:
            self.fairness.a1M = 1
        else:
            void_availability = 1 if self.kg_quality.extra.voidAvailability == 'VoID file available' else 0
            self.fairness.a1M = 1 if sparql_availability == 1 or void_availability == 1 else 0
        uses_https = 1 if self.kg_quality.security.useHTTPS in [True, 'True'] or self.kg_quality.availability.sparqlEndpoint == 'Available' else 0
        no_auth_required = 1 if self.kg_quality.security.requiresAuth in ["False", False, 'True', True] else 0
        self.fairness.a1_2 = round((uses_https + no_auth_required) / 2, 2)
        self.fairness.a2M = 1 if available_on_search_engine else find_search_engine_from_keywords_live(self.kg_quality.extra.KGid)
        self.fairness.a_score = round((self.fairness.a1D + self.fairness.a1M + self.fairness.a1_2 + self.fairness.a2M) / 4, 2)

    def evaluate_reusability(self):
        has_license_metadata = 1 if self.kg_quality.licensing.licenseMetadata not in [False, 'False', '', '-', '[]'] else 0
        has_license_query = 1 if self.kg_quality.licensing.licenseQuery != '-' and len(self.kg_quality.licensing.licenseQuery) > 0 else 0
        has_license_hr = 1 if self.kg_quality.licensing.licenseHR not in [False, 'False'] else 0
        self.fairness.r1_1 = 1 if has_license_metadata or has_license_query or has_license_hr else 0
        self.fairness.r1_2 = check_publisher_info_live(self.kg_quality)
        common_media_type = self.kg_quality.extra.commonMediaType in ['True', True]
        known_semantic_format = any(fmt in self.kg_quality.extra.metadataMediaType for fmt in ['api/sparql', 'rdf', 'RDF'])
        self.fairness.r1_3D = 1 if common_media_type or known_semantic_format else 0
        has_void = self.kg_quality.extra.urlVoid != ''
        has_void_from_endpoint = check_void_dcat_live(self.kg_quality.extra.endpointUrl, self.probe)
        lic_in_meta = 1 if self.kg_quality.licensing.licenseQuery != '-' and len(self.kg_quality.licensing.licenseQuery) > 0 else 0
        self.fairness.r1_3M = 1 if has_void or has_void_from_endpoint or lic_in_meta else 0
        self.fairness.r_score = round((self.fairness.r1_1 + self.fairness.r1_2 + self.fairness.r1_3D + self.fairness.r1_3M) / 4, 2)

    def evaluate_interoperability(self):
        available_on_search_engine = self.available_on_search_engine
        common_media_type = 1 if self.kg_quality.extra.commonMediaType in ['True', True] else 0
        known_semantic_format = any(fmt in self.kg_quality.extra.metadataMediaType for fmt in ['api/sparql', 'rdf', 'RDF'])
        self.fairness.i1D = 1 if common_media_type or known_semantic_format else 0
        has_void = self.kg_quality.extra.urlVoid != ''
        has_void_from_endpoint = check_void_dcat_live(self.kg_quality.extra.endpointUrl, self.probe)
        self.fairness.i1M = 1 if has_void or has_void_from_endpoint else 0
        has_vocab = self.kg_quality.verifiability.vocabularies not in ['-', '', '[]'] and len(self.kg_quality.verifiability.vocabularies) > 0
        self.fairness.i2 = check_if_fair_vocabs_live(self.kg_quality.verifiability.vocabularies) if has_vocab else 0
        if available_on_search_engine:
            try:
                self.fairness.i3D = 1 if self.kg_quality.interlinking.degreeConnection not in ['-', '', '0'] and int(self.kg_quality.interlinking.degreeConnection) > 0 else 0
            except TypeError:
                self.fairness.i3D = 0
        else:
            sameAs_valid = self.kg_quality.interlinking.sameAs not in ['-', '0', ''] and int(self.kg_quality.interlinking.sameAs) > 0
            skos_valid = self.kg_quality.interlinking.skosMapping not in ['-', '0', ''] and int(self.kg_quality.interlinking.skosMapping) > 0
            self.fairness.i3D = 1 if sameAs_valid or skos_valid else 0
        self.fairness.i_score = round((self.fairness.i1D + self.fairness.i1M + self.fairness.i2 + self.fairness.i3D) / 4, 2)

    def calculate_FAIR_score(self):
        self.fairness.fair_score = round(
            float(self.fairness.f_score) +
            float(self.fairness.a_score) +
            float(self.fairness.i_score) +
            float(self.fairness.r_score),
            2,
        )

    def run(self) -> dict:
        self.evaluate_findability()
        self.evaluate_availability()
        self.evaluate_reusability()
        self.evaluate_interoperability()
        self.calculate_FAIR_score()
        result = self.fairness.as_dict()
        result["url"] = self.url
        result["doi_found"] = self.doi
        result["notes"] = self.kg_quality.probe_notes
        return result

    def run_flat(self) -> dict:
        self.evaluate_findability()
        self.evaluate_availability()
        self.evaluate_reusability()
        self.evaluate_interoperability()
        self.calculate_FAIR_score()
        flat = self.fairness.as_flat_kgheartbeat_columns()
        flat["doi_found"] = self.doi
        flat["notes"] = self.kg_quality.probe_notes
        return flat


if __name__ == "__main__":
    import sys
    import json

    target = sys.argv[1] if len(sys.argv) > 1 else "https://dbpedia.org/sparql"
    evaluator = RealtimeEvaluateFAIRness(target)
    print(json.dumps(evaluator.run(), indent=2, default=str))
