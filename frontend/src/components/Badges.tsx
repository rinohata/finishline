import type { Confidence } from "../api/types";

const CONFIDENCE_LABEL: Record<Confidence, string> = {
  high: "信頼度：高",
  medium: "信頼度：中",
  low: "信頼度：低",
};

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const warn = confidence === "low";
  return (
    <span
      style={{
        fontSize: 12,
        fontWeight: 700,
        padding: "3px 8px",
        borderRadius: 999,
        background: warn ? "#fff4e5" : "#eef2f5",
        color: warn ? "#a3690b" : "var(--color-text-muted)",
        border: warn ? "1px solid #f0c987" : "1px solid var(--color-border)",
      }}
    >
      {CONFIDENCE_LABEL[confidence]}
    </span>
  );
}

export function EstimatedNote({ isEstimated, isOngoing }: { isEstimated: boolean; isOngoing: boolean }) {
  if (!isEstimated && !isOngoing) return null;
  const text = isOngoing
    ? "放送中の作品のため、完走データが不足しています。内容の傾向から推定しています"
    : "2021年以降の作品のため、内容の傾向から推定しています";
  return (
    <p
      style={{
        fontSize: 12.5,
        background: "#eef2f5",
        borderRadius: 8,
        padding: "8px 10px",
        margin: "8px 0",
        color: "var(--color-text-muted)",
      }}
    >
      ⓘ {text}
    </p>
  );
}
