import type { CurvePoint } from "../api/types";

interface Props {
  curve: CurvePoint[];
}

const WIDTH = 320;
const HEIGHT = 160;
const PAD_L = 34;
const PAD_B = 22;
const PAD_T = 10;
const PAD_R = 10;

/** [C] ブロック5: 脱落曲線グラフ。個人曲線(太・濃)と全体平均(細・淡)を必ず重ねる（UI仕様書4.7）。 */
export default function DropoutCurveChart({ curve }: Props) {
  if (curve.length < 2) {
    return (
      <div style={{ margin: "16px 12px" }}>
        <p className="section-title">あなたが完走できる話数</p>
        <p className="muted">もう少し回答すると表示されます</p>
      </div>
    );
  }

  // X軸は実測話数ではなく固定4バケット（EPISODE_BUCKET_DEFS）のインデックスで等間隔に並べる。
  // 実測話数（11, 12, 24, 25, 358話など）だとラベルが不規則に密集・重複するため。
  const sorted = curve;
  const plotW = WIDTH - PAD_L - PAD_R;
  const plotH = HEIGHT - PAD_T - PAD_B;

  const x = (i: number) => (sorted.length <= 1 ? PAD_L : PAD_L + (i / (sorted.length - 1)) * plotW);
  const y = (rate: number) => PAD_T + (1 - rate) * plotH;

  const userPath = sorted.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p.user)}`).join(" ");
  const avgPath = sorted.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p.avg)}`).join(" ");

  const last = sorted[sorted.length - 1];
  const summary =
    last.user < last.avg
      ? `${last.range}まで見ると完走率が${Math.round(last.user * 100)}%まで下がります`
      : `${last.range}まで、平均以上の完走率を維持しています`;

  return (
    <div style={{ margin: "16px 12px" }}>
      <p className="section-title">あなたが完走できる話数</p>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} width="100%" role="img" aria-label="脱落曲線グラフ">
        {[0, 0.5, 1].map((t) => (
          <line
            key={t}
            x1={PAD_L}
            x2={WIDTH - PAD_R}
            y1={y(t)}
            y2={y(t)}
            stroke="var(--color-border)"
            strokeWidth={1}
          />
        ))}
        {[0, 0.5, 1].map((t) => (
          <text key={t} x={PAD_L - 6} y={y(t) + 4} fontSize={9} textAnchor="end" fill="var(--color-text-muted)">
            {Math.round(t * 100)}%
          </text>
        ))}

        {/* 全体平均: 細く・淡く */}
        <path d={avgPath} fill="none" stroke="#9aa5b1" strokeWidth={1.5} strokeDasharray="3 2" />
        {/* 個人曲線: 太く・濃く */}
        <path d={userPath} fill="none" stroke="var(--color-primary)" strokeWidth={3} />

        {sorted.map((p, i) => (
          <circle key={`u${p.range}`} cx={x(i)} cy={y(p.user)} r={3} fill="var(--color-primary)" />
        ))}

        {sorted.map((p, i) => (
          <text
            key={`x${i}`}
            x={x(i)}
            y={HEIGHT - 4}
            fontSize={9}
            textAnchor="middle"
            fill="var(--color-text-muted)"
          >
            {p.range}
          </text>
        ))}
      </svg>
      <div style={{ display: "flex", gap: 14, fontSize: 11, color: "var(--color-text-muted)", marginTop: 2 }}>
        <span>
          <span style={{ display: "inline-block", width: 14, height: 3, background: "var(--color-primary)", marginRight: 4, verticalAlign: "middle" }} />
          あなた
        </span>
        <span>
          <span style={{ display: "inline-block", width: 14, height: 2, background: "#9aa5b1", marginRight: 4, verticalAlign: "middle" }} />
          全体平均
        </span>
      </div>
      <p className="muted" style={{ marginTop: 6 }}>{summary}</p>
    </div>
  );
}
