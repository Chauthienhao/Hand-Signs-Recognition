"""
core/engine.py
==============
File này dùng để làm gì?
    "Động cơ" xử lý thời gian thực, nối tất cả module lại theo đúng luồng:
        CAMERA -> OPENCV -> MEDIAPIPE -> 21 LANDMARKS -> FEATURE EXTRACTION
        -> ML CLASSIFIER -> GESTURE RESULT -> GUI + DATABASE
    Chạy trên một thread riêng để giao diện không bị đơ.

Dữ liệu đi vào từ đâu?
    - Frame từ camera/camera_manager.py.
    - Thiết lập từ config/config.py (Settings).
    - Lệnh điều khiển từ GUI: start/stop, chụp ảnh, quay video, thu thập dữ liệu.

Dữ liệu được xử lý như thế nào?
    Mỗi vòng lặp: đọc frame -> lật gương -> HandDetector.detect() ->
    Predictor.predict() -> (nếu đang thu thập) DataCollector.process() ->
    vẽ kết quả -> ghi video -> lưu lịch sử khi gesture thay đổi ->
    cập nhật FrameResult mới nhất (có khóa thread).

Dữ liệu được truyền sang module nào?
    - FrameResult -> gui (main_window lấy định kỳ bằng get_latest()).
    - Kết quả nhận diện -> database/history.py.
    - Mẫu dữ liệu -> dataset/collector.py -> CSV.

Kết quả trả về ở đâu?
    get_latest(), pop_errors(), status; ảnh/video lưu trong captures/ và recordings/.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

from camera.camera_manager import CameraError, CameraManager, FPSCounter
from config.config import CAPTURE_DIR, RECORD_DIR, Settings
from dataset.collector import CollectorState, DataCollector
from dataset.dataset_manager import DatasetManager
from detection.hand_detector import HandDetector, HandDetectorError
from detection.landmark_extractor import draw_hand
from recognition.gesture_classifier import GestureClassifier, ModelLoadError
from recognition.predictor import Prediction, Predictor
from utils.constants import (
    COLOR_ACCEPTED, COLOR_BLACK, COLOR_UNKNOWN, COLOR_WHITE, overlay_gesture,
)
from utils.helpers import file_stamp, save_image
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FrameResult:
    frame_id: int
    frame: np.ndarray
    predictions: List[Prediction] = field(default_factory=list)
    fps: float = 0.0
    timestamp: float = 0.0

    @property
    def num_hands(self) -> int:
        return len(self.predictions)

    def primary(self) -> Optional[Prediction]:
        if not self.predictions:
            return None
        accepted = [p for p in self.predictions if p.accepted]
        pool = accepted or self.predictions
        return max(pool, key=lambda p: p.confidence)


class RecognitionEngine:
    def __init__(self, settings: Settings, classifier: GestureClassifier,
                 dataset_manager: DatasetManager, history_repo=None) -> None:
        self.settings = settings
        self.classifier = classifier
        self.history_repo = history_repo
        self.camera = CameraManager()
        self.detector = HandDetector(
            num_hands=settings.get("num_hands"),
            min_detection_confidence=settings.get("min_detection_confidence"),
            min_tracking_confidence=settings.get("min_tracking_confidence"),
        )
        self.predictor = Predictor(
            classifier, mode=settings.get("model_mode"), threshold=settings.get("confidence_threshold"),
            smoothing=settings.get("smoothing_window"), mirror_left=settings.get("mirror_left_hand"),
        )
        self.collector = DataCollector(dataset_manager, interval_ms=settings.get("collect_interval_ms"),
                                       mirror_left=settings.get("mirror_left_hand"))

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._latest: Optional[FrameResult] = None
        self._frame_id = 0
        self._errors: "queue.Queue[str]" = queue.Queue()
        self._status = "Camera stopped"
        self._fps = 0.0
        self._camera_dirty = False
        self._detector_dirty = False
        self._last_logged: Dict[str, Optional[str]] = {}
        self._warned_no_model = False
        self._camera_request = settings.resolution

        try:
            self.classifier.load()
        except ModelLoadError as exc:
            self._push_error(str(exc))

    # ---------------------------------------------------------------- state
    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def fps(self) -> float:
        with self._lock:
            return self._fps

    def _set_status(self, text: str) -> None:
        with self._lock:
            self._status = text
        logger.info("Engine status: %s", text)

    def _push_error(self, msg: str) -> None:
        logger.error(msg)
        self._errors.put(msg)

    def pop_errors(self) -> List[str]:
        errors = []
        while True:
            try:
                errors.append(self._errors.get_nowait())
            except queue.Empty:
                return errors

    def get_latest(self) -> Optional[FrameResult]:
        with self._lock:
            return self._latest

    # --------------------------------------------------------------- control
    def start(self) -> bool:
        if self.is_running:
            return True
        self._stop_event.clear()
        self.predictor.reset()
        self._last_logged.clear()
        self._thread = threading.Thread(target=self._run, name="RecognitionEngine", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout: float = 3.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout)
        self._thread = None
        with self._lock:
            self._latest = None
            self._fps = 0.0

    def shutdown(self) -> None:
        self.collector.cancel()
        self.stop()
        self.detector.close()
        logger.info("Engine shut down")

    def reload_model(self) -> bool:
        try:
            loaded = self.classifier.load()
        except ModelLoadError as exc:
            self._push_error(str(exc))
            return False
        self.predictor.reset()
        self._warned_no_model = False
        return loaded

    def apply_settings(self) -> None:
        s = self.settings
        self.predictor.configure(s.get("model_mode"), s.get("confidence_threshold"),
                                 s.get("smoothing_window"), s.get("mirror_left_hand"))
        self.collector.interval = s.get("collect_interval_ms") / 1000.0
        self.collector.mirror_left = s.get("mirror_left_hand")
        if self.detector.update_config(s.get("num_hands"), s.get("min_detection_confidence"),
                                       s.get("min_tracking_confidence")):
            self._detector_dirty = True
        if self.is_running and self.camera.index is not None and (
                self.camera.index != s.get("camera_index") or self._requested_size() != self._camera_request):
            self._camera_dirty = True
        self._warned_no_model = False
        logger.info("Settings applied to engine")

    def _requested_size(self):
        return self.settings.resolution

    # ---------------------------------------------------------- collection
    def start_collection(self, label: str, target: int) -> None:
        self.collector.start(label, target)
        if not self.is_running:
            self.start()

    def cancel_collection(self) -> None:
        self.collector.cancel()

    # ------------------------------------------------------ capture/record
    def capture(self) -> Optional[Path]:
        latest = self.get_latest()
        if latest is None:
            self._push_error("Camera is not running.")
            return None
        path = CAPTURE_DIR / f"capture_{file_stamp()}.png"
        if save_image(path, latest.frame):
            logger.info("Captured %s", path)
            return path
        self._push_error(f"Cannot save image to {path}")
        return None

    def toggle_recording(self) -> Optional[Path]:
        """Bắt đầu/dừng quay. Trả đường dẫn file khi DỪNG, None khi bắt đầu."""
        if self.camera.is_recording:
            return self.camera.stop_recording()
        latest = self.get_latest()
        if latest is None:
            self._push_error("Camera is not running.")
            return None
        h, w = latest.frame.shape[:2]
        fps = min(30.0, max(10.0, self.fps or float(self.settings.get("target_fps"))))
        try:
            self.camera.start_recording(RECORD_DIR / f"record_{file_stamp()}.mp4", fps, (w, h))
        except CameraError as exc:
            self._push_error(str(exc))
        return None

    @property
    def is_recording(self) -> bool:
        return self.camera.is_recording

    # ------------------------------------------------------------- main loop
    def _open_camera(self) -> None:
        w, h = self._requested_size()
        self._camera_request = (w, h)
        self._set_status("Opening camera...")
        self.camera.open(self.settings.get("camera_index"), w, h)

    def _run(self) -> None:
        self._camera_dirty = False
        try:
            if not self.detector.is_loaded or self._detector_dirty:
                self.detector.load(status_cb=self._set_status)
                self._detector_dirty = False
            self._open_camera()
        except (HandDetectorError, CameraError) as exc:
            self._push_error(str(exc))
            self._set_status("Camera stopped")
            self.camera.release()
            return
        except Exception as exc:  # lỗi không lường trước
            logger.exception("Engine start failed")
            self._push_error(f"Unexpected error: {exc}")
            self._set_status("Camera stopped")
            self.camera.release()
            return

        self._set_status("Running")
        fps_counter = FPSCounter()
        failures = 0
        try:
            while not self._stop_event.is_set():
                loop_start = time.perf_counter()
                if self._camera_dirty:
                    self._camera_dirty = False
                    self._open_camera()
                    fps_counter.reset()
                    self._set_status("Running")
                if self._detector_dirty:
                    self._detector_dirty = False
                    self.detector.load(status_cb=self._set_status)
                    self._set_status("Running")

                ok, frame = self.camera.read()
                if not ok:
                    failures += 1
                    if failures > 50:
                        raise CameraError("Lost connection to the camera.")
                    time.sleep(0.02)
                    continue
                failures = 0
                self._process_frame(frame, fps_counter)

                target = 1.0 / max(1, int(self.settings.get("target_fps")))
                elapsed = time.perf_counter() - loop_start
                if elapsed < target:
                    self._stop_event.wait(target - elapsed)
        except (CameraError, HandDetectorError) as exc:
            self._push_error(str(exc))
        except Exception as exc:
            logger.exception("Engine loop crashed")
            self._push_error(f"Unexpected error: {exc}")
        finally:
            self.collector.cancel()
            self.camera.release()
            self._set_status("Camera stopped")

    def _process_frame(self, frame: np.ndarray, fps_counter: FPSCounter) -> None:
        if self.settings.get("mirror"):
            frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        aspect = w / float(h)

        hands = self.detector.detect(frame)
        predictions = self.predictor.predict(hands, aspect)

        if self.predictor.active_source == "none" and not self._warned_no_model:
            self._warned_no_model = True
            self._push_error("Model mode is 'ml' but no trained model was found. "
                             "Train a model in the Training screen or set Model mode to 'auto'.")

        if self.collector.active:
            self.collector.process(hands, aspect)

        fps = fps_counter.update()
        self._annotate(frame, predictions, fps)
        if self.camera.is_recording:
            self.camera.write(frame)
        self._log_history(predictions)

        with self._lock:
            self._frame_id += 1
            self._fps = fps
            self._latest = FrameResult(self._frame_id, frame, predictions, fps, time.time())

    # -------------------------------------------------------------- drawing
    def _annotate(self, frame: np.ndarray, predictions: List[Prediction], fps: float) -> None:
        show_lm = self.settings.get("show_landmarks")
        show_bb = self.settings.get("show_bbox")
        for p in predictions:
            color = COLOR_ACCEPTED if p.accepted else COLOR_UNKNOWN
            text = f"{p.hand.handedness}: {overlay_gesture(p.gesture)} {p.confidence * 100:.0f}%"
            draw_hand(frame, p.hand, color, text, show_lm, show_bb)

        lines = [f"FPS: {fps:.1f}", f"Hands: {len(predictions)}", f"Mode: {self.predictor.active_source}"]
        self._draw_panel(frame, lines, (10, 10))

        if self.camera.is_recording:
            cv2.circle(frame, (frame.shape[1] - 30, 25), 9, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (frame.shape[1] - 80, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 0, 255), 2, cv2.LINE_AA)

        snap = self.collector.snapshot()
        state = snap["state"]
        if state in (CollectorState.COUNTDOWN, CollectorState.COLLECTING):
            label = str(snap["label"]).upper()
            if state == CollectorState.COUNTDOWN:
                text = f"GET READY: {label}  {int(snap['countdown']) + 1}"
            else:
                text = f"COLLECTING {label}: {snap['collected']}/{snap['target']}"
            h = frame.shape[0]
            cv2.rectangle(frame, (0, h - 40), (frame.shape[1], h), COLOR_BLACK, -1)
            cv2.putText(frame, text, (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 255), 2, cv2.LINE_AA)

    @staticmethod
    def _draw_panel(frame: np.ndarray, lines: List[str], origin) -> None:
        x, y = origin
        width = 170
        height = 24 * len(lines) + 10
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + width, y + height), COLOR_BLACK, -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (x + 8, y + 24 * (i + 1)), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        COLOR_WHITE, 1, cv2.LINE_AA)

    # -------------------------------------------------------------- history
    def _log_history(self, predictions: List[Prediction]) -> None:
        """Chỉ lưu khi gesture của một bàn tay THAY ĐỔI -> tránh ghi trùng mỗi frame."""
        if self.history_repo is None or not self.settings.get("save_history"):
            return
        seen = set()
        for p in predictions:
            key = p.key or p.hand.handedness  # "Left_0", "Left_1"... phân biệt 2 tay cùng nhãn
            seen.add(key)
            if not p.accepted:
                self._last_logged[key] = None
                continue
            if self._last_logged.get(key) != p.gesture:
                self._last_logged[key] = p.gesture
                try:
                    self.history_repo.add(p.gesture, p.confidence, key, p.source)
                except Exception as exc:
                    logger.error("Cannot save history: %s", exc)
        for key in list(self._last_logged):
            if key not in seen:
                del self._last_logged[key]
