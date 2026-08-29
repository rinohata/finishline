import type { BaselineComparison, BaselineItem } from "../api/types";

interface Props {
  data: BaselineComparison;
}

function Column({ label, items }: { label: string; items: BaselineItem[] }) {
  return (
    <div>
      <p style={{ fontSize: 12.5, fontWeight: 700, margin: "0 0 6px", color: "var(--color-text-muted)" }}>
        {label}
      </p>
      <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
        {items.map((item, i) => (
          <li
            key={`${label}-${item.anime_id}`}
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 4,
              padding: "5px 0",
              borderBottom: i < items.length - 1 ? "1px solid var(--color-border)" : "none",
              fontSize: 12.5,
            }}
          >
            <span className="muted" style={{ flexShrink: 0, minWidth: 16 }}>
              {i + 1}.
            </span>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {item.title}
            </span>
            {item.is_at_risk && (
              <span
                title="あなたには続きにくい予測"
                aria-label="あなたには続きにくい予測"
                style={{ flexShrink: 0, color: "var(--color-accent)" }}
              >
                ⚠
              </span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

/** [C] ブロック6: 人気順との比較（UI仕様書4.8）。
 * 「人気順は完走予測にほとんど情報を持たない」という本サービスの主張そのものの
 * ブロックのため、重なりの少なさが伝わるよう重複件数を大きく強調する。 */
export default function BaselineComparisonBlock({ data }: Props) {
  if (data.popular.length === 0 && data.personalized.length === 0) return null;

  return (
    <div style={{ margin: "16px 12px" }}>
      <p className="section-title">一般的なおすすめとの違い</p>

      <div className="baseline-comparison-columns">
        <Column label="人気順" items={data.popular} />
        <Column label="あなた向け" items={data.personalized} />
      </div>

      <p className="muted" style={{ margin: "10px 0 0", fontSize: 11.5 }}>
        ⚠ = あなたには続きにくい予測
      </p>

      <div
        style={{
          marginTop: 14,
          padding: "16px 12px",
          borderRadius: 12,
          background: "var(--color-bg)",
          border: "1px solid var(--color-border)",
          textAlign: "center",
        }}
      >
        <p style={{ margin: 0, fontSize: 13 }}>
          20件中、重なったのは
          <span
            style={{
              fontSize: 28,
              fontWeight: 800,
              color: "var(--color-accent)",
              margin: "0 4px",
            }}
          >
            {data.overlap}
          </span>
          件
        </p>
        <p className="muted" style={{ margin: "6px 0 0" }}>
          人気だけでは、あなたが完走できるかはわかりません
        </p>
      </div>
    </div>
  );
}
