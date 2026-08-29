import type { WillCompleteItem } from "../api/types";
import { pct } from "../lib/format";
import { useGenreJp } from "../state/useGenreJp";

interface Props {
  items: WillCompleteItem[];
}

/** [C] ブロック4: 完走できる作品（UI仕様書4.6）。10件表示、理由は1行。 */
export default function WillCompleteBlock({ items }: Props) {
  const { jp } = useGenreJp();
  if (items.length === 0) return null;

  return (
    <div style={{ margin: "16px 12px" }}>
      <p className="section-title">あなたが最後まで見られそうな作品</p>
      <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
        {items.slice(0, 10).map((item, i) => (
          <li
            key={item.anime_id}
            style={{
              padding: "10px 0",
              borderBottom: i < items.length - 1 ? "1px solid var(--color-border)" : "none",
            }}
          >
            <p style={{ margin: 0, fontSize: 14 }}>
              <strong>
                {i + 1}. {item.title}
              </strong>
              <span style={{ float: "right", fontWeight: 700 }}>
                完走率 {pct(item.completion_prob)}（一般 {pct(item.population_completion_rate)}）
              </span>
            </p>
            <p className="muted" style={{ margin: "2px 0 0" }}>
              {item.year ?? "―"} / {item.episodes ? `全${item.episodes}話` : "話数不明"}
              {item.genres.length > 0 ? ` / ${item.genres.slice(0, 2).map(jp).join("・")}` : ""}
            </p>
            <p className="muted" style={{ margin: "2px 0 0" }}>└ {item.reason}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
