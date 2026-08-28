"""reasons（/predict の at_risk）・evidence（/predict/single）の生成。

predict.py から分離: 「何を予測するか」と「なぜそう予測したか を言葉にするか」を
別モジュールにすることで、文言のチューニングがモデル・特徴量ロジックに触れずに行える。
"""

from api.ml.inference import UserProfileVectors, cos_sim
from api.services.data_store import DataStore
from api.services.profile import Response, bucket_index_for_episodes

GENRE_JP = {
    "Slice of Life": "日常系", "Comedy": "コメディ", "Drama": "ドラマ", "Romance": "恋愛",
    "Action": "アクション", "Adventure": "アドベンチャー", "Fantasy": "ファンタジー",
    "Sci-Fi": "SF", "Mystery": "ミステリー", "Psychological": "心理", "Horror": "ホラー",
    "Sports": "スポーツ", "School": "学園", "Supernatural": "超自然", "Music": "音楽",
    "Shounen": "少年向け", "Shoujo": "少女向け", "Seinen": "青年向け", "Josei": "女性向け",
    "Military": "ミリタリー", "Mecha": "メカ", "Historical": "歴史",
}


def _jp(genre: str) -> str:
    return GENRE_JP.get(genre, genre)


def build_reasons(store: DataStore, profile: UserProfileVectors, anime_id: int, max_reasons: int = 3) -> list[dict]:
    """候補作品に対する理由を最大3件、実データに基づいて生成する。"""
    reasons: list[dict] = []

    episodes = store.episodes(anime_id)
    best = profile.best_episode_bucket
    if episodes is not None and best is not None and bucket_index_for_episodes(episodes) > best["index"]:
        reasons.append({
            "type": "episode_bucket",
            "text": f"全{episodes}話。あなたが完走しやすいのは{best['range']}です",
        })

    a_genres = store.genres(anime_id)
    genre_hits = [(g, profile.genre_rate[g]) for g in a_genres if g in profile.genre_rate]
    if genre_hits:
        g, rate = min(genre_hits, key=lambda x: x[1])
        reasons.append({
            "type": "genre",
            "text": f"{_jp(g)}のあなたの完走率は{rate*100:.0f}%",
        })

    a_emb = store.embedding(anime_id)
    if a_emb is not None and profile.dropped_vector is not None:
        sim = cos_sim(a_emb, profile.dropped_vector)
        if sim is not None and sim > 0.75:
            reasons.append({
                "type": "similarity",
                "text": "途中で止まった作品と傾向が近いです",
            })

    if len(reasons) < max_reasons:
        pop_rate = store.population_completion_rate(anime_id)
        reasons.append({
            "type": "population",
            "text": f"一般的な完走率は{pop_rate*100:.0f}%です",
        })

    return reasons[:max_reasons]


def build_will_complete_reason(
    store: DataStore,
    profile: UserProfileVectors,
    anime_id: int,
    completion_prob: float,
    population_completion_rate: float,
) -> str:
    """完走できる作品(will_complete)の1行理由。

    修正5: 一般には完走率が低い作品でも、あなたの予測完走率がそれを大きく上回る場合は
    その差分を説明する（relative_completionが高いことの言語化）。それ以外は従来どおり
    ジャンル・埋め込み類似度による理由を使う。
    """
    if population_completion_rate < 0.6 and completion_prob - population_completion_rate > 0.15:
        return "一般には完走されにくいですが、あなたの傾向なら見切れそうです"

    a_genres = store.genres(anime_id)
    genre_hits = [(g, profile.genre_rate[g]) for g in a_genres if g in profile.genre_rate]
    if genre_hits:
        g, rate = max(genre_hits, key=lambda x: x[1])
        return f"{_jp(g)}の完走実績があります"
    if profile.completed_vector is not None:
        a_emb = store.embedding(anime_id)
        sim = cos_sim(a_emb, profile.completed_vector)
        if sim is not None and sim > 0.7:
            return "完走した作品と傾向が近いです"
    return "あなたの視聴傾向に合っています"


def _similarity_score(store: DataStore, target_id: int, candidate_id: int) -> float:
    target_genres = set(store.genres(target_id))
    cand_genres = set(store.genres(candidate_id))
    genre_overlap = len(target_genres & cand_genres) / max(len(target_genres | cand_genres), 1)

    target_ep = store.episodes(target_id)
    cand_ep = store.episodes(candidate_id)
    if target_ep and cand_ep:
        ep_closeness = 1.0 / (1.0 + abs(target_ep - cand_ep) / max(target_ep, 1))
    else:
        ep_closeness = 0.0

    emb_sim = cos_sim(store.embedding(target_id), store.embedding(candidate_id)) or 0.0
    return genre_overlap * 0.4 + ep_closeness * 0.2 + emb_sim * 0.4


def build_evidence(store: DataStore, responses: list[Response], target_anime_id: int, max_items: int = 3):
    scored = [
        (r, _similarity_score(store, target_anime_id, r.anime_id))
        for r in responses
        if r.anime_id != target_anime_id
    ]
    scored.sort(key=lambda x: -x[1])
    top = scored[:max_items]

    evidence = []
    for r, _score in top:
        evidence.append({
            "title": store.title(r.anime_id) or "(不明)",
            "episodes": store.episodes(r.anime_id),
            "genre": (store.genres(r.anime_id)[0] if store.genres(r.anime_id) else None),
            "result": r.label,
        })

    insight = None
    if len(top) >= 2:
        target_genres = set(store.genres(target_anime_id))
        genre_matches = [r for r, _ in top if set(r.genres) & target_genres]
        genre_outcomes = {r.label for r in genre_matches}
        target_ep = store.episodes(target_anime_id)
        ep_matches = [
            r for r, _ in top
            if store.episodes(r.anime_id) and target_ep and abs(store.episodes(r.anime_id) - target_ep) <= 3
        ]
        ep_outcomes = {r.label for r in ep_matches}
        if len(genre_matches) >= 2 and len(genre_outcomes) == 1:
            insight = f"話数より「{_jp(next(iter(target_genres), ''))}」が効いていそうです"
        elif len(ep_matches) >= 2 and len(ep_outcomes) == 1:
            insight = "ジャンルより話数の長さが効いていそうです"

    return evidence, insight
