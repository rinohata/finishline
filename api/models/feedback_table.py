"""`feedback` テーブルのスキーマ定義（要件定義書 6.4）。

Phase 5 で実データベースに接続する際に、このカラム定義をそのまま
DDL（例: SQLAlchemy Table / Alembic migration）に落とし込む想定。
Phase 3 時点では実データベースへの接続は行わず、`services/feedback_store.py` が
ローカルファイルへの追記のみを行う最小実装とする。
"""

from dataclasses import dataclass

TABLE_NAME = "feedback"

# (column_name, sql_type, constraints)
COLUMNS: list[tuple[str, str, str]] = [
    ("id", "BIGINT", "PRIMARY KEY AUTOINCREMENT"),
    ("session_id", "VARCHAR(64)", "NOT NULL"),
    ("anime_id", "INTEGER", "NOT NULL"),
    ("result", "VARCHAR(16)", "NOT NULL"),  # 'completed' | 'dropped' | 'watching'
    ("created_at", "TIMESTAMP", "NOT NULL DEFAULT CURRENT_TIMESTAMP"),
]


@dataclass(frozen=True)
class FeedbackRecord:
    session_id: str
    anime_id: int
    result: str
    created_at: str
