import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchQuestions } from "../api/client";
import type { QuestionItem, SortOption } from "../api/types";
import FilterBar, { type FilterState } from "../components/FilterBar";
import FooterCTA from "../components/FooterCTA";
import ProgressBar from "../components/ProgressBar";
import QuestionCard from "../components/QuestionCard";
import SearchBar from "../components/SearchBar";
import SortTabs from "../components/SortTabs";
import { useResponses } from "../state/useResponses";

const PAGE_SIZE = 20;

export default function InputPage() {
  const navigate = useNavigate();
  const { count, getLabel, setLabel } = useResponses();

  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortOption>("split_score");
  const [filters, setFilters] = useState<FilterState>({ genres: [] });

  const [items, setItems] = useState<QuestionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [hasVisitedResults, setHasVisitedResults] = useState(false);

  useEffect(() => {
    setHasVisitedResults(sessionStorage.getItem("finishline_visited_results") === "1");
  }, []);

  const genreKey = filters.genres.join(",");

  const load = useCallback(
    async (offset: number, append: boolean) => {
      setLoading(true);
      setError(false);
      try {
        const res = await fetchQuestions({
          q: query || undefined,
          genre: filters.genres.length ? filters.genres : undefined,
          year_from: filters.yearFrom,
          year_to: filters.yearTo,
          episodes_max: filters.episodesMax,
          sort,
          limit: PAGE_SIZE,
          offset,
        });
        setItems((prev) => (append ? [...prev, ...res.items] : res.items));
        setTotal(res.total);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [query, sort, filters.yearFrom, filters.yearTo, filters.episodesMax, genreKey],
  );

  useEffect(() => {
    load(0, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, sort, filters.yearFrom, filters.yearTo, filters.episodesMax, genreKey]);

  const sentinelRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loading && items.length < total) {
          load(items.length, true);
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [items.length, total, loading, load]);

  const goToResults = () => {
    sessionStorage.setItem("finishline_visited_results", "1");
    navigate("/result");
  };

  return (
    <div className="screen">
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "var(--color-surface)",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        <div style={{ padding: "10px 12px 0" }}>
          <SearchBar onChange={setQuery} />
        </div>
        <SortTabs value={sort} onChange={setSort} />
        <FilterBar value={filters} onChange={setFilters} />
        <ProgressBar count={count} />
      </div>

      {error && (
        <div className="error-banner">
          一時的に判定できませんでした。時間をおいて再度お試しください
          <div>
            <button type="button" onClick={() => load(0, false)}>
              再試行
            </button>
          </div>
        </div>
      )}

      {!error && !loading && items.length === 0 && (
        <p className="muted" style={{ padding: 20, textAlign: "center" }}>
          {query
            ? "該当する作品が見つかりませんでした。2020年までの作品が対象です。"
            : "作品がありません"}
        </p>
      )}

      <div style={{ paddingTop: 12 }}>
        {items.map((item) => (
          <QuestionCard
            key={item.anime_id}
            item={item}
            label={getLabel(item.anime_id)}
            onSelect={(label) => setLabel(item.anime_id, label)}
          />
        ))}
      </div>

      {loading && <p className="loading">読み込み中...</p>}
      <div ref={sentinelRef} style={{ height: 1 }} />

      <FooterCTA count={count} isUpdate={hasVisitedResults} onClick={goToResults} />
    </div>
  );
}
