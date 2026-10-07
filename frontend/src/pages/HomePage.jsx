import { useEffect, useState } from "react";
import { fetchCorpusCategories, fetchCorpusSummary } from "../api/corpus";
import { CATEGORY_LABELS, CATEGORY_ICONS } from "../lib/categories";
import { scoreColor } from "../lib/scoreColor";


export default function HomePage({ onSelectCategory }) {
  const [categories, setCategories] = useState([]);
  const [scores, setScores] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");


  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchCorpusCategories()
      .then((data) => {
        if (cancelled) return;
        setCategories(data.categories);
        return Promise.all(
          data.categories.map((c) =>
            fetchCorpusSummary({ category: c.category })
              .then((s) => [c.category, s.mean_consensus_composite])
              .catch(() => [c.category, null])
          )
        );
      })
      .then((pairs) => {
        if (cancelled || !pairs) return;
        setScores(Object.fromEntries(pairs));
        requestAnimationFrame(() => requestAnimationFrame(() => !cancelled && setAnimate(true)));
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="home-page">
      <header className="home-page__hero">
        <h1>FAIR Multi-Assessor</h1>
        <p>
          Automatic FAIR assessment of LOD sub-cloud categories, BLOD and CheCloud providing
          agreed-upon results from three independent FAIR assessment tools — F-UJI, FAIR-Checker, and
          KGHeartBeat.
        </p>
      </header>

      {error && <p className="input-panel__error">{error}</p>}
      {loading && <p className="view-panel__note">Loading repositories…</p>}

      <div className="home-repo-grid">
        {categories.map((c, i) => {
          const score = scores[c.category];
          const pct = score != null ? Math.round(score * 100) : 0;
          return (
            <button
              key={c.category}
              className="home-repo-card"
              style={{ animationDelay: `${i * 45}ms` }}
              onClick={() => onSelectCategory(c.category)}
            >
              <span className="home-repo-card__icon">{CATEGORY_ICONS[c.category] || "📁"}</span>
              <span className="home-repo-card__name">{CATEGORY_LABELS[c.category] || c.category}</span>
              <span className="home-repo-card__count">{c.count.toLocaleString()} knowledge graphs</span>

              <span className="home-repo-card__score-row">
                <span className="home-repo-card__score" style={{ color: scoreColor(score) }}>
                  {score != null ? score.toFixed(3) : "—"}
                </span>
                <small>FAIR composite score</small>
              </span>
              <span className="home-repo-slider">
                <span
                  className="home-repo-slider__fill"
                  style={{ width: animate ? `${pct}%` : "0%", backgroundColor: scoreColor(score) }}
                />
                <span
                  className="home-repo-slider__thumb"
                  style={{ left: animate ? `${pct}%` : "0%", backgroundColor: scoreColor(score) }}
                />
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
