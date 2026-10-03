"""
dataset/dataset_manager.py
==========================
File này dùng để làm gì?
    Quản lý dataset data/hand_signs.csv: đọc, kiểm tra hợp lệ, ghi thêm mẫu,
    đếm số mẫu từng gesture, thêm/xóa gesture, xóa toàn bộ dữ liệu.

Dữ liệu đi vào từ đâu?
    - Vector đặc trưng từ dataset/collector.py (thu thập bằng webcam).
    - Lệnh thêm/xóa gesture từ gui/dataset_view.py.
    - Danh sách gesture đã đăng ký trong SQLite (GestureRepository).

Dữ liệu được xử lý như thế nào?
    CSV có cấu trúc: x0,y0,z0,x1,y1,z1,...,x20,y20,z20,label
    Khi đọc: kiểm tra đủ cột, ép kiểu số, loại bỏ dòng lỗi/thiếu dữ liệu.
    Khi xóa gesture: ghi ra file tạm rồi thay thế (an toàn nếu lỗi giữa chừng).

Dữ liệu được truyền sang module nào?
    training/train_model.py (X, y), gui/dataset_view.py (bảng thống kê).

Kết quả trả về ở đâu?
    DataFrame, dict số lượng mẫu, danh sách tóm tắt (gesture, số mẫu, trạng thái).
"""
from __future__ import annotations

import csv
import re
import threading
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from config.config import DATASET_CSV
from recognition.feature_extractor import CSV_COLUMNS, FEATURE_COLUMNS, LABEL_COLUMN
from utils.constants import FEATURE_DIM, display_gesture
from utils.logger import get_logger

logger = get_logger(__name__)

MIN_SAMPLES_FOR_TRAINING = 10


class DatasetError(Exception):
    """Dataset không tồn tại / sai cấu trúc / không đủ dữ liệu."""


def normalize_gesture_name(name: str) -> str:
    """'Thumb Up' / 'Ngón cái' -> 'thumb_up' / 'ngon_cai' (chỉ a-z, 0-9, _)."""
    text = unicodedata.normalize("NFKD", name or "").replace("đ", "d").replace("Đ", "D")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


class DatasetManager:
    def __init__(self, csv_path: Path = DATASET_CSV, gesture_repo=None) -> None:
        self.csv_path = Path(csv_path)
        self.gesture_repo = gesture_repo
        self._lock = threading.Lock()
        self.ensure_file()

    # ---------------------------------------------------------------- file
    def ensure_file(self) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists() or self.csv_path.stat().st_size == 0:
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_COLUMNS)
            logger.info("Created empty dataset %s", self.csv_path)

    def load(self) -> pd.DataFrame:
        with self._lock:
            if not self.csv_path.exists():
                return pd.DataFrame(columns=CSV_COLUMNS)
            try:
                df = pd.read_csv(self.csv_path)
            except pd.errors.EmptyDataError:
                return pd.DataFrame(columns=CSV_COLUMNS)
            except Exception as exc:
                raise DatasetError(f"Cannot read dataset {self.csv_path}: {exc}") from exc

        missing = [c for c in CSV_COLUMNS if c not in df.columns]
        if missing:
            raise DatasetError(
                f"Dataset has wrong structure, missing columns: {', '.join(missing[:6])}"
                f"{'...' if len(missing) > 6 else ''}"
            )
        df = df[CSV_COLUMNS].copy()
        df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
        df[LABEL_COLUMN] = df[LABEL_COLUMN].astype(str).str.strip()
        before = len(df)
        df = df.dropna()
        df = df[df[LABEL_COLUMN].isin(["", "nan"]) == False]  # noqa: E712
        if len(df) < before:
            logger.warning("Dropped %d invalid rows from dataset", before - len(df))
        return df.reset_index(drop=True)

    def append_samples(self, samples: Sequence[np.ndarray], label: str) -> int:
        if not samples:
            return 0
        rows = []
        for s in samples:
            arr = np.asarray(s, dtype=np.float32).flatten()
            if arr.size != FEATURE_DIM or not np.all(np.isfinite(arr)):
                continue
            rows.append([f"{v:.6f}" for v in arr] + [label])
        with self._lock:
            self.ensure_file()
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)
        logger.debug("Appended %d samples for %s", len(rows), label)
        return len(rows)

    # ------------------------------------------------------------- gestures
    def counts(self) -> Dict[str, int]:
        df = self.load()
        return {str(k): int(v) for k, v in df[LABEL_COLUMN].value_counts().items()}

    def total_samples(self) -> int:
        return sum(self.counts().values())

    def list_gestures(self) -> List[str]:
        names = list(self.gesture_repo.names()) if self.gesture_repo else []
        for label in self.counts():
            if label not in names:
                names.append(label)
        return names

    def display_name(self, key: str) -> str:
        return display_gesture(key)

    def summary(self, min_ready: int = 100) -> List[Dict[str, object]]:
        counts = self.counts()
        rows = []
        for g in self.list_gestures():
            n = counts.get(g, 0)
            status = "Empty" if n == 0 else ("Ready" if n >= min_ready else "Not enough")
            rows.append({"gesture": g, "display": self.display_name(g), "count": n, "status": status})
        return rows

    def add_gesture(self, name: str) -> str:
        key = normalize_gesture_name(name)
        if not key:
            raise DatasetError("Gesture name is empty or invalid (use letters and numbers).")
        if key in self.list_gestures():
            raise DatasetError(f"Gesture '{key}' already exists.")
        if self.gesture_repo:
            self.gesture_repo.add(key, name.strip())
        logger.info("Added gesture %s", key)
        return key

    def add_gestures(self, keys: Sequence[str]) -> Tuple[List[str], List[str]]:
        """Thêm nhiều gesture theo KEY có sẵn (vd bảng chữ cái NNKH). Trả (đã thêm, đã có)."""
        existing = set(self.list_gestures())
        added, skipped = [], []
        for key in keys:
            if key in existing:
                skipped.append(key)
                continue
            if self.gesture_repo:
                self.gesture_repo.add(key, display_gesture(key, "en"))
            added.append(key)
        logger.info("Added %d gestures (%d already existed)", len(added), len(skipped))
        return added, skipped

    def delete_gesture(self, key: str) -> int:
        df = self.load()
        removed = int((df[LABEL_COLUMN] == key).sum())
        if removed:
            self._rewrite(df[df[LABEL_COLUMN] != key])
        if self.gesture_repo:
            self.gesture_repo.delete(key)
        logger.info("Deleted gesture %s (%d samples)", key, removed)
        return removed

    def clear(self) -> None:
        self._rewrite(pd.DataFrame(columns=CSV_COLUMNS))
        logger.info("Dataset cleared")

    def _rewrite(self, df: pd.DataFrame) -> None:
        tmp = self.csv_path.with_suffix(".tmp")
        with self._lock:
            df.to_csv(tmp, index=False, float_format="%.6f", encoding="utf-8")
            tmp.replace(self.csv_path)

    # ------------------------------------------------------------ validate
    def validate(self, min_per_class: int = MIN_SAMPLES_FOR_TRAINING) -> Tuple[bool, List[str]]:
        msgs: List[str] = []
        try:
            counts = self.counts()
        except DatasetError as exc:
            return False, [str(exc)]
        if not counts:
            return False, ["Dataset is empty. Collect data in the Dataset screen first."]
        if len(counts) < 2:
            msgs.append("At least 2 gestures are required to train a classifier.")
        small = [f"{g} ({n})" for g, n in counts.items() if n < min_per_class]
        if small:
            msgs.append(f"Gestures with fewer than {min_per_class} samples: {', '.join(small)}")
        return (not msgs), msgs
