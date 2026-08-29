import { useNavigate } from "react-router-dom";
import Num from "../components/Num";

/** [A] ランディング画面（UI仕様書2章）。5秒で何をするサービスか伝え、入力画面へ送る。
 * スクロールなしで「はじめる」が見えることが必須要件のため、100dvhのflexで
 * 3ブロック（見出し・訴求・CTA）を配分し、フッターの説明文も画面内に収める。 */
export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        minHeight: "100dvh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: "linear-gradient(160deg, var(--fl-color-primary) 0%, #1e3fae 55%, #172e8a 100%)",
        fontFamily: "var(--fl-font-jp)",
      }}
    >
      <div style={{ padding: "clamp(28px, 8vh, 56px) 24px 0", textAlign: "center" }}>
        <p
          style={{
            margin: 0,
            fontSize: "clamp(22px, 6.5vw, 28px)",
            fontWeight: 800,
            lineHeight: 1.4,
            color: "#fff",
          }}
        >
          その作品、あなたは
          <br />
          最後まで見られますか？
        </p>
      </div>

      <div style={{ padding: "0 24px" }}>
        <div style={{ display: "flex", justifyContent: "center", gap: 10, margin: "0 0 16px" }}>
          <div
            style={{
              background: "rgba(255,255,255,0.94)",
              borderRadius: "var(--fl-radius-md)",
              padding: "8px 18px",
              textAlign: "center",
            }}
          >
            <Num size="lg" color="var(--fl-color-primary-dark)">
              5
            </Num>
            <span style={{ fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-secondary)", marginLeft: 2 }}>
              本選ぶだけ
            </span>
          </div>
          <div
            style={{
              background: "rgba(255,255,255,0.94)",
              borderRadius: "var(--fl-radius-md)",
              padding: "8px 18px",
              textAlign: "center",
            }}
          >
            約
            <Num size="lg" color="var(--fl-color-primary-dark)">
              30
            </Num>
            <span style={{ fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-secondary)", marginLeft: 2 }}>
              秒
            </span>
          </div>
        </div>
        <p
          style={{
            margin: "0 0 28px",
            textAlign: "center",
            fontSize: "var(--fl-text-body)",
            color: "rgba(255,255,255,0.92)",
          }}
        >
          見たことがあるアニメを選ぶだけ。難しい入力はありません。
        </p>

        <button
          type="button"
          onClick={() => navigate("/start")}
          style={{
            display: "block",
            width: "100%",
            minHeight: 52,
            border: "none",
            borderRadius: "var(--fl-radius-pill)",
            background: "#fff",
            color: "var(--fl-color-primary-dark)",
            fontFamily: "var(--fl-font-jp)",
            fontSize: "var(--fl-text-heading)",
            fontWeight: 800,
            boxShadow: "var(--fl-shadow-lg)",
          }}
        >
          はじめる
        </button>
      </div>

      <div
        style={{
          padding: "20px 24px clamp(20px, 5vh, 40px)",
          borderTop: "1px solid rgba(255,255,255,0.22)",
          marginTop: 24,
        }}
      >
        <p
          style={{
            margin: 0,
            textAlign: "center",
            fontSize: "var(--fl-text-body-sm)",
            lineHeight: 1.6,
            color: "rgba(255,255,255,0.82)",
          }}
        >
          <Num size="sm" color="#fff">
            32
          </Num>
          万人の視聴データから、あなたが完走できる作品と、
          <br />
          途中で止まりやすい作品を予測します。
        </p>
      </div>
    </div>
  );
}
