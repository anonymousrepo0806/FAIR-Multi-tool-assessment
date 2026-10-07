

const ALWAYS_BLOCKED_DOMAINS = new Set([
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
  "mdpi.com", "www.mdpi.com",
]);

const HOMEPAGE_ONLY_DOMAINS = new Set([
  "wikidata.org", "www.wikidata.org",
  "wikipedia.org", "www.wikipedia.org", "en.wikipedia.org",
  "github.com", "www.github.com",
  "dbpedia.org", "www.dbpedia.org",
  "data.gov",
  "europa.eu", "data.europa.eu",
]);


export function invalidDatasetUrlReason(value) {
  let u;
  try {
    u = new URL(value);
  } catch {
    return "Please enter a valid http(s) URL.";
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") {
    return "Please enter a valid http(s) URL.";
  }
  const domain = u.hostname.toLowerCase();
  const path = (u.pathname || "/").replace(/\/+$/, "") || "/";

  if (ALWAYS_BLOCKED_DOMAINS.has(domain)) {
    return `'${domain}' is a generic web service or paper/publication repository, not a dataset host — please link directly to a dataset, ontology, SPARQL endpoint, or knowledge-graph resource.`;
  }
  if (HOMEPAGE_ONLY_DOMAINS.has(domain) && path === "/") {
    return `That looks like the homepage of ${domain}, not a specific dataset — link directly to the dataset/entity/resource page instead.`;
  }
  return null;
}
