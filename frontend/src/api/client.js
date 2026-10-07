
import axios from "axios";


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL, timeout: 180_000 });


export async function assessUrl(url, { runFuji = true, runFairchecker = true, runKgheartbeat = true } = {}) {
  const form = new FormData();
  form.append("input_type", "url");
  form.append("url", url);
  form.append("run_fuji", String(runFuji));
  form.append("run_fairchecker", String(runFairchecker));
  form.append("run_kgheartbeat", String(runKgheartbeat));
  const { data } = await client.post("/assess", form);
  return data;
}


export async function assessFile(file, opts = {}) {
  const form = new FormData();
  form.append("input_type", "file");
  form.append("file", file);
  form.append("run_fuji", String(opts.runFuji ?? true));
  form.append("run_fairchecker", String(opts.runFairchecker ?? true));
  form.append("run_kgheartbeat", String(opts.runKgheartbeat ?? true));
  const { data } = await client.post("/assess", form);
  return data;
}


export async function assessFileBatch(file, opts = {}) {
  const form = new FormData();
  form.append("file", file);
  form.append("run_fuji", String(opts.runFuji ?? true));
  form.append("run_fairchecker", String(opts.runFairchecker ?? true));
  form.append("run_kgheartbeat", String(opts.runKgheartbeat ?? true));
  const { data } = await client.post("/assess/batch", form);
  return data;
}


export async function explain(consensus, toolResults) {
  const { data } = await client.post("/explain", {
    consensus,
    tool_results: toolResults,
  });
  return data;
}

export default client;
