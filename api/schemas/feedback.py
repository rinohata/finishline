"""POST /feedback のリクエスト/レスポンス。"""

from typing import Literal

from pydantic import BaseModel

FeedbackResult = Literal["completed", "dropped", "watching"]


class FeedbackRequest(BaseModel):
    session_id: str
    anime_id: int
    result: FeedbackResult


class FeedbackResponse(BaseModel):
    accepted: bool
    message: str
