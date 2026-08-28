"""GET /questions のリクエスト/レスポンス。"""

from typing import Literal

from pydantic import BaseModel

SortOption = Literal["split_score", "popularity", "low_completion", "year_desc"]


class QuestionItem(BaseModel):
    anime_id: int
    title: str
    year: int | None
    episodes: int | None
    genres: list[str]
    completion_rate: float | None
    split_score: float | None
    in_pool: bool


class QuestionsResponse(BaseModel):
    items: list[QuestionItem]
    total: int
    limit: int
    offset: int
