"""
detection/hand_detector.py
==========================
File này dùng để làm gì?
    Bọc (wrap) MediaPipe Tasks - Gesture Recognizer để:
      1) phát hiện tối đa 1-2 bàn tay trong frame,
      2) lấy 21 landmark mỗi bàn tay,
      3) xác định tay trái/phải + độ tin cậy,
      4) lấy luôn gesture có sẵn của MediaPipe (dùng khi chưa train model riêng).
    Tự động tải file model gesture_recognizer.task ở lần chạy đầu tiên.

Dữ liệu đi vào từ đâu?
    Frame BGR từ camera/camera_manager.py (qua core.engine).

Dữ liệu được xử lý như thế nào?
    BGR -> RGB -> mp.Image -> recognize_for_video(timestamp tăng dần)
    -> kết quả thô -> LandmarkExtractor -> list[HandInfo].

Dữ liệu được truyền sang module nào?
    list[HandInfo] -> recognition/predictor.py, dataset/collector.py, core.engine.

Kết quả trả về ở đâu?
    Giá trị trả về của detect().
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, List, Optional

import cv2
import numpy as np

from config.config import MP_MODEL_PATH, MP_MODEL_URL
from detection.landmark_extractor import HandInfo, LandmarkExtractor
from utils.helpers import download_file
from utils.logger import get_logger

logger = get_logger(__name__)

MIN_MODEL_SIZE = 1_000_000  # file .task hợp lệ khoảng 8 MB


class HandDetectorError(Exception):
    """Lỗi khởi tạo hoặc chạy MediaPipe."""


def ensure_model(
    path: Path = MP_MODEL_PATH,
    url: str = MP_MODEL_URL,
    status_cb: Optional[Callable[[str], None]] = None,
) -> Path:
    """Đảm bảo file model MediaPipe tồn tại, nếu chưa có thì tải về."""
    path = Path(path)
    if path.exists() and path.stat().st_size > MIN_MODEL_SIZE:
        return path

    logger.info("MediaPipe model not found, downloading from %s", url)
    if status_cb:
        status_cb("Downloading MediaPipe model (~8 MB)...")

    def progress(done: int, total: int) -> None:
        if status_cb and total:
            status_cb(f"Downloading MediaPipe model... {done * 100 // total}%")

    try:
        download_file(url, path, progress)
    except Exception as exc:
        raise HandDetectorError(
            "Cannot download the MediaPipe model file.\n"
            f"Please check the Internet connection, or download it manually from:\n{url}\n"
            f"and save it as:\n{path}"
        ) from exc
    logger.info("MediaPipe model saved to %s", path)
    return path


class HandDetector:
    def __init__(
        self,
        num_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_path: Path = MP_MODEL_PATH,
    ) -> None:
        self.num_hands = num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.model_path = Path(model_path)
        self._recognizer = None
        self._mp = None
        self._last_ts = 0

    # ---------------------------------------------------------------- setup
    @property
    def is_loaded(self) -> bool:
        return self._recognizer is not None

    def load(self, status_cb: Optional[Callable[[str], None]] = None) -> None:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
        except ImportError as exc:
            raise HandDetectorError(
                "MediaPipe is not installed or cannot be loaded.\nRun: python -m pip install --upgrade mediapipe\nThen check with: python check_environment.py"
            ) from exc

        model_file = ensure_model(self.model_path, status_cb=status_cb)
        if status_cb:
            status_cb("Loading hand detector...")
        self.close()
        try:
            # Đọc model dạng bytes -> tránh lỗi đường dẫn có dấu tiếng Việt trên Windows
            base_options = mp_python.BaseOptions(model_asset_buffer=model_file.read_bytes())
            options = vision.GestureRecognizerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_hands=int(self.num_hands),
                min_hand_detection_confidence=float(self.min_detection_confidence),
                min_hand_presence_confidence=float(self.min_detection_confidence),
                min_tracking_confidence=float(self.min_tracking_confidence),
            )
            self._recognizer = vision.GestureRecognizer.create_from_options(options)
            self._mp = mp
        except Exception as exc:
            self._recognizer = None
            raise HandDetectorError(
                f"Cannot initialize MediaPipe Gesture Recognizer: {exc}\n"
                f"If the model file is corrupted, delete {model_file} and try again."
            ) from exc
        logger.info(
            "Hand detector ready (hands=%s, det=%.2f, track=%.2f)",
            self.num_hands, self.min_detection_confidence, self.min_tracking_confidence,
        )

    def update_config(self, num_hands: int, min_detection_confidence: float,
                      min_tracking_confidence: float) -> bool:
        """Cập nhật cấu hình; trả True nếu có thay đổi (cần load lại)."""
        new = (int(num_hands), float(min_detection_confidence), float(min_tracking_confidence))
        old = (self.num_hands, self.min_detection_confidence, self.min_tracking_confidence)
        if new == old:
            return False
        self.num_hands, self.min_detection_confidence, self.min_tracking_confidence = new
        return True

    # ------------------------------------------------------------ detection
    def detect(self, frame_bgr: np.ndarray) -> List[HandInfo]:
        if self._recognizer is None:
            raise HandDetectorError("Hand detector is not loaded.")
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        # Chế độ VIDEO yêu cầu timestamp (ms) tăng nghiêm ngặt
        ts = int(time.monotonic() * 1000)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts
        result = self._recognizer.recognize_for_video(mp_image, ts)
        return LandmarkExtractor.from_gesture_result(result)

    def close(self) -> None:
        if self._recognizer is not None:
            try:
                self._recognizer.close()
            except Exception as exc:  # pragma: no cover
                logger.warning("Error closing recognizer: %s", exc)
            self._recognizer = None


if __name__ == "__main__":
    # python -m detection.hand_detector  -> chỉ tải model MediaPipe
    print("Model:", ensure_model(status_cb=print))
