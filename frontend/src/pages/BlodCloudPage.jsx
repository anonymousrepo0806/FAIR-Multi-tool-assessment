import { useEffect, Fragment, useState } from "react";
import { fetchCorpusCategories, fetchCorpusSummary, fetchCorpusDatasets, fetchCorpusDatasetDetail } from "../api/corpus";
import ToolScoreView from "../components/ToolScoreView";
import ConsensusView from "../components/ConsensusView";
import AIExplanation from "../components/AIExplanation";

const AGREEMENT_COLOR = { high: "#16a34a", medium: "#d97706", low: "#dc2626", single_tool: "#6b7280" };

function AgreementDot({ level }) {
  return (
    <span
      className="agreement-dot"
      style={{ backgroundColor: AGREEMENT_COLOR[level] || "#6b7280" }}
      title={level}
    />
  );
}


export default function BlodCloudPage() {
  const [categories, setCategories] = useState([]);
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [repository, setRepository] = useState("");
  const [sortDesc, setSortDesc] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [expandedId, setExpandedId] = useState(null);
  const [expandedDetail, setExpandedDetail] = useState(null);
  const [expandedLoading, setExpandedLoading] = useState(false);

  useEffect(() => {
    fetchCorpusCategories()
      .then((data) => setCategories(data.categories))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    fetchCorpusSummary({ category }).then(setSummary).catch((e) => setError(e.message));
  }, [category]);

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchCorpusDatasets({ search, category, repository, sortBy: "consensus", sortDesc, page, pageSize })
      .then((data) => {
        setRows(data.results);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      })
      .catch((e) => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [search, category, repository, sortDesc, page]);

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
      const detail = await fetchCorpusDatasetDetail(id);
      setExpandedDetail(detail);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setExpandedLoading(false);
    }
  }

  const repositories = summary ? Object.keys(summary.repository_breakdown).sort() : [];

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <h1>BLOD Cloud</h1>
        <p>
          Automatic, precomputed FAIR assessment — already agreed upon across F-UJI, FAIR-Checker, and
          KGHeartBeat — across all 10 LOD sub-cloud categories this corpus covers (BLOD, life-sciences,
          linguistic, government, publications, social-networking, cross-domain, user-generated, geography,
          media). No live tool calls, browse instantly. Filter by category below, or see the CheCLOUD tab
          for cultural-heritage knowledge graphs (scored separately, on its own published numbers).
        </p>
      </header>

      {summary && (
        <div className="corpus-summary-bar">
          <div>
            <strong>{summary.total_datasets.toLocaleString()}</strong> knowledge graphs
          </div>
          <div>
            Mean consensus composite: <strong>{summary.mean_consensus_composite?.toFixed(3) ?? "—"}</strong>
          </div>
          <div>{repositories.length} repositories</div>
        </div>
      )}

      <div className="corpus-controls">
        <input
          type="text"
          placeholder="Search by dataset id…"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <select
          value={category}
          onChange={(e) => {
            setPage(1);
            setCategory(e.target.value);
          }}
        >
          <option value="">All categories ({categories.reduce((sum, c) => sum + c.count, 0).toLocaleString()})</option>
          {categories.map((c) => (
            <option key={c.category} value={c.category}>
              {c.category} ({c.count})
            </option>
          ))}
        </select>
        <select
          value={repository}
          onChange={(e) => {
            setPage(1);
            setRepository(e.target.value);
          }}
        >
          <option value="">All repositories</option>
          {repositories.map((r) => (
            <option key={r} value={r}>
              {r} ({summary.repository_breakdown[r]})
            </option>
          ))}
        </select>
        <button onClick={() => setSortDesc((d) => !d)}>
          Sort by consensus: {sortDesc ? "high → low" : "low → high"}
        </button>
      </div>

      {error && <p className="input-panel__error">{error}</p>}
      {loading && <p className="view-panel__note">Loading…</p>}

      <div className="score-table-wrap">
        <table className="score-table">
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Category</th>
              <th>Repository</th>
              <th>F-UJI</th>
              <th>FAIR Checker</th>
              <th>KG Heartbeat</th>
              <th>Consensus</th>
              <th>Agreement</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <Fragment key={r.id}>
                <tr
                  className="corpus-row"
                  onClick={() => toggleExpand(r.id)}
                  style={{ cursor: "pointer" }}
                >
                  <td>{r.id}</td>
                  <td>{r.category || "—"}</td>
                  <td>{r.repository || "—"}</td>
                  <td>{r.tool_composites.fuji != null ? r.tool_composites.fuji.toFixed(3) : "—"}</td>
                  <td>{r.tool_composites.fairchecker != null ? r.tool_composites.fairchecker.toFixed(3) : "—"}</td>
                  <td>{r.tool_composites.kgheartbeat != null ? r.tool_composites.kgheartbeat.toFixed(3) : "—"}</td>
                  <td>{r.consensus.overall != null ? r.consensus.overall.toFixed(3) : "—"}</td>
                  <td>
                    <AgreementDot level={r.consensus.agreement} /> {r.consensus.agreement}
                  </td>
                </tr>
                {expandedId === r.id && (
                  <tr key={`${r.id}-detail`}>
                    <td colSpan={8} style={{ background: "#f8fafc" }}>
                      {expandedLoading && <p className="view-panel__note">Loading detail…</p>}
                      {expandedDetail && (
                        <>
                          <ToolScoreView toolResults={expandedDetail.tool_results} />
                          <ConsensusView consensus={expandedDetail.consensus} />
                          <AIExplanation
                            consensus={expandedDetail.consensus}
                            toolResults={expandedDetail.tool_results}
                          />
                        </>
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
          Page {page} of {totalPages} ({total.toLocaleString()} results)
        </span>
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
          Next →
        </button>
      </div>
    </div>
  );
}
