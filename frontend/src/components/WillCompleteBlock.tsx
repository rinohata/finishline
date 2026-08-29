import type { WillCompleteItem } from "../api/types";
import Num from "./Num";
import { useGenreJp } from "../state/useGenreJp";

interface Props {
  items: WillCompleteItem[];
}

/** [C] ブロック4: 完走できる作品（UI仕様書4.6）。10件表示、理由は1行。
 * ポジティブな文脈のため成功色（--fl-color-success、緑）を使う。 */
export default function WillCompleteBlock({ items }: Props) {
  const { jp } = useGenreJp();
  if (items.length === 0) return null;

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
        あなたが最後まで見られそうな作品
      </p>
      <div
        style={{
          background: "var(--fl-color-surface)",
          borderRadius: "var(--fl-radius-md)",
          boxShadow: "var(--fl-shadow-sm)",
          overflow: "hidden",
        }}
      >
        <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
          {items.slice(0, 10).map((item, i) => (
            <li
              key={item.anime_id}
              style={{
                display: "flex",
                gap: 10,
                padding: "12px 14px",
                borderBottom: i < items.length - 1 ? "1px solid var(--fl-color-border)" : "none",
              }}
            >
              <span
                style={{
                  flexShrink: 0,
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  background: "var(--fl-color-success-tint)",
                  color: "var(--fl-color-success-dark)",
                  fontSize: 11.5,
                  fontWeight: 800,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "var(--fl-font-numeric)",
                }}
              >
                {i + 1}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: "var(--fl-text-body)", fontFamily: "var(--fl-font-jp)" }}>
                  <strong>{item.title}</strong>
                  <span style={{ float: "right", fontWeight: 700, color: "var(--fl-color-success-dark)" }}>
                    <Num size="sm" color="var(--fl-color-success-dark)">
                      {Math.round(item.completion_prob * 100)}%
                    </Num>
                    <span style={{ fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)", fontFamily: "var(--fl-font-jp)" }}>
                      {" "}
                      （一般 <Num size="sm">{Math.round(item.population_completion_rate * 100)}%</Num>）
                    </span>
                  </span>
                </p>
                <p style={{ margin: "2px 0 0", fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)" }}>
                  {item.year ?? "―"} / {item.episodes ? `全${item.episodes}話` : "話数不明"}
                  {item.genres.length > 0 ? ` / ${item.genres.slice(0, 2).map(jp).join("・")}` : ""}
                </p>
                <p style={{ margin: "2px 0 0", fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-secondary)" }}>
                  └ {item.reason}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
