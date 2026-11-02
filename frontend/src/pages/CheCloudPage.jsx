import { Fragment, useEffect, useState } from "react";
import { fetchChecloudSummary, fetchChecloudDatasets, fetchChecloudDatasetDetail } from "../api/checloud";

/**
 * CheCloudPage
 * ==============
 * Browse CheCLOUD (Cultural Heritage LOD Cloud) -- a sibling corpus to
 * BLOD from the same research group, 190 KGs, assessed by KGHeartBeat
 * ALONE (not three tools like BLOD). Deliberately a separate page rather
 * than folded into BlodCloudPage: the data shape is genuinely different
 * (single-tool dimension scores + full metric breakdown, no per-tool
 * composites, no cross-tool consensus to show), so reusing
 * ToolScoreView/ConsensusView here would mean forcing this shape into
 * components built for a different one.
 */
export default function CheCloudPage() {
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [sortDesc, setSortDesc] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [expandedId, setExpandedId] = useState(null);
  const [expandedDetail, setExpandedDetail] = useState(null);
  const [expandedLoading, setExpandedLoading] = useState(false);

  useEffect(() => {
    fetchChecloudSummary().then(setSummary).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchChecloudDatasets({ search, sortDesc, page, pageSize })
      .then((data) => {
        setRows(data.results);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      })
      .catch((e) => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [search, sortDesc, page]);

  async function toggleExpand(id) {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    setExpandedId(id);
    setExpandedDetail(null);
    setExpandedLoading(true);
    try {
      const detail = await fetchChecloudDatasetDetail(id);
      setExpandedDetail(detail);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setExpandedLoading(false);
    }
  }

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <h1>CheCLOUD</h1>
        <p>
          Cultural Heritage Linked Open Data Cloud — a sibling corpus to BLOD from the same research
          group, assessed by KGHeartBeat alone (not three tools). No cross-tool consensus here — there's
          only one tool's opinion to show.
        </p>
      </header>

      {summary && (
        <div className="corpus-summary-bar">
          <div>
            <strong>{summary.total_datasets}</strong> cultural heritage knowledge graphs
          </div>
          <div>
            Mean FAIR score: <strong>{summary.mean_normalized_fair_score?.toFixed(3) ?? "—"}</strong>
          </div>
          <div style={{ fontSize: "13px", color: "#64748b" }}>{summary.tool}</div>
        </div>
      )}

      <div className="corpus-controls">
        <input
          type="text"
          placeholder="Search by id or name…"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <button onClick={() => setSortDesc((d) => !d)}>
          Sort by FAIR score: {sortDesc ? "high → low" : "low → high"}
        </button>
      </div>

      {error && <p className="input-panel__error">{error}</p>}
      {loading && <p className="view-panel__note">Loading…</p>}

      <div className="score-table-wrap">
        <table className="score-table">
          <thead>
            <tr>
              <th>Dataset</th>
              <th>F</th>
              <th>A</th>
              <th>I</th>
              <th>R</th>
              <th>FAIR score</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <Fragment key={r.id}>
                <tr className="corpus-row" onClick={() => toggleExpand(r.id)} style={{ cursor: "pointer" }}>
                  <td>{r.name || r.id}</td>
                  <td>{r.dimension_scores?.F?.toFixed(2) ?? "—"}</td>
                  <td>{r.dimension_scores?.A?.toFixed(2) ?? "—"}</td>
                  <td>{r.dimension_scores?.I?.toFixed(2) ?? "—"}</td>
                  <td>{r.dimension_scores?.R?.toFixed(2) ?? "—"}</td>
                  <td>{r.normalized_fair_score?.toFixed(3) ?? "—"}</td>
                </tr>
                {expandedId === r.id && (
                  <tr>
                    <td colSpan={6} style={{ background: "#f8fafc" }}>
                      {expandedLoading && <p className="view-panel__note">Loading detail…</p>}
                      {expandedDetail && (
                        <div style={{ padding: "12px" }}>
                          {expandedDetail.sparql_endpoint && (
                            <p style={{ fontSize: "13px", color: "#64748b" }}>
                              SPARQL endpoint: <code>{expandedDetail.sparql_endpoint}</code>
                            </p>
                          )}
                          <table className="score-table">
                            <thead>
                              <tr>
                                <th>Metric</th>
                                <th>Score</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(expandedDetail.metric_scores || {}).map(([metric, score]) => (
                                <tr key={metric}>
                                  <td>{metric}</td>
                                  <td>{Number(score).toFixed(2)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      <div className="corpus-pagination">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          ← Prev
        </button>
        <span>
          Page {page} of {totalPages} ({total} results)
        </span>
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
          Next →
        </button>
      </div>
    </div>
  );
}
