"""FinishLine API（Phase 3）。

起動時に読むのは `anime.csv`・`question_pool.json`・`dropout_curves.json`・
学習済みモデルと Phase 2 で永続化したルックアップのみ。`animelist.csv`（1億行超）は読まない。
"""

from fastapi import FastAPI, HTTPException, Query

from api.schemas.feedback import FeedbackRequest, FeedbackResponse
from api.schemas.predict import PredictRequest, PredictResponse
from api.schemas.predict_single import AlreadyAnsweredResponse, PredictSingleRequest, PredictSingleResponse
from api.schemas.questions import QuestionsResponse
from api.services import feedback_store, predict, search
from api.services.data_store import get_store
from api.services.genres import GENRE_JP

app = FastAPI(title="FinishLine API")


@app.on_event("startup")
def _warm_up() -> None:
    get_store()  # 起動時に一度だけロードしてキャッシュする


@app.get("/genres", response_model=dict[str, str])
def get_genres() -> dict[str, str]:
    """英語ジャンル名 -> 日本語表記の対応表。フロント側の表示・絞り込み選択肢の
    日本語化に使う（api/services/genres.py が唯一の翻訳表）。"""
    return GENRE_JP


@app.get("/questions", response_model=QuestionsResponse)
def get_questions(
    q: str | None = None,
    genre: list[str] | None = Query(default=None),
    year_from: int | None = None,
    year_to: int | None = None,
    episodes_max: int | None = None,
    sort: str = "split_score",
    limit: int = 20,
    offset: int = 0,
) -> QuestionsResponse:
    store = get_store()
    catalog = search.build_catalog(store)
    items, total = search.search_questions(
        store, catalog, q=q, genre=genre, year_from=year_from, year_to=year_to,
        episodes_max=episodes_max, sort=sort, limit=limit, offset=offset,
    )
    return QuestionsResponse(items=items, total=total, limit=limit, offset=offset)


@app.post("/predict", response_model=PredictResponse)
def post_predict(req: PredictRequest) -> PredictResponse:
    store = get_store()
    raw = [r.model_dump() for r in req.responses]
    result = predict.build_predict_response(store, raw)
    return PredictResponse(**result)


@app.post("/predict/single", response_model=PredictSingleResponse | AlreadyAnsweredResponse)
def post_predict_single(req: PredictSingleRequest):
    store = get_store()
    if req.target_anime_id not in store.anime.index:
        raise HTTPException(status_code=404, detail="anime_id not found in catalog")
    raw = [r.model_dump() for r in req.responses]
    result = predict.build_predict_single_response(store, raw, req.target_anime_id)
    return result


@app.post("/feedback", response_model=FeedbackResponse)
def post_feedback(req: FeedbackRequest) -> FeedbackResponse:
    feedback_store.save_feedback(req.session_id, req.anime_id, req.result)
    return FeedbackResponse(accepted=True, message="ありがとうございます。次回の判定に反映されます。")
