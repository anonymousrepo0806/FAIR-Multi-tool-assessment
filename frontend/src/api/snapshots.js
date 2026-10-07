
import client from "./client";

export async function fetchSnapshots() {
  const { data } = await client.get("/snapshots");
  return data.snapshots;
}

export async function fetchSources() {
  const { data } = await client.get("/snapshots/sources");
  return data.sources;
}

export function downloadUrl(filename) {
  const base = client.defaults.baseURL || "";
  return `${base}/snapshots/download/${encodeURIComponent(filename)}`;
}
