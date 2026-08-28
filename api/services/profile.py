"""ユーザープロファイル算出ロジック（要件定義書 4.3）。

すべて純粋関数として実装する。外部I/O・グローバル状態を持たず、
呼び出し側（Phase 3 の API 層）が anime.csv 由来のメタデータを
`Response` に詰めて渡す。genre_baseline（ジャンル出現率の全体平均）も
同様に呼び出し側が用意し、`compute_catalog_genre_baseline` で作れる。
"""

from dataclasses import dataclass, field
from itertools import groupby
from statistics import mean, median

Label = str  # "loved" | "completed" | "dropped"

COMPLETED_LABELS = {"loved", "completed"}
DROPPED_LABELS = {"dropped"}


@dataclass(frozen=True)
class Response:
    anime_id: int
    label: Label
    episodes: int
    genres: list[str] = field(default_factory=list)
    members: int = 0


# 好みの軸（好むジャンルの上位1件から決まる）。ネガティブな語は使わない。
GENRE_AXIS = {
    "Action": "熱血・王道派", "Adventure": "熱血・王道派", "Shounen": "熱血・王道派",
    "Super Power": "熱血・王道派", "Martial Arts": "熱血・王道派", "Sports": "熱血・王道派",
    "Military": "熱血・王道派",
    "Psychological": "心理・重量級派", "Drama": "心理・重量級派", "Mystery": "心理・重量級派",
    "Thriller": "心理・重量級派", "Horror": "心理・重量級派", "Seinen": "心理・重量級派",
    "Dementia": "心理・重量級派", "Demons": "心理・重量級派",
    "Slice of Life": "癒し・日常派", "Comedy": "癒し・日常派", "School": "癒し・日常派",
    "Kids": "癒し・日常派", "Music": "癒し・日常派", "Parody": "癒し・日常派",
    "Sci-Fi": "SF・世界観派", "Space": "SF・世界観派", "Mecha": "SF・世界観派",
    "Fantasy": "SF・世界観派", "Magic": "SF・世界観派", "Supernatural": "SF・世界観派",
    "Game": "SF・世界観派",
    "Romance": "恋愛・人間ドラマ派", "Shoujo": "恋愛・人間ドラマ派", "Josei": "恋愛・人間ドラマ派",
    "Harem": "恋愛・人間ドラマ派", "Shounen Ai": "恋愛・人間ドラマ派", "Shoujo Ai": "恋愛・人間ドラマ派",
    "Yaoi": "恋愛・人間ドラマ派", "Yuri": "恋愛・人間ドラマ派",
}
DEFAULT_AXIS = "多彩派"

# 話数レンジ別完走率（要件修正: 単一の「50%を切る話数」は長編完走者では外れ値化し、
# 表示・特徴量ともに1本のデータで壊れるため、4バケットの分布に置き換える）。
# (下限, 上限 or None=上限なし, 表示ラベル)
EPISODE_BUCKET_DEFS: list[tuple[int, int | None, str]] = [
    (1, 13, "〜13話"),
    (14, 26, "14〜26話"),
    (27, 50, "27〜50話"),
    (51, None, "51話〜"),
]
MIN_BUCKET_COUNT = 3


def compute_completion_rate(responses: list[Response]) -> float | None:
    n_completed = sum(1 for r in responses if r.label in COMPLETED_LABELS)
    n_dropped = sum(1 for r in responses if r.label in DROPPED_LABELS)
    denom = n_completed + n_dropped
    if denom == 0:
        return None
    return n_completed / denom


def compute_endurance_episodes(responses: list[Response]) -> int | None:
    """完走した作品の話数の分布から、累積完走率が50%を切る話数を返す。

    注意: 外れ値1本（例: 長編1本だけ完走）で最大値に張り付く弱点があるため、
    ユーザー表示にはこの関数の戻り値を直接使わないこと。予測モデルの
    `endurance_episodes` 特徴量（gain重要度は低い）にのみ使う。同じ弱点を持っていた
    `episode_gap` 特徴量は2026-08の再学習で `episode_bucket_completion_rate` /
    `episode_bucket_gap`（`compute_episode_buckets`ベース）に置き換えて廃止した
    （詳細: reports/retrain_episode_bucket.md）。表示には
    `compute_episode_buckets` / `best_episode_bucket` を使う。
    """
    labeled = [r for r in responses if r.label in COMPLETED_LABELS | DROPPED_LABELS]
    if not labeled:
        return None

    labeled_sorted = sorted(labeled, key=lambda r: r.episodes)
    n_completed = 0
    n_total = 0
    last_ok_episodes = 0

    for episodes, group in groupby(labeled_sorted, key=lambda r: r.episodes):
        group = list(group)
        n_total += len(group)
        n_completed += sum(1 for r in group if r.label in COMPLETED_LABELS)
        if n_completed / n_total >= 0.5:
            last_ok_episodes = episodes
        else:
            break

    return last_ok_episodes


def bucket_index_for_episodes(episodes: int) -> int:
    """話数がどのバケットに属するかのインデックスを返す（範囲外は最終バケットに丸める）。"""
    for i, (lo, hi, _label) in enumerate(EPISODE_BUCKET_DEFS):
        if hi is None or episodes <= hi:
            return i
    return len(EPISODE_BUCKET_DEFS) - 1


def compute_episode_buckets(responses: list[Response]) -> list[dict]:
    """話数を4バケットに分け、バケットごとの完走率と本数を返す。

    本数が MIN_BUCKET_COUNT 未満のバケットは completion_rate を None にする
    （呼び出し側は「データ不足」として表示する）。
    """
    labeled = [r for r in responses if r.label in COMPLETED_LABELS | DROPPED_LABELS and r.episodes > 0]

    buckets = []
    for i, (lo, hi, label) in enumerate(EPISODE_BUCKET_DEFS):
        in_bucket = [
            r for r in labeled
            if r.episodes >= lo and (hi is None or r.episodes <= hi)
        ]
        count = len(in_bucket)
        if count > 0:
            n_completed = sum(1 for r in in_bucket if r.label in COMPLETED_LABELS)
            completion_rate = n_completed / count
        else:
            completion_rate = None
        buckets.append({
            "index": i,
            "range": label,
            "completion_rate": (round(completion_rate, 4) if completion_rate is not None else None),
            "count": count,
            "sufficient": count >= MIN_BUCKET_COUNT,
        })
    return buckets


def best_episode_bucket(buckets: list[dict]) -> dict | None:
    """本数が十分な（MIN_BUCKET_COUNT以上の）バケットのうち、完走率が最も高いものを返す。

    十分なバケットが1つもなければ None（「データ不足」）。
    """
    candidates = [b for b in buckets if b["sufficient"] and b["completion_rate"] is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda b: b["completion_rate"])


def compute_genre_preferences(
    responses: list[Response],
    genre_baseline: dict[str, float],
    top_n: int = 5,
) -> dict[str, list[str]]:
    """完走作品のジャンル出現率 − 全体平均 の上位/下位を返す。"""
    completed = [r for r in responses if r.label in COMPLETED_LABELS]
    if not completed:
        return {"preferred": [], "avoided": []}

    genre_counts: dict[str, int] = {}
    for r in completed:
        for g in r.genres:
            genre_counts[g] = genre_counts.get(g, 0) + 1

    n_completed = len(completed)
    diffs = {
        g: (count / n_completed) - genre_baseline.get(g, 0.0)
        for g, count in genre_counts.items()
    }
    ranked = sorted(diffs.items(), key=lambda kv: kv[1], reverse=True)

    preferred = [g for g, diff in ranked if diff > 0][:top_n]
    avoided = [g for g, diff in reversed(ranked) if diff < 0][:top_n]
    return {"preferred": preferred, "avoided": avoided}


def compute_mainstream_affinity(responses: list[Response]) -> dict[str, float] | None:
    """回答した作品の登録者数分布（話題作追従度）。"""
    members = [r.members for r in responses if r.members > 0]
    if not members:
        return None
    return {"median_members": float(median(members)), "mean_members": float(mean(members))}


def compute_catalog_genre_baseline(catalog: list[dict]) -> dict[str, float]:
    """作品カタログ（anime_id, genres を持つレコード列）からジャンル出現率の全体平均を作る。

    呼び出し側が anime.csv 由来のカタログを一度だけ渡して事前計算する想定。
    """
    n = len(catalog)
    if n == 0:
        return {}
    counts: dict[str, int] = {}
    for item in catalog:
        for g in item.get("genres", []):
            counts[g] = counts.get(g, 0) + 1
    return {g: count / n for g, count in counts.items()}


def _durability_bucket(best_bucket: dict | None) -> str:
    if best_bucket is None:
        return "バランス型"
    if best_bucket["index"] == 0:
        return "短距離"
    if best_bucket["index"] == 1:
        return "中距離"
    return "長距離"


def generate_type_name(best_bucket: dict | None, preferred_genres: list[str]) -> str:
    """話数レンジ別完走率(短/中/長) × 好みの軸 の組み合わせでタイプ名を生成する。

    ネガティブな語（飽きっぽい、脱落型 等）は使わない。
    """
    durability = _durability_bucket(best_bucket)
    axis = GENRE_AXIS.get(preferred_genres[0], DEFAULT_AXIS) if preferred_genres else DEFAULT_AXIS
    return f"{durability}・{axis}タイプ"


def build_profile(responses: list[Response], genre_baseline: dict[str, float]) -> dict:
    """要件定義書 4.3 の6項目をまとめて算出する。"""
    endurance_episodes = compute_endurance_episodes(responses)
    episode_buckets = compute_episode_buckets(responses)
    best_bucket = best_episode_bucket(episode_buckets)
    completion_rate = compute_completion_rate(responses)
    genre_prefs = compute_genre_preferences(responses, genre_baseline)
    mainstream_affinity = compute_mainstream_affinity(responses)
    type_name = generate_type_name(best_bucket, genre_prefs["preferred"])

    return {
        "type_name": type_name,
        "endurance_episodes": endurance_episodes,
        "episode_buckets": episode_buckets,
        "best_episode_bucket": best_bucket,
        "completion_rate": completion_rate,
        "preferred_genres": genre_prefs["preferred"],
        "avoided_genres": genre_prefs["avoided"],
        "mainstream_affinity": mainstream_affinity,
    }
