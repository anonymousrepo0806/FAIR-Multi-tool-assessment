import { CATEGORY_ICONS, CATEGORY_LABELS } from "../lib/categories";
import { scoreColor, scoreLabel } from "../lib/scoreColor";


export default function DatasetCircleGallery({ rows, onSelect }) {
  if (rows.length === 0) {
    return <p className="view-panel__note">No knowledge graphs match this filter.</p>;
  }

  return (
    <div className="dataset-gallery">
      {rows.map((r) => {
        const score = r.consensus?.overall;
        const color = scoreColor(score);
        return (
          <button
            key={`${r.category || ""}|${r.repository || ""}|${r.id}`}
            className="dataset-circle"
            style={{ borderColor: color, background: `${color}14` }}
            onClick={() => onSelect(r)}
            title={`${r.id} — consensus ${score != null ? score.toFixed(3) : "—"} (${scoreLabel(score)}, agreement: ${r.consensus?.agreement || "n/a"})`}
          >
            <span className="dataset-circle__score" style={{ color }}>
              {score != null ? score.toFixed(2) : "—"}
            </span>
            <span className="dataset-circle__id">{r.id}</span>
            {r.category && (
              <span className="dataset-circle__cat">
                {CATEGORY_ICONS[r.category] || "📁"} {CATEGORY_LABELS[r.category] || r.category}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
