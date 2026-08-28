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
        background: "var(--color-surface)",
        borderTop: "1px solid var(--color-border)",
      }}
    >
      <button
        type="button"
        onClick={onClick}
        style={{
          width: "100%",
          padding: "14px",
          borderRadius: 10,
          border: "none",
          background: "var(--color-primary)",
          color: "#fff",
          fontSize: 15,
          fontWeight: 700,
        }}
      >
        {isUpdate ? `結果を更新（${count}本）` : `結果を見る（${count}本）`}
      </button>
    </div>
  );
}
