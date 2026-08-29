import type { AtRiskItem } from "../api/types";
import { relativeRiskText } from "../lib/format";
import Num from "./Num";
import { WarningIcon } from "./icons";
import { useGenreJp } from "../state/useGenreJp";

interface Props {
  items: AtRiskItem[];
}

/** [C] ブロック3: 話題作だけど続かないかも（本体, UI仕様書4.5）。
 * 注意色（--fl-color-warning、橙寄り）を使う。作品を否定しているわけではなく
 * 「あなたには合わないかもしれない」という注意喚起のため、エラー色（赤）は使わない。 */
export default function AtRiskBlock({ items }: Props) {
  const { jp } = useGenreJp();
  return (
    <div style={{ margin: "16px 12px" }}>
      <p
        style={{
          margin: "0 0 10px",
          fontSize: "var(--fl-text-heading)",
          fontWeight: 800,
          fontFamily: "var(--fl-font-jp)",
          color: "var(--fl-color-text)",
        }}
      >
        話題作だけど、あなたには続かないかも
      </p>

      {items.length === 0 && (
        <p style={{ fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
          今回の候補には、あなたが特に止まりやすそうな作品はありませんでした
        </p>
      )}

      {items.slice(0, 5).map((item) => (
        <div
          key={item.anime_id}
          style={{
            background: "var(--fl-color-surface)",
            border: "1px solid var(--fl-color-border)",
            borderLeft: "3px solid var(--fl-color-warning)",
            borderRadius: "var(--fl-radius-md)",
            boxShadow: "var(--fl-shadow-sm)",
            padding: "14px 16px",
            marginBottom: "var(--fl-space-3)",
          }}
        >
          <p style={{ fontWeight: 800, fontSize: 15, margin: "0 0 4px", fontFamily: "var(--fl-font-jp)" }}>
            {item.title}
          </p>
          <p style={{ margin: "0 0 2px", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
            {item.year ?? "―"} / {item.episodes ? `全${item.episodes}話` : "話数不明"}
            {item.genres.length > 0 ? ` / ${item.genres.slice(0, 2).map(jp).join("・")}` : ""}
          </p>
          {item.popularity_rank != null && (
            <p style={{ margin: "0 0 10px", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
              MAL人気ランキング <Num size="sm">{item.popularity_rank}</Num>位
            </p>
          )}

          <p
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              margin: "8px 0 4px",
              fontSize: 17,
              fontWeight: 800,
              color: "var(--fl-color-warning-dark)",
              fontFamily: "var(--fl-font-jp)",
            }}
          >
            <WarningIcon size={16} />
            {relativeRiskText(item.relative_risk)}
          </p>
          <p style={{ margin: "0 0 6px", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
            完走率 <Num size="sm">{Math.round(item.completion_prob * 100)}%</Num>（一般平均{" "}
            <Num size="sm">{Math.round(item.population_completion_rate * 100)}%</Num>）
          </p>
          <div style={{ height: 6, borderRadius: "var(--fl-radius-pill)", background: "var(--fl-color-warning-tint)", overflow: "hidden" }}>
            <div
              style={{
                width: `${Math.max(0, Math.min(1, item.completion_prob)) * 100}%`,
                height: "100%",
                background: "var(--fl-color-warning)",
              }}
            />
          </div>

          <p
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              fontSize: "var(--fl-text-body-sm)",
              fontWeight: 700,
              margin: "12px 0 4px",
              color: "var(--fl-color-text-secondary)",
            }}
          >
            続きにくい理由
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-secondary)" }}>
            {item.reasons.map((r, i) => (
              <li key={i} style={{ marginBottom: 2 }}>
                {r.text}
              </li>
            ))}
          </ul>
        </div>
      ))}

      {items.length > 0 && (
        <p style={{ marginTop: 4, fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)" }}>
          ※ 作品の評価ではなく、あなたとの相性の話です
        </p>
      )}
    </div>
  );
}
