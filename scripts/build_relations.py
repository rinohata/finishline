"""AniListデータセット（calebmwelsh/anilist-anime-dataset, Kaggle）の `relations` から
SEQUEL/PREQUEL 関係だけを抽出し、`data/processed/anime_relations.json` を生成する。

`anime.csv`にはrelated/sequel/prequelに相当する列が無く、Jikan API `/v4/anime/{id}/relations`
は現状 504 が続き実運用に耐えないため（成功率0/10）、AniListのGraphQL由来データセットを採用する。
（詳細は reports/anime_relations_investigation.md を参照）

このスクリプトは実行時に Kaggle API 経由で AniList データセットをダウンロードする
（`~/.kaggle/kaggle.json` の認証情報が必要）。ダウンロード先は data/raw/anilist/ とし、
他の data/raw/ 配下のファイルと同様 .gitignore 対象・生成コード（本スクリプト）はコミットする。

## 抽出ルール
- relationType が SEQUEL または PREQUEL、かつ関連先 node.type == "ANIME" のみを使う
  （SIDE_STORY / SUMMARY / ALTERNATIVE / SPIN_OFF / PARENT / ADAPTATION / CHARACTER 等は除外）
- AniList内部ID → MAL_ID（idMal列）の変換ができたエッジのみを採用する
  （idMalが無い関連作品は無視する。判定不能扱いであり除外エッジとしてログに残す）
- SEQUEL/PREQUELの向きはAniList側のrelationTypeをそのまま使う。
  MAL_IDの大小関係からは絶対に前後を判定しない
  （"To Heart"(472) より "To Heart 2"(471) の方がMAL_IDが小さい実例があるため）
- prequelは複数ありうる（分岐するシリーズ）ため、prequels/sequelsは共にリストとして
  全件保持する。franchise_root はリストの1本道ではなく単一値が必要なため、
  複数prequelがある場合は "MAL_IDが小さい方を辿る" という決定論的だが恣意的な
  タイブレークで1本を選ぶ（これは前後判定ではなく、単に再現可能な分岐選択のためだけの規則）
- 循環参照に備え、再帰の深さは最大20、訪問済みノードを再訪した場合はそこで打ち切る
"""

import json
import subprocess
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
ANILIST_DIR = RAW_DIR / "anilist"
ANILIST_PKL = ANILIST_DIR / "anilist_anime_data_complete.pkl"

TARGET_RELATION_TYPES = {"SEQUEL", "PREQUEL"}
MAX_DEPTH = 20


def log(msg: str) -> None:
    print(f"[build_relations] {msg}", flush=True)


def ensure_anilist_dataset() -> None:
    if ANILIST_PKL.exists():
        log(f"既存のデータセットを再利用: {ANILIST_PKL}")
        return
    ANILIST_DIR.mkdir(parents=True, exist_ok=True)
    log("Kaggleからanilist-anime-datasetをダウンロード中（~/.kaggle/kaggle.json が必要）")
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", "calebmwelsh/anilist-anime-dataset",
         "-p", str(ANILIST_DIR), "--unzip"],
        check=True,
    )
    if not ANILIST_PKL.exists():
        raise FileNotFoundError(f"ダウンロード後もファイルが見つからない: {ANILIST_PKL}")


def load_relations_df() -> pd.DataFrame:
    df = pd.read_pickle(ANILIST_PKL)

    def parse_relations(s):
        if pd.isna(s):
            return []
        try:
            return json.loads(s)
        except Exception:
            return []

    df["relations_parsed"] = df["relations"].apply(parse_relations)
    return df


def build_prequel_graph(df: pd.DataFrame) -> tuple[dict[int, set[int]], dict[int, set[int]], dict]:
    """prequel_of[mal_id] = そのmal_idの前作集合、sequel_of[mal_id] = 続編集合。
    SEQUEL/PREQUELどちらの向きで書かれていても、両方向から同じグラフに正規化して統合する。"""
    id_to_idmal = dict(zip(df["id"], df["idMal"]))

    prequel_of: dict[int, set[int]] = {}
    stats = {"n_edges_seen": 0, "n_edges_used": 0, "n_edges_unresolved": 0, "n_edges_non_anime": 0}

    for _, row in df.iterrows():
        x_idmal = row["idMal"]
        if pd.isna(x_idmal):
            continue
        x = int(x_idmal)
        for edge in row["relations_parsed"]:
            rtype = edge.get("relationType")
            if rtype not in TARGET_RELATION_TYPES:
                continue
            stats["n_edges_seen"] += 1
            node = edge.get("node") or {}
            if node.get("type") != "ANIME":
                stats["n_edges_non_anime"] += 1
                continue
            y_idmal = id_to_idmal.get(node.get("id"))
            if y_idmal is None or pd.isna(y_idmal):
                stats["n_edges_unresolved"] += 1
                continue
            y = int(y_idmal)
            if x == y:
                continue
            stats["n_edges_used"] += 1
            if rtype == "SEQUEL":
                # x の続編が y -> y の前作は x
                prequel_of.setdefault(y, set()).add(x)
            else:  # PREQUEL
                # x の前作が y
                prequel_of.setdefault(x, set()).add(y)

    sequel_of: dict[int, set[int]] = {}
    for child, parents in prequel_of.items():
        for parent in parents:
            sequel_of.setdefault(parent, set()).add(child)

    return prequel_of, sequel_of, stats


def compute_franchise_root(mal_id: int, prequel_of: dict[int, set[int]]) -> tuple[int, bool]:
    """PREQUELを再帰的に辿った最上流を返す。分岐時はMAL_IDが小さい方を辿る
    （前後判定ではなく、単に再現可能にするための決定論的タイブレーク）。
    循環参照を検知した場合は (現在地, True) を返す。"""
    visited = {mal_id}
    current = mal_id
    for _ in range(MAX_DEPTH):
        parents = prequel_of.get(current)
        if not parents:
            return current, False
        nxt = min(parents)
        if nxt in visited:
            return current, True  # 循環参照
        visited.add(nxt)
        current = nxt
    return current, True  # 深さ上限到達（実質的に循環扱いで打ち切り）


def main() -> None:
    ensure_anilist_dataset()
    log("AniListデータセットを読み込み中")
    df = load_relations_df()
    log(f"{len(df):,}件のうちidMal充足 {df['idMal'].notna().sum():,}件")

    prequel_of, sequel_of, stats = build_prequel_graph(df)
    log(f"SEQUEL/PREQUELエッジ: 検出={stats['n_edges_seen']:,} 採用={stats['n_edges_used']:,} "
        f"非ANIME除外={stats['n_edges_non_anime']:,} idMal未解決={stats['n_edges_unresolved']:,}")

    all_ids = set(prequel_of.keys()) | set(sequel_of.keys())
    log(f"relations対象作品数: {len(all_ids):,}")

    n_multi_prequel = sum(1 for v in prequel_of.values() if len(v) > 1)
    log(f"prequelが複数あるタイトル数: {n_multi_prequel:,} "
        f"(franchise_root計算ではMAL_IDが小さい方を決定論的に辿る)")

    n_cycles = 0
    result = {}
    for mal_id in sorted(all_ids):
        root, is_cycle_or_capped = compute_franchise_root(mal_id, prequel_of)
        if is_cycle_or_capped:
            n_cycles += 1
        result[str(mal_id)] = {
            "sequels": sorted(sequel_of.get(mal_id, set())),
            "prequels": sorted(prequel_of.get(mal_id, set())),
            "franchise_root": root,
        }
    log(f"循環参照/深さ上限で打ち切ったタイトル数: {n_cycles:,}")

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROC_DIR / "anime_relations.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"saved: {out_path} ({len(result):,}件)")


if __name__ == "__main__":
    main()
