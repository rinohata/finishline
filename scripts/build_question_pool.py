"""data/question_pool.json を、話数レンジ別の最低本数を保証した形で再生成する。

## 経緯
旧選定ロジック（notebooks/01_aggregation.ipynb）は、split_score（完走率0.5に近いほど
高スコアになるエントロピー指標）優先の貪欲法に「話数レンジの上限キャップ」しか
持たせておらず、下限保証が無かった。完走率0.5付近を優先すると完走率の低い長編が
選ばれにくいため、結果として250本中「27〜50話」9本(3.6%)・「51話〜」31本(12.4%)
しかなく、ユーザーが20本回答してもこの2レンジの分母が構造的に3本を切っていた
（reports/question_pool_episode_rebalance.md 参照）。

## 新選定ロジック
1. 登録者数（anime.csv Members列）上位3,000件から選定母集団を作る
   （Type: Movie/Music/Special/Unknown除外、年代・話数・ジャンル・タイトル欠損は除外）
2. 登録者数上位200位以内から上位50本を無条件確保（認知度の担保。従来通り）
3. 話数4レンジそれぞれで最低本数を保証する（reserved分もレンジ内カウントに含む）:
   〜13話 60本 / 14〜26話 60本 / 27〜50話 50本 / 51話〜 50本
   （希少なレンジ＝候補数が少ないレンジから先に埋め、ジャンル・年代の分散上限
   （genre_cap/year_cap）を候補数の多いレンジに食い潰されないようにする。
   上限内で埋まりきらない場合は上限を外した補充パスで必ず本数を満たす）
4. 残り30本は話数レンジを問わず split_score 降順で自由選定（従来の多様化ロジックを流用）

completion_rate・split_score は data/processed/anime_population_completion_rate_B.json
（scripts/build_lookups.py の出力、定義B・全作品分）を使う。
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
ANIME_PATH = RAW_DIR / "anime.csv"

EXCLUDED_TYPES = {"Movie", "Music", "Special", "Unknown"}
TOP_N_POPULARITY = 3000
RESERVED_TOP_N = 200
RESERVED_COUNT = 50
TARGET_SIZE = 250

EPISODE_BUCKETS: list[tuple[float, float, str, int]] = [
    # (下限, 上限, ラベル, 最低本数)
    (1, 13, "〜13話", 60),
    (14, 26, "14〜26話", 60),
    (27, 50, "27〜50話", 50),
    (51, float("inf"), "51話〜", 50),
]

GENRE_CAP = max(10, TARGET_SIZE // 8)
YEAR_CAP = max(20, TARGET_SIZE // 3)


def log(msg: str) -> None:
    print(f"[build_question_pool] {msg}", flush=True)


def episode_bucket_label(ep: float) -> str:
    for lo, hi, label, _min_count in EPISODE_BUCKETS:
        if lo <= ep <= hi:
            return label
    return "〜13話"  # 保険（通常到達しない）


def year_bucket(y: int) -> str:
    if y <= 2005:
        return "~2005"
    if y <= 2010:
        return "2006-2010"
    if y <= 2015:
        return "2011-2015"
    return "2016-2020"


def entropy(p: float) -> float:
    if p <= 0 or p >= 1:
        return 0.0
    return float(-p * np.log2(p) - (1 - p) * np.log2(1 - p))


def load_pool_src() -> pd.DataFrame:
    anime = pd.read_csv(ANIME_PATH, usecols=[
        "MAL_ID", "Name", "Japanese name", "Genres", "Episodes", "Aired", "Type", "Members",
    ])
    anime = anime.rename(columns={"MAL_ID": "anime_id"})

    import re

    def extract_year(aired):
        m = re.search(r"(19|20)\d{2}", str(aired))
        return int(m.group()) if m else None

    anime["year"] = anime["Aired"].apply(extract_year)
    anime["episodes_num"] = pd.to_numeric(anime["Episodes"], errors="coerce")
    anime["title"] = anime["Japanese name"].where(
        anime["Japanese name"].notna() & (anime["Japanese name"] != "Unknown"), anime["Name"]
    )
    anime["genre_list"] = anime["Genres"].apply(
        lambda s: [g.strip() for g in str(s).split(",")] if pd.notna(s) else []
    )
    anime["members_num"] = pd.to_numeric(anime["Members"], errors="coerce")

    pop_b = json.load(open(PROC_DIR / "anime_population_completion_rate_B.json", encoding="utf-8"))
    pop_b = {int(k): v for k, v in pop_b.items()}
    anime["completion_rate"] = anime["anime_id"].map(pop_b)

    pool_src = anime[~anime["Type"].isin(EXCLUDED_TYPES)]
    pool_src = pool_src[pool_src["year"].notna()]
    pool_src = pool_src[pool_src["episodes_num"].notna() & (pool_src["episodes_num"] > 0)]
    pool_src = pool_src[pool_src["genre_list"].apply(len) > 0]
    pool_src = pool_src[pool_src["title"].notna()]
    pool_src = pool_src[pool_src["completion_rate"].notna()]
    log(f"品質フィルタ後: {len(pool_src):,}件")

    pool_src = pool_src.sort_values("members_num", ascending=False).head(TOP_N_POPULARITY).reset_index(drop=True)
    log(f"登録者数上位{TOP_N_POPULARITY}件に絞り込み: {len(pool_src):,}件")

    pool_src["split_score"] = pool_src["completion_rate"].apply(entropy)
    pool_src["year_bucket"] = pool_src["year"].astype(int).apply(year_bucket)
    pool_src["episode_bucket"] = pool_src["episodes_num"].apply(episode_bucket_label)
    pool_src["primary_genre"] = pool_src["genre_list"].apply(lambda g: g[0] if g else "unknown")
    return pool_src


def main() -> None:
    pool_src = load_pool_src()

    top_pool = pool_src.head(RESERVED_TOP_N)
    reserved = top_pool.head(RESERVED_COUNT).copy()
    log(f"登録者数上位{RESERVED_TOP_N}件から無条件確保: {len(reserved)}件")
    log("  reserved の話数レンジ内訳:\n" + reserved["episode_bucket"].value_counts().to_string())

    selected_ids: set[int] = set(reserved["anime_id"])
    genre_count: dict[str, int] = {}
    year_count: dict[str, int] = {}
    for _, row in reserved.iterrows():
        genre_count[row["primary_genre"]] = genre_count.get(row["primary_genre"], 0) + 1
        year_count[row["year_bucket"]] = year_count.get(row["year_bucket"], 0) + 1

    def try_add(row) -> bool:
        if row["anime_id"] in selected_ids:
            return False
        if genre_count.get(row["primary_genre"], 0) >= GENRE_CAP:
            return False
        if year_count.get(row["year_bucket"], 0) >= YEAR_CAP:
            return False
        selected_ids.add(row["anime_id"])
        genre_count[row["primary_genre"]] = genre_count.get(row["primary_genre"], 0) + 1
        year_count[row["year_bucket"]] = year_count.get(row["year_bucket"], 0) + 1
        return True

    def force_add(row) -> bool:
        if row["anime_id"] in selected_ids:
            return False
        selected_ids.add(row["anime_id"])
        genre_count[row["primary_genre"]] = genre_count.get(row["primary_genre"], 0) + 1
        year_count[row["year_bucket"]] = year_count.get(row["year_bucket"], 0) + 1
        return True

    # 候補数が少ないレンジ（希少）から先に埋める。ジャンル/年代の分散上限を
    # 候補が豊富な短編レンジに先に食い潰されないようにするため。
    buckets_by_scarcity = sorted(
        EPISODE_BUCKETS,
        key=lambda b: len(pool_src[pool_src["episode_bucket"] == b[2]]),
    )

    for lo, hi, label, min_count in buckets_by_scarcity:
        bucket_df = pool_src[pool_src["episode_bucket"] == label].sort_values(
            ["split_score", "members_num"], ascending=[False, False]
        )
        current = sum(1 for aid in selected_ids if aid in set(bucket_df["anime_id"]))
        need = min_count - current
        if need <= 0:
            log(f"{label}: reservedのみで最低本数({min_count})を満たしている（現在{current}件）")
            continue

        n_added_capped = 0
        for _, row in bucket_df.iterrows():
            if need <= 0:
                break
            if try_add(row):
                need -= 1
                n_added_capped += 1
        n_added_forced = 0
        if need > 0:
            log(f"{label}: 分散上限内では{n_added_capped}件しか追加できず、"
                f"残り{need}件は上限を外した補充パスで満たす")
            for _, row in bucket_df.iterrows():
                if need <= 0:
                    break
                if force_add(row):
                    need -= 1
                    n_added_forced += 1
        total_in_bucket = sum(1 for aid in selected_ids if aid in set(bucket_df["anime_id"]))
        log(f"{label}: reserved={current} +上限内={n_added_capped} +補充={n_added_forced} "
            f"→ 計{total_in_bucket}件（候補プール内 {len(bucket_df)}件）")

    n_guaranteed = len(selected_ids)
    log(f"レンジ最低本数保証フェーズ終了: 計{n_guaranteed}件選定済み")

    # 残り枠を split_score 降順で自由選定（話数レンジ不問）
    remaining_target = TARGET_SIZE - n_guaranteed
    log(f"残り{remaining_target}件を split_score ベースで自由選定")
    free_candidates = pool_src[~pool_src["anime_id"].isin(selected_ids)].sort_values(
        ["split_score", "members_num"], ascending=[False, False]
    )
    n_free_capped = 0
    for _, row in free_candidates.iterrows():
        if remaining_target <= 0:
            break
        if try_add(row):
            remaining_target -= 1
            n_free_capped += 1
    if remaining_target > 0:
        log(f"自由選定: 分散上限内では{n_free_capped}件のみ。残り{remaining_target}件は上限を外して補充")
        for _, row in free_candidates.iterrows():
            if remaining_target <= 0:
                break
            if force_add(row):
                remaining_target -= 1

    pool_df = pool_src[pool_src["anime_id"].isin(selected_ids)].sort_values("split_score", ascending=False)
    log(f"最終プールサイズ: {len(pool_df):,}件")

    pool = []
    for _, row in pool_df.iterrows():
        pool.append({
            "title": row["title"],
            "anime_id": int(row["anime_id"]),
            "year": int(row["year"]),
            "episodes": int(row["episodes_num"]),
            "genres": row["genre_list"],
            "completion_rate": round(float(row["completion_rate"]), 4),
            "split_score": round(float(row["split_score"]), 4),
        })

    out_path = BASE_DIR / "data" / "question_pool.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
    log(f"saved: {out_path} ({len(pool)}本)")


if __name__ == "__main__":
    main()
