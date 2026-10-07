import { useEffect, useState } from "react";
import { fetchCorpusDatasetDetail } from "../api/corpus";
import { CATEGORY_LABELS, CATEGORY_ICONS } from "../lib/categories";
import ToolScoreView from "../components/ToolScoreView";
import MetricMappingTable from "../components/MetricMappingTable";
import ConsensusView from "../components/ConsensusView";
import AIExplanation from "../components/AIExplanation";


export default function DatasetDetailPage({ datasetId, category, repository, onBack }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    setDetail(null);
    fetchCorpusDatasetDetail(datasetId, category)
      .then(setDetail)
      .catch((e) => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [datasetId, category]);

  return (
    <div className="dataset-detail">
      <button className="dataset-detail__back" onClick={onBack}>
        ← Back to FAIR Results
      </button>

      <header className="dataset-detail__header">
        <h1>{datasetId}</h1>
        <div className="dataset-detail__meta">
          {category && (
            <span className="category-chip category-chip--lg">
              {CATEGORY_ICONS[category] || "📁"} {CATEGORY_LABELS[category] || category}
            </span>
          )}
          {repository && <span className="dataset-detail__repo">via {repository}</span>}
          {detail?.dataset_url && (
            <a className="dataset-detail__url" href={detail.dataset_url} target="_blank" rel="noreferrer">
              {detail.dataset_url} ↗
            </a>
          )}
        </div>
      </header>

      {loading && <p className="view-panel__note">Loading assessment…</p>}
      {error && <p className="input-panel__error">{error}</p>}

      {detail && (
        <>
          <ToolScoreView toolResults={detail.tool_results} />
          <MetricMappingTable toolResults={detail.tool_results} />
          <ConsensusView consensus={detail.consensus} />
          <AIExplanation consensus={detail.consensus} toolResults={detail.tool_results} />
        </>
      )}
    </div>
  );
}
