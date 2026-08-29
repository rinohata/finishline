import type { BaselineComparison, BaselineItem } from "../api/types";
import Num from "./Num";
import { WarningIcon } from "./icons";

interface Props {
  data: BaselineComparison;
}

function Column({ label, items, accent }: { label: string; items: BaselineItem[]; accent: string }) {
  return (
    <div>
      <p
        style={{
          fontSize: "var(--fl-text-body-sm)",
          fontWeight: 800,
          margin: "0 0 6px",
          color: accent,
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: accent, display: "inline-block" }} />
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
              borderBottom: i < items.length - 1 ? "1px solid var(--fl-color-border)" : "none",
              fontSize: "var(--fl-text-body-sm)",
            }}
          >
            <span style={{ flexShrink: 0, minWidth: 16, color: "var(--fl-color-text-muted)" }}>
              <Num size="sm">{i + 1}</Num>.
            </span>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontFamily: "var(--fl-font-jp)" }}>
              {item.title}
            </span>
            {item.is_at_risk && (
              <span
                title="あなたには続きにくい予測"
                aria-label="あなたには続きにくい予測"
                style={{ flexShrink: 0, color: "var(--fl-color-warning-dark)" }}
              >
                <WarningIcon size={12} />
              </span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

/** 重なりの少なさを一目で伝えるための簡易ベン図。実際の重複件数に応じて円の距離を
 * 変える（重複0なら完全に離す）。装飾目的の図であり、正確な集合演算の描画ではない。 */
function OverlapVenn({ overlap, total }: { overlap: number; total: number }) {
  const r = 44;
  const maxGap = r * 2.5;
  const minGap = r * 0.5;
  const ratio = Math.max(0, Math.min(1, overlap / total));
  const gap = maxGap - ratio * (maxGap - minGap);
  const cxA = 100 - gap / 2;
  const cxB = 100 + gap / 2;

  return (
    <svg viewBox="0 0 200 100" width="100%" style={{ maxWidth: 220, display: "block", margin: "0 auto" }} role="img" aria-label="人気順とあなた向けの重なりの少なさを示す図">
      <circle cx={cxA} cy={50} r={r} fill="var(--fl-color-primary)" fillOpacity={0.22} stroke="var(--fl-color-primary)" strokeWidth={1.5} />
      <circle cx={cxB} cy={50} r={r} fill="var(--fl-color-success)" fillOpacity={0.22} stroke="var(--fl-color-success)" strokeWidth={1.5} />
      <text x={cxA - r * 0.55} y={53} fontSize={9} textAnchor="middle" fill="var(--fl-color-primary-dark)" fontFamily="var(--fl-font-jp)" fontWeight={700}>
        人気順
      </text>
      <text x={cxB + r * 0.55} y={53} fontSize={9} textAnchor="middle" fill="var(--fl-color-success-dark)" fontFamily="var(--fl-font-jp)" fontWeight={700}>
        あなた向け
      </text>
    </svg>
  );
}

/** [C] ブロック6: 人気順との比較（UI仕様書4.8）。
 * 「人気順は完走予測にほとんど情報を持たない」という本サービスの主張そのものの
 * ブロックのため、重なりの少なさが伝わるよう重複件数を大きく強調する。 */
export default function BaselineComparisonBlock({ data }: Props) {
  if (data.popular.length === 0 && data.personalized.length === 0) return null;
  const total = Math.max(data.popular.length, data.personalized.length, 1);

  return (
    <div
      style={{
        margin: "16px 12px",
        background: "var(--fl-color-surface)",
        borderRadius: "var(--fl-radius-lg)",
        boxShadow: "var(--fl-shadow-sm)",
        padding: "16px",
      }}
    >
      <p style={{ margin: "0 0 12px", fontSize: "var(--fl-text-heading)", fontWeight: 800, fontFamily: "var(--fl-font-jp)" }}>
        一般的なおすすめとの違い
      </p>

      <div
        style={{
          padding: "16px 12px 14px",
          borderRadius: "var(--fl-radius-md)",
          background: "var(--fl-color-surface-alt)",
          textAlign: "center",
          marginBottom: "var(--fl-space-5)",
        }}
      >
        <OverlapVenn overlap={data.overlap} total={total} />
        <p style={{ margin: "10px 0 0", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-secondary)", fontFamily: "var(--fl-font-jp)" }}>
          {total}件中、重なったのは
        </p>
        <div style={{ margin: "2px 0 0" }}>
          <Num size="xl" color="var(--fl-color-success-dark)">
            {data.overlap}
          </Num>
          <span style={{ fontSize: "var(--fl-text-body)", color: "var(--fl-color-text-secondary)", fontFamily: "var(--fl-font-jp)", marginLeft: 4 }}>
            件
          </span>
        </div>
        <p style={{ margin: "6px 0 0", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
          人気だけでは、あなたが完走できるかはわかりません
        </p>
      </div>

      <div className="baseline-comparison-columns">
        <Column label="人気順" items={data.popular} accent="var(--fl-color-primary)" />
        <Column label="あなた向け" items={data.personalized} accent="var(--fl-color-success-dark)" />
      </div>

      <p style={{ margin: "10px 0 0", fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)", display: "flex", alignItems: "center", gap: 4 }}>
        <span style={{ color: "var(--fl-color-warning-dark)" }}>
          <WarningIcon size={11} />
        </span>
        = あなたには続きにくい予測
      </p>
    </div>
  );
}
