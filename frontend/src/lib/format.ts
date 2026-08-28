/** relative_risk（一般平均に対して何倍止まりやすいか）の表示文言。UI仕様書5.1・4.5で共用。 */
export function relativeRiskText(r: number | null): string | null {
  if (r == null) return null;
  if (r >= 1) return `平均より ${r.toFixed(1)}倍 止まりやすい`;
  const inv = 1 / Math.max(r, 0.01);
  return `平均より ${inv.toFixed(1)}倍 完走しやすい`;
}

export function pct(v: number | null | undefined): string {
  return v == null ? "―" : `${Math.round(v * 100)}%`;
}
