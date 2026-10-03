"""
database/history.py
===================
File này dùng để làm gì?
    Các repository thao tác bảng lịch sử:
      - HistoryRepository: bảng recognition_history (lưu, tìm kiếm, lọc theo
        ngày, xóa, xuất CSV, thống kê).
      - TrainingHistoryRepository: bảng training_history (kết quả mỗi lần train).

Dữ liệu đi vào từ đâu?
    - core.engine gửi kết quả nhận diện (gesture, confidence, hand).
    - training/train_model.py gửi chỉ số đánh giá model.
    - gui gửi điều kiện tìm kiếm/lọc.

Dữ liệu được xử lý như thế nào?
    Câu lệnh SQL có tham số (tránh SQL injection). Timestamp dạng
    'YYYY-MM-DD HH:MM:SS' nên lọc ngày bằng so sánh chuỗi.

Dữ liệu được truyền sang module nào?
    gui/history_view.py, gui/statistics_view.py, gui/training_view.py.

Kết quả trả về ở đâu?
    list[dict], số liệu thống kê, hoặc file CSV khi xuất.
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from database.database import Database
from utils.helpers import now_str
from utils.logger import get_logger

logger = get_logger(__name__)

HISTORY_COLUMNS = ["id", "gesture", "confidence", "hand", "source", "timestamp"]


class HistoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, gesture: str, confidence: float, hand: str, source: str = "ml",
            timestamp: Optional[str] = None) -> int:
        return self.db.execute(
            "INSERT INTO recognition_history(gesture, confidence, hand, source, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (gesture, round(float(confidence), 4), hand, source, timestamp or now_str()),
        )

    def search(self, gesture: str = "", date_from: Optional[date] = None,
               date_to: Optional[date] = None, hand: str = "", limit: int = 2000) -> List[Dict[str, Any]]:
        where, params = [], []
        if gesture:
            where.append("gesture LIKE ?")
            params.append(f"%{gesture.strip().lower().replace(' ', '_')}%")
        if date_from:
            where.append("timestamp >= ?")
            params.append(f"{date_from.isoformat()} 00:00:00")
        if date_to:
            where.append("timestamp <= ?")
            params.append(f"{date_to.isoformat()} 23:59:59")
        if hand:
            where.append("hand = ?")
            params.append(hand)
        sql = "SELECT * FROM recognition_history"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(int(limit))
        return self.db.query(sql, params)

    def delete_ids(self, ids: Sequence[int]) -> int:
        if not ids:
            return 0
        marks = ",".join("?" * len(ids))
        return self.db.execute(f"DELETE FROM recognition_history WHERE id IN ({marks})", list(ids))

    def clear(self) -> int:
        return self.db.execute("DELETE FROM recognition_history")

    @staticmethod
    def export_csv(rows: List[Dict[str, Any]], path: Path) -> int:
        path = Path(path)
        # utf-8-sig để Excel trên Windows mở đúng tiếng Việt
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=HISTORY_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Exported %d history rows to %s", len(rows), path)
        return len(rows)

    # ------------------------------------------------------------- thống kê
    def total_count(self) -> int:
        return int(self.db.query_one("SELECT COUNT(*) AS n FROM recognition_history")["n"])

    def count_by_gesture(self) -> List[Tuple[str, int]]:
        rows = self.db.query(
            "SELECT gesture, COUNT(*) AS n FROM recognition_history GROUP BY gesture ORDER BY n DESC"
        )
        return [(r["gesture"], int(r["n"])) for r in rows]

    def count_by_hand(self) -> List[Tuple[str, int]]:
        rows = self.db.query("SELECT hand, COUNT(*) AS n FROM recognition_history GROUP BY hand")
        return [(r["hand"], int(r["n"])) for r in rows]

    def most_common(self) -> Optional[Tuple[str, int]]:
        data = self.count_by_gesture()
        return data[0] if data else None

    def average_confidence(self) -> Optional[float]:
        row = self.db.query_one("SELECT AVG(confidence) AS a FROM recognition_history")
        return float(row["a"]) if row and row["a"] is not None else None

    def count_by_day(self, days: int = 14) -> List[Tuple[str, int]]:
        start = date.today() - timedelta(days=days - 1)
        rows = self.db.query(
            "SELECT substr(timestamp, 1, 10) AS d, COUNT(*) AS n FROM recognition_history "
            "WHERE timestamp >= ? GROUP BY d",
            (f"{start.isoformat()} 00:00:00",),
        )
        found = {r["d"]: int(r["n"]) for r in rows}
        return [((start + timedelta(days=i)).isoformat(), found.get((start + timedelta(days=i)).isoformat(), 0))
                for i in range(days)]


class TrainingHistoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, algorithm: str, metrics: Dict[str, float], num_samples: int,
            num_classes: int, test_size: float, model_path: str = "") -> int:
        return self.db.execute(
            "INSERT INTO training_history(algorithm, accuracy, precision_score, recall, f1_score, "
            "num_samples, num_classes, test_size, model_path, trained_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (algorithm, metrics.get("accuracy"), metrics.get("precision"), metrics.get("recall"),
             metrics.get("f1"), num_samples, num_classes, test_size, model_path, now_str()),
        )

    def all(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.db.query("SELECT * FROM training_history ORDER BY id DESC LIMIT ?", (limit,))

    def latest(self) -> Optional[Dict[str, Any]]:
        return self.db.query_one("SELECT * FROM training_history ORDER BY id DESC LIMIT 1")

    def average_accuracy(self) -> Optional[float]:
        row = self.db.query_one("SELECT AVG(accuracy) AS a FROM training_history")
        return float(row["a"]) if row and row["a"] is not None else None
