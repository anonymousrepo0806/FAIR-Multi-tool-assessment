
import client from "./client";

export async function fetchCorpusCategories() {
  const { data } = await client.get("/corpus/categories");
  return data;
}

export async function fetchCorpusSummary({ category } = {}) {
  const { data } = await client.get("/corpus/summary", {
    params: { category: category || undefined },
  });
  return data;
}

export async function fetchCorpusDatasets({
  search,
  category,
  repository,
  minConsensus,
  maxConsensus,
  sortBy = "id",
  sortDesc = false,
  page = 1,
  pageSize = 25,
} = {}) {
  const { data } = await client.get("/corpus/datasets", {
    params: {
      search: search || undefined,
      category: category || undefined,
      repository: repository || undefined,
      min_consensus: minConsensus ?? undefined,
      max_consensus: maxConsensus ?? undefined,
      sort_by: sortBy,
      sort_desc: sortDesc,
      page,
      page_size: pageSize,
    },
  });
  return data;
}

export async function fetchCorpusDatasetDetail(datasetId, category) {


  const { data } = await client.get(`/corpus/datasets/${encodeURIComponent(datasetId)}`, {
    params: { category: category || undefined },
  });
  return data;
}
