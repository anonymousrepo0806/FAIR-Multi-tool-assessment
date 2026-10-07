import { useRef } from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import ChartDownloadButtons from "./ChartDownloadButtons";
import ScoreValue from "./ScoreValue";

const DIMENSIONS = ["F", "A", "I", "R"];
const TOOL_COLORS = { fuji: "#2563eb", fairchecker: "#16a34a", kgheartbeat: "#d97706" };
const TOOL_LABELS = { fuji: "F-UJI", fairchecker: "FAIR Checker", kgheartbeat: "KG Heartbeat" };


export default function ToolScoreView({ toolResults }) {
  const tools = Object.keys(toolResults || {});
  const chartRef = useRef(null);

  const radarData = DIMENSIONS.map((dim) => {
    const row = { dimension: dim };
    for (const tool of tools) {
      const mapped = toolResults[tool]?.mapped;
      row[tool] = mapped?.dimension_scores?.[dim] ?? null;
    }
    return row;
  });

  return (
    <div className="view-panel">
      <h3>Mapped Scores (Unified Schema)</h3>
      <p className="view-panel__note">
        Each tool's raw metrics normalised onto the same 0–1 scale, so scores are directly comparable
        across tools.
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
              <tr key={dim}>
                <td>{dim}</td>
                {tools.map((t) => {
                  const mapped = toolResults[t]?.mapped;
                  const err = mapped?.error;
                  const val = mapped?.dimension_scores?.[dim];
                  return (
                    <td key={t}>
                      {err ? <span className="cell-error">error</span> : <ScoreValue score={val} />}
                    </td>
                  );
                })}
              </tr>
            ))}
            <tr className="score-table__composite">
              <td>Composite</td>
              {tools.map((t) => {
                const mapped = toolResults[t]?.mapped;
                return (
                  <td key={t}>
                    {mapped?.error ? (
                      <span className="cell-error">error</span>
                    ) : (
                      <ScoreValue score={mapped?.composite} />
                    )}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="chart-wrap" ref={chartRef}>
        <ResponsiveContainer width="100%" height={320}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="dimension" />
            <PolarRadiusAxis domain={[0, 1]} />
            <Tooltip />
            <Legend />
            {tools.map((t) => (
              <Radar
                key={t}
                name={TOOL_LABELS[t] || t}
                dataKey={t}
                stroke={TOOL_COLORS[t] || "#888"}
                fill={TOOL_COLORS[t] || "#888"}
                fillOpacity={0.15}
              />
            ))}
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <ChartDownloadButtons targetRef={chartRef} filename="fair-mapped-scores-per-tool" />

      {tools.map((t) =>
        toolResults[t]?.mapped?.error ? (
          <p key={t} className="tool-error-note">
            {TOOL_LABELS[t] || t}: {toolResults[t].mapped.error}
          </p>
        ) : null
      )}
    </div>
  );
}
