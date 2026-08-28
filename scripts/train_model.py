"""dropout_predictor.lgb を data/raw/{anime.csv, animelist.csv} と
data/processed/ のルックアップ（scripts/build_lookups.py の出力）から再学習する。

models/*.lgb・feature_columns.json・model_card.json 自体は .gitignore 対象ではなく
git管理下にある（gitignore対象なのは models/archive/ のみ）。それでも学習に使う
data/raw・data/processed が失われた際に models/ だけでは再学習できないため、
再現性のためにこのスクリプトを必ずコミットする（CLAUDE.md「再現性」節）。

このスクリプトは実行前に scripts/build_lookups.py が完了していることを前提とする
（user_splits.json・anime_avg_completion_rate_A_train.json 等の processed ファイルを読む）。

特徴量エンジニアリングは既存の本番コード
（api/services/profile.py の純粋関数 / api/ml/inference.py の build_candidate_features）
と同じ定義を使う。これにより学習時と提供時（inference.py）の特徴量の食い違いを防ぐ。
分割・データセット構築（N_TIERS プーリング、MAX_N、TARGET_CAP_PER_USER）は
notebooks/02_model.ipynb セル1・13・14 と同一ロジック。

既存モデル（trained_on_users=10004）との数値的な再現は狙わない方針だったが、
実際にはSEED=42・N_USERS_TARGET=15,000という02_model.ipynbのパラメータが元々の
本番モデルと同一だったため、trained_on_usersを含め実質的に再現された
（詳細: reports/data_recovery.md）。

使い方: python3 -m scripts.train_model  (リポジトリルートから実行)
"""

import gc
import json
import re
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from api.ml.inference import cos_sim  # noqa: E402
from api.services.profile import (  # noqa: E402
    Response,
    best_episode_bucket,
    bucket_index_for_episodes,
    compute_completion_rate,
    compute_endurance_episodes,
    compute_episode_buckets,
)

RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"
ANIMELIST_PATH = RAW_DIR / "animelist.csv"
ANIME_PATH = RAW_DIR / "anime.csv"

SEED = 42
CHUNKSIZE = 15_000_000
MAX_N = 30
N_TIERS = [3, 5, 10, 20, 30]
TARGET_CAP_PER_USER = 40
CAT_COLS = ["source"]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _extract_year(aired: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", str(aired))
    return int(m.group()) if m else None


def load_anime_feat() -> tuple[pd.DataFrame, list[str]]:
    """api/services/data_store.py の DataStore.__init__ と同一ロジック（genre列・popularity_percentileの
    定義を本番と完全一致させるため、意図的に処理内容を揃えている）。"""
    anime = pd.read_csv(ANIME_PATH)
    anime["year"] = anime["Aired"].apply(_extract_year)
    anime["episodes_num"] = pd.to_numeric(anime["Episodes"], errors="coerce")
    anime["score_num"] = pd.to_numeric(anime["Score"], errors="coerce")
    anime["members_num"] = pd.to_numeric(anime["Members"], errors="coerce")
    anime["members_log"] = np.log1p(anime["members_num"])
    anime["genre_list"] = anime["Genres"].apply(
        lambda s: [g.strip() for g in str(s).split(",")] if pd.notna(s) else []
    )
    anime["source"] = anime["Source"].fillna("Unknown")

    all_genres = sorted({g for gl in anime["genre_list"] for g in gl if g and g != "Unknown"})
    for g in all_genres:
        anime[f"genre_{g}"] = anime["genre_list"].apply(lambda gl, g=g: 1 if g in gl else 0)
    anime["popularity_percentile"] = anime["members_num"].rank(pct=True)

    return anime.set_index("MAL_ID"), all_genres


def load_processed_lookups() -> dict:
    def _load(name):
        with open(PROC_DIR / name, encoding="utf-8") as f:
            return json.load(f)

    return {
        "user_splits": _load("user_splits.json"),
        "avg_rate": {int(k): v for k, v in _load("anime_avg_completion_rate_A_train.json").items()},
        "avg_fallback": _load("anime_avg_completion_rate_A_train_fallback.json")["mean"],
        "is_ongoing": set(_load("anime_is_ongoing.json")),
        "embeddings": np.load(PROC_DIR / "anime_embeddings.npy"),
        "embedding_ids": np.load(PROC_DIR / "anime_embeddings_ids.npy"),
    }


def load_labels(all_user_ids: set[int]) -> pd.DataFrame:
    """train+val+test 全ユーザーぶんの完走(2)/離脱(4) 行動（定義A。保留(3)は除外）を読み込む。
    02_model.ipynb セル4 と同一ロジック。"""
    dtypes = {"user_id": "int32", "anime_id": "int32", "watching_status": "int8"}
    parts = []
    n_rows_seen = 0
    t0 = time.time()
    for chunk in pd.read_csv(ANIMELIST_PATH, dtype=dtypes, usecols=list(dtypes.keys()), chunksize=CHUNKSIZE):
        n_rows_seen += len(chunk)
        mask = chunk["user_id"].isin(all_user_ids) & chunk["watching_status"].isin([2, 4])
        if mask.any():
            parts.append(chunk.loc[mask])
        log(f"  labels chunk: rows_seen={n_rows_seen:,} elapsed={time.time()-t0:.1f}s")
    labels = pd.concat(parts, ignore_index=True)
    log(f"labels rows={len(labels):,} users_covered={labels['user_id'].nunique():,}")
    return labels


def main() -> None:
    for path in [ANIMELIST_PATH, ANIME_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"必要な入力ファイルがありません: {path}")
    required_processed = [
        "user_splits.json", "anime_avg_completion_rate_A_train.json",
        "anime_avg_completion_rate_A_train_fallback.json", "anime_is_ongoing.json",
        "anime_embeddings.npy", "anime_embeddings_ids.npy",
    ]
    for name in required_processed:
        if not (PROC_DIR / name).exists():
            raise FileNotFoundError(f"data/processed/{name} がありません。先に scripts/build_lookups.py を実行してください")
    if not (MODELS_DIR / "feature_columns.json").exists():
        raise FileNotFoundError("models/feature_columns.json がありません（学習する特徴量の定義に必要）")

    with open(MODELS_DIR / "feature_columns.json", encoding="utf-8") as f:
        feature_columns: list[str] = json.load(f)

    log("anime.csv 読み込み・特徴量準備")
    anime_feat, all_genres = load_anime_feat()
    genres_lookup = anime_feat["genre_list"].to_dict()
    episodes_lookup = anime_feat["episodes_num"].to_dict()
    members_lookup = anime_feat["members_num"].fillna(0).to_dict()

    lookups = load_processed_lookups()
    splits = lookups["user_splits"]
    train_users, val_users, test_users = splits["train"], splits["val"], splits["test"]
    all_user_ids = set(train_users) | set(val_users) | set(test_users)

    emb_lookup = {int(aid): lookups["embeddings"][i] for i, aid in enumerate(lookups["embedding_ids"])}

    is_ongoing_ids = lookups["is_ongoing"]
    avg_rate = lookups["avg_rate"]
    avg_fallback = lookups["avg_fallback"]

    def anime_avg_for_model(anime_id: int) -> float:
        """api/services/data_store.py の anime_avg_for_model() と同一ロジック。
        放送継続中は右側打ち切りで完走率が機械的に0近辺へ偏るため学習時もNaN化する
        （models/model_card.json の ongoing_series_fix と同じ扱い）。"""
        if anime_id in is_ongoing_ids:
            return float("nan")
        return avg_rate.get(anime_id, avg_fallback)

    pool = json.load(open(BASE_DIR / "data" / "question_pool.json", encoding="utf-8"))
    pool_ids = set(p["anime_id"] for p in pool)

    labels_all = load_labels(all_user_ids)
    labels_by_user = {uid: g for uid, g in labels_all.groupby("user_id")}

    def make_response(anime_id: int, status: int) -> Response:
        return Response(
            anime_id=int(anime_id), label=("completed" if status == 2 else "dropped"),
            episodes=int(episodes_lookup.get(anime_id) or 0),
            genres=genres_lookup.get(anime_id) or [],
            members=int(members_lookup.get(anime_id) or 0),
        )

    def profile_vectors(responses: list[Response]):
        comp_embs = [emb_lookup[r.anime_id] for r in responses if r.label == "completed" and r.anime_id in emb_lookup]
        drop_embs = [emb_lookup[r.anime_id] for r in responses if r.label == "dropped" and r.anime_id in emb_lookup]
        comp_vec = np.mean(comp_embs, axis=0) if comp_embs else None
        drop_vec = np.mean(drop_embs, axis=0) if drop_embs else None
        return comp_vec, drop_vec

    def build_target_rows(user_group: pd.DataFrame, rng: np.random.Generator):
        rows = user_group[["anime_id", "watching_status"]].values.tolist()
        pool_rows = [r for r in rows if r[0] in pool_ids]
        nonpool_rows = [r for r in rows if r[0] not in pool_ids]
        perm_idx = rng.permutation(len(pool_rows))
        pool_rows_shuffled = [pool_rows[i] for i in perm_idx]
        input_pool_rows = pool_rows_shuffled[:MAX_N]
        holdout_pool_rows = pool_rows_shuffled[MAX_N:]
        target_rows = holdout_pool_rows + nonpool_rows
        if len(target_rows) > TARGET_CAP_PER_USER:
            idx = rng.choice(len(target_rows), size=TARGET_CAP_PER_USER, replace=False)
            target_rows = [target_rows[i] for i in idx]
        return input_pool_rows, target_rows

    def compute_profile(responses: list[Response]) -> dict:
        """入力(N本)から決まるプロファイル統計。1ユーザー×1Nにつき1回だけ計算し、
        target行のループでは使い回す（02_model.ipynb セル13の構造と同じ。target行ごとに
        再計算すると最大40倍の無駄な計算になるため、意図的にここで1回にまとめている）。"""
        episode_buckets = compute_episode_buckets(responses)
        comp_vec, drop_vec = profile_vectors(responses)
        genre_rate: dict[str, float] = {}
        for g_name in all_genres:
            c = sum(1 for r in responses if r.label == "completed" and g_name in r.genres)
            d = sum(1 for r in responses if r.label == "dropped" and g_name in r.genres)
            if c + d > 0:
                genre_rate[g_name] = c / (c + d)
        return {
            "endurance": compute_endurance_episodes(responses),
            "episode_buckets": episode_buckets,
            "best_bucket": best_episode_bucket(episode_buckets),
            "completion_rate": compute_completion_rate(responses),
            "comp_vec": comp_vec, "drop_vec": drop_vec,
            "genre_rate": genre_rate,
        }

    # build_row_features は「入力(N本)から決まる動的な特徴量」だけを1行あたり最小限の
    # dictで返す（anime_idごとの静的特徴量・44genre列はここでは持たせない）。
    # 静的特徴量は build_dataset_for_split の最後に anime_feat との1回のvectorized mergeで
    # まとめて付与する（02_model.ipynb の attach_static_features と同じ設計）。
    # 理由: target行ごとに `anime_feat.loc[aid]` でgenre列を44回ずつPython/pandasループで
    # 引くと、最大数百万行 × 44列 の呼び出しになりCPU・メモリ（1行あたりのdictが巨大化する）
    # の両方で破綻する（実測: 8GB RAMマシンでswapが枯渇しかけた）。

    def build_row_features(profile: dict, aid: int, status: int, n_input: int) -> dict:
        a_genres = genres_lookup.get(aid) or []
        a_episodes = episodes_lookup.get(aid)
        a_emb = emb_lookup.get(aid)
        cos_c = cos_sim(a_emb, profile["comp_vec"])
        cos_d = cos_sim(a_emb, profile["drop_vec"])

        episode_buckets = profile["episode_buckets"]
        best_bucket = profile["best_bucket"]
        cand_bucket_idx = bucket_index_for_episodes(int(a_episodes)) if pd.notna(a_episodes) else None
        if cand_bucket_idx is not None and cand_bucket_idx < len(episode_buckets):
            b = episode_buckets[cand_bucket_idx]
            episode_bucket_completion_rate = b["completion_rate"] if b["count"] >= 3 else None
        else:
            episode_bucket_completion_rate = None
        episode_bucket_gap = (
            (cand_bucket_idx - best_bucket["index"])
            if (cand_bucket_idx is not None and best_bucket is not None) else None
        )

        genre_rate = profile["genre_rate"]
        gmatch = [genre_rate[g] for g in a_genres if g in genre_rate]
        genre_match_rate = float(np.mean(gmatch)) if gmatch else None

        return {
            "n_input": n_input, "anime_id": aid, "label_dropped": 1 if status == 4 else 0,
            "anime_avg_completion_rate_A": anime_avg_for_model(aid),
            "endurance_episodes": profile["endurance"],
            "user_completion_rate": profile["completion_rate"],
            "genre_match_completion_rate": genre_match_rate,
            "episode_bucket_completion_rate": episode_bucket_completion_rate,
            "episode_bucket_gap": episode_bucket_gap,
            "cos_completed": cos_c, "cos_dropped": cos_d,
        }

    STATIC_COLS = ["year", "episodes_num", "score_num", "members_log", "source", "popularity_percentile"]
    STATIC_MERGE_COLS = STATIC_COLS + [f"genre_{g}" for g in all_genres]
    F32_COLS = [
        "anime_avg_completion_rate_A", "endurance_episodes", "user_completion_rate",
        "genre_match_completion_rate", "episode_bucket_completion_rate", "episode_bucket_gap",
        "cos_completed", "cos_dropped", "year", "episodes_num", "score_num", "members_log",
        "popularity_percentile",
    ] + [f"genre_{g}" for g in all_genres]

    def attach_static_features(df: pd.DataFrame) -> pd.DataFrame:
        static = anime_feat[STATIC_MERGE_COLS].reset_index().rename(columns={"MAL_ID": "anime_id"})
        df = df.merge(static, on="anime_id", how="left")
        df["source"] = df["source"].astype("category")
        for col in F32_COLS:
            df[col] = df[col].astype("float32")
        return df

    def build_dataset_for_split(user_ids, split_name: str) -> pd.DataFrame:
        all_rows = []
        n_used = 0
        t0 = time.time()
        n_total = len(user_ids)
        for i, uid in enumerate(user_ids):
            if i > 0 and i % 2000 == 0:
                log(f"  [{split_name}] {i:,}/{n_total:,} ({i/n_total*100:.1f}%) "
                    f"rows={len(all_rows):,} elapsed={time.time()-t0:.1f}s")
            if uid not in labels_by_user:
                continue
            g = labels_by_user[uid]
            rng = np.random.default_rng(SEED + int(uid))
            input_pool_rows, target_rows = build_target_rows(g, rng)
            if len(target_rows) == 0 or len(input_pool_rows) == 0:
                continue
            n_used += 1
            for n in N_TIERS:
                responses = [make_response(aid, st) for aid, st in input_pool_rows[:n]]
                profile = compute_profile(responses)
                for aid, status in target_rows:
                    row = build_row_features(profile, aid, status, len(responses))
                    row["N"] = n
                    row["user_id"] = uid
                    all_rows.append(row)
        df = pd.DataFrame(all_rows)
        del all_rows
        df = attach_static_features(df)
        log(f"[{split_name}] users_used={n_used:,} rows={len(df):,}")
        return df, n_used

    # メモリを抑えるため、train/val で学習を終わらせてから test を構築する
    # （8GB RAMマシンでの実測で train+val+test を同時に保持すると swap が枯渇しかけたため。
    # free_raw_data はデフォルト(True)のままにし、lgb.Dataset構築後は生pandasを解放させる）。
    log("train/val データセット構築開始")
    train_df, train_n_used = build_dataset_for_split(train_users, "train")
    val_df, _val_n_used = build_dataset_for_split(val_users, "val")

    missing = [c for c in feature_columns if c not in train_df.columns]
    if missing:
        raise RuntimeError(f"feature_columns.json にあるが生成できなかった特徴量: {missing}")

    params = {
        "objective": "binary", "metric": "auc", "verbosity": -1, "learning_rate": 0.05,
        "num_leaves": 31, "min_data_in_leaf": 50, "feature_fraction": 0.8, "bagging_fraction": 0.8,
        "bagging_freq": 1, "seed": SEED,
    }
    dtrain = lgb.Dataset(train_df[feature_columns], label=train_df["label_dropped"], categorical_feature=CAT_COLS)
    dval = lgb.Dataset(val_df[feature_columns], label=val_df["label_dropped"], reference=dtrain,
                        categorical_feature=CAT_COLS)

    log("LightGBM 学習開始")
    model = lgb.train(params, dtrain, num_boost_round=500, valid_sets=[dval],
                       callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(0)])

    del train_df, val_df, dtrain, dval
    gc.collect()

    log("test データセット構築開始")
    test_df, _test_n_used = build_dataset_for_split(test_users, "test")
    te20 = test_df[test_df["N"] == 20]
    pred = model.predict(te20[feature_columns], num_iteration=model.best_iteration)
    test_auc = roc_auc_score(te20["label_dropped"], pred)
    test_pr_auc = average_precision_score(te20["label_dropped"], pred)
    test_baseline_pos_rate = te20["label_dropped"].mean()
    log(f"評価(N=20): test_auc={test_auc:.4f} test_pr_auc={test_pr_auc:.4f} "
        f"baseline_pos_rate={test_baseline_pos_rate:.4f}")

    model.save_model(str(MODELS_DIR / "dropout_predictor.lgb"))
    with open(MODELS_DIR / "feature_columns.json", "w", encoding="utf-8") as f:
        json.dump(feature_columns, f, ensure_ascii=False, indent=2)

    model_card = {
        "target": "label_dropped (定義A: MAL離脱=4のみ、保留(3)は学習から除外)",
        "performance": {
            "description": "data/raw・data/processed 消失後の全面再構築（scripts/build_lookups.py + "
                            "scripts/train_model.py）による再学習。分割・特徴量エンジニアリングはSEED=42・"
                            "N_USERS_TARGET=15,000（notebooks/02_model.ipynb と同一パラメータ）で再現しており、"
                            "trained_on_users（学習に使えるデータを持っていたユーザー数）は偶然ではなく"
                            "再構築前の値（10,004）と完全一致した。既存モデルとの数値的な再現は狙っていなかったが、"
                            "結果としてAUC/PR-AUCも同水準（0.837台/0.32台）に戻っている。",
            "test_auc": round(float(test_auc), 4),
            "test_pr_auc": round(float(test_pr_auc), 4),
            "test_baseline_pos_rate": round(float(test_baseline_pos_rate), 4),
        },
        "feature_columns": feature_columns,
        "trained_on_users": train_n_used,
        "n_tiers_pooled": N_TIERS,
        "rebuild": {
            "description": "data/raw と data/processed が誤って削除された後の復元作業。"
                            ".gitignore対象の生成物のみで生成コードをコミットしていなかったことが原因のため、"
                            "以後は scripts/build_lookups.py と scripts/train_model.py を必ずコミットする。",
            "date": time.strftime("%Y-%m-%d"),
            "seed": SEED,
            "n_users_sampled": len(all_user_ids),
        },
    }
    with open(MODELS_DIR / "model_card.json", "w", encoding="utf-8") as f:
        json.dump(model_card, f, ensure_ascii=False, indent=2)

    log("saved: models/dropout_predictor.lgb, feature_columns.json, model_card.json")
    log("train_model.py 完了")


if __name__ == "__main__":
    main()
