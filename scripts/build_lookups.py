"""data/processed/ の全ルックアップとあらすじ埋め込みを、
data/raw/{anime.csv, animelist.csv, anime_with_synopsis.csv} から再生成する。

data/processed/ は .gitignore 対象で生成物自体は永続化されないため、
再現性のためにこのスクリプトを必ずコミットする（CLAUDE.md「再現性」節）。

ロジックの根拠（すべて既存コードからの復元・引用元を明記する）:
- train/val/test分割・anime_avg_completion_rate_A_train:
  notebooks/02_model.ipynb セル3・セル7 と同一ロジック
- anime_population_completion_rate_B・anime_peak_at_risk（ハザード曲線・at_risk）:
  notebooks/01_aggregation.ipynb セル5・7・9・10 と同一ロジック
  （population_completion_rate_B は dropout_curves.json と異なり eligible 作品に絞らず全作品分を出す）
- anime_is_ongoing: reports/api_verification.md 追記3「修正1: 放送中作品の判定」
  （Aired基準="... to ?"パターン525本 OR watching_ratio>0.5・denom>=50基準230本 の和集合577本）
- anime_embeddings: notebooks/02_model.ipynb セル9 と同一ロジック

data/dropout_curves.json・data/question_pool.json は対象外（既存のまま維持する）。

使い方: python3 -m scripts.build_lookups  (リポジトリルートから実行)
"""

import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
ANIMELIST_PATH = RAW_DIR / "animelist.csv"
ANIME_PATH = RAW_DIR / "anime.csv"
SYNOPSIS_PATH = RAW_DIR / "anime_with_synopsis.csv"

SEED = 42
N_USERS_TARGET = 15_000
CHUNKSIZE = 15_000_000
MIN_DROPPED_FOR_CURVE = 50  # 01_aggregation.ipynb と同じ閾値。dropout_curves.json の eligible 判定と揃える
WATCHING_RATIO_DENOM_MIN = 50
WATCHING_RATIO_THRESHOLD = 0.5


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _extract_year(aired: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", str(aired))
    return int(m.group()) if m else None


def _is_aired_ongoing(aired: str) -> bool:
    """終了日がない（"... to ?" パターン）作品。reports/api_verification.md 追記3 修正1。"""
    return bool(re.search(r"to\s*\?", str(aired)))


# ---------------------------------------------------------------------------
# Pass 1: animelist.csv 全行を1回走査し、母集団全体（全ユーザー）のみで決まる値を集計する。
#   - ユニークユーザー一覧（train/val/test分割のサンプリング元）
#   - 完走(2)/離脱定義B(3,4) の (anime_id, watched_episodes) 別カウント → population_completion_rate_B, peak_at_risk
#   - 視聴中(1)/完走(2)/離脱定義A(4) の anime_id 別カウント → anime_is_ongoing の watching_ratio 判定
# ---------------------------------------------------------------------------

def pass1_population_scan(ep_lookup: dict[int, float]) -> dict:
    dtypes = {
        "user_id": "int32", "anime_id": "int32",
        "watching_status": "int8", "watched_episodes": "int32",
    }
    unique_chunks = []
    completed_parts = []
    dropped_b_parts = []
    watching1_parts = []
    dropped_a_parts = []
    n_rows_seen = 0
    n_clipped = 0

    t0 = time.time()
    for chunk in pd.read_csv(ANIMELIST_PATH, dtype=dtypes, usecols=list(dtypes.keys()), chunksize=CHUNKSIZE):
        n_rows_seen += len(chunk)
        unique_chunks.append(chunk["user_id"].unique())

        ceiling = chunk["anime_id"].map(ep_lookup)  # NaN -> クリップ対象外（01_aggregation セル3・5と同じ）
        clip_mask = ceiling.notna() & (chunk["watched_episodes"] > ceiling)
        n_clipped += int(clip_mask.sum())
        chunk.loc[clip_mask, "watched_episodes"] = ceiling[clip_mask].astype("int32")

        c = chunk[chunk["watching_status"] == 2]
        d_b = chunk[chunk["watching_status"].isin([3, 4])]
        completed_parts.append(c.groupby(["anime_id", "watched_episodes"]).size().rename("count"))
        dropped_b_parts.append(d_b.groupby(["anime_id", "watched_episodes"]).size().rename("count"))

        watching1_parts.append(chunk[chunk["watching_status"] == 1].groupby("anime_id").size())
        dropped_a_parts.append(chunk[chunk["watching_status"] == 4].groupby("anime_id").size())

        log(f"  pass1 chunk: rows_seen={n_rows_seen:,} elapsed={time.time()-t0:.1f}s")

    unique_users = np.unique(np.concatenate(unique_chunks))
    completed_ep = pd.concat(completed_parts).groupby(level=[0, 1]).sum().reset_index()
    dropped_ep_b = pd.concat(dropped_b_parts).groupby(level=[0, 1]).sum().reset_index()
    watching1_by_anime = pd.concat(watching1_parts).groupby(level=0).sum()
    dropped_a_by_anime = pd.concat(dropped_a_parts).groupby(level=0).sum()

    log(f"pass1 done: rows={n_rows_seen:,} clipped={n_clipped:,} unique_users={len(unique_users):,} "
        f"elapsed={time.time()-t0:.1f}s")

    return {
        "unique_users": unique_users,
        "completed_ep": completed_ep,
        "dropped_ep_b": dropped_ep_b,
        "watching1_by_anime": watching1_by_anime,
        "dropped_a_by_anime": dropped_a_by_anime,
    }


# ---------------------------------------------------------------------------
# 01_aggregation.ipynb セル7・9・10 相当: population_completion_rate_B と
# ハザード曲線由来の peak_dropout_episode / at_risk（到達者数）を計算する。
# ---------------------------------------------------------------------------

def compute_population_b_and_peak_at_risk(completed_ep: pd.DataFrame, dropped_ep_b: pd.DataFrame):
    n_completed = completed_ep.groupby("anime_id")["count"].sum().rename("n_completed")
    n_dropped = dropped_ep_b.groupby("anime_id")["count"].sum().rename("n_dropped")
    totals = pd.concat([n_completed, n_dropped], axis=1).fillna(0)
    totals["n_completed"] = totals["n_completed"].astype(int)
    totals["n_dropped"] = totals["n_dropped"].astype(int)
    totals["population_completion_rate"] = totals["n_completed"] / (totals["n_completed"] + totals["n_dropped"])

    # ハザード率: hazard(k) = k話で止まった人数 / k話に到達した人数（01_aggregation セル9）
    combined = pd.concat([completed_ep, dropped_ep_b]).groupby(
        ["anime_id", "watched_episodes"], as_index=False
    )["count"].sum().sort_values(["anime_id", "watched_episodes"])
    totals_by_anime = combined.groupby("anime_id")["count"].sum()
    combined["cum_asc"] = combined.groupby("anime_id")["count"].cumsum()
    combined["total"] = combined["anime_id"].map(totals_by_anime)
    combined["at_risk"] = combined["total"] - combined["cum_asc"] + combined["count"]

    dropped_valid = dropped_ep_b[dropped_ep_b["watched_episodes"] > 0]
    valid_ids = set(dropped_valid.groupby("anime_id")["count"].sum().index)

    hz = dropped_valid.merge(
        combined[["anime_id", "watched_episodes", "at_risk"]],
        on=["anime_id", "watched_episodes"], how="left",
    )
    hz["hazard"] = hz["count"] / hz["at_risk"]

    eligible_ids = totals.index[(totals["n_dropped"] >= MIN_DROPPED_FOR_CURVE) & totals.index.isin(valid_ids)]

    # peak_dropout_episode: 1話を除いたハザード率最大の話数（01_aggregation セル10）
    hz_not_ep1 = hz[hz["watched_episodes"] != 1]
    hz_sorted = hz_not_ep1.sort_values(["anime_id", "hazard", "watched_episodes"], ascending=[True, False, True])
    peak_not_ep1 = hz_sorted.groupby("anime_id").first()["watched_episodes"]
    hz_ep1 = hz[hz["watched_episodes"] == 1].set_index("anime_id")["watched_episodes"]

    def get_peak(aid):
        if aid in peak_not_ep1.index:
            return int(peak_not_ep1.loc[aid])
        if aid in hz_ep1.index:
            return 1
        return None

    peak_lookup = {aid: get_peak(aid) for aid in eligible_ids}

    at_risk_lookup = combined.set_index(["anime_id", "watched_episodes"])["at_risk"]
    anime_peak_at_risk = {}
    for aid, peak_ep in peak_lookup.items():
        if peak_ep is None:
            continue
        key = (aid, peak_ep)
        if key in at_risk_lookup.index:
            anime_peak_at_risk[int(aid)] = int(at_risk_lookup.loc[key])

    population_completion_rate_B = {
        int(aid): round(float(rate), 4) for aid, rate in totals["population_completion_rate"].items()
    }
    return population_completion_rate_B, anime_peak_at_risk, totals, peak_lookup


def validate_against_dropout_curves(peak_lookup: dict[int, int]) -> None:
    """dropout_curves.json は同じ 01_aggregation ロジック（サンプリングなし・決定論的）から
    作られているはずなので、peak_dropout_episode が完全一致するかで復元ロジックを検証する。"""
    curves_path = BASE_DIR / "data" / "dropout_curves.json"
    if not curves_path.exists():
        log("検証スキップ: data/dropout_curves.json が見つからない")
        return
    curves = json.load(open(curves_path, encoding="utf-8"))
    existing_peak = {
        c["anime_id"]: c["peak_dropout_episode"] for c in curves if not c.get("insufficient_data")
    }
    common_ids = set(existing_peak) & set(peak_lookup)
    mismatches = [aid for aid in common_ids if existing_peak[aid] != peak_lookup[aid]]
    only_existing = set(existing_peak) - set(peak_lookup)
    only_new = set(peak_lookup) - set(existing_peak)
    log(f"検証(dropout_curves.jsonとの突合): 共通={len(common_ids):,} 不一致={len(mismatches):,} "
        f"既存のみ={len(only_existing):,} 新規のみ={len(only_new):,}")
    if mismatches or only_existing or only_new:
        log(f"  不一致サンプル: {mismatches[:5]}")
        log(f"  既存のみサンプル: {list(only_existing)[:5]}")
        log(f"  新規のみサンプル: {list(only_new)[:5]}")
        log("  → peak_dropout_episode の復元ロジックが dropout_curves.json 生成時と一致していない可能性がある")
    else:
        log("  → 完全一致。ハザード曲線の復元ロジックは正しいと確認できた")


# ---------------------------------------------------------------------------
# anime_is_ongoing: reports/api_verification.md 追記3「修正1: 放送中作品の判定」
# ---------------------------------------------------------------------------

def compute_is_ongoing(anime: pd.DataFrame, watching1_by_anime: pd.Series, dropped_a_by_anime: pd.Series,
                        n_completed_by_anime: pd.Series) -> tuple[set[int], dict]:
    aired_ongoing_ids = set(anime.loc[anime["Aired"].apply(_is_aired_ongoing), "MAL_ID"])

    denom = pd.concat(
        [watching1_by_anime.rename("w1"), n_completed_by_anime.rename("w2"), dropped_a_by_anime.rename("w4")],
        axis=1,
    ).fillna(0)
    denom["denom"] = denom["w1"] + denom["w2"] + denom["w4"]
    eligible = denom[denom["denom"] >= WATCHING_RATIO_DENOM_MIN].copy()
    eligible["watching_ratio"] = eligible["w1"] / eligible["denom"]
    ratio_ongoing_ids = set(eligible.index[eligible["watching_ratio"] > WATCHING_RATIO_THRESHOLD].astype(int))

    union_ids = aired_ongoing_ids | ratio_ongoing_ids
    counts = {
        "aired_pattern": len(aired_ongoing_ids),
        "watching_ratio_denom_eligible": len(eligible),
        "watching_ratio_over_threshold": len(ratio_ongoing_ids),
        "union": len(union_ids),
    }
    log(f"is_ongoing 判定件数: Aired基準={counts['aired_pattern']}（期待値525）"
        f" watching_ratio対象={counts['watching_ratio_denom_eligible']}（期待値14056）"
        f" watching_ratio>0.5={counts['watching_ratio_over_threshold']}（期待値230）"
        f" 和集合={counts['union']}（期待値577）")
    return union_ids, counts


# ---------------------------------------------------------------------------
# train/val/test 分割 + anime_avg_completion_rate_A_train（02_model.ipynb セル3・7）
# ---------------------------------------------------------------------------

def build_user_split(unique_users: np.ndarray) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(SEED)
    sampled_users = rng.choice(unique_users, size=min(N_USERS_TARGET, len(unique_users)), replace=False)
    perm = rng.permutation(sampled_users)
    n = len(perm)
    n_train, n_val = int(n * 0.70), int(n * 0.15)
    return {
        "train": perm[:n_train],
        "val": perm[n_train:n_train + n_val],
        "test": perm[n_train + n_val:],
    }


def pass2_train_avg_completion_rate(train_user_set: set[int]) -> tuple[dict, float, dict]:
    dtypes = {"user_id": "int32", "anime_id": "int32", "watching_status": "int8"}
    n_completed_parts = []
    n_dropped_a_parts = []
    n_rows_seen = 0

    t0 = time.time()
    for chunk in pd.read_csv(ANIMELIST_PATH, dtype=dtypes, usecols=list(dtypes.keys()), chunksize=CHUNKSIZE):
        n_rows_seen += len(chunk)
        mask = chunk["user_id"].isin(train_user_set) & chunk["watching_status"].isin([2, 4])
        if mask.any():
            sub = chunk.loc[mask]
            n_completed_parts.append(sub[sub["watching_status"] == 2].groupby("anime_id").size())
            n_dropped_a_parts.append(sub[sub["watching_status"] == 4].groupby("anime_id").size())
        log(f"  pass2 chunk: rows_seen={n_rows_seen:,} elapsed={time.time()-t0:.1f}s")

    n_completed = pd.concat(n_completed_parts).groupby(level=0).sum() if n_completed_parts else pd.Series(dtype=int)
    n_dropped_a = pd.concat(n_dropped_a_parts).groupby(level=0).sum() if n_dropped_a_parts else pd.Series(dtype=int)
    anime_avg = pd.DataFrame({"n_completed": n_completed, "n_dropped_A": n_dropped_a}).fillna(0)
    anime_avg["rate"] = anime_avg["n_completed"] / (anime_avg["n_completed"] + anime_avg["n_dropped_A"])
    anime_avg["n_labeled"] = anime_avg["n_completed"] + anime_avg["n_dropped_A"]

    log(f"pass2 done: train作品数={len(anime_avg):,} elapsed={time.time()-t0:.1f}s")

    avg_rate = {int(aid): round(float(r), 4) for aid, r in anime_avg["rate"].items()}
    fallback_mean = float(anime_avg["rate"].mean())
    n_labeled = {int(aid): int(n) for aid, n in anime_avg["n_labeled"].items()}
    return avg_rate, fallback_mean, n_labeled


# ---------------------------------------------------------------------------
# あらすじ埋め込み（02_model.ipynb セル9 と同一ロジック）
# ---------------------------------------------------------------------------

def build_embeddings() -> None:
    if (PROC_DIR / "anime_embeddings.npy").exists():
        log("anime_embeddings.npy は既に存在するためスキップ")
        return
    from sentence_transformers import SentenceTransformer

    syn = pd.read_csv(SYNOPSIS_PATH)
    syn = syn.dropna(subset=["sypnopsis"])
    syn = syn[syn["sypnopsis"].str.strip().str.len() > 0]
    syn = syn[syn["sypnopsis"] != "No synopsis information has been added to this title."]
    texts = ("query: " + syn["sypnopsis"].astype(str).str.slice(0, 2000)).tolist()
    emb_ids = syn["MAL_ID"].values

    log(f"embedding計算開始: {len(texts):,}件")
    t0 = time.time()
    model_e5 = SentenceTransformer("intfloat/multilingual-e5-small")
    embeddings = model_e5.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    log(f"embedding計算完了: {embeddings.shape} elapsed={time.time()-t0:.1f}s")

    np.save(PROC_DIR / "anime_embeddings.npy", embeddings.astype(np.float32))
    np.save(PROC_DIR / "anime_embeddings_ids.npy", emb_ids)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    for path in [ANIMELIST_PATH, ANIME_PATH, SYNOPSIS_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"必要な入力ファイルがありません: {path}")
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    log("anime.csv 読み込み")
    anime_ep = pd.read_csv(ANIME_PATH, usecols=["MAL_ID", "Episodes"])
    anime_ep["Episodes"] = pd.to_numeric(anime_ep["Episodes"], errors="coerce")
    ep_lookup = dict(zip(anime_ep["MAL_ID"], anime_ep["Episodes"]))

    pass1 = pass1_population_scan(ep_lookup)

    population_completion_rate_B, anime_peak_at_risk, totals, peak_lookup = compute_population_b_and_peak_at_risk(
        pass1["completed_ep"], pass1["dropped_ep_b"]
    )
    validate_against_dropout_curves(peak_lookup)

    with open(PROC_DIR / "anime_population_completion_rate_B.json", "w", encoding="utf-8") as f:
        json.dump(population_completion_rate_B, f, ensure_ascii=False)
    log(f"saved: anime_population_completion_rate_B.json ({len(population_completion_rate_B):,}作品)")

    with open(PROC_DIR / "anime_peak_at_risk.json", "w", encoding="utf-8") as f:
        json.dump(anime_peak_at_risk, f, ensure_ascii=False)
    log(f"saved: anime_peak_at_risk.json ({len(anime_peak_at_risk):,}作品)")

    log("anime.csv（Aired列含む）読み込み")
    anime_full = pd.read_csv(ANIME_PATH, usecols=["MAL_ID", "Aired"])
    is_ongoing_ids, ongoing_counts = compute_is_ongoing(
        anime_full, pass1["watching1_by_anime"], pass1["dropped_a_by_anime"], totals["n_completed"]
    )
    with open(PROC_DIR / "anime_is_ongoing.json", "w", encoding="utf-8") as f:
        json.dump(sorted(int(x) for x in is_ongoing_ids), f, ensure_ascii=False)
    log(f"saved: anime_is_ongoing.json ({len(is_ongoing_ids):,}作品)")

    splits = build_user_split(pass1["unique_users"])
    log(f"user split: train={len(splits['train']):,} val={len(splits['val']):,} test={len(splits['test']):,}")
    with open(PROC_DIR / "user_splits.json", "w", encoding="utf-8") as f:
        json.dump({k: sorted(int(u) for u in v) for k, v in splits.items()}, f, ensure_ascii=False)
    log("saved: user_splits.json")

    train_user_set = set(int(u) for u in splits["train"])
    avg_rate, fallback_mean, n_labeled = pass2_train_avg_completion_rate(train_user_set)

    with open(PROC_DIR / "anime_avg_completion_rate_A_train.json", "w", encoding="utf-8") as f:
        json.dump(avg_rate, f, ensure_ascii=False)
    log(f"saved: anime_avg_completion_rate_A_train.json ({len(avg_rate):,}作品)")

    with open(PROC_DIR / "anime_avg_completion_rate_A_train_fallback.json", "w", encoding="utf-8") as f:
        json.dump({"mean": round(fallback_mean, 4)}, f, ensure_ascii=False)
    log(f"saved: anime_avg_completion_rate_A_train_fallback.json (mean={fallback_mean:.4f})")

    with open(PROC_DIR / "anime_n_labeled_A_train.json", "w", encoding="utf-8") as f:
        json.dump(n_labeled, f, ensure_ascii=False)
    log(f"saved: anime_n_labeled_A_train.json ({len(n_labeled):,}作品)")

    # population_stats.json: api/services/data_store.py にロードされるのみで、
    # 現状 api/ のどこからも参照されていない未使用ルックアップ（predict.py 等を grep して確認済み）。
    # スキーマの「正解」はないため、名前に沿った妥当な統計値を保存する。
    n_dropped_b_total = int(totals["n_dropped"].sum())
    n_completed_total = int(totals["n_completed"].sum())
    population_stats = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_users_total": int(len(pass1["unique_users"])),
        "n_anime_with_records": int(len(totals)),
        "n_completed_total": n_completed_total,
        "n_dropped_B_total": n_dropped_b_total,
        "population_completion_rate_B_overall": round(n_completed_total / (n_completed_total + n_dropped_b_total), 4),
        "n_ongoing_anime": len(is_ongoing_ids),
        "is_ongoing_breakdown": ongoing_counts,
    }
    with open(PROC_DIR / "population_stats.json", "w", encoding="utf-8") as f:
        json.dump(population_stats, f, ensure_ascii=False, indent=2)
    log("saved: population_stats.json（api/では未使用。参考値として保存）")

    build_embeddings()

    log("build_lookups.py 完了")


if __name__ == "__main__":
    main()
