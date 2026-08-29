import type { ProfileOut } from "../api/types";
import { useGenreJp } from "../state/useGenreJp";

interface Props {
  profile: ProfileOut;
}

/** [C] ブロック2: タイプ診断カード（UI仕様書4.4）。 */
export default function TypeDiagnosisCard({ profile }: Props) {
  const { jp } = useGenreJp();
  const pct = (v: number | null) => (v == null ? "―" : `${Math.round(v * 100)}%`);

  return (
    <div
      style={{
        margin: "16px 12px",
        padding: "20px 16px",
        borderRadius: 16,
        background: "linear-gradient(180deg, #f2f7fc, #ffffff)",
        border: "1px solid var(--color-border)",
        textAlign: "center",
      }}
    >
      <p style={{ fontSize: 19, fontWeight: 800, margin: "0 0 8px" }}>{profile.type_name}</p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
          margin: "16px 0",
        }}
      >
        <div style={{ background: "var(--color-surface)", borderRadius: 10, padding: "10px 6px" }}>
          <p className="muted" style={{ margin: 0 }}>
            合う話数
          </p>
          <p style={{ fontSize: 20, fontWeight: 800, margin: "4px 0 0" }}>
            {profile.best_episode_bucket ? profile.best_episode_bucket.range : "データ不足"}
          </p>
        </div>
        <div style={{ background: "var(--color-surface)", borderRadius: 10, padding: "10px 6px" }}>
          <p className="muted" style={{ margin: 0 }}>
            完走率
          </p>
          <p style={{ fontSize: 20, fontWeight: 800, margin: "4px 0 0" }}>
            {pct(profile.completion_rate)}
          </p>
          <p className="muted" style={{ margin: 0 }}>
            (全作品平均{pct(profile.completion_rate_avg)})
          </p>
        </div>
      </div>

      <div style={{ margin: "0 0 16px" }}>
        <p className="muted" style={{ margin: "0 0 6px", fontSize: 12 }}>
          話数レンジ別の完走率
        </p>
        <div style={{ display: "flex", gap: 6 }}>
          {profile.episode_buckets.map((b) => (
            <div
              key={b.range}
              style={{
                flex: 1,
                textAlign: "center",
                padding: "6px 2px",
                borderRadius: 8,
                background: b.range === profile.best_episode_bucket?.range ? "var(--color-surface)" : "transparent",
                border: "1px solid var(--color-border)",
              }}
            >
              <p style={{ fontSize: 10, margin: 0 }} className="muted">{b.range}</p>
              <p style={{ fontSize: 13, fontWeight: 700, margin: "2px 0 0" }}>
                {b.count >= 3 && b.completion_rate != null ? pct(b.completion_rate) : "データ不足"}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div style={{ textAlign: "left", fontSize: 13, lineHeight: 1.8 }}>
        <p style={{ margin: "4px 0" }}>
          <strong>好む傾向</strong>{" "}
          {profile.preferred_genres.length ? profile.preferred_genres.map(jp).join(" / ") : "―"}
        </p>
        <p style={{ margin: "4px 0" }}>
          <strong>避ける傾向</strong>{" "}
          {profile.avoided_genres.length ? profile.avoided_genres.map(jp).join(" / ") : "―"}
        </p>
      </div>
    </div>
  );
}
