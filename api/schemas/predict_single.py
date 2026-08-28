"""POST /predict/single のリクエスト/レスポンス。"""

from typing import Literal

from pydantic import BaseModel, Field

from api.schemas.predict import Reason, ResponseInput

Confidence = Literal["high", "medium", "low"]


class PredictSingleRequest(BaseModel):
    responses: list[ResponseInput] = Field(min_length=5)
    target_anime_id: int


class AnimeMeta(BaseModel):
    title: str
    episodes: int | None
    genres: list[str]
    year: int | None


class Factors(BaseModel):
    negative: list[Reason]
    positive: list[Reason]


class EvidenceItem(BaseModel):
    title: str
    episodes: int | None
    genre: str | None
    result: Literal["completed", "dropped"]


class DropoutCurvePoint(BaseModel):
    episode: int
    rate: float


class NextRecommendation(BaseModel):
    anime_id: int
    title: str
    completion_prob: float


class PredictSingleResponse(BaseModel):
    anime: AnimeMeta
    completion_prob: float
    population_completion_rate: float
    relative_risk: float | None
    confidence: Confidence
    is_estimated: bool
    is_ongoing: bool
    factors: Factors
    evidence: list[EvidenceItem]
    evidence_insight: str | None
    dropout_curve: list[DropoutCurvePoint] | None
    peak_dropout_episode: int | None
    survival_after_peak: float | None
    insufficient_data: bool
    advice: str
    # UI仕様書5.5: 完走率80%以上のとき「次に完走できる作品」導線を出す。それ未満は空配列。
    next_recommendations: list[NextRecommendation]


class AlreadyAnsweredResponse(BaseModel):
    already_answered: Literal[True] = True
    anime_id: int
    label: str
    message: str
