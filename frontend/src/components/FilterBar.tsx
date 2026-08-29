import type { CSSProperties } from "react";
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

const chipStyle = (active: boolean): CSSProperties => ({
  flexShrink: 0,
  minHeight: 32,
  padding: "6px 12px",
  borderRadius: "var(--fl-radius-pill)",
  border: active ? "1px solid var(--fl-color-primary)" : "1px solid var(--fl-color-border)",
  background: active ? "var(--fl-color-primary)" : "var(--fl-color-surface)",
  color: active ? "#fff" : "var(--fl-color-text-secondary)",
  fontFamily: "var(--fl-font-jp)",
  fontSize: "var(--fl-text-body-sm)",
  fontWeight: 700,
});

const optionStyle = (active: boolean): CSSProperties => ({
  padding: "6px 10px",
  borderRadius: "var(--fl-radius-sm)",
  border: active ? "1px solid var(--fl-color-primary)" : "1px solid var(--fl-color-border)",
  background: active ? "var(--fl-color-primary-tint)" : "var(--fl-color-surface)",
  color: active ? "var(--fl-color-primary-dark)" : "var(--fl-color-text-secondary)",
  fontFamily: "var(--fl-font-jp)",
  fontSize: "var(--fl-text-body-sm)",
  fontWeight: 600,
});

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
          <button key={kind} type="button" onClick={() => setOpen(open === kind ? null : kind)} style={chipStyle(open === kind)}>
            {chipLabel(kind)} ▾
          </button>
        ))}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={() => onChange({ genres: [] })}
            style={{
              flexShrink: 0,
              minHeight: 32,
              padding: "6px 12px",
              borderRadius: "var(--fl-radius-pill)",
              border: "1px solid var(--fl-color-border)",
              background: "var(--fl-color-surface)",
              fontFamily: "var(--fl-font-jp)",
              fontSize: "var(--fl-text-body-sm)",
              color: "var(--fl-color-text-muted)",
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
              style={optionStyle(value.yearFrom === b.from && value.yearTo === b.to)}
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
              style={optionStyle(value.episodesMax === b.max)}
            >
              {b.label}
            </button>
          ))}
        </div>
      )}

      {open === "genre" && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "8px 0" }}>
          {GENRES.map((g) => (
            <button key={g} type="button" onClick={() => toggleGenre(g)} style={optionStyle(value.genres.includes(g))}>
              {jp(g)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
