import { useEffect, useState } from "react";
import { fetchCorpusCategories, fetchCorpusSummary, fetchCorpusDatasets } from "../api/corpus";
import { CATEGORY_LABELS, CATEGORY_ICONS } from "../lib/categories";
import DatasetCircleGallery from "../components/DatasetCircleGallery";
import DatasetDetailPage from "./DatasetDetailPage";


export default function GalleryPage({ initialSource = null }) {
  const [categories, setCategories] = useState([]);
  const [blodRepositories, setBlodRepositories] = useState({});


  const [source, setSource] = useState(initialSource ?? "cat:blod");
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 60;
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [viewedRow, setViewedRow] = useState(null);

  const category = source && source.startsWith("cat:") ? source.slice(4) : source && source.startsWith("repo:") ? "blod" : "";
  const repository = source && source.startsWith("repo:") ? source.slice(5) : "";

  useEffect(() => {
    fetchCorpusCategories()
      .then((data) => setCategories(data.categories))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    fetchCorpusSummary({ category: "blod" })
      .then((data) => setBlodRepositories(data.repository_breakdown || {}))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchCorpusDatasets({ category, repository, sortBy: "consensus", sortDesc: true, page, pageSize })
      .then((data) => {
        setRows(data.results);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      })
      .catch((e) => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [source, category, repository, page]);

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
        <h1>FAIR Results</h1>
      </header>

      <div className={`fair-results__layout ${sidebarOpen ? "" : "fair-results__layout--collapsed"}`}>
        <button
          className="fair-sidebar__toggle"
          onClick={() => setSidebarOpen((v) => !v)}
          title={sidebarOpen ? "Collapse sidebar" : "Open sidebar"}
        >
          {sidebarOpen ? "⟨" : "⟩"}
        </button>

        {sidebarOpen && (
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
        )}

        <main className="fair-results__main">
          {error && <p className="input-panel__error">{error}</p>}
          {loading && <p className="view-panel__note">Loading…</p>}

          <DatasetCircleGallery
            rows={rows}
            onSelect={(r) => setViewedRow({ id: r.id, category: r.category, repository: r.repository })}
          />

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
