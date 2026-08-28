import { useEffect, useState } from "react";
import { postPredictSingle } from "../api/client";
import { isAlreadyAnswered, type PredictSingleResult, type ResponseInput } from "../api/types";
import { pct, relativeRiskText } from "../lib/format";
import { ConfidenceBadge, EstimatedNote } from "./Badges";
import RateBar from "./RateBar";
import SingleAnimeDropoutCurve from "./SingleAnimeDropoutCurve";

interface Props {
  animeId: number;
  responses: ResponseInput[];
  onClose: () => void;
}

/** UI仕様書5.2（改訂版しきい値）。断定せず、すべて推量形。 */
function judgmentText(prob: number): string {
  if (prob >= 0.95) return "✓ 問題なく見られそうです";
  if (prob >= 0.88) return "✓ 完走できそうです";
  if (prob >= 0.75) return "〜 やや注意。平均より止まりやすい傾向";
  if (prob >= 0.5) return "⚠ 完走は難しいかもしれません";
  return "⚠ 最後まで届きにくいかもしれません";
}

const RESULT_LABEL_JP: Record<string, string> = { completed: "完走", dropped: "途中で止まった" };

/** [D] 単体判定画面全体（UI仕様書5章）。モーダル表示。 */
export default function SingleJudgmentModal({ animeId, responses, onClose }: Props) {
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

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
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
          background: "var(--color-surface)",
          borderRadius: 14,
          padding: "20px 18px",
          width: "100%",
          maxWidth: 480,
          position: "relative",
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
            color: "var(--color-text-muted)",
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

        {result && !isAlreadyAnswered(result) && (
          <>
            <p style={{ fontWeight: 800, fontSize: 17, margin: "4px 24px 2px 0" }}>{result.anime.title}</p>
            <p className="muted" style={{ margin: "0 0 16px" }}>
              {result.anime.year ?? "―"} /{" "}
              {result.anime.episodes ? `全${result.anime.episodes}話${result.is_ongoing ? "（放送中）" : ""}` : "話数不明"}
            </p>

            <p style={{ fontSize: 19, fontWeight: 800, margin: "0 0 4px", textAlign: "center" }}>
              {result.is_estimated || result.is_ongoing ? "推定 " : ""}
              {relativeRiskText(result.relative_risk)}
            </p>
            <p className="muted" style={{ textAlign: "center", margin: "0 0 6px" }}>
              完走率 {pct(result.completion_prob)}（一般平均 {pct(result.population_completion_rate)}）
            </p>
            <RateBar rate={result.completion_prob} />

            <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center", margin: "12px 0" }}>
              <span style={{ fontSize: 13 }}>{judgmentText(result.completion_prob)}</span>
              <ConfidenceBadge confidence={result.confidence} />
            </div>

            <EstimatedNote isEstimated={result.is_estimated} isOngoing={result.is_ongoing} />

            {(result.factors.negative.length > 0 || result.factors.positive.length > 0) && (
              <div style={{ margin: "14px 0 0", borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
                {result.factors.negative.length > 0 && (
                  <>
                    <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px" }}>▼ 不利な要素</p>
                    <ul style={{ margin: "0 0 10px", paddingLeft: 18, fontSize: 13 }}>
                      {result.factors.negative.map((r, i) => (
                        <li key={i}>{r.text}</li>
                      ))}
                    </ul>
                  </>
                )}
                {result.factors.positive.length > 0 && (
                  <>
                    <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px" }}>▲ 有利な要素</p>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
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
              <div style={{ margin: "14px 0 0", borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
                <p className="section-title">あなたの実績（条件が近い作品）</p>
                {result.evidence.map((e, i) => (
                  <p key={i} style={{ fontSize: 13, margin: "4px 0" }}>
                    {e.title}　全{e.episodes ?? "?"}話・{e.genre ?? "―"}　→{" "}
                    {RESULT_LABEL_JP[e.result] ?? e.result}
                  </p>
                ))}
                {result.evidence_insight && (
                  <p className="muted" style={{ marginTop: 6 }}>
                    → {result.evidence_insight}
                  </p>
                )}
              </div>
            )}

            <div style={{ margin: "14px 0 0", borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
              <SingleAnimeDropoutCurve
                curve={result.dropout_curve ?? []}
                peakEpisode={result.peak_dropout_episode}
                survivalAfterPeak={result.survival_after_peak}
                insufficientData={result.insufficient_data}
              />
              {result.advice && (
                <p className="muted" style={{ marginTop: 4 }}>
                  → {result.advice}
                </p>
              )}
            </div>

            {/* UI仕様書5.5: 完走率80%以上のとき次の導線を出す */}
            {result.next_recommendations.length > 0 && (
              <div style={{ margin: "14px 0 0", borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
                <p className="muted" style={{ margin: "0 0 6px" }}>
                  この作品を完走した人のうち、あなたと傾向が近い層が次に完走している作品
                </p>
                {result.next_recommendations.map((n) => (
                  <p key={n.anime_id} style={{ fontSize: 13, margin: "4px 0" }}>
                    {n.title}　あなたの完走率 {pct(n.completion_prob)}
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
