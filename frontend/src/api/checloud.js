/**
 * api/checloud.js
 * ==================
 * Client for the CheCLOUD endpoints (/checloud/*). CheCLOUD is a separate
 * corpus from BLOD (cultural heritage KGs, KGHeartBeat-only assessment),
 * so this is a distinct client rather than reusing api/corpus.js -- the
 * response shapes are intentionally different (single-tool dimension
 * scores + full metric breakdown, no cross-tool consensus).
 */
import client from "./client";

export async function fetchChecloudSummary() {
  const { data } = await client.get("/checloud/summary");
  return data;
}

export async function fetchChecloudDatasets({ search, sortDesc = true, page = 1, pageSize = 25 } = {}) {
  const { data } = await client.get("/checloud/datasets", {
    params: { search: search || undefined, sort_desc: sortDesc, page, page_size: pageSize },
  });
  return data;
}

export async function fetchChecloudDatasetDetail(datasetId) {
  const { data } = await client.get(`/checloud/datasets/${encodeURIComponent(datasetId)}`);
  return data;
}
