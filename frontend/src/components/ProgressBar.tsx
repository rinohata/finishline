interface Props {
  count: number;
  onResetClick?: () => void;
}

function message(count: number): string {
  if (count === 0) return "気になる作品から答えてみてください";
  if (count < 5) return `あと${5 - count}本で結果が見られます`;
  if (count < 10) return "結果を見られます。10本で精度が上がります";
  if (count < 20) return "精度：中。20本でさらに上がります";
  return "精度：高。十分です";
}

/** UI仕様書3.6。20本を超えたら追加を促さない。3.9: 回答が0件のときはリセットボタンを隠す。 */
export default function ProgressBar({ count, onResetClick }: Props) {
  const filled = Math.min(count, 20);
  const segments = 10;
  const filledSegments = Math.round((filled / 20) * segments);

  return (
    <div style={{ padding: "8px 12px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 12.5, fontWeight: 600, whiteSpace: "nowrap" }}>
          {count}本回答
        </span>
        <div style={{ display: "flex", gap: 2, flex: 1 }}>
          {Array.from({ length: segments }).map((_, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                height: 6,
                borderRadius: 3,
                background: i < filledSegments ? "var(--color-primary)" : "var(--color-border)",
              }}
            />
          ))}
        </div>
        {count > 0 && onResetClick && (
          <button
            type="button"
            onClick={onResetClick}
            style={{
              flexShrink: 0,
              padding: "5px 10px",
              borderRadius: 999,
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              color: "var(--color-text-muted)",
              fontSize: 12,
              fontWeight: 600,
              whiteSpace: "nowrap",
            }}
          >
            リセット
          </button>
        )}
      </div>
      <p className="muted" style={{ margin: "4px 0 0" }}>
        {message(count)}
      </p>
    </div>
  );
}
