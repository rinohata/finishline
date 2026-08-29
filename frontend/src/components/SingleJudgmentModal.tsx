import { useEffect, useState } from "react";
import { postPredictSingle } from "../api/client";
import { isAlreadyAnswered, type PredictSingleResult, type ResponseInput } from "../api/types";
import { relativeRiskText } from "../lib/format";
import { useGenreJp } from "../state/useGenreJp";
import { ConfidenceBadge, EstimatedNote } from "./Badges";
import { WarningIcon } from "./icons";
import Num from "./Num";
import RateBar from "./RateBar";
import SingleAnimeDropoutCurve from "./SingleAnimeDropoutCurve";

interface Props {
  animeId: number;
  responses: ResponseInput[];
  onClose: () => void;
}

type Tone = "success" | "warning";

/** UI仕様書5.2（改訂版しきい値）。断定せず、すべて推量形。 */
function judgmentTier(prob: number): { text: string; tone: Tone } {
  if (prob >= 0.95) return { text: "問題なく見られそうです", tone: "success" };
  if (prob >= 0.88) return { text: "完走できそうです", tone: "success" };
  if (prob >= 0.75) return { text: "やや注意。平均より止まりやすい傾向", tone: "warning" };
  if (prob >= 0.5) return { text: "完走は難しいかもしれません", tone: "warning" };
  return { text: "最後まで届きにくいかもしれません", tone: "warning" };
}

const RESULT_LABEL_JP: Record<string, string> = { completed: "完走", dropped: "途中で止まった" };

/** [D] 単体判定画面全体（UI仕様書5章）。モーダル表示。 */
export default function SingleJudgmentModal({ animeId, responses, onClose }: Props) {
  const { jp } = useGenreJp();
  const [result, setResult] = useState<PredictSingleResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = () => {
    setLoading(true);
    setError(false);
    postPredictSingle(responses, animeId)
      .then(setResult)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animeId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const tier = result && !isAlreadyAnswered(result) ? judgmentTier(result.completion_prob) : null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,23,42,0.5)",
        zIndex: 100,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        overflowY: "auto",
        padding: "24px 12px",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--fl-color-surface)",
          borderRadius: "var(--fl-radius-lg)",
          boxShadow: "var(--fl-shadow-lg)",
          padding: "20px 18px",
          width: "100%",
          maxWidth: 480,
          position: "relative",
          fontFamily: "var(--fl-font-jp)",
        }}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="閉じる"
          style={{
            position: "absolute",
            top: 10,
            right: 10,
            border: "none",
            background: "none",
            fontSize: 20,
            lineHeight: 1,
            color: "var(--fl-color-text-muted)",
            padding: 6,
          }}
        >
          ×
        </button>

        {loading && <p className="loading">判定中...</p>}

        {error && (
          <div className="error-banner">
            一時的に判定できませんでした。時間をおいて再度お試しください
            <div>
              <button type="button" onClick={load}>
                再試行
              </button>
            </div>
          </div>
        )}

        {result && isAlreadyAnswered(result) && (
          <p style={{ padding: "20px 20px 8px 0", fontSize: 15 }}>{result.message}</p>
        )}

        {result && !isAlreadyAnswered(result) && tier && (
          <>
            <p style={{ fontWeight: 800, fontSize: 17, margin: "4px 24px 2px 0" }}>{result.anime.title}</p>
            <p style={{ margin: "0 0 16px", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
              {result.anime.year ?? "―"} /{" "}
              {result.anime.episodes ? (
                <>
                  全<Num size="sm">{result.anime.episodes}</Num>話{result.is_ongoing ? "（放送中）" : ""}
                </>
              ) : (
                "話数不明"
              )}
            </p>

            <p style={{ fontSize: 19, fontWeight: 800, margin: "0 0 4px", textAlign: "center" }}>
              {result.is_estimated || result.is_ongoing ? "推定 " : ""}
              {relativeRiskText(result.relative_risk)}
            </p>
            <p style={{ textAlign: "center", margin: "0 0 6px", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
              完走率 <Num size="sm">{Math.round(result.completion_prob * 100)}%</Num>（一般平均{" "}
              <Num size="sm">{Math.round(result.population_completion_rate * 100)}%</Num>）
            </p>
            <RateBar rate={result.completion_prob} tone={tier.tone} />

            <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center", margin: "12px 0" }}>
              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 5,
                  fontSize: 13,
                  color: tier.tone === "warning" ? "var(--fl-color-warning-dark)" : "var(--fl-color-success-dark)",
                  fontWeight: 700,
                }}
              >
                {tier.tone === "warning" ? <WarningIcon size={13} /> : "✓"}
                {tier.text}
              </span>
              <ConfidenceBadge confidence={result.confidence} />
            </div>

            <EstimatedNote isEstimated={result.is_estimated} isOngoing={result.is_ongoing} />

            {(result.factors.negative.length > 0 || result.factors.positive.length > 0) && (
              <div style={{ margin: "14px 0 0", borderTop: "1px solid var(--fl-color-border)", paddingTop: 12 }}>
                {result.factors.negative.length > 0 && (
                  <>
                    <p
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        fontSize: "var(--fl-text-body-sm)",
                        fontWeight: 700,
                        margin: "0 0 4px",
                        color: "var(--fl-color-warning-dark)",
                      }}
                    >
                      <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--fl-color-warning)", display: "inline-block" }} />
                      不利な要素
                    </p>
                    <ul style={{ margin: "0 0 10px", paddingLeft: 18, fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-secondary)" }}>
                      {result.factors.negative.map((r, i) => (
                        <li key={i}>{r.text}</li>
                      ))}
                    </ul>
                  </>
                )}
                {result.factors.positive.length > 0 && (
                  <>
                    <p
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        fontSize: "var(--fl-text-body-sm)",
                        fontWeight: 700,
                        margin: "0 0 4px",
                        color: "var(--fl-color-success-dark)",
                      }}
                    >
                      <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--fl-color-success)", display: "inline-block" }} />
                      有利な要素
                    </p>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-secondary)" }}>
                      {result.factors.positive.map((r, i) => (
                        <li key={i}>{r.text}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}

            {/* UI仕様書5.3: 該当0件ならブロックごと非表示 */}
            {result.evidence.length > 0 && (
              <div style={{ margin: "14px 0 0", borderTop: "1px solid var(--fl-color-border)", paddingTop: 12 }}>
                <p style={{ margin: "0 0 6px", fontSize: "var(--fl-text-heading)", fontWeight: 800 }}>
                  あなたの実績（条件が近い作品）
                </p>
                {result.evidence.map((e, i) => (
                  <p key={i} style={{ fontSize: "var(--fl-text-body-sm)", margin: "4px 0", color: "var(--fl-color-text-secondary)" }}>
                    {e.title}　全<Num size="sm">{e.episodes ?? "?"}</Num>話・{e.genre ? jp(e.genre) : "―"}　→{" "}
                    {RESULT_LABEL_JP[e.result] ?? e.result}
                  </p>
                ))}
                {result.evidence_insight && (
                  <p style={{ marginTop: 6, fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
                    → {result.evidence_insight}
                  </p>
                )}
              </div>
            )}

            <div style={{ margin: "14px 0 0", borderTop: "1px solid var(--fl-color-border)", paddingTop: 12 }}>
              <SingleAnimeDropoutCurve
                curve={result.dropout_curve ?? []}
                peakEpisode={result.peak_dropout_episode}
                survivalAfterPeak={result.survival_after_peak}
                insufficientData={result.insufficient_data}
              />
              {result.advice && (
                <p style={{ marginTop: 4, fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-secondary)" }}>
                  → {result.advice}
                </p>
              )}
            </div>

            {/* UI仕様書5.5: 完走率80%以上のとき次の導線を出す */}
            {result.next_recommendations.length > 0 && (
              <div style={{ margin: "14px 0 0", borderTop: "1px solid var(--fl-color-border)", paddingTop: 12 }}>
                <p style={{ margin: "0 0 6px", fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
                  この作品を完走した人のうち、あなたと傾向が近い層が次に完走している作品
                </p>
                {result.next_recommendations.map((n) => (
                  <p key={n.anime_id} style={{ fontSize: "var(--fl-text-body-sm)", margin: "4px 0", color: "var(--fl-color-text-secondary)" }}>
                    {n.title}　あなたの完走率 <Num size="sm">{Math.round(n.completion_prob * 100)}%</Num>
                  </p>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
