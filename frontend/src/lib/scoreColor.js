

export const SCORE_HIGH = 0.7;
export const SCORE_LOW = 0.4;

export const SCORE_COLOR_HIGH = "#16a34a";
export const SCORE_COLOR_MEDIUM = "#d97706";
export const SCORE_COLOR_LOW = "#dc2626";
export const SCORE_COLOR_UNKNOWN = "#6b7280";


export function scoreColor(score) {
  if (score == null || Number.isNaN(score)) return SCORE_COLOR_UNKNOWN;
  if (score >= SCORE_HIGH) return SCORE_COLOR_HIGH;
  if (score >= SCORE_LOW) return SCORE_COLOR_MEDIUM;
  return SCORE_COLOR_LOW;
}


export function scoreLabel(score) {
  if (score == null || Number.isNaN(score)) return "No score";
  if (score >= SCORE_HIGH) return "High FAIR score";
  if (score >= SCORE_LOW) return "Mediocre FAIR score";
  return "Low FAIR score";
}
