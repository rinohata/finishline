"""POST /predict, POST /predict/single のコアロジック。

モデルは離脱確率（定義A）を予測するので、完走率 = 1 - 離脱確率 として
UIに渡す直前に変換する。離脱確率そのものは一切レスポンスに含めない
（`relative_risk` は完走率から導出する副次指標であり、離脱確率の直接表示ではない）。
"""

from api.ml.inference import build_profile_vectors, predict_dropped_prob
from api.services import explain
from api.services.data_store import DataStore
from api.services.genres import jp as _jp
from api.services.profile import (
    EPISODE_BUCKET_DEFS,
    Response,
    bucket_index_for_episodes,
    build_profile,
)

CONFIDENCE_MIN_LABELED = {"high": 200, "medium": 30}

LABEL_JP = {"loved": "完走", "completed": "完走", "dropped": "途中で止まった"}

# UI仕様書5.5: 完走率80%以上のとき「次に完走できる作品」導線を出す。
NEXT_RECOMMENDATION_THRESHOLD = 0.80
NEXT_RECOMMENDATION_MAX_ITEMS = 3

# at_risk 抽出の絶対しきい値のみを使う（相対条件=ユーザー内 平均-1σ は削除済み）。
# 候補を話題作（登録者数上位300作品）に限定したことで、以前の広い候補プール
# （登録者数上位3,000件・250件）で観測された「常に上限5件が埋まる」飽和が緩和される見込みのため、
# 0.85に戻す。
AT_RISK_ABSOLUTE_THRESHOLD = 0.85
AT_RISK_MAX_ITEMS = 5

# has_meaningful_peak の緩和後しきい値（Phase 3確認④を踏まえた調整）。
PEAK_NEAR_FINAL_RATIO = 0.9
PEAK_MIN_AT_RISK = 100
PEAK_MIN_TOTAL_EPISODES = 3

# will_complete 修正: 完走確率の降順だけでソートすると、1話の映画・OVA
# （定義上ほぼ100%完走）が上位を独占し推薦として意味をなさなくなる問題への対応。
WILL_COMPLETE_EXCLUDED_TYPES = {"Movie", "Music", "Special"}
WILL_COMPLETE_MIN_EPISODES = 6
WILL_COMPLETE_MIN_MEMBERS = 50_000
WILL_COMPLETE_MIN_SCORE = 7.0
WILL_COMPLETE_MAX_ITEMS = 10
WILL_COMPLETE_GENRE_CAP = 3
WILL_COMPLETE_MIN_POOL_SIZE = 10

# will_complete: relative_completion（母集団完走率に対する相対値）が1.0未満の作品は
# 出さない。「一般平均より完走しにくい」作品を「あなたが完走できる作品」として
# 見せるのは矛盾するため（例: 灰羽連盟86% vs 一般87%）。10件出せない場合でも
# 質を優先し、件数を減らす（テストユーザー10人の実測では候補プールが十分大きく
# 10件を切ることは無かったが、ジャンル多様化フィルタと組み合わさると起こりうる）。
WILL_COMPLETE_MIN_RELATIVE_COMPLETION = 1.0

# 前提条件チェック: 直接のprequelが存在し、ユーザーがそのどれも回答していない作品は
# 「前作を知らないのに続編を薦める」ことになるため候補から除外する。
# ただし対象作品のMembers（登録者数）が全prequelのMembersのPREREQUISITE_MEMBERS_RATIO倍
# 以上ある場合は、対象作品自体が実質的なシリーズの入り口とみなし除外しない
# （例: 進撃の巨人1期の直接prequelが配信専用OVA「悔いなき選択」になっているが、
# 誰もがまずTVシリーズ1期から見る）。
# 倍率7: 8では進撃の巨人1期（実測7.8369倍）を含む本命ケースを救済できなかったため、
# 7と8の差分2件（進撃の巨人1期 vs 悔いなき選択OVA、Another vs The Other - Inga）の
# 中身を確認した上で7に決めた。両方とも「OVAは本編を補完するサイドコンテンツで
# 視聴の前提条件ではない」という同じ構造で、救済して問題ない事例だった
# （reports/franchise_prerequisite.md 参照）。
# 6以下にさらに下げないのは、その差分の中身を未確認のため
# （過剰救済＝本当に前提が必要な続編まで通してしまうリスクを避ける）。
PREREQUISITE_MEMBERS_RATIO = 7


def _passes_prerequisite_check(store: DataStore, anime_id: int, answered_ids: set[int]) -> bool:
    """前提条件チェックを通過するか（True=候補に残す、False=除外）。

    anime_relations.json に無い作品・prequelを持たない作品は常に通す（判定不能・該当なし）。
    複数prequelがある場合は、Members比率で救済されない「実質的な前提作品」のうち
    1本でも回答済みであれば通す（全prequelを見ていることまでは要求しない）。
    """
    entry = store.anime_relations.get(anime_id)
    if entry is None or not entry["prequels"]:
        return True

    cand_members = store.members(anime_id)
    effective_prequels = [
        p for p in entry["prequels"]
        if cand_members < PREREQUISITE_MEMBERS_RATIO * store.members(p)
    ]
    if not effective_prequels:
        return True  # 全prequelがMembers比率ルールで救済された

    return any(p in answered_ids for p in effective_prequels)


def _has_meaningful_peak(store: DataStore, curve_entry: dict | None, total_episodes: int | None) -> bool:
    if curve_entry is None or curve_entry.get("insufficient_data"):
        return False
    peak = curve_entry.get("peak_dropout_episode")
    anime_id = curve_entry.get("anime_id")
    if peak is None or total_episodes is None:
        return False
    if peak == 1:
        return False
    if peak > total_episodes * PEAK_NEAR_FINAL_RATIO:
        return False
    at_risk = store.anime_peak_at_risk.get(anime_id)
    if at_risk is None or at_risk < PEAK_MIN_AT_RISK:
        return False
    if total_episodes <= PEAK_MIN_TOTAL_EPISODES:
        return False
    return True


def to_responses(store: DataStore, raw_responses: list[dict]) -> list[Response]:
    return [
        Response(
            anime_id=r["anime_id"],
            label="dropped" if r["label"] == "dropped" else "completed",
            episodes=store.episodes(r["anime_id"]) or 0,
            genres=store.genres(r["anime_id"]),
            members=store.members(r["anime_id"]),
        )
        for r in raw_responses
    ]


def _confidence(n_labeled: float) -> str:
    if n_labeled >= CONFIDENCE_MIN_LABELED["high"]:
        return "high"
    if n_labeled >= CONFIDENCE_MIN_LABELED["medium"]:
        return "medium"
    return "low"


def _relative_risk(completion_prob: float, population_completion_rate: float) -> float | None:
    """(1 - 個人完走率) / (1 - 母集団完走率)。母集団完走率が1.0に近い作品は分母をわずかに床上げする。"""
    denom = max(1 - population_completion_rate, 0.01)
    return round((1 - completion_prob) / denom, 2)


def _relative_completion(completion_prob: float, population_completion_rate: float) -> float | None:
    """個人完走率 / 母集団完走率。at_riskのrelative_riskと対称の設計（will_complete用）。
    母集団完走率が0に近い作品は分母をわずかに床上げする。"""
    denom = max(population_completion_rate, 0.01)
    return round(completion_prob / denom, 2)


def _will_complete_candidate_pool(store: DataStore, answered_ids: set[int], best_bucket: dict | None) -> list[int]:
    """will_complete の候補プールを構築する（修正1: 属性フィルタ、修正3: 話数バケット連動）。

    「合う話数」バケット、またはその1つ上のバケットに属する作品に限定する
    （診断結果と推薦を連動させるため）。該当作品がWILL_COMPLETE_MIN_POOL_SIZE件に
    満たない場合のみ、隣接バケットまで広げる。best_bucketがNone（データ不足）の場合は
    バケット制限をかけない。
    """
    base = [
        aid for aid in store.anime.index
        if aid not in answered_ids
        and not store.is_ongoing(aid)
        and store.anime_type(aid) not in WILL_COMPLETE_EXCLUDED_TYPES
        and (store.episodes(aid) or 0) > WILL_COMPLETE_MIN_EPISODES
        and store.members(aid) >= WILL_COMPLETE_MIN_MEMBERS
        and (store.score(aid) or 0) >= WILL_COMPLETE_MIN_SCORE
        and _passes_prerequisite_check(store, aid, answered_ids)
    ]

    if best_bucket is None:
        return base

    n_buckets = len(EPISODE_BUCKET_DEFS)
    idx = best_bucket["index"]

    def _filter_by_indices(indices: set[int]) -> list[int]:
        return [aid for aid in base if bucket_index_for_episodes(store.episodes(aid) or 0) in indices]

    # 「合う話数」バケット + その1つ上のバケット
    primary_indices = {idx, min(idx + 1, n_buckets - 1)}
    candidates = _filter_by_indices(primary_indices)
    if len(candidates) >= WILL_COMPLETE_MIN_POOL_SIZE:
        return candidates

    # 不足時のみ隣接バケット（1つ下・2つ上）まで広げる
    widened_indices = primary_indices | {max(idx - 1, 0), min(idx + 2, n_buckets - 1)}
    return _filter_by_indices(widened_indices)


def _select_diverse_will_complete(scored: list[tuple[int, float]], store: DataStore) -> list[tuple[int, float]]:
    """修正4: 主ジャンルごとの上限3件とする貪欲法で上位10件を選ぶ（同一ジャンル偏重を防ぐ）。"""
    selected: list[tuple[int, float]] = []
    genre_counts: dict[str, int] = {}
    for aid, prob in scored:
        genres = store.genres(aid)
        primary_genre = genres[0] if genres else "unknown"
        if genre_counts.get(primary_genre, 0) >= WILL_COMPLETE_GENRE_CAP:
            continue
        selected.append((aid, prob))
        genre_counts[primary_genre] = genre_counts.get(primary_genre, 0) + 1
        if len(selected) >= WILL_COMPLETE_MAX_ITEMS:
            break
    return selected


def _build_curve(store: DataStore, responses: list[Response]) -> list[dict]:
    """ユーザー自身の回答を話数レンジ3バケット固定で区切り、累積完走率を全体平均と比較する。

    以前は実測話数（11, 12, 24, 25, 358話など）をそのままX軸にしていたため、
    値が不規則でラベルが重なって読めなかった。EPISODE_BUCKET_DEFS の上限を
    固定の目盛りとして使い、各目盛りまでの累積完走率を点として並べる
    （回答が届いていない目盛りは打たない）。
    """
    labeled = [r for r in responses if r.label in ("completed", "dropped") and r.episodes]
    if not labeled:
        return []
    max_ep = max(r.episodes for r in labeled)
    curve = []
    for lo, hi, label in EPISODE_BUCKET_DEFS:
        upper = hi if hi is not None else max_ep
        subset = [r for r in labeled if r.episodes <= upper]
        if not subset:
            continue
        n_completed = sum(1 for r in subset if r.label == "completed")
        user_rate = n_completed / len(subset)

        pool_subset = [p for p in store.question_pool if p["episodes"] <= upper]
        avg_rate = (
            sum(p["completion_rate"] for p in pool_subset) / len(pool_subset)
            if pool_subset else store.pool_completion_rate_mean
        )
        curve.append({"range": label, "user": round(user_rate, 4), "avg": round(avg_rate, 4)})
    return curve


def build_predict_response(store: DataStore, raw_responses: list[dict]) -> dict:
    responses = to_responses(store, raw_responses)
    answered_ids = {r.anime_id for r in responses}

    profile_dict = build_profile(responses, store.genre_baseline)
    profile_vectors = build_profile_vectors(store, responses)

    # at_risk: 「話題作だけど続かないかも」を成立させるため、話題作（登録者数上位300作品）に限定する。
    # 放送中作品は除外する: anime_avg特徴量をNaN化しても、学習ラベル自体が右側打ち切りで
    # 「決着＝ほぼ全員離脱」に偏っているため予測値を信頼できない（再学習でも解消しないことを確認済み）。
    at_risk_candidates = [
        aid for aid in store.top300_by_registration
        if aid not in answered_ids and not store.is_ongoing(aid)
        and _passes_prerequisite_check(store, aid, answered_ids)
    ]
    at_risk_preds = predict_dropped_prob(store, profile_vectors, at_risk_candidates)
    at_risk_scored = sorted(zip(at_risk_candidates, 1 - at_risk_preds), key=lambda x: x[1])
    at_risk_ids = [(aid, prob) for aid, prob in at_risk_scored if prob < AT_RISK_ABSOLUTE_THRESHOLD][:AT_RISK_MAX_ITEMS]

    at_risk = []
    for aid, prob in at_risk_ids:
        reasons = explain.build_reasons(store, profile_vectors, aid)
        pop_rate = store.population_completion_rate(aid)
        at_risk.append({
            "anime_id": aid,
            "title": store.title(aid) or "",
            "year": store.year(aid),
            "episodes": store.episodes(aid),
            "genres": store.genres(aid),
            "completion_prob": round(float(prob), 4),
            "population_completion_rate": round(pop_rate, 4),
            "relative_risk": _relative_risk(float(prob), pop_rate),
            "popularity_rank": int(store.registration_rank.get(aid)) if store.registration_rank.get(aid) else None,
            "is_ongoing": store.is_ongoing(aid),
            "reasons": reasons,
        })

    # baseline_comparison: 「知らない良作を見つける」ため、話題作に絞らない広い候補プール
    # （登録者数上位3,000作品。question_pool選定・Phase 2の人気順比較分析と同じ候補ユニバース）を使う。
    # at_risk同様、放送中作品は予測を信頼できないため除外する。
    wide_candidates = [
        aid for aid in store.top3000_by_registration
        if aid not in answered_ids and not store.is_ongoing(aid)
    ]
    wide_preds = predict_dropped_prob(store, profile_vectors, wide_candidates)
    wide_scored = sorted(zip(wide_candidates, 1 - wide_preds), key=lambda x: -x[1])

    popular_top20 = sorted(wide_candidates, key=lambda aid: -store.members(aid))[:20]
    personalized_top20 = [aid for aid, _ in wide_scored[:20]]
    overlap = len(set(popular_top20) & set(personalized_top20))

    # UI仕様書4.8: 人気順トップ20とあなた向けトップ20を並べて、重なりの少なさを見せる。
    # 「続きにくい予測」の警告マークは at_risk と同じ絶対しきい値で判定する
    # （どちらのリストの作品でも、この人にとっての予測完走率が低ければ付く）。
    wide_prob_by_id = dict(wide_scored)

    def _baseline_item(aid: int) -> dict:
        prob = wide_prob_by_id.get(aid, 0.0)
        return {
            "anime_id": aid,
            "title": store.title(aid) or "",
            "is_at_risk": prob < AT_RISK_ABSOLUTE_THRESHOLD,
        }

    popular_items = [_baseline_item(aid) for aid in popular_top20]
    personalized_items = [_baseline_item(aid) for aid in personalized_top20]

    # will_complete: 予測完走率の降順だけでソートすると、1話の映画・OVA（定義上ほぼ100%完走）が
    # 上位を独占し推薦として意味をなさなくなる問題への対応（2026-08修正）。
    # 修正1: Type(映画/音楽/特番)・話数・登録者数・スコアで候補を絞る
    # 修正3: ユーザーの「合う話数」バケット（+1つ上）に候補を連動させる
    will_complete_candidates = _will_complete_candidate_pool(store, answered_ids, profile_dict["best_episode_bucket"])
    will_complete = []
    if will_complete_candidates:
        wc_preds = predict_dropped_prob(store, profile_vectors, will_complete_candidates)
        wc_completion = 1 - wc_preds
        # 修正2: 予測完走率そのものではなく、母集団完走率に対する相対値（relative_completion）でソートする。
        # at_riskのrelative_riskと対称の設計。
        wc_scored = sorted(
            zip(will_complete_candidates, wc_completion),
            key=lambda x: -_relative_completion(float(x[1]), store.population_completion_rate(x[0])),
        )
        # relative_completionが1.0未満（一般平均より完走しにくい）の作品は出さない
        wc_scored = [
            (aid, prob) for aid, prob in wc_scored
            if _relative_completion(float(prob), store.population_completion_rate(aid))
            >= WILL_COMPLETE_MIN_RELATIVE_COMPLETION
        ]
        # 修正4: 主ジャンルごとの上限3件とする貪欲法で多様性を確保する
        will_complete_ids = _select_diverse_will_complete(wc_scored, store)

        for aid, prob in will_complete_ids:
            pop_rate = store.population_completion_rate(aid)
            will_complete.append({
                "anime_id": aid,
                "title": store.title(aid) or "",
                "year": store.year(aid),
                "episodes": store.episodes(aid),
                "genres": store.genres(aid),
                "completion_prob": round(float(prob), 4),
                "population_completion_rate": round(pop_rate, 4),
                "relative_completion": _relative_completion(float(prob), pop_rate),
                "is_ongoing": store.is_ongoing(aid),
                "reason": explain.build_will_complete_reason(store, profile_vectors, aid, float(prob), pop_rate),
            })

    curve = _build_curve(store, responses)

    return {
        "profile": {
            "type_name": profile_dict["type_name"],
            "endurance_episodes": profile_dict["endurance_episodes"],
            "episode_buckets": profile_dict["episode_buckets"],
            "best_episode_bucket": profile_dict["best_episode_bucket"],
            "completion_rate": profile_dict["completion_rate"],
            # 質問プール（≒あなたが回答した候補群）の完走率平均。個別作品の一般平均
            # （population_completion_rate, /predict/single や at_risk で使う）とは
            # 算出母集団が異なる別の指標なので混同しないこと（修正4で命名を明確化）。
            "completion_rate_avg": round(store.pool_completion_rate_mean, 4),
            "preferred_genres": profile_dict["preferred_genres"],
            "avoided_genres": profile_dict["avoided_genres"],
            "curve": curve,
        },
        "at_risk": at_risk,
        "at_risk_threshold": AT_RISK_ABSOLUTE_THRESHOLD,
        "will_complete": will_complete,
        "baseline_comparison": {
            "popular": popular_items,
            "personalized": personalized_items,
            "overlap": overlap,
        },
    }


def build_predict_single_response(store: DataStore, raw_responses: list[dict], target_anime_id: int) -> dict:
    already = next((r for r in raw_responses if r["anime_id"] == target_anime_id), None)
    if already is not None:
        label = already["label"]
        return {
            "already_answered": True,
            "anime_id": target_anime_id,
            "label": label,
            "message": f"この作品は回答済みです（{LABEL_JP.get(label, label)}）",
        }

    responses = to_responses(store, raw_responses)
    profile_vectors = build_profile_vectors(store, responses)

    preds = predict_dropped_prob(store, profile_vectors, [target_anime_id])
    completion_prob = float(1 - preds[0])
    pop_rate = store.population_completion_rate(target_anime_id)

    curve_entry = store.dropout_curves.get(target_anime_id)
    total_episodes = store.episodes(target_anime_id)
    has_meaningful_peak = _has_meaningful_peak(store, curve_entry, total_episodes)
    insufficient_data = curve_entry is None or curve_entry.get("insufficient_data") or not has_meaningful_peak

    n_labeled_count = store.n_labeled_for_confidence(target_anime_id)
    is_estimated = target_anime_id not in store.anime.index or n_labeled_count == 0
    is_ongoing = store.is_ongoing(target_anime_id)

    # 放送中の作品は is_estimated と同様、メタデータベースの推定として扱い confidence を low に固定する。
    confidence = "low" if (is_estimated or is_ongoing) else _confidence(n_labeled_count)

    evidence, evidence_insight = explain.build_evidence(store, responses, target_anime_id)

    negative, positive = [], []
    episodes = store.episodes(target_anime_id)
    a_genres = store.genres(target_anime_id)
    best_bucket = profile_vectors.best_episode_bucket
    if episodes is not None and best_bucket is not None:
        if bucket_index_for_episodes(episodes) > best_bucket["index"]:
            negative.append({
                "type": "episode_bucket",
                "text": f"全{episodes}話（あなたが完走しやすいのは{best_bucket['range']}）",
            })
        else:
            positive.append({
                "type": "episode_bucket",
                "text": f"全{episodes}話は、あなたが完走しやすい話数レンジ内です",
            })
    # 分母が薄いジャンル（回答本数が少なく統計的に無意味な完走率0%/100%等）を根拠に
    # しないよう、at_risk/will_completeと同じ displayed_genre_hits を使う
    # （表示先頭2ジャンル・回答3本以上のみ）。
    genre_hits = explain.displayed_genre_hits(store, profile_vectors, target_anime_id)
    if genre_hits:
        g, rate = min(genre_hits, key=lambda x: x[1])
        (negative if rate < 0.5 else positive).append({
            "type": "genre", "text": f"{_jp(g)}のあなたの完走率は{rate*100:.0f}%",
        })

    if not insufficient_data:
        peak = curve_entry["peak_dropout_episode"]
        survival = curve_entry["survival_after_peak"]
        advice = f"まず{peak}話まで。越えられれば完走の可能性が高いです（{peak}話を超えた人の{survival*100:.0f}%が完走）"
        dropout_curve = curve_entry["dropout_curve"]
        peak_dropout_episode = peak
        survival_after_peak = survival
    else:
        advice = "この作品はデータが少なく、具体的な話数のアドバイスはできません"
        dropout_curve = None
        peak_dropout_episode = None
        survival_after_peak = None

    # UI仕様書5.5: 完走率80%以上は情報量が乏しくなるため「次に完走できる作品」を出す。
    next_recommendations = []
    if completion_prob >= NEXT_RECOMMENDATION_THRESHOLD:
        answered_ids = {r["anime_id"] for r in raw_responses} | {target_anime_id}
        next_candidates = [
            aid for aid in store.top3000_by_registration
            if aid not in answered_ids and not store.is_ongoing(aid)
        ]
        next_preds = predict_dropped_prob(store, profile_vectors, next_candidates)
        next_scored = sorted(zip(next_candidates, 1 - next_preds), key=lambda x: -x[1])
        for aid, prob in next_scored[:NEXT_RECOMMENDATION_MAX_ITEMS]:
            next_recommendations.append({
                "anime_id": aid,
                "title": store.title(aid) or "",
                "completion_prob": round(float(prob), 4),
            })

    return {
        "anime": {
            "title": store.title(target_anime_id) or "",
            "episodes": episodes,
            "genres": a_genres,
            "year": store.year(target_anime_id),
        },
        "completion_prob": round(completion_prob, 4),
        "population_completion_rate": round(pop_rate, 4),
        "relative_risk": _relative_risk(completion_prob, pop_rate),
        "confidence": confidence,
        "is_estimated": is_estimated,
        "is_ongoing": is_ongoing,
        "factors": {"negative": negative, "positive": positive},
        "evidence": evidence,
        "evidence_insight": evidence_insight,
        "dropout_curve": dropout_curve,
        "peak_dropout_episode": peak_dropout_episode,
        "survival_after_peak": survival_after_peak,
        "insufficient_data": insufficient_data,
        "advice": advice,
        "next_recommendations": next_recommendations,
    }
