"""POST /predict のリクエスト/レスポンス。"""

from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["loved", "completed", "dropped"]


class ResponseInput(BaseModel):
    anime_id: int
    label: Label


class PredictRequest(BaseModel):
    responses: list[ResponseInput] = Field(min_length=5)


class Reason(BaseModel):
    type: str
    text: str


class EpisodeBucket(BaseModel):
    range: str
    completion_rate: float | None
    count: int


class ProfileOut(BaseModel):
    type_name: str
    endurance_episodes: int | None
    episode_buckets: list[EpisodeBucket]
    best_episode_bucket: EpisodeBucket | None
    completion_rate: float | None
    completion_rate_avg: float
    preferred_genres: list[str]
    avoided_genres: list[str]
    curve: list[dict]


class AtRiskItem(BaseModel):
    anime_id: int
    title: str
    year: int | None
    episodes: int | None
    genres: list[str]
    completion_prob: float
    population_completion_rate: float
    relative_risk: float | None
    popularity_rank: int | None
    is_ongoing: bool
    reasons: list[Reason]


class WillCompleteItem(BaseModel):
    anime_id: int
    title: str
    year: int | None
    episodes: int | None
    genres: list[str]
    completion_prob: float
    population_completion_rate: float
    relative_completion: float | None
    is_ongoing: bool
    reason: str


class BaselineItem(BaseModel):
    anime_id: int
    title: str
    is_at_risk: bool


class BaselineComparison(BaseModel):
    popular: list[BaselineItem]
    personalized: list[BaselineItem]
    overlap: int


class PredictResponse(BaseModel):
    profile: ProfileOut
    at_risk: list[AtRiskItem]
    at_risk_threshold: float
    will_complete: list[WillCompleteItem]
    baseline_comparison: BaselineComparison
