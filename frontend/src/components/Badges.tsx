import type { Confidence } from "../api/types";
import { InfoIcon } from "./icons";

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
        fontSize: "var(--fl-text-caption)",
        fontWeight: 700,
        padding: "3px 10px",
        borderRadius: "var(--fl-radius-pill)",
        fontFamily: "var(--fl-font-jp)",
        background: warn ? "var(--fl-color-warning-tint)" : "var(--fl-color-surface-alt)",
        color: warn ? "var(--fl-color-warning-dark)" : "var(--fl-color-text-muted)",
        border: warn ? "1px solid var(--fl-color-warning-border)" : "1px solid var(--fl-color-border)",
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
        display: "flex",
        alignItems: "flex-start",
        gap: 6,
        fontSize: "var(--fl-text-body-sm)",
        fontFamily: "var(--fl-font-jp)",
        background: "var(--fl-color-surface-alt)",
        borderRadius: "var(--fl-radius-sm)",
        padding: "8px 10px",
        margin: "8px 0",
        color: "var(--fl-color-text-secondary)",
      }}
    >
      <span style={{ flexShrink: 0, marginTop: 2, color: "var(--fl-color-text-muted)" }}>
        <InfoIcon size={13} />
      </span>
      {text}
    </p>
  );
}
