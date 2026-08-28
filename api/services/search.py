"""GET /questions の検索・絞り込み・並び替えロジック。

`question_pool.json`（250本）に加え、`anime.csv` カタログ全体からも
タイトル検索でヒットさせる（UI仕様書3.3: 「question_pool 外の作品もヒットさせる」）。
"""

import unicodedata

from api.services.data_store import DataStore

# 複合スコア = split_score * (1-POPULARITY_WEIGHT) + popularity_percentile * POPULARITY_WEIGHT
#
# 人気作は完走率がもともと高く（母集団平均94%前後）split_score（エントロピー）が低く出るため、
# 単純な低ウェイトの合成では人気作が上位に出てこない。実際の question_pool（250本）で
# w を掃引したところ、w=0.70 が「先頭20本に登録者数上位200位以内の作品が3本以上」を満たす
# 最小値だった（w=0.35時点では1本のみ）。安全マージンを見て 0.75 を採用する（先頭20本中4本）。
POPULARITY_WEIGHT = 0.75


def normalize_text(s: str) -> str:
    """カタカナ→ひらがな正規化 + 大小文字・全角半角の統一。"""
    s = unicodedata.normalize("NFKC", s).casefold()
    result = []
    for ch in s:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:  # カタカナ -> ひらがな
            result.append(chr(code - 0x60))
        else:
            result.append(ch)
    return "".join(result)


def _composite_score(split_score: float, popularity_percentile: float) -> float:
    return split_score * (1 - POPULARITY_WEIGHT) + popularity_percentile * POPULARITY_WEIGHT


def build_catalog(store: DataStore) -> list[dict]:
    """question_pool + カタログ全体を1つの検索対象リストにする。"""
    items = []
    for p in store.question_pool:
        items.append({
            "anime_id": p["anime_id"], "title": p["title"], "year": p["year"],
            "episodes": p["episodes"], "genres": p["genres"],
            "completion_rate": p["completion_rate"], "split_score": p["split_score"],
            "popularity_percentile": (
                store.anime.loc[p["anime_id"], "popularity_percentile"]
                if p["anime_id"] in store.anime.index else 0.0
            ),
            "in_pool": True,
        })

    for anime_id, row in store.anime.iterrows():
        if anime_id in store.pool_ids:
            continue
        completion_rate = store.population_completion_rate_B.get(anime_id)
        items.append({
            "anime_id": int(anime_id), "title": row["title"], "year": (int(row["year"]) if row["year"] == row["year"] else None),
            "episodes": (int(row["episodes_num"]) if row["episodes_num"] == row["episodes_num"] else None),
            "genres": row["genre_list"], "completion_rate": completion_rate, "split_score": None,
            "popularity_percentile": row["popularity_percentile"] if row["popularity_percentile"] == row["popularity_percentile"] else 0.0,
            "in_pool": False,
        })
    return items


def search_questions(
    store: DataStore, catalog: list[dict], *, q: str | None = None, genre: list[str] | None = None,
    year_from: int | None = None, year_to: int | None = None, episodes_max: int | None = None,
    sort: str = "split_score", limit: int = 20, offset: int = 0,
) -> tuple[list[dict], int]:
    items = catalog

    if q:
        nq = normalize_text(q)
        items = [it for it in items if it["title"] and nq in normalize_text(it["title"])]
    if genre:
        genre_set = set(genre)
        items = [it for it in items if genre_set & set(it["genres"])]
    if year_from is not None:
        items = [it for it in items if it["year"] is not None and it["year"] >= year_from]
    if year_to is not None:
        items = [it for it in items if it["year"] is not None and it["year"] <= year_to]
    if episodes_max is not None:
        items = [it for it in items if it["episodes"] is not None and it["episodes"] <= episodes_max]

    if sort == "popularity":
        items = sorted(items, key=lambda it: -it["popularity_percentile"])
    elif sort == "low_completion":
        items = sorted(items, key=lambda it: (it["completion_rate"] is None, it["completion_rate"] or 0))
    elif sort == "year_desc":
        items = sorted(items, key=lambda it: -(it["year"] or 0))
    else:  # split_score (デフォルト・おすすめ順): 情報量とポピュラリティの複合スコア
        items = sorted(
            items,
            key=lambda it: -_composite_score(it["split_score"] or 0.0, it["popularity_percentile"]),
        )

    total = len(items)
    page = items[offset:offset + limit]
    return page, total
