import { useState } from "react";
import { useGenreJp } from "../state/useGenreJp";

const GENRES = [
  "Action", "Adventure", "Comedy", "Drama", "Fantasy", "Sci-Fi",
  "Slice of Life", "Romance", "Mystery", "Psychological", "Horror",
  "Sports", "School", "Supernatural", "Music", "Shounen", "Shoujo",
  "Seinen", "Military", "Mecha",
];

const YEAR_BUCKETS: { label: string; from?: number; to?: number }[] = [
  { label: "すべて" },
  { label: "〜2005", to: 2005 },
  { label: "2006-2010", from: 2006, to: 2010 },
  { label: "2011-2015", from: 2011, to: 2015 },
  { label: "2016-2020", from: 2016, to: 2020 },
];

const EPISODE_BUCKETS: { label: string; max?: number }[] = [
  { label: "すべて" },
  { label: "〜13話", max: 13 },
  { label: "14〜26話", max: 26 },
];

export interface FilterState {
  genres: string[];
  yearFrom?: number;
  yearTo?: number;
  episodesMax?: number;
}

interface Props {
  value: FilterState;
  onChange: (value: FilterState) => void;
}

export default function FilterBar({ value, onChange }: Props) {
  const [open, setOpen] = useState<"year" | "genre" | "episodes" | null>(null);
  const { jp } = useGenreJp();

  const toggleGenre = (g: string) => {
    const next = value.genres.includes(g)
      ? value.genres.filter((x) => x !== g)
      : [...value.genres, g];
    onChange({ ...value, genres: next });
  };

  const chipLabel = (kind: "year" | "genre" | "episodes") => {
    if (kind === "year") {
      const b = YEAR_BUCKETS.find((b) => b.from === value.yearFrom && b.to === value.yearTo);
      return b?.label ?? "年代";
    }
    if (kind === "episodes") {
      const b = EPISODE_BUCKETS.find((b) => b.max === value.episodesMax);
      return b?.label ?? "話数";
    }
    return value.genres.length > 0 ? `ジャンル(${value.genres.length})` : "ジャンル";
  };

  const hasActiveFilters =
    value.genres.length > 0 || value.yearFrom != null || value.yearTo != null || value.episodesMax != null;

  return (
    <div style={{ padding: "8px 12px 0" }}>
      <div style={{ display: "flex", gap: 8, overflowX: "auto" }}>
        {(["year", "genre", "episodes"] as const).map((kind) => (
          <button
            key={kind}
            type="button"
            onClick={() => setOpen(open === kind ? null : kind)}
            style={{
              flexShrink: 0,
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid var(--color-border)",
              background: open === kind ? "var(--color-primary)" : "var(--color-surface)",
              color: open === kind ? "#fff" : "var(--color-text)",
              fontSize: 12.5,
              fontWeight: 600,
            }}
          >
            {chipLabel(kind)} ▾
          </button>
        ))}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={() => onChange({ genres: [] })}
            style={{
              flexShrink: 0,
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              fontSize: 12.5,
              color: "var(--color-text-muted)",
            }}
          >
            すべてクリア ×
          </button>
        )}
      </div>

      {open === "year" && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "8px 0" }}>
          {YEAR_BUCKETS.map((b) => (
            <button
              key={b.label}
              type="button"
              onClick={() => {
                onChange({ ...value, yearFrom: b.from, yearTo: b.to });
                setOpen(null);
              }}
              style={{
                padding: "6px 10px",
                borderRadius: 8,
                border: "1px solid var(--color-border)",
                background:
                  value.yearFrom === b.from && value.yearTo === b.to ? "#e8f0f9" : "var(--color-surface)",
                fontSize: 12.5,
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      )}

      {open === "episodes" && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "8px 0" }}>
          {EPISODE_BUCKETS.map((b) => (
            <button
              key={b.label}
              type="button"
              onClick={() => {
                onChange({ ...value, episodesMax: b.max });
                setOpen(null);
              }}
              style={{
                padding: "6px 10px",
                borderRadius: 8,
                border: "1px solid var(--color-border)",
                background: value.episodesMax === b.max ? "#e8f0f9" : "var(--color-surface)",
                fontSize: 12.5,
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      )}

      {open === "genre" && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "8px 0" }}>
          {GENRES.map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => toggleGenre(g)}
              style={{
                padding: "6px 10px",
                borderRadius: 8,
                border: "1px solid var(--color-border)",
                background: value.genres.includes(g) ? "#e8f0f9" : "var(--color-surface)",
                fontSize: 12.5,
              }}
            >
              {jp(g)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
