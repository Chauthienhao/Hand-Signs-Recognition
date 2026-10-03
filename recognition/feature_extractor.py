"""
recognition/feature_extractor.py
================================
File này dùng để làm gì?
    Biến 21 landmark thô của MediaPipe thành vector đặc trưng (feature vector)
    63 chiều đã chuẩn hóa, dùng chung cho cả lúc tạo dataset, train và nhận
    diện thời gian thực (đảm bảo dữ liệu train và dữ liệu dự đoán giống nhau).

Dữ liệu đi vào từ đâu?
    HandInfo.landmarks (21 x 3) từ detection/landmark_extractor.py.

Dữ liệu được xử lý như thế nào? (chuẩn hóa 4 bước)
    1. Bù tỉ lệ khung hình: x, z nhân với width/height để 1 đơn vị x = 1 đơn vị y.
    2. Tịnh tiến: lấy cổ tay (điểm 0) làm gốc toạ độ -> không phụ thuộc vị trí tay.
    3. Lật tay trái (x -> -x) để tay trái trông giống tay phải -> 1 model dùng
       cho cả hai tay, giảm một nửa lượng dữ liệu cần thu thập.
    4. Co giãn: chia cho khoảng cách lớn nhất từ cổ tay -> không phụ thuộc tay
       to/nhỏ hay đứng gần/xa camera.
    Sau đó làm phẳng (flatten) thành [x0,y0,z0,...,x20,y20,z20].

Dữ liệu được truyền sang module nào?
    dataset/collector.py (ghi CSV), recognition/predictor.py (đưa vào model).

Kết quả trả về ở đâu?
    numpy array 63 phần tử (float32).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np

from utils.constants import FEATURE_DIM, NUM_LANDMARKS

FEATURE_COLUMNS: List[str] = [f"{axis}{i}" for i in range(NUM_LANDMARKS) for axis in "xyz"]
LABEL_COLUMN = "label"
CSV_COLUMNS: List[str] = FEATURE_COLUMNS + [LABEL_COLUMN]


def normalize_landmarks(
    landmarks: np.ndarray,
    handedness: Optional[str] = None,
    aspect_ratio: float = 1.0,
    mirror_left: bool = True,
) -> np.ndarray:
    pts = np.asarray(landmarks, dtype=np.float32)
    if pts.size != FEATURE_DIM:
        raise ValueError(f"Expected {NUM_LANDMARKS} landmarks with 3 coordinates, got shape {pts.shape}")
    pts = pts.reshape(NUM_LANDMARKS, 3).copy()

    pts[:, 0] *= aspect_ratio          # 1. bù tỉ lệ khung hình
    pts[:, 2] *= aspect_ratio
    pts -= pts[0]                      # 2. cổ tay làm gốc
    if mirror_left and handedness == "Left":
        pts[:, 0] *= -1.0              # 3. lật tay trái
    scale = float(np.max(np.linalg.norm(pts[:, :2], axis=1)))
    if scale < 1e-6:
        scale = 1.0
    pts /= scale                       # 4. co giãn về [-1, 1]
    return pts


def extract_features(hand, aspect_ratio: float = 1.0, mirror_left: bool = True) -> np.ndarray:
    """HandInfo -> vector 63 chiều."""
    pts = normalize_landmarks(hand.landmarks, hand.handedness, aspect_ratio, mirror_left)
    return pts.flatten().astype(np.float32)
