"""POST /feedback の最小実装。実データベースへの接続は行わず、
ローカルのJSONLファイルに追記する（テーブル設計は `api/models/feedback_table.py` を参照）。
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from api.models.feedback_table import FeedbackRecord

_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "feedback_log.jsonl"
_lock = Lock()


def save_feedback(session_id: str, anime_id: int, result: str) -> FeedbackRecord:
    record = FeedbackRecord(
        session_id=session_id, anime_id=anime_id, result=result,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")
    return record
