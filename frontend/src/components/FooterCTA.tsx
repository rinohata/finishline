import Num from "./Num";

interface Props {
  count: number;
  isUpdate: boolean;
  onClick: () => void;
}

/** UI仕様書3.7: 4本以下は非表示、5本以上で固定表示。 */
export default function FooterCTA({ count, isUpdate, onClick }: Props) {
  if (count < 5) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: "50%",
        transform: "translateX(-50%)",
        width: "100%",
        maxWidth: 720,
        padding: 12,
        background: "var(--fl-color-surface)",
        borderTop: "1px solid var(--fl-color-border)",
        boxShadow: "var(--fl-shadow-lg)",
      }}
    >
      <button
        type="button"
        onClick={onClick}
        style={{
          width: "100%",
          minHeight: 48,
          padding: "14px",
          borderRadius: "var(--fl-radius-md)",
          border: "none",
          background: "var(--fl-color-primary)",
          color: "#fff",
          fontFamily: "var(--fl-font-jp)",
          fontSize: "var(--fl-text-body)",
          fontWeight: 800,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 4,
        }}
      >
        {isUpdate ? "結果を更新" : "結果を見る"}（<Num size="sm" color="#fff">{count}</Num>本）
      </button>
    </div>
  );
}
