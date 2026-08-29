import { useEffect, useState } from "react";
import { fetchQuestions } from "../api/client";
import type { QuestionItem, ResponseInput } from "../api/types";
import SingleJudgmentModal from "./SingleJudgmentModal";

interface Props {
  responses: ResponseInput[];
}

/** [C] ブロック1: 単体判定の入力欄。最上部にsticky固定(UI仕様書4.3)。 */
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
          background: "var(--fl-color-surface)",
          borderBottom: "1px solid var(--fl-color-border)",
          padding: "10px 12px",
        }}
      >
        <p
          style={{
            fontSize: "var(--fl-text-body-sm)",
            fontWeight: 700,
            margin: "0 0 6px",
            fontFamily: "var(--fl-font-jp)",
          }}
        >
          この作品、あなたは完走できる？
        </p>
        <div style={{ position: "relative" }}>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="タイトルを入力"
            style={{
              width: "100%",
              padding: "10px 12px",
              borderRadius: "var(--fl-radius-sm)",
              border: "1px solid var(--fl-color-border)",
              fontSize: "var(--fl-text-body)",
              fontFamily: "var(--fl-font-jp)",
            }}
          />
          {candidates.length > 0 && (
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                border: "1px solid var(--fl-color-border)",
                borderRadius: "var(--fl-radius-sm)",
                marginTop: 4,
                overflow: "hidden",
                background: "var(--fl-color-surface)",
                boxShadow: "var(--fl-shadow-md)",
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
                    borderBottom: "1px solid var(--fl-color-border)",
                    background: "var(--fl-color-surface)",
                    fontSize: "var(--fl-text-body-sm)",
                    fontFamily: "var(--fl-font-jp)",
                  }}
                >
                  {c.title}
                  <span style={{ color: "var(--fl-color-text-muted)" }}> {c.year ? `(${c.year})` : ""}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {searched && candidates.length === 0 && value.trim().length >= 2 && (
          <p style={{ marginTop: 4, fontSize: "var(--fl-text-body-sm)", color: "var(--fl-color-text-muted)" }}>
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
