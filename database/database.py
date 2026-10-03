"""
database/database.py
====================
File này dùng để làm gì?
    Quản lý kết nối SQLite (database/hand_signs.db), tạo bảng khi chạy lần
    đầu và cung cấp các hàm execute/query an toàn. Chứa GestureRepository
    quản lý danh sách gesture (kể cả gesture mới chưa có mẫu).

Dữ liệu đi vào từ đâu?
    Câu lệnh SQL + tham số từ database/history.py, dataset/dataset_manager.py.

Dữ liệu được xử lý như thế nào?
    Mỗi thao tác mở một kết nối riêng (an toàn khi gọi từ nhiều thread: GUI,
    camera, training), tự commit/rollback, ghi có khóa (lock).

Dữ liệu được truyền sang module nào?
    history.py, dataset_manager.py, gui (thông qua các repository).

Kết quả trả về ở đâu?
    query() trả list[dict]; execute() trả lastrowid hoặc số dòng bị ảnh hưởng.

Sơ đồ bảng (ERD):
    gestures(id PK, name UNIQUE, display_name, created_at)
    recognition_history(id PK, gesture, confidence, hand, source, timestamp)
    training_history(id PK, algorithm, accuracy, precision_score, recall,
                     f1_score, num_samples, num_classes, test_size, model_path, trained_at)
    recognition_history.gesture và training ... tham chiếu logic tới gestures.name
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

from config.config import DB_PATH
from utils.constants import DEFAULT_GESTURES, display_gesture
from utils.helpers import now_str
from utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS gestures (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recognition_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    gesture     TEXT NOT NULL,
    confidence  REAL NOT NULL,
    hand        TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'ml',
    timestamp   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_time ON recognition_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_history_gesture ON recognition_history(gesture);
CREATE TABLE IF NOT EXISTS training_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm       TEXT NOT NULL,
    accuracy        REAL,
    precision_score REAL,
    recall          REAL,
    f1_score        REAL,
    num_samples     INTEGER,
    num_classes     INTEGER,
    test_size       REAL,
    model_path      TEXT,
    trained_at      TEXT NOT NULL
);
"""


class DatabaseError(Exception):
    """Lỗi thao tác cơ sở dữ liệu."""


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = Path(path)
        self._write_lock = threading.Lock()
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        try:
            conn = sqlite3.connect(self.path, timeout=10)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Cannot open database {self.path}: {exc}") from exc
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(f"Database error: {exc}") from exc
        finally:
            conn.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock, self.connect() as conn:
            conn.executescript(SCHEMA)
        logger.info("Database ready: %s", self.path)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with self._write_lock, self.connect() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid if sql.lstrip().upper().startswith("INSERT") else cur.rowcount

    def executemany(self, sql: str, rows: Iterable[Sequence[Any]]) -> int:
        with self._write_lock, self.connect() as conn:
            cur = conn.executemany(sql, rows)
            return cur.rowcount

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
        rows = self.query(sql, params)
        return rows[0] if rows else None


class GestureRepository:
    """Bảng gestures: danh sách ký hiệu mà hệ thống quản lý."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self.seed_defaults()

    def seed_defaults(self) -> None:
        if self.db.query_one("SELECT COUNT(*) AS n FROM gestures")["n"] == 0:
            ts = now_str()
            self.db.executemany(
                "INSERT OR IGNORE INTO gestures(name, display_name, created_at) VALUES (?, ?, ?)",
                [(g, display_gesture(g, "en"), ts) for g in DEFAULT_GESTURES],
            )
            logger.info("Seeded %d default gestures", len(DEFAULT_GESTURES))

    def list_all(self) -> List[Dict[str, Any]]:
        return self.db.query("SELECT * FROM gestures ORDER BY id")

    def names(self) -> List[str]:
        return [row["name"] for row in self.list_all()]

    def exists(self, name: str) -> bool:
        return self.db.query_one("SELECT 1 AS x FROM gestures WHERE name = ?", (name,)) is not None

    def add(self, name: str, display_name: str) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO gestures(name, display_name, created_at) VALUES (?, ?, ?)",
            (name, display_name, now_str()),
        )

    def delete(self, name: str) -> int:
        return self.db.execute("DELETE FROM gestures WHERE name = ?", (name,))

    def display_name(self, name: str) -> Optional[str]:
        row = self.db.query_one("SELECT display_name FROM gestures WHERE name = ?", (name,))
        return row["display_name"] if row else None
