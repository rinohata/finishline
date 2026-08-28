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
              padding: "8px 6px",
              borderRadius: 8,
              border:
                value === t.value ? "1px solid var(--color-primary)" : "1px solid var(--color-border)",
              background: value === t.value ? "#e8f0f9" : "var(--color-surface)",
              color: value === t.value ? "var(--color-primary-dark)" : "var(--color-text)",
              fontSize: 12.5,
              fontWeight: 600,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      {value === "low_completion" && (
        <p className="muted" style={{ padding: "6px 12px 0", margin: 0 }}>
          途中で止まった作品は思い出しにくいもの。よく止まる作品を並べました。
        </p>
      )}
    </div>
  );
}
