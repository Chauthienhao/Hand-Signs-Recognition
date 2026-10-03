"""
recognition/gesture_classifier.py
=================================
File này dùng để làm gì?
    Nạp model Machine Learning đã train (models/hand_sign_model.pkl) và dự
    đoán gesture từ vector đặc trưng 63 chiều.

Dữ liệu đi vào từ đâu?
    - File .pkl do training/train_model.py tạo ra (joblib).
    - Vector đặc trưng từ recognition/feature_extractor.py.

Dữ liệu được xử lý như thế nào?
    File .pkl là một "bundle" (dict) gồm: pipeline scikit-learn (scaler +
    classifier), danh sách nhãn, tên thuật toán, các chỉ số đánh giá...
    Khi dự đoán: predict_proba -> lấy lớp có xác suất cao nhất làm kết quả,
    xác suất đó chính là "Confidence".

Dữ liệu được truyền sang module nào?
    recognition/predictor.py; thông tin model hiển thị ở gui.

Kết quả trả về ở đâu?
    predict() trả (label, confidence).
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np

from config.config import MODEL_PATH
from utils.constants import FEATURE_DIM
from utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_KEYS = {"model", "labels", "algorithm", "feature_dim"}


class ModelLoadError(Exception):
    """File model không tồn tại hoặc không hợp lệ."""


class GestureClassifier:
    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self._bundle: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    def exists(self) -> bool:
        return self.model_path.exists()

    def load(self) -> bool:
        """Nạp model. Trả False nếu chưa có file; raise ModelLoadError nếu file lỗi."""
        if not self.exists():
            logger.info("No trained model at %s", self.model_path)
            with self._lock:
                self._bundle = None
            return False
        try:
            bundle = joblib.load(self.model_path)
        except Exception as exc:
            raise ModelLoadError(f"Cannot read model file {self.model_path}: {exc}") from exc

        if not isinstance(bundle, dict) or not REQUIRED_KEYS.issubset(bundle):
            raise ModelLoadError("Model file is invalid or was created by another program. Please retrain.")
        if int(bundle["feature_dim"]) != FEATURE_DIM:
            raise ModelLoadError(
                f"Model expects {bundle['feature_dim']} features but the system uses {FEATURE_DIM}. Please retrain."
            )
        with self._lock:
            self._bundle = bundle
        logger.info("Loaded model %s (%s, %d classes)", self.model_path.name,
                    bundle["algorithm"], len(bundle["labels"]))
        return True

    def unload(self) -> None:
        with self._lock:
            self._bundle = None

    @property
    def is_loaded(self) -> bool:
        with self._lock:
            return self._bundle is not None

    @property
    def algorithm(self) -> Optional[str]:
        with self._lock:
            return self._bundle.get("algorithm_name", self._bundle["algorithm"]) if self._bundle else None

    @property
    def labels(self) -> List[str]:
        with self._lock:
            return list(self._bundle["labels"]) if self._bundle else []

    def info(self) -> Dict[str, Any]:
        with self._lock:
            if not self._bundle:
                return {}
            return {k: v for k, v in self._bundle.items() if k != "model"}

    def predict(self, features: np.ndarray) -> Tuple[str, float]:
        x = np.asarray(features, dtype=np.float32).reshape(1, -1)
        with self._lock:
            if self._bundle is None:
                raise ModelLoadError("No model loaded.")
            model = self._bundle["model"]
            if x.shape[1] != int(self._bundle["feature_dim"]):
                raise ValueError(f"Feature size {x.shape[1]} does not match model")
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(x)[0]
                idx = int(np.argmax(proba))
                return str(model.classes_[idx]), float(proba[idx])
            return str(model.predict(x)[0]), 1.0
