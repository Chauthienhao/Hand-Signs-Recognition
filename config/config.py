"""
config/config.py
================
File này dùng để làm gì?
    Quản lý toàn bộ cấu hình của hệ thống: đường dẫn thư mục (dataset, model,
    database, log, ảnh chụp, video), URL tải model MediaPipe và các thiết lập
    người dùng (camera, ngưỡng tin cậy, số bàn tay, theme, ngôn ngữ...).

Dữ liệu đi vào từ đâu?
    - Giá trị mặc định khai báo trong DEFAULT_SETTINGS.
    - File config/settings.json do màn hình Settings lưu lại.

Dữ liệu được xử lý như thế nào?
    Lớp Settings đọc file JSON, trộn với giá trị mặc định, ép kiểu đúng
    với kiểu mặc định (bool/int/float/str) để tránh lỗi khi file bị sửa tay.

Dữ liệu được truyền sang module nào?
    Hầu hết các module: camera, detection, recognition, core.engine, gui.

Kết quả trả về ở đâu?
    Qua đối tượng dùng chung `settings` và các hằng số đường dẫn bên dưới.
"""
from __future__ import annotations

import json
import logging
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Đường dẫn
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DB_DIR = BASE_DIR / "database"
LOG_DIR = BASE_DIR / "logs"
CAPTURE_DIR = BASE_DIR / "captures"
RECORD_DIR = BASE_DIR / "recordings"
REPORT_DIR = BASE_DIR / "reports"

DATASET_CSV = DATA_DIR / "hand_signs.csv"
MODEL_PATH = MODELS_DIR / "hand_sign_model.pkl"
DB_PATH = DB_DIR / "hand_signs.db"
SETTINGS_PATH = CONFIG_DIR / "settings.json"

# Model MediaPipe Gesture Recognizer (phát hiện tay + 21 landmark + 7 cử chỉ có sẵn)
MP_MODEL_PATH = MODELS_DIR / "gesture_recognizer.task"
MP_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/latest/gesture_recognizer.task"
)

# ----------------------------------------------------------------------------
# Các lựa chọn cho màn hình Settings
# ----------------------------------------------------------------------------
RESOLUTIONS = ["640x480", "800x600", "1280x720", "1920x1080"]
FPS_OPTIONS = ["15", "24", "30", "60"]
MODEL_MODES = ["auto", "ml", "builtin"]
THEMES = ["Dark", "Light", "System"]
LANGUAGES = {"en": "English", "vi": "Tiếng Việt"}
TTS_BACKENDS = ["auto", "pyttsx3", "gtts"]

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Camera
    "camera_index": 0,
    "resolution": "640x480",
    "target_fps": 30,
    "mirror": True,
    # Phát hiện bàn tay (MediaPipe)
    "num_hands": 2,
    "min_detection_confidence": 0.5,
    "min_tracking_confidence": 0.5,
    # Nhận diện
    "confidence_threshold": 0.6,
    "smoothing_window": 5,
    "model_mode": "auto",          # auto | ml | builtin
    "mirror_left_hand": True,      # lật tay trái thành tay phải khi trích đặc trưng
    # Hiển thị & lưu trữ
    "show_landmarks": True,
    "show_bbox": True,
    "save_history": True,
    # Dataset
    "collect_samples": 300,
    "collect_interval_ms": 50,
    "min_samples_ready": 100,
    # Chế độ đánh vần + đọc thành tiếng
    "spelling_hold_time": 1.0,     # giữ ký hiệu bao lâu (giây) thì chốt
    "spelling_auto_space": 1.5,    # hạ tay bao lâu (giây) thì tự thêm khoảng trắng; 0 = tắt
    "tts_backend": "auto",         # auto | pyttsx3 | gtts
    "tts_lang": "vi",              # ngôn ngữ đọc: vi | en
    # Giao diện
    "theme": "Dark",
    "language": "vi",
}


class Settings:
    """Đọc / ghi thiết lập người dùng (thread-safe)."""

    def __init__(self, path: Path = SETTINGS_PATH) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = deepcopy(DEFAULT_SETTINGS)
        self.load()

    # ------------------------------------------------------------------ I/O
    def load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Cannot read settings file %s: %s (using defaults)", self._path, exc)
            return
        if not isinstance(raw, dict):
            logger.warning("Settings file is not a JSON object, using defaults")
            return
        with self._lock:
            for key, value in raw.items():
                if key in DEFAULT_SETTINGS:
                    self._data[key] = self._coerce(key, value)

    def save(self) -> None:
        with self._lock:
            data = deepcopy(self._data)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
            logger.info("Settings saved to %s", self._path)
        except OSError as exc:
            logger.error("Cannot save settings: %s", exc)
            raise

    # ------------------------------------------------------------- accessors
    @staticmethod
    def _coerce(key: str, value: Any) -> Any:
        default = DEFAULT_SETTINGS[key]
        try:
            if isinstance(default, bool):
                if isinstance(value, str):
                    return value.strip().lower() in ("1", "true", "yes", "on")
                return bool(value)
            if isinstance(default, int):
                return int(value)
            if isinstance(default, float):
                return float(value)
            return str(value)
        except (TypeError, ValueError):
            logger.warning("Invalid value for setting '%s': %r (using default)", key, value)
            return default

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key not in DEFAULT_SETTINGS:
            raise KeyError(f"Unknown setting: {key}")
        with self._lock:
            self._data[key] = self._coerce(key, value)

    def update(self, mapping: Dict[str, Any]) -> None:
        for key, value in mapping.items():
            self.set(key, value)

    def reset(self) -> None:
        with self._lock:
            self._data = deepcopy(DEFAULT_SETTINGS)

    def as_dict(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    @property
    def resolution(self) -> Tuple[int, int]:
        text = str(self.get("resolution", "640x480"))
        try:
            w, h = (int(v) for v in text.lower().split("x"))
            return w, h
        except ValueError:
            return 640, 480


# Đối tượng dùng chung toàn chương trình
settings = Settings()
