const TOOL_LABELS = { fuji: "F-UJI", fairchecker: "FAIR Checker", kgheartbeat: "KG Heartbeat" };
const DIMENSIONS = ["F", "A", "I", "R", "FAIR"];


export default function NativeScoreView({ toolResults }) {
  const tools = Object.keys(toolResults || {});

  return (
    <div className="view-panel">
      <h3>Native Scores (Tool's Own Methodology)</h3>
      <p className="view-panel__note">
        Each tool's own reported FAIR score, exactly as that tool computes it — not normalised or
        remapped. These numbers are <em>not</em> directly comparable across tools; use the Mapped view
        for that.
      </p>

      <div className="score-table-wrap">
        <table className="score-table">
          <thead>
            <tr>
              <th>Dimension</th>
              {tools.map((t) => (
                <th key={t}>{TOOL_LABELS[t] || t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DIMENSIONS.map((dim) => (
              <tr key={dim} className={dim === "FAIR" ? "score-table__composite" : ""}>
                <td>{dim === "FAIR" ? "Overall (native)" : dim}</td>
                {tools.map((t) => {
                  const native = toolResults[t]?.native;
                  if (native?.error) {
                    return (
                      <td key={t}>
                        <span className="cell-error">error</span>
                      </td>
                    );
                  }
                  if (native?.note && !(dim in (native || {}))) {
                    return (
                      <td key={t}>
                        <span className="cell-note" title={native.note}>
                          n/a
                        </span>
                      </td>
                    );
                  }
                  const val = native?.[dim];
                  return <td key={t}>{val != null ? Number(val).toFixed(3) : "—"}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {tools.map((t) => {
        const native = toolResults[t]?.native;
        if (native?.note) {
          return (
            <p key={t} className="tool-error-note">
              {TOOL_LABELS[t] || t}: {native.note}
            </p>
          );
        }
        if (native?.error) {
          return (
            <p key={t} className="tool-error-note">
              {TOOL_LABELS[t] || t}: {native.error}
            </p>
          );
        }
        return null;
      })}
    </div>
  );
}
