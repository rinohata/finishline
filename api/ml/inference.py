"""プロファイル（ユーザー入力から作った特徴量）と候補作品から、
学習済みモデルへ渡す特徴ベクトルを組み立てる。

モデルは「離脱確率（定義A: MAL離脱(4)相当）」を予測するよう学習済み。
このモジュールはその生の予測確率のみを返し、UIへの「完走率」変換は
呼び出し側（predict.py）の責務とする。
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from api.services.data_store import DataStore
from api.services.profile import Response, bucket_index_for_episodes


def cos_sim(a, b) -> float | None:
    if a is None or b is None:
        return None
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return None
    return float(np.dot(a, b) / (na * nb))


@dataclass
class UserProfileVectors:
    """プロファイル計算の中間生成物。候補ごとの特徴量組み立てに使い回す。"""

    endurance_episodes: int | None
    episode_buckets: list[dict]
    best_episode_bucket: dict | None
    max_completed_episodes: int | None
    user_completion_rate: float | None
    completed_vector: np.ndarray | None
    dropped_vector: np.ndarray | None
    user_mean_popularity: float | None
    genre_rate: dict[str, float]
    genre_count: dict[str, int]
    n_input: int


def build_profile_vectors(store: DataStore, responses: list[Response]) -> UserProfileVectors:
    from api.services.profile import (
        best_episode_bucket,
        compute_completion_rate,
        compute_endurance_episodes,
        compute_episode_buckets,
    )

    endurance = compute_endurance_episodes(responses)
    episode_buckets = compute_episode_buckets(responses)
    best_bucket = best_episode_bucket(episode_buckets)
    completion_rate = compute_completion_rate(responses)

    # バケットが粗い（27話〜が上限なし）ため、同じバケット内でも27話と203話のような
    # 大きな差を見落としうる。実話数どうしの直接比較のフォールバックに使う
    # （explain.episode_reason / api/services/predict.py の factors 生成）。
    completed_episodes = [r.episodes for r in responses if r.label == "completed" and r.episodes]
    max_completed_episodes = max(completed_episodes) if completed_episodes else None

    comp_embs = [store.embedding(r.anime_id) for r in responses if r.label == "completed"]
    comp_embs = [e for e in comp_embs if e is not None]
    drop_embs = [store.embedding(r.anime_id) for r in responses if r.label == "dropped"]
    drop_embs = [e for e in drop_embs if e is not None]
    comp_vec = np.mean(comp_embs, axis=0) if comp_embs else None
    drop_vec = np.mean(drop_embs, axis=0) if drop_embs else None

    comp_pop = [store.registration_rank.get(r.anime_id) for r in responses if r.label == "completed"]
    comp_pop = [p for p in comp_pop if p is not None]
    user_mean_pop = float(np.mean(comp_pop)) if comp_pop else None

    genre_rate: dict[str, float] = {}
    genre_count: dict[str, int] = {}
    for g in store.all_genres:
        c = sum(1 for r in responses if r.label == "completed" and g in r.genres)
        d = sum(1 for r in responses if r.label == "dropped" and g in r.genres)
        if c + d > 0:
            genre_rate[g] = c / (c + d)
            genre_count[g] = c + d

    return UserProfileVectors(
        endurance_episodes=endurance,
        episode_buckets=episode_buckets,
        best_episode_bucket=best_bucket,
        max_completed_episodes=max_completed_episodes,
        user_completion_rate=completion_rate,
        completed_vector=comp_vec,
        dropped_vector=drop_vec,
        user_mean_popularity=user_mean_pop,
        genre_rate=genre_rate,
        genre_count=genre_count,
        n_input=len(responses),
    )


def build_candidate_features(store: DataStore, profile: UserProfileVectors, anime_id: int) -> dict:
    a_genres = store.genres(anime_id)
    a_episodes = store.episodes(anime_id)
    a_emb = store.embedding(anime_id)
    cos_c = cos_sim(a_emb, profile.completed_vector)
    cos_d = cos_sim(a_emb, profile.dropped_vector)

    # episode_gap（候補話数 − 耐久話数のスカラー差）は、耐久話数が外れ値に弱いため廃止。
    # 話数レンジバケット（EPISODE_BUCKET_DEFS、api/services/profile.py）ベースの2特徴量に
    # 置き換えた（2026-08 再学習, reports/retrain_episode_bucket.md。バケット構成は当初
    # 4分割だったが同月中に3分割へ再修正, reports/question_pool_episode_rebalance.md）。
    # 学習時と同じ定義: 該当バケットの本数が3本未満ならNaN（LightGBMに委ねる）。
    cand_bucket_idx = bucket_index_for_episodes(int(a_episodes)) if a_episodes is not None else None
    if cand_bucket_idx is not None and cand_bucket_idx < len(profile.episode_buckets):
        b = profile.episode_buckets[cand_bucket_idx]
        episode_bucket_completion_rate = b["completion_rate"] if b["count"] >= 3 else None
    else:
        episode_bucket_completion_rate = None
    episode_bucket_gap = (
        (cand_bucket_idx - profile.best_episode_bucket["index"])
        if (cand_bucket_idx is not None and profile.best_episode_bucket is not None)
        else None
    )

    gmatch = [profile.genre_rate[g] for g in a_genres if g in profile.genre_rate]
    genre_match_rate = float(np.mean(gmatch)) if gmatch else None
    a_pop_rank = store.registration_rank.get(anime_id)
    pop_div = (
        (a_pop_rank - profile.user_mean_popularity)
        if (a_pop_rank is not None and profile.user_mean_popularity is not None)
        else None
    )

    row = {
        "anime_avg_completion_rate_A": store.anime_avg_for_model(anime_id),
        "endurance_episodes": profile.endurance_episodes,
        "user_completion_rate": profile.user_completion_rate,
        "genre_match_completion_rate": genre_match_rate,
        "episode_bucket_completion_rate": episode_bucket_completion_rate,
        "episode_bucket_gap": episode_bucket_gap,
        "cos_completed": cos_c,
        "cos_dropped": cos_d,
        "popularity_divergence": pop_div,
        "n_input": profile.n_input,
        "year": store.year(anime_id),
        "episodes_num": a_episodes,
        "score_num": (store.anime.loc[anime_id, "score_num"] if anime_id in store.anime.index else None),
        "members_log": (store.anime.loc[anime_id, "members_log"] if anime_id in store.anime.index else None),
        "source": (store.anime.loc[anime_id, "source"] if anime_id in store.anime.index else "Unknown"),
        "popularity_percentile": (
            store.anime.loc[anime_id, "popularity_percentile"] if anime_id in store.anime.index else None
        ),
    }
    for g in store.all_genres:
        col = f"genre_{g}"
        row[col] = 1 if g in a_genres else 0
    return row


def predict_dropped_prob(store: DataStore, profile: UserProfileVectors, anime_ids: list[int]) -> np.ndarray:
    rows = [build_candidate_features(store, profile, aid) for aid in anime_ids]
    df = pd.DataFrame(rows)
    for col in store.feature_columns:
        if col not in df.columns:
            df[col] = np.nan
    numeric_cols = [c for c in store.feature_columns if c != "source"]
    # プロファイルが completed/dropped の一方を欠く場合、cos_completed/cos_dropped 等が
    # 全行 None になり列全体が object dtype になることがある（LightGBMはint/float/bool以外を拒否する）。
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    df["source"] = df["source"].astype("category")
    return store.model.predict(df[store.feature_columns])
