import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { postPredict } from "../api/client";
import type { PredictResponse } from "../api/types";
import AtRiskBlock from "../components/AtRiskBlock";
import BaselineComparisonBlock from "../components/BaselineComparisonBlock";
import DropoutCurveChart from "../components/DropoutCurveChart";
import { InfoIcon } from "../components/icons";
import SingleJudgmentBlock from "../components/SingleJudgmentBlock";
import TypeDiagnosisCard from "../components/TypeDiagnosisCard";
import WillCompleteBlock from "../components/WillCompleteBlock";
import { useResponses } from "../state/useResponses";

export default function ResultPage() {
  const navigate = useNavigate();
  const { responses, count } = useResponses();
  const [data, setData] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // UI仕様書7章: 回答5本未満で結果画面に直接アクセス → 入力画面へリダイレクト
  useEffect(() => {
    if (count < 5) {
      navigate("/", { replace: true });
    }
  }, [count, navigate]);

  const load = () => {
    if (count < 5) return;
    setLoading(true);
    setError(false);
    postPredict(responses)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (count < 5) return null;

  // UI仕様書7章のエッジケース: 離脱データ0件／完走データ0件のときは精度が限定的である旨を注記する
  const hasDropped = responses.some((r) => r.label === "dropped");
  const hasCompleted = responses.some((r) => r.label === "completed" || r.label === "loved");

  return (
    <div className="screen">
      {/* ブロック1: 単体判定入力（最上部・sticky固定、UI仕様書4.1・4.3） */}
      <SingleJudgmentBlock responses={responses} />

      <div style={{ padding: "16px 12px 0" }}>
        <button
          type="button"
          onClick={() => navigate("/")}
          style={{
            border: "none",
            background: "none",
            color: "var(--fl-color-primary)",
            fontSize: "var(--fl-text-body-sm)",
            fontFamily: "var(--fl-font-jp)",
            padding: 0,
          }}
        >
          ← 回答を追加する
        </button>
      </div>

      {!hasDropped && (
        <p
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 6,
            margin: "8px 12px 0",
            fontSize: "var(--fl-text-body-sm)",
            color: "var(--fl-color-text-muted)",
          }}
        >
          <span style={{ flexShrink: 0, marginTop: 2 }}>
            <InfoIcon size={13} />
          </span>
          途中で止まった作品の情報がないため、精度が限定的です
        </p>
      )}
      {!hasCompleted && (
        <p
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 6,
            margin: "8px 12px 0",
            fontSize: "var(--fl-text-body-sm)",
            color: "var(--fl-color-text-muted)",
          }}
        >
          <span style={{ flexShrink: 0, marginTop: 2 }}>
            <InfoIcon size={13} />
          </span>
          完走した作品の情報がないため、精度が限定的です
        </p>
      )}

      {loading && <p className="loading">診断中...</p>}

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

      {data && (
        <>
          {/* ブロック2: タイプ診断カード */}
          <TypeDiagnosisCard profile={data.profile} />
          {/* ブロック3: 話題作だけど続かないかも【本体】 */}
          <AtRiskBlock items={data.at_risk} />
          {/* ブロック4: 完走できる作品 */}
          <WillCompleteBlock items={data.will_complete} />
          {/* ブロック5: 脱落曲線グラフ */}
          <DropoutCurveChart curve={data.profile.curve} />
          {/* ブロック6: 人気順との比較 */}
          <BaselineComparisonBlock data={data.baseline_comparison} />
        </>
      )}
    </div>
  );
}
