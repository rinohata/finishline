import type { DropoutCurvePoint } from "../api/types";

interface Props {
  curve: DropoutCurvePoint[];
  peakEpisode: number | null;
  survivalAfterPeak: number | null;
  insufficientData: boolean;
}

const WIDTH = 320;
const HEIGHT = 140;
const PAD_L = 30;
const PAD_B = 20;
const PAD_T = 10;
const PAD_R = 10;

/**
 * [D] 5.4 脱落曲線ブロック。insufficient_data（離脱者50件未満、またはhas_meaningful_peakがfalse）の
 * 場合はグラフ本体を非表示にし、「この作品はデータが少なく、止まりやすい話数を表示できません」と表示する。
 */
export default function SingleAnimeDropoutCurve({
  curve,
  peakEpisode,
  survivalAfterPeak,
  insufficientData,
}: Props) {
  if (insufficientData || !curve || curve.length === 0) {
    return (
      <div style={{ margin: "16px 0" }}>
        <p className="muted">📉 この作品はデータが少なく、止まりやすい話数を表示できません</p>
      </div>
    );
  }

  const maxRate = Math.max(...curve.map((p) => p.rate), 0.0001);
  const maxEp = curve[curve.length - 1].episode;
  const plotW = WIDTH - PAD_L - PAD_R;
  const plotH = HEIGHT - PAD_T - PAD_B;
  const barW = Math.max(plotW / curve.length - 1, 1);

  const x = (ep: number) => PAD_L + (ep / maxEp) * plotW;
  const y = (rate: number) => PAD_T + (1 - rate / maxRate) * plotH;

  return (
    <div style={{ margin: "16px 0" }}>
      <p className="section-title">📉 この作品で人が止まりやすい話数</p>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} width="100%" role="img" aria-label="話数別の離脱傾向">
        {curve.map((p) => (
          <rect
            key={p.episode}
            x={x(p.episode) - barW / 2}
            y={y(p.rate)}
            width={barW}
            height={PAD_T + plotH - y(p.rate)}
            fill={p.episode === 1 ? "#c9ced6" : p.episode === peakEpisode ? "var(--color-accent)" : "#9ec3e3"}
          />
        ))}
        {curve
          .filter((_, i) => i % Math.ceil(curve.length / 6) === 0)
          .map((p) => (
            <text
              key={`x${p.episode}`}
              x={x(p.episode)}
              y={HEIGHT - 4}
              fontSize={9}
              textAnchor="middle"
              fill="var(--color-text-muted)"
            >
              {p.episode}話
            </text>
          ))}
      </svg>
      {peakEpisode != null && survivalAfterPeak != null && (
        <p className="muted" style={{ marginTop: 4 }}>
          {peakEpisode}話で止まる人が最多。ここを越えた人の{Math.round(survivalAfterPeak * 100)}%は最後まで見ています。
        </p>
      )}
      {curve.some((p) => p.episode === 1) && (
        <p className="muted" style={{ marginTop: 2, fontSize: 11 }}>
          ※ 1話（様子見離脱のため除外）はグレーで表示しています
        </p>
      )}
    </div>
  );
}
