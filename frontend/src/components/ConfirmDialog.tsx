import { useEffect } from "react";

interface Props {
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** 破壊的操作の前に挟む確認ダイアログ（UI仕様書3.9）。誤タップでの取り返しのつかない
 * 操作（回答の全解除など）を防ぐため、必ずこのコンポーネントを経由すること。 */
export default function ConfirmDialog({ message, confirmLabel, onConfirm, onCancel }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onCancel}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,23,42,0.5)",
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 12,
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
          maxWidth: 320,
          fontFamily: "var(--fl-font-jp)",
        }}
      >
        <p style={{ margin: "0 0 16px", fontSize: "var(--fl-text-body)", fontWeight: 700, textAlign: "center" }}>
          {message}
        </p>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={onCancel}
            style={{
              flex: 1,
              minHeight: 44,
              padding: "10px 0",
              borderRadius: "var(--fl-radius-sm)",
              border: "1px solid var(--fl-color-border)",
              background: "var(--fl-color-surface)",
              color: "var(--fl-color-text)",
              fontFamily: "var(--fl-font-jp)",
              fontSize: "var(--fl-text-body-sm)",
              fontWeight: 700,
            }}
          >
            キャンセル
          </button>
          <button
            type="button"
            onClick={onConfirm}
            style={{
              flex: 1,
              minHeight: 44,
              padding: "10px 0",
              borderRadius: "var(--fl-radius-sm)",
              border: "1px solid var(--fl-color-warning)",
              background: "var(--fl-color-warning)",
              color: "#fff",
              fontFamily: "var(--fl-font-jp)",
              fontSize: "var(--fl-text-body-sm)",
              fontWeight: 700,
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
