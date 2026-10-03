"""
detection/landmark_extractor.py
===============================
File này dùng để làm gì?
    - Định nghĩa cấu trúc HandInfo: thông tin 1 bàn tay (21 landmark,
      tay trái/phải, độ tin cậy, gesture có sẵn của MediaPipe).
    - Chuyển kết quả thô của MediaPipe thành danh sách HandInfo.
    - Vẽ 21 điểm landmark, đường nối, bounding box và nhãn lên frame.

Dữ liệu đi vào từ đâu?
    Đối tượng GestureRecognizerResult do detection/hand_detector.py trả về.

Dữ liệu được xử lý như thế nào?
    Mỗi landmark gồm (x, y, z): x, y chuẩn hóa theo kích thước ảnh [0..1],
    z là độ sâu tương đối so với cổ tay. Dữ liệu được gom thành mảng numpy
    kích thước (21, 3).

Dữ liệu được truyền sang module nào?
    HandInfo được chuyển cho recognition (trích đặc trưng + phân loại),
    dataset/collector.py (thu thập mẫu) và core.engine (vẽ kết quả).

Kết quả trả về ở đâu?
    from_gesture_result() trả list[HandInfo]; draw_hand() vẽ trực tiếp lên frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from utils.constants import (
    BUILTIN_GESTURE_MAP, COLOR_BLACK, COLOR_WHITE, FINGERTIPS, HAND_CONNECTIONS, NUM_LANDMARKS,
)


@dataclass
class HandInfo:
    landmarks: np.ndarray                 # (21, 3) toạ độ chuẩn hóa của MediaPipe
    handedness: str = "Unknown"           # "Left" / "Right"
    handedness_score: float = 0.0         # độ tin cậy phát hiện tay
    builtin_gesture: Optional[str] = None # gesture có sẵn của MediaPipe (đã đổi sang key)
    builtin_score: float = 0.0

    def pixel_points(self, width: int, height: int) -> np.ndarray:
        pts = self.landmarks[:, :2] * np.array([width, height], dtype=np.float32)
        return pts.astype(np.int32)

    def bounding_box(self, width: int, height: int, padding: int = 20) -> Tuple[int, int, int, int]:
        pts = self.pixel_points(width, height)
        x1, y1 = pts.min(axis=0) - padding
        x2, y2 = pts.max(axis=0) + padding
        return (max(0, int(x1)), max(0, int(y1)), min(width - 1, int(x2)), min(height - 1, int(y2)))


class LandmarkExtractor:
    """Chuyển kết quả MediaPipe -> HandInfo."""

    @staticmethod
    def from_gesture_result(result) -> List[HandInfo]:
        hands: List[HandInfo] = []
        if result is None:
            return hands
        landmark_lists = getattr(result, "hand_landmarks", None) or []
        handedness_lists = getattr(result, "handedness", None) or []
        gesture_lists = getattr(result, "gestures", None) or []

        for i, landmarks in enumerate(landmark_lists):
            arr = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)
            if arr.shape != (NUM_LANDMARKS, 3):
                continue

            hand_label, hand_score = "Unknown", 0.0
            if i < len(handedness_lists) and handedness_lists[i]:
                cat = handedness_lists[i][0]
                hand_label = cat.category_name or cat.display_name or "Unknown"
                hand_score = float(cat.score or 0.0)

            gesture, gesture_score = None, 0.0
            if i < len(gesture_lists) and gesture_lists[i]:
                cat = gesture_lists[i][0]
                gesture = BUILTIN_GESTURE_MAP.get(cat.category_name)
                gesture_score = float(cat.score or 0.0)

            hands.append(HandInfo(arr, hand_label, hand_score, gesture, gesture_score))
        return hands


def draw_hand(
    frame: np.ndarray,
    hand: HandInfo,
    color: Tuple[int, int, int],
    label: Optional[str] = None,
    show_landmarks: bool = True,
    show_bbox: bool = True,
) -> None:
    """Vẽ khung xương bàn tay, 21 điểm, bounding box và nhãn kết quả."""
    h, w = frame.shape[:2]
    pts = hand.pixel_points(w, h)

    if show_landmarks:
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, tuple(pts[a]), tuple(pts[b]), COLOR_WHITE, 3, cv2.LINE_AA)
            cv2.line(frame, tuple(pts[a]), tuple(pts[b]), color, 1, cv2.LINE_AA)
        for idx, (x, y) in enumerate(pts):
            radius = 6 if idx in FINGERTIPS else 4
            cv2.circle(frame, (int(x), int(y)), radius, color, -1, cv2.LINE_AA)
            cv2.circle(frame, (int(x), int(y)), radius, COLOR_WHITE, 1, cv2.LINE_AA)

    x1, y1, x2, y2 = hand.bounding_box(w, h)
    if show_bbox:
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    if label:
        font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        (tw, th), base = cv2.getTextSize(label, font, scale, thick)
        if y1 - th - 12 > 0:            # đủ chỗ phía trên khung
            ty = y1 - 8
        elif y2 + th + 12 < h:          # đặt phía dưới khung
            ty = y2 + th + 8
        else:                           # tay chiếm hết chiều cao -> đặt bên trong
            ty = y1 + th + 10
        x1 = min(x1, max(0, w - tw - 10))
        cv2.rectangle(frame, (x1, ty - th - 6), (x1 + tw + 8, ty + base), color, -1)
        cv2.putText(frame, label, (x1 + 4, ty - 2), font, scale, COLOR_BLACK, thick, cv2.LINE_AA)
