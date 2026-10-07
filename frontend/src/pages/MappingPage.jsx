import { useEffect, useState } from "react";
import { fetchMappingReference } from "../api/mapping";

const DIM_COLOR = { F: "#1d4ed8", A: "#059669", I: "#7c3aed", R: "#b45309" };
const DIM_BG = { F: "#eff6ff", A: "#ecfdf5", I: "#f5f3ff", R: "#fffbeb" };

function DimBadge({ dim }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        color: DIM_COLOR[dim] || "#334155",
        background: DIM_BG[dim] || "#f1f5f9",
      }}
    >
      {dim}
    </span>
  );
}

function ToolCell({ entries }) {
  if (!entries || entries.length === 0) {
    return <span className="view-panel__note">not implemented</span>;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {entries.map((e) => (
        <code key={e.column} style={{ fontSize: 12 }}>
          {e.column}
          <span className="view-panel__note"> (max {e.attainable})</span>
        </code>
      ))}
    </div>
  );
}


export default function MappingPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchMappingReference()
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail || e.message));
  }, []);

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <h1>FAIR Mapping</h1>
        <p>
          How F-UJI, FAIR-Checker, and KGHeartBeat's raw outputs map onto the eleven FAIR
          sub-principles used throughout this app, and how those map up into the F/A/I/R/FAIR
          scores shown on every other page.
        </p>
      </header>

      {error && <p className="input-panel__error">{error}</p>}
      {!data && !error && <p className="view-panel__note">Loading…</p>}

      {data && (
        <>
          <section style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 16 }}>Metric → principle mapping</h2>
            <p className="view-panel__note">
              Each cell is the raw column a tool reports for that principle. A tool with more
              than one column for a principle has its own sub-checks averaged together first
              (Eq. 2, below). "not implemented" means that tool has no check for that principle
              at all — it contributes no term to that principle's or dimension's mean, rather
              than a fabricated zero.
            </p>
            <div className="score-table-wrap">
              <table className="score-table">
                <thead>
                  <tr>
                    <th>Principle</th>
                    <th>Dimension</th>
                    <th>{data.tool_labels.fuji}</th>
                    <th>{data.tool_labels.fairchecker}</th>
                    <th>{data.tool_labels.kgheartbeat}</th>
                    <th>KGHeartBeat scoring function</th>
                  </tr>
                </thead>
                <tbody>
                  {data.principles.map((p) => (
                    <tr key={p}>
                      <td>
                        <code>{p}</code>
                      </td>
                      <td>
                        <DimBadge dim={data.dimension_of[p]} />
                      </td>
                      <td>
                        <ToolCell entries={data.tools.fuji[p]} />
                      </td>
                      <td>
                        <ToolCell entries={data.tools.fairchecker[p]} />
                      </td>
                      <td>
                        <ToolCell entries={data.tools.kgheartbeat[p]} />
                      </td>
                      <td style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 320 }}>
                        {(data.tools.kgheartbeat[p] || [])
                          .map((e) => data.kgheartbeat_metric_definitions[e.column])
                          .filter(Boolean)
                          .map((def, i) => (
                            <div key={i} style={{ marginBottom: 4 }}>
                              {def}
                            </div>
                          ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 16 }}>Aggregation formula</h2>
            <p className="view-panel__note">
              Applied identically for every tool, live or precomputed — an unweighted mean at
              each of four levels, so a tool that checks more sub-metrics for one principle
              doesn't get extra weight for it.
            </p>
            <div className="score-table-wrap" style={{ padding: 20, fontFamily: "monospace", fontSize: 14, lineHeight: 2 }}>
              <div>
                <strong>Eq. 1 — metric score:</strong> s(m, x) = earned(m, x) / attainable(m){" "}
                <span className="view-panel__note">→ each raw column rescaled to [0, 1]</span>
              </div>
              <div>
                <strong>Eq. 2 — principle score:</strong> S(p, x) = mean{"{"}m ∈ M_p{"}"} s(m, x){" "}
                <span className="view-panel__note">→ mean of that principle's metric(s)</span>
              </div>
              <div>
                <strong>Eq. 3 — dimension score:</strong> S(d, x) = mean{"{"}p ∈ P_d{"}"} S(p, x){" "}
                <span className="view-panel__note">→ mean of that dimension's principles</span>
              </div>
              <div>
                <strong>Eq. 4 — FAIR composite:</strong> S(FAIR, x) = mean{"{"}d ∈ [F,A,I,R]{"}"} S(d, x){" "}
                <span className="view-panel__note">→ mean of the four dimensions</span>
              </div>
            </div>
            <p className="view-panel__note" style={{ marginTop: 8 }}>
              This is the <strong>mapped</strong> score (0–1, comparable across tools). Each
              tool's <strong>native</strong> score (shown alongside it everywhere in the app) is
              that tool's own methodology, in its own units — not put through this formula, and
              not comparable across tools.
            </p>
          </section>

          <section>
            <h2 style={{ fontSize: 16 }}>Cross-tool consensus</h2>
            <p className="view-panel__note">
              Once every available tool has a mapped composite and per-dimension scores,
              "agreed upon by tools" is computed the same way everywhere in the app (one
              function, reused by live assessment, BLOD Cloud, and CheCLOUD):
            </p>
            <div className="score-table-wrap" style={{ padding: 20, fontFamily: "monospace", fontSize: 14, lineHeight: 2 }}>
              <div>overall = mean(composite across tools that produced a usable score)</div>
              <div>range = max(composite) − min(composite), across those same tools</div>
              <div>
                agreement = <strong>high</strong> if range &lt; 0.15, <strong>medium</strong> if
                range &lt; 0.35, else <strong>low</strong>
                <span className="view-panel__note"> · single_tool if only one tool produced a score</span>
              </div>
            </div>
            <p className="view-panel__note" style={{ marginTop: 8 }}>
              The same range → agreement thresholds apply per-dimension (F/A/I/R), not just to
              the overall composite — see the "Agreement" column and per-dimension breakdown on
              any assessment.
            </p>
          </section>
        </>
      )}
    </div>
  );
}
