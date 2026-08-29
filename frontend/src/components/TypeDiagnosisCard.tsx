import type { ProfileOut } from "../api/types";
import { useGenreJp } from "../state/useGenreJp";

interface Props {
  profile: ProfileOut;
}

/** 数字はInter・tabular-numsで統一し、装飾（グラデーション背景・斜体・絵文字併記）は
 * 一切加えない（docs/design_guidelines.md「パッケージはカラフルに、数字は硬派に」）。 */
function Num({ children, size }: { children: React.ReactNode; size: "xl" | "lg" | "sm" }) {
  const fontSize = size === "xl" ? "var(--fl-numeric-xl)" : size === "lg" ? "var(--fl-numeric-lg)" : "var(--fl-numeric-sm)";
  return (
    <span className="fl-numeric" style={{ fontSize }}>
      {children}
    </span>
  );
}

/** [C] ブロック2: タイプ診断カード（UI仕様書4.4）。シェアされる想定の主役。 */
export default function TypeDiagnosisCard({ profile }: Props) {
  const { jp } = useGenreJp();
  const pct = (v: number | null) => (v == null ? "―" : `${Math.round(v * 100)}%`);

  return (
    <div
      style={{
        margin: "16px 12px",
        borderRadius: "var(--fl-radius-lg)",
        background: "var(--fl-color-surface)",
        boxShadow: "var(--fl-shadow-md)",
        overflow: "hidden",
        fontFamily: "var(--fl-font-jp)",
      }}
    >
      {/* ヘッダー帯: パッケージ側。カラフルに、グラデーション可 */}
      <div
        style={{
          position: "relative",
          padding: "22px 16px 26px",
          textAlign: "center",
          background: "linear-gradient(135deg, var(--fl-color-primary), #3fb6f0)",
          color: "var(--fl-color-text-on-primary)",
          overflow: "hidden",
        }}
      >
        <svg
          aria-hidden
          viewBox="0 0 200 100"
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.16 }}
          preserveAspectRatio="xMidYMid slice"
        >
          <circle cx="12" cy="10" r="34" fill="#ffffff" />
          <circle cx="188" cy="88" r="46" fill="#ffffff" />
          <circle cx="170" cy="14" r="16" fill="#ffffff" />
        </svg>
        <p
          style={{
            position: "relative",
            margin: "0 0 6px",
            fontSize: "var(--fl-text-caption)",
            fontWeight: 700,
            letterSpacing: "0.08em",
            opacity: 0.85,
          }}
        >
          あなたの完走タイプ
        </p>
        <p
          style={{
            position: "relative",
            margin: 0,
            fontSize: "var(--fl-text-display)",
            fontWeight: 800,
            lineHeight: 1.3,
          }}
        >
          {profile.type_name}
        </p>
      </div>

      {/* 本体: 数字はここから硬派に */}
      <div style={{ padding: "16px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "var(--fl-space-2)",
            marginBottom: "var(--fl-space-5)",
          }}
        >
          <div
            style={{
              background: "var(--fl-color-surface-alt)",
              borderRadius: "var(--fl-radius-md)",
              padding: "12px 8px",
              textAlign: "center",
            }}
          >
            <p style={{ margin: 0, fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)", fontWeight: 700 }}>
              合う話数
            </p>
            <div style={{ margin: "6px 0 0" }}>
              <Num size="lg">{profile.best_episode_bucket ? profile.best_episode_bucket.range : "データ不足"}</Num>
            </div>
          </div>
          <div
            style={{
              background: "var(--fl-color-surface-alt)",
              borderRadius: "var(--fl-radius-md)",
              padding: "12px 8px",
              textAlign: "center",
            }}
          >
            <p style={{ margin: 0, fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)", fontWeight: 700 }}>
              完走率
            </p>
            <div style={{ margin: "6px 0 0" }}>
              <Num size="xl">{pct(profile.completion_rate)}</Num>
            </div>
            <p style={{ margin: "2px 0 0", fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)" }}>
              (全作品平均<Num size="sm">{pct(profile.completion_rate_avg)}</Num>)
            </p>
          </div>
        </div>

        <div style={{ marginBottom: "var(--fl-space-5)" }}>
          <p
            style={{
              margin: "0 0 8px",
              fontSize: "var(--fl-text-caption)",
              color: "var(--fl-color-text-muted)",
              fontWeight: 700,
            }}
          >
            話数レンジ別の完走率
          </p>
          <div style={{ display: "flex", gap: "var(--fl-space-2)" }}>
            {profile.episode_buckets.map((b) => {
              const isBest = b.range === profile.best_episode_bucket?.range;
              const hasData = b.count >= 3 && b.completion_rate != null;
              return (
                <div
                  key={b.range}
                  style={{
                    flex: 1,
                    textAlign: "center",
                    padding: "8px 4px",
                    borderRadius: "var(--fl-radius-sm)",
                    background: isBest ? "var(--fl-color-primary-tint)" : "var(--fl-color-surface-alt)",
                    border: isBest ? "1.5px solid var(--fl-color-primary)" : "1px solid var(--fl-color-border)",
                  }}
                >
                  <p style={{ fontSize: 10, margin: 0, color: "var(--fl-color-text-muted)", fontWeight: 600 }}>
                    {b.range}
                  </p>
                  <div style={{ margin: "3px 0 0" }}>
                    <Num size="sm">{hasData ? pct(b.completion_rate) : "データ不足"}</Num>
                  </div>
                  {!hasData && (
                    <p style={{ fontSize: 9.5, margin: "1px 0 0", color: "var(--fl-color-text-muted)" }}>
                      （回答<Num size="sm">{b.count}</Num>本）
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--fl-space-2)" }}>
          <div>
            <p style={{ margin: "0 0 5px", fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)", fontWeight: 700 }}>
              好む傾向
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {profile.preferred_genres.length ? (
                profile.preferred_genres.map((g) => (
                  <span
                    key={g}
                    style={{
                      padding: "4px 10px",
                      borderRadius: "var(--fl-radius-pill)",
                      background: "var(--fl-color-primary-tint)",
                      color: "var(--fl-color-primary-dark)",
                      fontSize: "var(--fl-text-body-sm)",
                      fontWeight: 700,
                    }}
                  >
                    {jp(g)}
                  </span>
                ))
              ) : (
                <span style={{ fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>―</span>
              )}
            </div>
          </div>
          <div>
            <p style={{ margin: "0 0 5px", fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)", fontWeight: 700 }}>
              避ける傾向
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {profile.avoided_genres.length ? (
                profile.avoided_genres.map((g) => (
                  <span
                    key={g}
                    style={{
                      padding: "4px 10px",
                      borderRadius: "var(--fl-radius-pill)",
                      background: "var(--fl-color-surface-alt)",
                      border: "1px solid var(--fl-color-border)",
                      color: "var(--fl-color-text-secondary)",
                      fontSize: "var(--fl-text-body-sm)",
                      fontWeight: 700,
                    }}
                  >
                    {jp(g)}
                  </span>
                ))
              ) : (
                <span style={{ fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>―</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
