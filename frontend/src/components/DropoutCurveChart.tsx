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

const NUMERIC_STYLE = { fontFamily: "var(--fl-font-numeric)" };

/** [C] ブロック5: 脱落曲線グラフ。個人曲線(太・濃)と全体平均(細・淡)を必ず重ねる（UI仕様書4.7）。
 * 曲線そのものはデータの可視化なので装飾を加えない。カードのパッケージ（背景・影・角丸）
 * のみカラフル化の対象。 */
export default function DropoutCurveChart({ curve }: Props) {
  if (curve.length < 2) {
    return (
      <div
        style={{
          margin: "16px 12px",
          background: "var(--fl-color-surface)",
          borderRadius: "var(--fl-radius-md)",
          boxShadow: "var(--fl-shadow-sm)",
          padding: "16px",
        }}
      >
        <p style={{ margin: "0 0 4px", fontSize: "var(--fl-text-heading)", fontWeight: 800, fontFamily: "var(--fl-font-jp)" }}>
          あなたが完走できる話数
        </p>
        <p style={{ fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
          もう少し回答すると表示されます
        </p>
      </div>
    );
  }

  // X軸は実測話数ではなく固定バケット（EPISODE_BUCKET_DEFS）のインデックスで等間隔に並べる。
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
    <div
      style={{
        margin: "16px 12px",
        background: "var(--fl-color-surface)",
        borderRadius: "var(--fl-radius-md)",
        boxShadow: "var(--fl-shadow-sm)",
        padding: "16px",
      }}
    >
      <p style={{ margin: "0 0 10px", fontSize: "var(--fl-text-heading)", fontWeight: 800, fontFamily: "var(--fl-font-jp)" }}>
        あなたが完走できる話数
      </p>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} width="100%" role="img" aria-label="脱落曲線グラフ">
        {[0, 0.5, 1].map((t) => (
          <line
            key={t}
            x1={PAD_L}
            x2={WIDTH - PAD_R}
            y1={y(t)}
            y2={y(t)}
            stroke="var(--fl-color-border)"
            strokeWidth={1}
          />
        ))}
        {[0, 0.5, 1].map((t) => (
          <text
            key={t}
            x={PAD_L - 6}
            y={y(t) + 4}
            fontSize={9}
            textAnchor="end"
            fill="var(--fl-color-text-muted)"
            style={NUMERIC_STYLE}
          >
            {Math.round(t * 100)}%
          </text>
        ))}

        {/* 全体平均: 細く・淡く */}
        <path d={avgPath} fill="none" stroke="#a7b0c0" strokeWidth={1.5} strokeDasharray="3 2" />
        {/* 個人曲線: 太く・濃く */}
        <path d={userPath} fill="none" stroke="var(--fl-color-primary)" strokeWidth={3} />

        {sorted.map((p, i) => (
          <circle key={`u${p.range}`} cx={x(i)} cy={y(p.user)} r={3.5} fill="var(--fl-color-primary)" />
        ))}

        {sorted.map((p, i) => (
          <text
            key={`x${i}`}
            x={x(i)}
            y={HEIGHT - 4}
            fontSize={9}
            textAnchor="middle"
            fill="var(--fl-color-text-muted)"
            fontFamily="var(--fl-font-jp)"
          >
            {p.range}
          </text>
        ))}
      </svg>
      <div style={{ display: "flex", gap: 14, fontSize: "var(--fl-text-caption)", color: "var(--fl-color-text-muted)", marginTop: 2 }}>
        <span>
          <span style={{ display: "inline-block", width: 14, height: 3, background: "var(--fl-color-primary)", marginRight: 4, verticalAlign: "middle" }} />
          あなた
        </span>
        <span>
          <span style={{ display: "inline-block", width: 14, height: 2, background: "#a7b0c0", marginRight: 4, verticalAlign: "middle" }} />
          全体平均
        </span>
      </div>
      <p style={{ marginTop: 6, fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-secondary)" }}>{summary}</p>
    </div>
  );
}
