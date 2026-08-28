import { useEffect, useState } from "react";
import { fetchQuestions } from "../api/client";
import type { QuestionItem, ResponseInput } from "../api/types";
import SingleJudgmentModal from "./SingleJudgmentModal";

interface Props {
  responses: ResponseInput[];
}

/** [C] ブロック1: 単体判定の入力欄。最上部にsticky固定（UI仕様書4.3）。 */
export default function SingleJudgmentBlock({ responses }: Props) {
  const [value, setValue] = useState("");
  const [candidates, setCandidates] = useState<QuestionItem[]>([]);
  const [searched, setSearched] = useState(false);
  const [activeId, setActiveId] = useState<number | null>(null);

  useEffect(() => {
    const trimmed = value.trim();
    if (trimmed.length < 2) {
      setCandidates([]);
      setSearched(false);
      return;
    }
    const handle = setTimeout(() => {
      fetchQuestions({ q: trimmed, limit: 8 })
        .then((res) => setCandidates(res.items))
        .catch(() => setCandidates([]))
        .finally(() => setSearched(true));
    }, 300);
    return () => clearTimeout(handle);
  }, [value]);

  const select = (item: QuestionItem) => {
    setActiveId(item.anime_id);
    setValue("");
    setCandidates([]);
    setSearched(false);
  };

  return (
    <>
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          background: "var(--color-surface)",
          borderBottom: "1px solid var(--color-border)",
          padding: "10px 12px",
        }}
      >
        <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 6px" }}>この作品、あなたは完走できる？</p>
        <div style={{ position: "relative" }}>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="タイトルを入力"
            style={{
              width: "100%",
              padding: "10px 12px",
              borderRadius: 8,
              border: "1px solid var(--color-border)",
              fontSize: 14,
            }}
          />
          {candidates.length > 0 && (
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                marginTop: 4,
                overflow: "hidden",
                background: "var(--color-surface)",
                boxShadow: "0 4px 10px rgba(0,0,0,0.08)",
              }}
            >
              {candidates.map((c) => (
                <button
                  key={c.anime_id}
                  type="button"
                  onClick={() => select(c)}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    padding: "8px 10px",
                    border: "none",
                    borderBottom: "1px solid var(--color-border)",
                    background: "var(--color-surface)",
                    fontSize: 13,
                  }}
                >
                  {c.title}
                  <span className="muted"> {c.year ? `(${c.year})` : ""}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {searched && candidates.length === 0 && value.trim().length >= 2 && (
          <p className="muted" style={{ marginTop: 4 }}>
            該当する作品が見つかりませんでした。2020年までの作品が対象です。
          </p>
        )}
      </div>

      {activeId != null && (
        <SingleJudgmentModal animeId={activeId} responses={responses} onClose={() => setActiveId(null)} />
      )}
    </>
  );
}
