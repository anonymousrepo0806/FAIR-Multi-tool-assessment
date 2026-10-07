import { useRef } from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Legend,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import ChartDownloadButtons from "./ChartDownloadButtons";
import ScoreValue from "./ScoreValue";
import { scoreColor } from "../lib/scoreColor";

const DIMENSIONS = ["F", "A", "I", "R"];
const AGREEMENT_COLOR = { high: "#16a34a", medium: "#d97706", low: "#dc2626", single_tool: "#6b7280", insufficient_data: "#6b7280" };
const AGREEMENT_LABEL = {
  high: "High consensus",
  medium: "Medium consensus",
  low: "Low consensus",
  single_tool: "Single tool only",
  insufficient_data: "Insufficient data",
};

function AgreementBadge({ level }) {
  const color = AGREEMENT_COLOR[level] || "#6b7280";
  return (
    <span className="agreement-badge" style={{ backgroundColor: color }}>
      {AGREEMENT_LABEL[level] || level}
    </span>
  );
}


export default function ConsensusView({ consensus }) {
  const chartRef = useRef(null);

  if (!consensus || consensus.overall == null) {
    return (
      <div className="view-panel">
        <h3>Consensus</h3>
        <p className="view-panel__note">{consensus?.note || "No tool produced a usable score."}</p>
      </div>
    );
  }

  const radarData = DIMENSIONS.map((dim) => ({
    dimension: dim,
    consensus: consensus.by_dimension?.[dim] ?? 0,
  }));

  return (
    <div className="view-panel">
      <h3>Agreed-Upon Consensus Result</h3>

      <div className="consensus-summary">
        <div className="consensus-summary__overall">
          <span className="consensus-summary__value" style={{ color: scoreColor(consensus.overall) }}>
            {consensus.overall.toFixed(3)}
          </span>
          <span className="consensus-summary__label">Overall FAIR score</span>
        </div>
        <AgreementBadge level={consensus.agreement} />
      </div>

      <p className="view-panel__note">
        Computed as the mean composite score across:{" "}
        {consensus.tools_used.map((t) => t).join(", ") || "no tools"}.
        {consensus.tools_missing?.length > 0 && (
          <> Not included (missing/failed): {consensus.tools_missing.join(", ")}.</>
        )}
      </p>

      <div className="chart-wrap" ref={chartRef}>
        <ResponsiveContainer width="100%" height={320}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="dimension" />
            <PolarRadiusAxis domain={[0, 1]} />
            <Tooltip />
            <Legend />
            <Radar name="Consensus" dataKey="consensus" stroke="#4f46e5" fill="#4f46e5" fillOpacity={0.25} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <ChartDownloadButtons targetRef={chartRef} filename="fair-consensus-score" />

      <div className="score-table-wrap">
        <table className="score-table">
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Consensus score</th>
              <th>Spread across tools</th>
              <th>Agreement</th>
            </tr>
          </thead>
          <tbody>
            {DIMENSIONS.map((dim) => {
              const score = consensus.by_dimension?.[dim];
              const range = consensus.range_by_dimension?.[dim];
              const level = consensus.agreement_by_dimension?.[dim];
              return (
                <tr key={dim}>
                  <td>{dim}</td>
                  <td><ScoreValue score={score} /></td>
                  <td>{range != null ? `±${range.toFixed(3)}` : "—"}</td>
                  <td>{level ? <AgreementBadge level={level} /> : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
