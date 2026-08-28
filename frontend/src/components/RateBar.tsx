interface Props {
  rate: number;
}

/** 完走率を表す横棒（0.0〜1.0）。ブロック3・単体判定で共用。 */
export default function RateBar({ rate }: Props) {
  const pct = Math.max(0, Math.min(1, rate)) * 100;
  return (
    <div
      style={{
        height: 6,
        borderRadius: 3,
        background: "var(--color-border)",
        overflow: "hidden",
      }}
    >
      <div style={{ width: `${pct}%`, height: "100%", background: "var(--color-primary)" }} />
    </div>
  );
}
