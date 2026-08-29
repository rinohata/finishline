interface Props {
  rate: number;
  tone?: "success" | "warning" | "primary";
}

const TONE_COLOR: Record<NonNullable<Props["tone"]>, string> = {
  success: "var(--fl-color-success)",
  warning: "var(--fl-color-warning)",
  primary: "var(--fl-color-primary)",
};

/** 完走率を表す横棒（0.0〜1.0）。ブロック3・単体判定で共用。 */
export default function RateBar({ rate, tone = "primary" }: Props) {
  const pct = Math.max(0, Math.min(1, rate)) * 100;
  return (
    <div
      style={{
        height: 6,
        borderRadius: "var(--fl-radius-pill)",
        background: "var(--fl-color-border)",
        overflow: "hidden",
      }}
    >
      <div style={{ width: `${pct}%`, height: "100%", background: TONE_COLOR[tone] }} />
    </div>
  );
}
