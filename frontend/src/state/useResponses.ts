import { useCallback, useEffect, useState } from "react";
import type { Label, ResponseInput } from "../api/types";

const STORAGE_KEY = "finishline_responses_v1";

function load(): ResponseInput[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

function save(responses: ResponseInput[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(responses));
  } catch {
    // ストレージが使えない環境でもクラッシュさせない
  }
}

/**
 * ユーザーの回答（好き/完走/途中で止まった）を localStorage に保持するフック。
 * リロード・画面遷移をまたいで保持される（UI仕様書3.8）。
 */
export function useResponses() {
  const [responses, setResponses] = useState<ResponseInput[]>(() => load());

  useEffect(() => {
    save(responses);
  }, [responses]);

  // 他タブでの変更にも追従
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setResponses(load());
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const getLabel = useCallback(
    (animeId: number): Label | null => {
      return responses.find((r) => r.anime_id === animeId)?.label ?? null;
    },
    [responses],
  );

  // 同じボタンを再度押すと選択解除（UI仕様書3.2）
  const setLabel = useCallback((animeId: number, label: Label) => {
    setResponses((prev) => {
      const existing = prev.find((r) => r.anime_id === animeId);
      if (existing?.label === label) {
        return prev.filter((r) => r.anime_id !== animeId);
      }
      const rest = prev.filter((r) => r.anime_id !== animeId);
      return [...rest, { anime_id: animeId, label }];
    });
  }, []);

  return { responses, count: responses.length, getLabel, setLabel };
}
