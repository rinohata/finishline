import { useEffect, useState } from "react";

interface Props {
  onChange: (q: string) => void;
}

/** タイトル検索。2文字以上で300msデバウンス（UI仕様書3.3）。 */
export default function SearchBar({ onChange }: Props) {
  const [value, setValue] = useState("");

  useEffect(() => {
    const trimmed = value.trim();
    const handle = setTimeout(() => {
      onChange(trimmed.length >= 2 ? trimmed : "");
    }, 300);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        border: "1px solid var(--fl-color-border)",
        borderRadius: "var(--fl-radius-sm)",
        background: "var(--fl-color-surface)",
        padding: "8px 12px",
      }}
    >
      <span aria-hidden>🔍</span>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="タイトルを検索"
        style={{
          flex: 1,
          border: "none",
          outline: "none",
          fontSize: "var(--fl-text-body)",
          fontFamily: "var(--fl-font-jp)",
          background: "transparent",
          color: "var(--fl-color-text)",
        }}
      />
    </div>
  );
}
