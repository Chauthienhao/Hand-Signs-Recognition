"""
dataset/collector.py
====================
File này dùng để làm gì?
    Thu thập dữ liệu huấn luyện tự động bằng webcam cho một gesture:
    đếm ngược -> mỗi khoảng thời gian lấy 1 mẫu -> trích đặc trưng ->
    gán nhãn -> ghi vào CSV, cho đến khi đủ số mẫu yêu cầu.

Dữ liệu đi vào từ đâu?
    - Nhãn gesture + số mẫu do người dùng chọn ở gui/dataset_view.py.
    - list[HandInfo] mỗi frame do core.engine truyền vào process().

Dữ liệu được xử lý như thế nào?
    Máy trạng thái: IDLE -> COUNTDOWN (3 giây chuẩn bị) -> COLLECTING -> DONE.
    Nếu có 2 tay, lấy tay có độ tin cậy cao nhất. Mẫu được gom vào bộ đệm và
    ghi xuống CSV theo từng đợt (giảm thao tác ổ đĩa).

Dữ liệu được truyền sang module nào?
    Vector đặc trưng + nhãn -> dataset/dataset_manager.py (CSV).

Kết quả trả về ở đâu?
    snapshot() trả trạng thái/tiến độ cho GUI và để vẽ lên khung hình.
"""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

from dataset.dataset_manager import DatasetError, DatasetManager
from detection.landmark_extractor import HandInfo
from recognition.feature_extractor import extract_features
from utils.logger import get_logger

logger = get_logger(__name__)


class CollectorState(str, Enum):
    IDLE = "Idle"
    COUNTDOWN = "Get ready"
    COLLECTING = "Collecting"
    DONE = "Done"
    CANCELLED = "Cancelled"
    ERROR = "Error"


class DataCollector:
    def __init__(self, dataset_manager: DatasetManager, interval_ms: int = 50,
                 countdown_s: float = 3.0, flush_every: int = 50, mirror_left: bool = True) -> None:
        self.dataset_manager = dataset_manager
        self.interval = max(0.0, interval_ms / 1000.0)
        self.countdown_s = countdown_s
        self.flush_every = flush_every
        self.mirror_left = mirror_left
        self._lock = threading.Lock()
        self._state = CollectorState.IDLE
        self._label: Optional[str] = None
        self._target = 0
        self._collected = 0
        self._buffer: List[np.ndarray] = []
        self._start_time = 0.0
        self._last_sample = 0.0
        self._message = ""

    # -------------------------------------------------------------- control
    def start(self, label: str, target: int) -> None:
        if not label:
            raise ValueError("Gesture label is required.")
        if target <= 0:
            raise ValueError("Number of samples must be greater than 0.")
        with self._lock:
            self._label, self._target = label, int(target)
            self._collected, self._buffer = 0, []
            self._state = CollectorState.COUNTDOWN
            self._start_time = time.monotonic()
            self._message = ""
        logger.info("Start collecting %d samples for '%s'", target, label)

    def cancel(self) -> None:
        with self._lock:
            if self._state in (CollectorState.COUNTDOWN, CollectorState.COLLECTING):
                self._flush()
                self._state = CollectorState.CANCELLED
                logger.info("Collection cancelled (%d samples saved)", self._collected)

    @property
    def active(self) -> bool:
        with self._lock:
            return self._state in (CollectorState.COUNTDOWN, CollectorState.COLLECTING)

    # -------------------------------------------------------------- process
    def process(self, hands: List[HandInfo], aspect: float = 1.0) -> None:
        with self._lock:
            now = time.monotonic()
            if self._state == CollectorState.COUNTDOWN:
                if now - self._start_time < self.countdown_s:
                    return
                self._state = CollectorState.COLLECTING
                self._last_sample = 0.0
            if self._state != CollectorState.COLLECTING:
                return
            if not hands:
                self._message = "Show your hand to the camera"
                return
            self._message = ""
            if now - self._last_sample < self.interval:
                return

            hand = max(hands, key=lambda h: h.handedness_score)
            try:
                self._buffer.append(extract_features(hand, aspect, self.mirror_left))
            except ValueError as exc:
                logger.warning("Skip invalid sample: %s", exc)
                return
            self._collected += 1
            self._last_sample = now

            if len(self._buffer) >= self.flush_every:
                self._flush()
            if self._collected >= self._target and self._state == CollectorState.COLLECTING:
                self._flush()
                if self._state != CollectorState.ERROR:
                    self._state = CollectorState.DONE
                    logger.info("Collected %d samples for '%s'", self._collected, self._label)

    def _flush(self) -> None:
        """Ghi bộ đệm xuống CSV (gọi khi đang giữ lock)."""
        if not self._buffer or not self._label:
            return
        try:
            self.dataset_manager.append_samples(self._buffer, self._label)
        except (DatasetError, OSError) as exc:
            logger.error("Cannot save samples: %s", exc)
            self._state = CollectorState.ERROR
            self._message = f"Cannot save samples: {exc}"
        self._buffer = []

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            left = 0.0
            if self._state == CollectorState.COUNTDOWN:
                left = max(0.0, self.countdown_s - (time.monotonic() - self._start_time))
            return {
                "state": self._state, "label": self._label, "collected": self._collected,
                "target": self._target, "countdown": left, "message": self._message,
            }
