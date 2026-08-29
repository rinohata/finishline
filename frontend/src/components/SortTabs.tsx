import type { SortOption } from "../api/types";

interface Props {
  value: SortOption;
  onChange: (v: SortOption) => void;
}

const TABS: { value: SortOption; label: string }[] = [
  { value: "split_score", label: "おすすめ" },
  { value: "popularity", label: "人気" },
  { value: "low_completion", label: "途中で止まりやすい作品" },
];

/** UI仕様書3.5: low_completionは専用タブとして目立たせる。 */
export default function SortTabs({ value, onChange }: Props) {
  return (
    <div>
      <div style={{ display: "flex", gap: 6, padding: "8px 12px 0" }}>
        {TABS.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => onChange(t.value)}
            style={{
              flex: t.value === "low_completion" ? 1.4 : 1,
              minHeight: 40,
              padding: "8px 6px",
              borderRadius: "var(--fl-radius-sm)",
              border:
                value === t.value
                  ? "1px solid var(--fl-color-primary)"
                  : "1px solid var(--fl-color-border)",
              background: value === t.value ? "var(--fl-color-primary-tint)" : "var(--fl-color-surface)",
              color: value === t.value ? "var(--fl-color-primary-dark)" : "var(--fl-color-text-secondary)",
              fontFamily: "var(--fl-font-jp)",
              fontSize: "var(--fl-text-body-sm)",
              fontWeight: 700,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      {value === "low_completion" && (
        <p
          style={{
            padding: "6px 12px 0",
            margin: 0,
            fontSize: "var(--fl-text-body-sm)",
            color: "var(--fl-color-text-muted)",
          }}
        >
          途中で止まった作品は思い出しにくいもの。よく止まる作品を並べました。
        </p>
      )}
    </div>
  );
}
