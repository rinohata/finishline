import type { AtRiskItem } from "../api/types";
import { pct, relativeRiskText } from "../lib/format";
import { useGenreJp } from "../state/useGenreJp";
import RateBar from "./RateBar";

interface Props {
  items: AtRiskItem[];
}

/** [C] ブロック3: 話題作だけど続かないかも（本体, UI仕様書4.5）。 */
export default function AtRiskBlock({ items }: Props) {
  const { jp } = useGenreJp();
  return (
    <div style={{ margin: "16px 12px" }}>
      <p className="section-title">話題作だけど、あなたには続かないかも</p>

      {items.length === 0 && (
        <p className="muted">
          今回の候補には、あなたが特に止まりやすそうな作品はありませんでした
        </p>
      )}

      {items.slice(0, 5).map((item) => (
        <div
          key={item.anime_id}
          style={{
            border: "1px solid var(--color-border)",
            borderRadius: 12,
            padding: 14,
            marginBottom: 12,
          }}
        >
          <p style={{ fontWeight: 800, fontSize: 15, margin: "0 0 4px" }}>{item.title}</p>
          <p className="muted" style={{ margin: "0 0 2px" }}>
            {item.year ?? "―"} / {item.episodes ? `全${item.episodes}話` : "話数不明"}
            {item.genres.length > 0 ? ` / ${item.genres.slice(0, 2).map(jp).join("・")}` : ""}
          </p>
          {item.popularity_rank != null && (
            <p className="muted" style={{ margin: "0 0 10px" }}>
              MAL人気ランキング {item.popularity_rank}位
            </p>
          )}

          <p style={{ fontSize: 17, fontWeight: 800, margin: "8px 0 4px" }}>
            {relativeRiskText(item.relative_risk)}
          </p>
          <p className="muted" style={{ margin: "0 0 6px" }}>
            完走率 {pct(item.completion_prob)}（一般平均 {pct(item.population_completion_rate)}）
          </p>
          <RateBar rate={item.completion_prob} />

          <p style={{ fontSize: 13, fontWeight: 700, margin: "12px 0 4px" }}>▼ 続きにくい理由</p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
            {item.reasons.map((r, i) => (
              <li key={i} style={{ marginBottom: 2 }}>
                {r.text}
              </li>
            ))}
          </ul>
        </div>
      ))}

      {items.length > 0 && (
        <p className="muted" style={{ marginTop: 4 }}>
          ※ 作品の評価ではなく、あなたとの相性の話です
        </p>
      )}
    </div>
  );
}
