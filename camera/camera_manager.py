"""
camera/camera_manager.py
========================
File này dùng để làm gì?
    Quản lý webcam bằng OpenCV: liệt kê camera, mở/tắt camera, đặt độ phân
    giải, đọc frame, đo FPS, ghi video (VideoWriter).

Dữ liệu đi vào từ đâu?
    - Chỉ số camera và độ phân giải từ Settings (qua core.engine).
    - Frame đã vẽ kết quả (annotated) do engine gửi vào để ghi video.

Dữ liệu được xử lý như thế nào?
    Trên Windows dùng backend DirectShow (CAP_DSHOW) để mở camera nhanh và ổn
    định. Kiểm tra camera mở được và đọc được frame đầu tiên, nếu không sẽ báo
    lỗi rõ ràng (CameraError).

Dữ liệu được truyền sang module nào?
    Frame BGR (numpy array) được trả cho core.engine -> detection.

Kết quả trả về ở đâu?
    read() trả (ok, frame); stop_recording() trả đường dẫn video đã lưu.
"""
from __future__ import annotations

import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


class CameraError(Exception):
    """Lỗi liên quan đến webcam (không mở được, mất kết nối...)."""


class FPSCounter:
    """Tính FPS trung bình trên N frame gần nhất."""

    def __init__(self, window: int = 30) -> None:
        self._times: deque = deque(maxlen=window)

    def update(self) -> float:
        self._times.append(time.perf_counter())
        if len(self._times) < 2:
            return 0.0
        span = self._times[-1] - self._times[0]
        return (len(self._times) - 1) / span if span > 0 else 0.0

    def reset(self) -> None:
        self._times.clear()


class CameraManager:
    def __init__(self) -> None:
        self._cap: Optional[cv2.VideoCapture] = None
        self._writer: Optional[cv2.VideoWriter] = None
        self._record_path: Optional[Path] = None
        self._lock = threading.Lock()
        self.index: Optional[int] = None
        self.frame_size: Tuple[int, int] = (0, 0)

    # ------------------------------------------------------------ helpers
    @staticmethod
    def backend() -> int:
        return cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY

    @classmethod
    def list_cameras(cls, max_index: int = 5) -> List[int]:
        """Thử mở các camera 0..max_index-1 và trả về những camera đọc được frame."""
        found: List[int] = []
        for idx in range(max_index):
            cap = cv2.VideoCapture(idx, cls.backend())
            try:
                if cap.isOpened():
                    ok, _ = cap.read()
                    if ok:
                        found.append(idx)
            finally:
                cap.release()
        logger.info("Available cameras: %s", found)
        return found

    # ------------------------------------------------------------ camera
    def open(self, index: int = 0, width: int = 640, height: int = 480) -> None:
        self.release()
        logger.info("Opening camera %s at %sx%s", index, width, height)
        cap = cv2.VideoCapture(index, self.backend())
        if not cap.isOpened():
            cap.release()
            raise CameraError(
                f"Cannot open camera {index}. Check that the webcam is connected, "
                f"not used by another application (Zoom, Teams...) and that camera "
                f"access is allowed in Windows Privacy settings."
            )
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        frame = None
        for _ in range(10):  # một số webcam cần vài frame để "khởi động"
            ok, frame = cap.read()
            if ok and frame is not None:
                break
            time.sleep(0.05)
        else:
            cap.release()
            raise CameraError(f"Camera {index} opened but returned no image.")

        with self._lock:
            self._cap = cap
            self.index = index
            self.frame_size = (frame.shape[1], frame.shape[0])
        logger.info("Camera %s ready, actual size %sx%s", index, *self.frame_size)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            cap = self._cap
        if cap is None:
            return False, None
        try:
            ok, frame = cap.read()
        except cv2.error as exc:
            logger.error("Camera read error: %s", exc)
            return False, None
        return (ok and frame is not None), frame

    @property
    def is_opened(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened()

    def release(self) -> None:
        self.stop_recording()
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                logger.info("Camera %s released", self.index)
            self._cap = None

    # ------------------------------------------------------------ recording
    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._writer is not None

    def start_recording(self, path: Path, fps: float, frame_size: Tuple[int, int]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(path), fourcc, max(5.0, float(fps)), frame_size)
        if not writer.isOpened():
            raise CameraError(f"Cannot create video file: {path}")
        with self._lock:
            if self._writer is not None:
                self._writer.release()
            self._writer = writer
            self._record_path = path
        logger.info("Recording started: %s (%.1f fps, %sx%s)", path, fps, *frame_size)
        return path

    def write(self, frame: np.ndarray) -> None:
        with self._lock:
            if self._writer is not None:
                self._writer.write(frame)

    def stop_recording(self) -> Optional[Path]:
        with self._lock:
            writer, path = self._writer, self._record_path
            self._writer, self._record_path = None, None
        if writer is not None:
            writer.release()
            logger.info("Recording saved: %s", path)
        return path
