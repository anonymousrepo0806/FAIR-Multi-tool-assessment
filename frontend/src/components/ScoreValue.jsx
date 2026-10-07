import { scoreColor, scoreLabel } from "../lib/scoreColor";


export default function ScoreValue({ score, className = "" }) {
  if (score == null) return <span className={className}>—</span>;
  return (
    <span
      className={className}
      style={{ color: scoreColor(score), fontWeight: 600 }}
      title={scoreLabel(score)}
    >
      {score.toFixed(3)}
    </span>
  );
}
