import Num from "./Num";

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
        <span style={{ fontSize: "var(--fl-text-body-sm)", fontWeight: 700, whiteSpace: "nowrap", fontFamily: "var(--fl-font-jp)" }}>
          <Num size="sm">{count}</Num>本回答
        </span>
        <div style={{ display: "flex", gap: 2, flex: 1 }}>
          {Array.from({ length: segments }).map((_, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                height: 6,
                borderRadius: "var(--fl-radius-pill)",
                background:
                  i < filledSegments
                    ? "linear-gradient(90deg, var(--fl-color-primary), var(--fl-color-success))"
                    : "var(--fl-color-border)",
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
              minHeight: 32,
              padding: "5px 10px",
              borderRadius: "var(--fl-radius-pill)",
              border: "1px solid var(--fl-color-border)",
              background: "var(--fl-color-surface)",
              color: "var(--fl-color-text-muted)",
              fontFamily: "var(--fl-font-jp)",
              fontSize: "var(--fl-text-caption)",
              fontWeight: 700,
              whiteSpace: "nowrap",
            }}
          >
            リセット
          </button>
        )}
      </div>
      <p style={{ margin: "4px 0 0", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
        {message(count)}
      </p>
    </div>
  );
}
