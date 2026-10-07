import { useEffect, useState } from "react";
import { fetchCorpusCategories, fetchCorpusSummary, fetchCorpusDatasets } from "../api/corpus";
import { CATEGORY_LABELS, CATEGORY_ICONS } from "../lib/categories";
import DatasetDetailPage from "./DatasetDetailPage";
import ScoreValue from "../components/ScoreValue";

const AGREEMENT_COLOR = { high: "#16a34a", medium: "#d97706", low: "#dc2626", single_tool: "#6b7280" };

function AgreementBadge({ level }) {
  return (
    <span
      className="agreement-badge-sm"
      style={{ backgroundColor: `${AGREEMENT_COLOR[level] || "#6b7280"}1a`, color: AGREEMENT_COLOR[level] || "#6b7280" }}
    >
      <span className="agreement-dot" style={{ backgroundColor: AGREEMENT_COLOR[level] || "#6b7280" }} />
      {level ? level.replace("_", " ") : "—"}
    </span>
  );
}


export default function CorpusPage() {
  const [categories, setCategories] = useState([]);
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");


  const [source, setSource] = useState("");
  const [sortDesc, setSortDesc] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 20;


  const [viewedRow, setViewedRow] = useState(null);

  const category = source.startsWith("cat:") ? source.slice(4) : source.startsWith("repo:") ? "blod" : "";
  const repository = source.startsWith("repo:") ? source.slice(5) : "";

  useEffect(() => {
    fetchCorpusCategories()
      .then((data) => setCategories(data.categories))
      .catch((e) => setError(e.message));
  }, []);


  const [blodRepositories, setBlodRepositories] = useState({});
  useEffect(() => {
    fetchCorpusSummary({ category: "blod" })
      .then((data) => setBlodRepositories(data.repository_breakdown || {}))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchCorpusSummary({ category, repository }).then(setSummary).catch((e) => setError(e.message));
  }, [category, repository]);

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

  function selectSource(next) {
    setPage(1);
    setSource(next);
  }

  const totalKgs = categories.reduce((sum, c) => sum + c.count, 0);
  const repoNames = Object.keys(blodRepositories).sort();

  if (viewedRow) {
    return (
      <div className="fair-results">
        <DatasetDetailPage
          datasetId={viewedRow.id}
          category={viewedRow.category}
          repository={viewedRow.repository}
          onBack={() => setViewedRow(null)}
        />
      </div>
    );
  }

  return (
    <div className="fair-results">
      <header className="fair-results__header">
        <h1>Search</h1>
      </header>

      <div className="fair-results__layout">
        <aside className="fair-sidebar">
          <div className="fair-sidebar__section">
            <button
              className={`fair-sidebar__item fair-sidebar__item--all ${source === "" ? "active" : ""}`}
              onClick={() => selectSource("")}
            >
              <span className="fair-sidebar__icon">🌍</span>
              <span className="fair-sidebar__label">All sources</span>
              <span className="fair-sidebar__count">{totalKgs.toLocaleString()}</span>
            </button>
          </div>

          <div className="fair-sidebar__section">
            <div className="fair-sidebar__title">LOD sub-cloud categories</div>
            {categories.map((c) => (
              <button
                key={c.category}
                className={`fair-sidebar__item ${source === `cat:${c.category}` ? "active" : ""}`}
                onClick={() => selectSource(`cat:${c.category}`)}
              >
                <span className="fair-sidebar__icon">{CATEGORY_ICONS[c.category] || "📁"}</span>
                <span className="fair-sidebar__label">{CATEGORY_LABELS[c.category] || c.category}</span>
                <span className="fair-sidebar__count">{c.count}</span>
              </button>
            ))}
          </div>

          {repoNames.length > 0 && (
            <div className="fair-sidebar__section">
              <div className="fair-sidebar__title">BLOD source repositories</div>
              {repoNames.map((r) => (
                <button
                  key={r}
                  className={`fair-sidebar__item ${source === `repo:${r}` ? "active" : ""}`}
                  onClick={() => selectSource(`repo:${r}`)}
                >
                  <span className="fair-sidebar__icon">📦</span>
                  <span className="fair-sidebar__label">{r}</span>
                  <span className="fair-sidebar__count">{blodRepositories[r]}</span>
                </button>
              ))}
            </div>
          )}
        </aside>

        <main className="fair-results__main">
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
            <button className="corpus-controls__sort" onClick={() => setSortDesc((d) => !d)}>
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
                  <tr
                    key={`${r.category || ""}|${r.repository || ""}|${r.id}`}
                    className="corpus-row"
                    onClick={() => setViewedRow({ id: r.id, category: r.category, repository: r.repository })}
                  >
                    <td className="corpus-row__id" title={r.id}>{r.id}</td>
                    <td>
                      <span className="category-chip" title={CATEGORY_LABELS[r.category] || r.category || ""}>
                        {CATEGORY_ICONS[r.category] || "📁"} {CATEGORY_LABELS[r.category] || r.category || "—"}
                      </span>
                    </td>
                    <td className="corpus-row__repo" title={r.repository || ""}>{r.repository || "—"}</td>
                    <td><ScoreValue score={r.tool_composites.fuji} /></td>
                    <td><ScoreValue score={r.tool_composites.fairchecker} /></td>
                    <td><ScoreValue score={r.tool_composites.kgheartbeat} /></td>
                    <td className="score-table__composite">
                      <ScoreValue score={r.consensus.overall} />
                    </td>
                    <td>
                      <AgreementBadge level={r.consensus.agreement} />
                    </td>
                  </tr>
                ))}
                {!loading && rows.length === 0 && (
                  <tr>
                    <td colSpan={8} className="view-panel__note" style={{ textAlign: "center", padding: 32 }}>
                      No knowledge graphs match this filter.
                    </td>
                  </tr>
                )}
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
        </main>
      </div>
    </div>
  );
}
