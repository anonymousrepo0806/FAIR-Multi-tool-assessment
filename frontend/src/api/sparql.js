
import client from "./client";

export async function fetchSparqlSchema() {
  const { data } = await client.get("/sparql/schema");
  return data;
}

export async function runSparqlQuery(query) {
  const { data } = await client.post("/sparql", { query });
  return data;
}

export function sparqlCsvUrl(query) {
  const base = client.defaults.baseURL || "";
  return `${base}/sparql/csv?query=${encodeURIComponent(query)}`;
}
