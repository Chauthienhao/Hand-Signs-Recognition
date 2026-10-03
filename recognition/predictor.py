"""
recognition/predictor.py
========================
File này dùng để làm gì?
    Bộ "não" nhận diện: nhận danh sách bàn tay, chọn nguồn dự đoán phù hợp
    (model ML tự train hoặc gesture có sẵn của MediaPipe), làm mượt kết quả
    theo thời gian và áp ngưỡng tin cậy.

Dữ liệu đi vào từ đâu?
    list[HandInfo] từ detection/hand_detector.py (qua core.engine).

Dữ liệu được xử lý như thế nào?
    1. Chọn chế độ:  ml | builtin | auto (có model ML thì dùng, không thì builtin).
    2. Chế độ ml: HandInfo -> feature_extractor (63 chiều) -> GestureClassifier.
    3. Làm mượt (smoothing): giữ N kết quả gần nhất của mỗi bàn tay, bỏ phiếu
       đa số -> giảm hiện tượng nhãn "nhảy" giữa các frame.
    4. So sánh độ tin cậy với ngưỡng (confidence threshold): thấp hơn -> Unknown.

Dữ liệu được truyền sang module nào?
    list[Prediction] -> core.engine (vẽ, lưu lịch sử) -> gui.

Kết quả trả về ở đâu?
    Giá trị trả về của predict().
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple

from detection.landmark_extractor import HandInfo
from recognition.feature_extractor import extract_features
from recognition.gesture_classifier import GestureClassifier
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Prediction:
    hand: HandInfo
    gesture: Optional[str]     # key gesture, None nếu không chắc chắn
    confidence: float          # 0..1
    source: str                # "ml" | "builtin" | "none"
    accepted: bool             # True nếu confidence >= threshold
    key: str = ""              # định danh bàn tay ổn định giữa các frame, vd "Left_0"


class Predictor:
    def __init__(self, classifier: GestureClassifier, mode: str = "auto",
                 threshold: float = 0.6, smoothing: int = 5, mirror_left: bool = True) -> None:
        self.classifier = classifier
        self.mode = mode
        self.threshold = threshold
        self.smoothing = max(1, int(smoothing))
        self.mirror_left = mirror_left
        self._buffers: Dict[str, Deque[Tuple[Optional[str], float]]] = {}

    def configure(self, mode: str, threshold: float, smoothing: int, mirror_left: bool) -> None:
        if mode != self.mode:
            self._buffers.clear()
        self.mode, self.threshold, self.mirror_left = mode, float(threshold), bool(mirror_left)
        smoothing = max(1, int(smoothing))
        if smoothing != self.smoothing:
            self.smoothing = smoothing
            self._buffers.clear()

    @property
    def active_source(self) -> str:
        if self.mode == "ml" or (self.mode == "auto" and self.classifier.is_loaded):
            return "ml" if self.classifier.is_loaded else "none"
        return "builtin"

    def reset(self) -> None:
        self._buffers.clear()

    # ------------------------------------------------------------------
    def _raw_predict(self, hand: HandInfo, aspect: float) -> Tuple[Optional[str], float, str]:
        source = self.active_source
        if source == "ml":
            try:
                feats = extract_features(hand, aspect, self.mirror_left)
                label, conf = self.classifier.predict(feats)
                return label, conf, "ml"
            except Exception as exc:
                logger.error("ML prediction failed: %s", exc)
                return None, 0.0, "none"
        if source == "builtin":
            return hand.builtin_gesture, hand.builtin_score, "builtin"
        return None, 0.0, "none"

    def predict(self, hands: List[HandInfo], aspect: float = 1.0) -> List[Prediction]:
        results: List[Prediction] = []
        seen: Dict[str, int] = {}
        active_keys = set()
        for hand in hands:
            # Khóa bộ đệm theo tay trái/phải (thêm chỉ số nếu MediaPipe trả trùng nhãn)
            n = seen.get(hand.handedness, 0)
            seen[hand.handedness] = n + 1
            key = f"{hand.handedness}_{n}"
            active_keys.add(key)

            label, conf, source = self._raw_predict(hand, aspect)
            buf = self._buffers.setdefault(key, deque(maxlen=self.smoothing))
            buf.append((label, conf))

            best, _ = Counter(l for l, _ in buf).most_common(1)[0]
            confs = [c for l, c in buf if l == best]
            mean_conf = sum(confs) / len(confs) if confs else 0.0
            accepted = best is not None and mean_conf >= self.threshold
            results.append(Prediction(
                hand=hand,
                gesture=best if accepted else None,
                confidence=mean_conf if best is not None else conf,
                source=source,
                accepted=accepted,
                key=key,
            ))

        for key in list(self._buffers):
            if key not in active_keys:
                del self._buffers[key]
        return results
