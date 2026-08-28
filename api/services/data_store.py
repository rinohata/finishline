"""起動時に一度だけ読み込む静的データの保持。

`animelist.csv`（1億行超）は起動時に読まない。使うのは
`anime.csv`（作品メタデータ、小さい）・`question_pool.json`・`dropout_curves.json`・
学習済みモデルと、Phase 2 で事前計算して永続化したルックアップのみ。
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from api.services.profile import compute_catalog_genre_baseline

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"


def _extract_year(aired: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", str(aired))
    return int(m.group()) if m else None


class DataStore:
    def __init__(self) -> None:
        anime = pd.read_csv(RAW_DIR / "anime.csv")
        anime["year"] = anime["Aired"].apply(_extract_year)
        anime["episodes_num"] = pd.to_numeric(anime["Episodes"], errors="coerce")
        anime["score_num"] = pd.to_numeric(anime["Score"], errors="coerce")
        anime["members_num"] = pd.to_numeric(anime["Members"], errors="coerce")
        anime["members_log"] = np.log1p(anime["members_num"])
        anime["genre_list"] = anime["Genres"].apply(
            lambda s: [g.strip() for g in str(s).split(",")] if pd.notna(s) else []
        )
        anime["source"] = anime["Source"].fillna("Unknown")
        anime["title"] = anime["Japanese name"].where(
            anime["Japanese name"].notna() & (anime["Japanese name"] != "Unknown"), anime["Name"]
        )

        all_genres = sorted({g for gl in anime["genre_list"] for g in gl if g and g != "Unknown"})
        for g in all_genres:
            anime[f"genre_{g}"] = anime["genre_list"].apply(lambda gl: 1 if g in gl else 0)
        anime["popularity_percentile"] = anime["members_num"].rank(pct=True)

        self.anime = anime.set_index("MAL_ID")
        self.all_genres = all_genres

        self.genre_baseline = compute_catalog_genre_baseline(
            [{"anime_id": int(idx), "genres": row.genre_list} for idx, row in self.anime.iterrows()]
        )

        with open(DATA_DIR / "question_pool.json", encoding="utf-8") as f:
            self.question_pool: list[dict] = json.load(f)
        self.pool_ids = {p["anime_id"] for p in self.question_pool}
        self.pool_by_id = {p["anime_id"]: p for p in self.question_pool}

        with open(DATA_DIR / "dropout_curves.json", encoding="utf-8") as f:
            curves = json.load(f)
        self.dropout_curves = {c["anime_id"]: c for c in curves}

        with open(PROC_DIR / "anime_population_completion_rate_B.json", encoding="utf-8") as f:
            raw = json.load(f)
        self.population_completion_rate_B = {int(k): v for k, v in raw.items()}

        with open(PROC_DIR / "anime_avg_completion_rate_A_train.json", encoding="utf-8") as f:
            raw = json.load(f)
        self.anime_avg_completion_rate_A = {int(k): v for k, v in raw.items()}
        with open(PROC_DIR / "anime_avg_completion_rate_A_train_fallback.json", encoding="utf-8") as f:
            self.anime_avg_fallback = json.load(f)["mean"]
        with open(PROC_DIR / "anime_n_labeled_A_train.json", encoding="utf-8") as f:
            raw = json.load(f)
        self.anime_n_labeled_A = {int(k): v for k, v in raw.items()}

        with open(PROC_DIR / "anime_peak_at_risk.json", encoding="utf-8") as f:
            raw = json.load(f)
        self.anime_peak_at_risk = {int(k): v for k, v in raw.items()}

        with open(PROC_DIR / "anime_is_ongoing.json", encoding="utf-8") as f:
            self.is_ongoing_ids: set[int] = set(json.load(f))

        with open(PROC_DIR / "population_stats.json", encoding="utf-8") as f:
            self.population_stats = json.load(f)

        emb = np.load(PROC_DIR / "anime_embeddings.npy")
        emb_ids = np.load(PROC_DIR / "anime_embeddings_ids.npy")
        self.embeddings = {int(aid): emb[i] for i, aid in enumerate(emb_ids)}

        self.model = lgb.Booster(model_file=str(MODELS_DIR / "dropout_predictor.lgb"))
        with open(MODELS_DIR / "feature_columns.json", encoding="utf-8") as f:
            self.feature_columns = json.load(f)

        registrations_rank = self.anime["members_num"].fillna(0).rank(ascending=False, method="min")
        self.registration_rank = registrations_rank.to_dict()
        self.pool_completion_rate_mean = float(
            np.mean([p["completion_rate"] for p in self.question_pool])
        )

        by_registration = self.anime["members_num"].fillna(0).sort_values(ascending=False)
        self.top300_by_registration = [int(aid) for aid in by_registration.index[:300]]
        self.top3000_by_registration = [int(aid) for aid in by_registration.index[:3000]]

    def episodes(self, anime_id: int) -> int | None:
        if anime_id in self.anime.index:
            v = self.anime.loc[anime_id, "episodes_num"]
            return int(v) if pd.notna(v) else None
        return None

    def genres(self, anime_id: int) -> list[str]:
        if anime_id in self.anime.index:
            return self.anime.loc[anime_id, "genre_list"] or []
        return []

    def members(self, anime_id: int) -> int:
        if anime_id in self.anime.index:
            v = self.anime.loc[anime_id, "members_num"]
            return int(v) if pd.notna(v) else 0
        return 0

    def anime_type(self, anime_id: int) -> str | None:
        if anime_id in self.anime.index:
            v = self.anime.loc[anime_id, "Type"]
            return v if pd.notna(v) else None
        return None

    def score(self, anime_id: int) -> float | None:
        if anime_id in self.anime.index:
            v = self.anime.loc[anime_id, "score_num"]
            return float(v) if pd.notna(v) else None
        return None

    def title(self, anime_id: int) -> str | None:
        if anime_id in self.anime.index:
            v = self.anime.loc[anime_id, "title"]
            return v if pd.notna(v) else None
        return None

    def year(self, anime_id: int) -> int | None:
        if anime_id in self.anime.index:
            v = self.anime.loc[anime_id, "year"]
            return int(v) if pd.notna(v) else None
        return None

    def population_completion_rate(self, anime_id: int) -> float:
        return self.population_completion_rate_B.get(anime_id, self.pool_completion_rate_mean)

    def anime_avg_for_model(self, anime_id: int) -> float:
        """モデルに渡す作品平均完走率。放送継続中の作品は右側打ち切り
        （視聴継続者のほぼ全員が`watching`のまま滞留し、決着＝completed/droppedが
        離脱者に偏る）により機械的に0近辺へ偏るため、実績値として使わずNaNとし、
        他の特徴量（ジャンル・話数・ユーザープロファイル等）で判断させる。"""
        if anime_id in self.is_ongoing_ids:
            return float("nan")
        return self.anime_avg_completion_rate_A.get(anime_id, self.anime_avg_fallback)

    def is_ongoing(self, anime_id: int) -> bool:
        return anime_id in self.is_ongoing_ids

    def n_labeled_for_confidence(self, anime_id: int) -> int:
        return self.anime_n_labeled_A.get(anime_id, 0)

    def embedding(self, anime_id: int):
        return self.embeddings.get(anime_id)


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return DataStore()
