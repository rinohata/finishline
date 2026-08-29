import { useEffect, useState } from "react";
import { fetchGenres } from "../api/client";

let cache: Record<string, string> | null = null;
let inflight: Promise<Record<string, string>> | null = null;

function load(): Promise<Record<string, string>> {
  if (cache) return Promise.resolve(cache);
  if (!inflight) {
    inflight = fetchGenres()
      .then((map) => {
        cache = map;
        return map;
      })
      .catch(() => ({}));
  }
  return inflight;
}

/**
 * 英語ジャンル名 -> 日本語表記の変換。`GET /genres`（api/services/genres.py が
 * 唯一の翻訳表）を初回マウント時に1回だけ取得し、以降はモジュールスコープの
 * キャッシュを共有する。取得が終わるまでは元の英語表記をそのまま返す。
 */
export function useGenreJp() {
  const [map, setMap] = useState<Record<string, string>>(cache ?? {});

  useEffect(() => {
    if (cache) return;
    load().then(setMap);
  }, []);

  const jp = (genre: string): string => map[genre] ?? genre;

  return { jp, map };
}
