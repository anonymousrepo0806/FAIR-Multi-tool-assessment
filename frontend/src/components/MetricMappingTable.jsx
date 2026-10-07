import { useState } from "react";


const PRINCIPLES = ["F1", "F2", "F3", "A1", "A1.2", "I1", "I2", "I3", "R1.1", "R1.2", "R1.3"];
const DIMENSION_OF = {
  F1: "F", F2: "F", F3: "F",
  A1: "A", "A1.2": "A",
  I1: "I", I2: "I", I3: "I",
  "R1.1": "R", "R1.2": "R", "R1.3": "R",
};
const TOOL_LABELS = { fuji: "F-UJI", fairchecker: "FAIR Checker", kgheartbeat: "KG Heartbeat" };


export default function MetricMappingTable({ toolResults }) {
  const tools = Object.keys(toolResults || {});
  const [expandedTool, setExpandedTool] = useState(null);

  return (
    <div className="view-panel">
      <h3>FAIR Metric Mapping — Sub-Principle Scores</h3>
      <p className="view-panel__note">
        Each cell is that tool's score for one FAIR sub-principle, on the unified 0–1 scale (the mean
        of its underlying metric checks for that principle) -- one level more granular than the F/A/I/R
        dimension scores above.
      </p>

      <div className="score-table-wrap">
        <table className="score-table">
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Principle</th>
              {tools.map((t) => (
                <th key={t}>{TOOL_LABELS[t] || t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PRINCIPLES.map((p) => (
              <tr key={p}>
                <td>{DIMENSION_OF[p]}</td>
                <td>{p}</td>
                {tools.map((t) => {
                  const mapped = toolResults[t]?.mapped;
                  const val = mapped?.principle_scores?.[p];
                  return (
                    <td key={t}>
                      {mapped?.error ? (
                        <span className="cell-error">error</span>
                      ) : val != null ? (
                        val.toFixed(3)
                      ) : (
                        "—"
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {tools.length > 0 && (
        <div className="metric-detail-toggle">
          {tools.map((t) => (
            <button
              key={t}
              className={`metric-detail-toggle__btn ${expandedTool === t ? "active" : ""}`}
              onClick={() => setExpandedTool(expandedTool === t ? null : t)}
            >
              {expandedTool === t ? "Hide" : "Show"} {TOOL_LABELS[t] || t} raw metrics
            </button>
          ))}
        </div>
      )}

      {expandedTool && (
        <div className="score-table-wrap">
          <table className="score-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Score</th>
                <th>Definition</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(toolResults[expandedTool]?.mapped?.metric_scores || {}).map(([m, v]) => (
                <tr key={m}>
                  <td>{m}</td>
                  <td>{v != null ? v.toFixed(3) : "—"}</td>
                  <td>{toolResults[expandedTool]?.mapped?.metric_definitions?.[m] || "—"}</td>
                </tr>
              ))}
              {Object.keys(toolResults[expandedTool]?.mapped?.metric_scores || {}).length === 0 && (
                <tr>
                  <td colSpan={3} className="view-panel__note" style={{ textAlign: "center", padding: 16 }}>
                    No per-metric detail available for {TOOL_LABELS[expandedTool] || expandedTool} on this dataset.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
