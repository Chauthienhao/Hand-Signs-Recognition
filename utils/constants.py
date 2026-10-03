"""
utils/constants.py
==================
File này dùng để làm gì?
    Chứa các hằng số dùng chung: tên ứng dụng, danh sách gesture mặc định,
    tên hiển thị (Anh/Việt), bảng ánh xạ gesture có sẵn của MediaPipe,
    các đường nối 21 landmark, màu sắc và bộ dịch giao diện EN/VI.

Dữ liệu đi vào từ đâu?
    Khai báo tĩnh trong file. Ngôn ngữ hiện tại được đặt bởi main.py
    (đọc từ Settings) qua hàm set_language().

Dữ liệu được xử lý như thế nào?
    tr(text) tra bảng dịch; display_gesture(key) đổi key ("thumb_up")
    thành tên hiển thị ("Thumb Up" / "Ngón cái lên").

Dữ liệu được truyền sang module nào?
    detection (vẽ landmark), recognition, dataset, database (seed gesture), gui.

Kết quả trả về ở đâu?
    Giá trị hằng / chuỗi đã dịch trả trực tiếp cho nơi gọi.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

APP_NAME = "Hand Signs Recognition System"
APP_VERSION = "1.0.0"

NUM_LANDMARKS = 21
FEATURE_DIM = NUM_LANDMARKS * 3

# Các cặp điểm nối tạo thành "khung xương" bàn tay (theo chuẩn MediaPipe)
HAND_CONNECTIONS: List[Tuple[int, int]] = [
    (0, 1), (1, 2), (2, 3), (3, 4),            # ngón cái
    (0, 5), (5, 6), (6, 7), (7, 8),            # ngón trỏ
    (5, 9), (9, 10), (10, 11), (11, 12),       # ngón giữa
    (9, 13), (13, 14), (14, 15), (15, 16),     # ngón áp út
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),  # ngón út + lòng bàn tay
]
FINGERTIPS = (4, 8, 12, 16, 20)

LANDMARK_NAMES = [
    "WRIST", "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_MCP", "INDEX_PIP", "INDEX_DIP", "INDEX_TIP",
    "MIDDLE_MCP", "MIDDLE_PIP", "MIDDLE_DIP", "MIDDLE_TIP",
    "RING_MCP", "RING_PIP", "RING_DIP", "RING_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP",
]

# Màu (BGR cho OpenCV)
COLOR_ACCEPTED = (80, 200, 80)
COLOR_UNKNOWN = (0, 165, 255)
COLOR_LEFT = (255, 140, 0)
COLOR_RIGHT = (60, 60, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)

# key -> (English, Tiếng Việt)
GESTURE_NAMES: Dict[str, Tuple[str, str]] = {
    "open_palm": ("Open Palm", "Bàn tay mở"),
    "closed_fist": ("Closed Fist", "Nắm tay"),
    "thumb_up": ("Thumb Up", "Ngón cái lên"),
    "thumb_down": ("Thumb Down", "Ngón cái xuống"),
    "victory": ("Victory / Peace", "Chữ V"),
    "pointing_up": ("Pointing Up", "Chỉ lên"),
    "i_love_you": ("I Love You", "I Love You"),
    "ok": ("OK", "OK"),
    "rock": ("Rock", "Rock"),
    "stop": ("Stop", "Dừng lại"),
    "call_me": ("Call Me", "Gọi cho tôi"),
    **{f"number_{i}": (f"Number {i}", f"Số {i}") for i in range(10)},
    # Bảng chữ cái ngón tay NNKH Việt Nam (chế độ Đánh vần)
    **{f"letter_{c}": (f"Letter {c.upper()}", f"Chữ {c.upper()}") for c in "abcdeghiklmnopqrstuvxy"},
    "letter_dd": ("Letter Đ", "Chữ Đ"),
    "mark_mu": ("Circumflex ^", "Dấu mũ ^"),
    "mark_rau": ("Horn ’", "Dấu móc/râu ’"),
    "mark_trang": ("Breve ˘", "Dấu trăng ˘"),
    "mark_sac": ("Acute tone", "Dấu sắc"),
    "mark_huyen": ("Grave tone", "Dấu huyền"),
    "mark_hoi": ("Hook tone", "Dấu hỏi"),
    "mark_nga": ("Tilde tone", "Dấu ngã"),
    "mark_nang": ("Dot tone", "Dấu nặng"),
    "ctrl_space": ("Space", "Dấu cách"),
    "ctrl_delete": ("Delete", "Xóa"),
    "ctrl_speak": ("Speak", "Đọc"),
    "ctrl_clear": ("Clear", "Xóa hết"),
}

# 7 gesture cơ bản (khớp với gesture có sẵn của MediaPipe Gesture Recognizer)
DEFAULT_GESTURES: List[str] = [
    "open_palm", "closed_fist", "thumb_up", "thumb_down",
    "victory", "pointing_up", "i_love_you",
]

# Nhãn của MediaPipe Gesture Recognizer -> key trong hệ thống
BUILTIN_GESTURE_MAP: Dict[str, Optional[str]] = {
    "None": None,
    "Closed_Fist": "closed_fist",
    "Open_Palm": "open_palm",
    "Pointing_Up": "pointing_up",
    "Thumb_Down": "thumb_down",
    "Thumb_Up": "thumb_up",
    "Victory": "victory",
    "ILoveYou": "i_love_you",
}

# ----------------------------------------------------------------------------
# Đa ngôn ngữ (chuỗi tiếng Anh là khóa, bảng dưới là bản dịch tiếng Việt)
# ----------------------------------------------------------------------------
_LANGUAGE = "en"

VI: Dict[str, str] = {
    # Sidebar / chung
    "Dashboard": "Tổng quan", "Recognition": "Nhận diện", "Dataset": "Dữ liệu",
    "Training": "Huấn luyện", "History": "Lịch sử", "Statistics": "Thống kê",
    "Settings": "Cài đặt", "Exit": "Thoát", "Start Camera": "Bật camera",
    "Stop Camera": "Tắt camera", "Error": "Lỗi", "Warning": "Cảnh báo",
    "Information": "Thông báo", "Confirm": "Xác nhận", "Refresh": "Làm mới",
    "Camera": "Camera", "Model": "Mô hình", "Status": "Trạng thái",
    "Running": "Đang chạy", "Stopped": "Đã dừng", "None": "Không có",
    "Built-in (MediaPipe)": "Có sẵn (MediaPipe)", "Not trained": "Chưa huấn luyện",
    "Do you want to exit?": "Bạn có muốn thoát chương trình?",
    # Dashboard
    "Hand Signs Recognition System": "Hệ thống nhận diện ký hiệu bàn tay",
    "Camera status": "Trạng thái camera", "Recognition model": "Mô hình nhận diện",
    "Dataset samples": "Số mẫu dữ liệu", "Total recognitions": "Tổng lượt nhận diện",
    "Quick start": "Bắt đầu nhanh",
    "Processing pipeline": "Luồng xử lý",
    "gestures": "gesture",
    # Recognition
    "Recognition result": "Kết quả nhận diện", "Gesture": "Ký hiệu",
    "Confidence": "Độ tin cậy", "Hand": "Bàn tay", "FPS": "FPS",
    "Detected hands": "Số bàn tay", "Source": "Nguồn", "Start": "Bắt đầu",
    "Stop": "Dừng", "Capture": "Chụp ảnh", "Record": "Quay video",
    "Stop Recording": "Dừng quay", "Image saved": "Đã lưu ảnh",
    "Video saved": "Đã lưu video", "Recording started": "Bắt đầu quay video",
    "Camera is not running": "Camera chưa được bật", "No hand": "Không có tay",
    "Unknown": "Không xác định", "Details": "Chi tiết",
    "Left": "Trái", "Right": "Phải",
    "Camera is off. Press Start to begin.": "Camera đang tắt. Nhấn Bắt đầu để chạy.",
    # Dataset
    "Dataset Management": "Quản lý dữ liệu", "Display name": "Tên hiển thị",
    "Number of Samples": "Số mẫu", "Add Gesture": "Thêm gesture",
    "Delete Gesture": "Xóa gesture", "View Dataset": "Xem dữ liệu",
    "Clear Dataset": "Xóa toàn bộ dữ liệu", "Collect Data": "Thu thập dữ liệu",
    "Start Collecting": "Bắt đầu thu thập", "Cancel": "Hủy",
    "New gesture name": "Tên gesture mới", "Samples": "Số mẫu",
    "Ready": "Sẵn sàng", "Not enough": "Chưa đủ", "Empty": "Trống",
    "Total samples": "Tổng số mẫu", "Classes": "Số lớp",
    "Select a gesture first": "Hãy chọn một gesture trước",
    "Collection finished": "Đã thu thập xong",
    "Get ready": "Chuẩn bị", "Collecting": "Đang thu thập",
    "Idle": "Đang chờ", "Cancelled": "Đã hủy", "Done": "Hoàn tất",
    "Show your hand to the camera": "Đưa bàn tay vào camera",
    "Delete all samples of gesture": "Xóa toàn bộ mẫu của gesture",
    "Delete ALL dataset samples?": "Xóa TOÀN BỘ mẫu dữ liệu?",
    "Dataset preview": "Xem trước dữ liệu",
    # Training
    "Training Dashboard": "Bảng huấn luyện", "Algorithm": "Thuật toán",
    "Test size": "Tỉ lệ test", "Train Model": "Huấn luyện",
    "Compare All Models": "So sánh các mô hình",
    "Save best model": "Lưu mô hình tốt nhất", "Accuracy": "Accuracy",
    "Precision": "Precision", "Recall": "Recall", "F1-score": "F1-score",
    "Confusion Matrix": "Ma trận nhầm lẫn",
    "Accuracy Comparison": "So sánh độ chính xác",
    "Training Statistics": "Thống kê huấn luyện", "Report": "Báo cáo",
    "Training...": "Đang huấn luyện...", "Training finished": "Huấn luyện xong",
    "Current model": "Mô hình hiện tại", "Training failed": "Huấn luyện thất bại",
    "Comparison finished": "So sánh xong", "Best model": "Mô hình tốt nhất",
    # History
    "Recognition History": "Lịch sử nhận diện", "Search gesture": "Tìm gesture",
    "From (YYYY-MM-DD)": "Từ ngày (YYYY-MM-DD)", "To (YYYY-MM-DD)": "Đến ngày (YYYY-MM-DD)",
    "Search": "Tìm kiếm", "Reset": "Đặt lại", "Delete Selected": "Xóa mục chọn",
    "Delete All": "Xóa tất cả", "Export CSV": "Xuất CSV", "Time": "Thời gian",
    "All": "Tất cả", "records": "bản ghi", "Exported": "Đã xuất",
    "Invalid date": "Ngày không hợp lệ", "Delete all history?": "Xóa toàn bộ lịch sử?",
    # Statistics
    "Most frequent gesture": "Gesture xuất hiện nhiều nhất",
    "Average confidence": "Độ tin cậy trung bình",
    "Latest model accuracy": "Accuracy mô hình gần nhất",
    "Average model accuracy": "Accuracy trung bình",
    "Recognitions by gesture": "Số lần nhận diện theo gesture",
    "Recognitions by hand": "Theo bàn tay", "Recognitions per day": "Nhận diện theo ngày",
    "No data": "Chưa có dữ liệu",
    # Settings
    "Camera index": "Chỉ số camera", "Scan cameras": "Quét camera",
    "Resolution": "Độ phân giải", "Target FPS": "FPS mục tiêu",
    "Mirror image": "Lật ảnh (gương)", "Number of hands": "Số bàn tay",
    "Detection confidence": "Ngưỡng phát hiện tay",
    "Confidence threshold": "Ngưỡng tin cậy", "Smoothing window": "Cửa sổ làm mượt",
    "Model mode": "Chế độ mô hình", "Show landmarks": "Hiện landmark",
    "Show bounding box": "Hiện khung bao", "Save history": "Lưu lịch sử",
    "Samples per gesture": "Số mẫu mỗi gesture", "Theme": "Giao diện",
    "Language": "Ngôn ngữ", "Save": "Lưu", "Reset defaults": "Khôi phục mặc định",
    "Settings saved": "Đã lưu cài đặt",
    "Restart the application to apply the new language.":
        "Khởi động lại chương trình để áp dụng ngôn ngữ mới.",
    "Stop the camera before scanning.": "Hãy tắt camera trước khi quét.",
    "Scanning...": "Đang quét...", "Found cameras": "Camera tìm thấy",
    "No camera found": "Không tìm thấy camera",
    "auto: use trained ML model if available, otherwise MediaPipe built-in gestures":
        "auto: dùng mô hình ML đã train nếu có, nếu không dùng gesture có sẵn của MediaPipe",
    "Display": "Hiển thị",
    # Spelling
    "Spelling": "Đánh vần", "Spelling Mode": "Chế độ đánh vần",
    "Current sign": "Ký hiệu hiện tại", "Hold": "Giữ", "Sentence": "Câu",
    "Space": "Cách", "Backspace": "Xóa lùi", "Undo": "Hoàn tác", "Clear": "Xóa hết",
    "Speak": "Đọc", "Copy": "Sao chép", "Save .txt": "Lưu .txt", "Speaking...": "Đang đọc...",
    "Diacritics": "Dấu phụ", "Tones": "Dấu thanh",
    "Recent signs": "Ký hiệu gần đây", "Release your hand to repeat": "Hạ tay để lặp lại ký hiệu",
    "Copied": "Đã sao chép", "Nothing to speak": "Chưa có nội dung để đọc",
    "Speech error": "Lỗi đọc thành tiếng", "Saved": "Đã lưu",
    "Hold time (s)": "Thời gian giữ (giây)", "Auto space (s)": "Tự cách sau (giây)",
    "Speech engine": "Bộ đọc", "Speech language": "Ngôn ngữ đọc",
    "Add VSL alphabet": "Thêm bảng chữ cái NNKH",
    "Added": "Đã thêm", "already existed": "đã có sẵn",
    "Spelling uses the trained ML model. Train letters first (Dataset → Add VSL alphabet).":
        "Đánh vần dùng mô hình ML đã train. Hãy thêm và train các chữ cái trước (Dữ liệu → Thêm bảng chữ cái NNKH).",
    "Shortcuts": "Phím tắt",
}


def set_language(lang: str) -> None:
    global _LANGUAGE
    _LANGUAGE = lang if lang in ("en", "vi") else "en"


def get_language() -> str:
    return _LANGUAGE


def tr(text: str) -> str:
    """Dịch chuỗi giao diện theo ngôn ngữ hiện tại (mặc định trả về tiếng Anh)."""
    if _LANGUAGE == "vi":
        return VI.get(text, text)
    return text


def display_gesture(key: Optional[str], lang: Optional[str] = None) -> str:
    """Đổi key gesture thành tên hiển thị."""
    if not key:
        return tr("Unknown")
    lang = lang or _LANGUAGE
    names = GESTURE_NAMES.get(key)
    if names:
        return names[1] if lang == "vi" else names[0]
    return key.replace("_", " ").title()


def overlay_gesture(key: Optional[str]) -> str:
    """Tên in lên khung hình OpenCV (chỉ dùng ASCII vì cv2.putText không hỗ trợ dấu)."""
    if not key:
        return "UNKNOWN"
    names = GESTURE_NAMES.get(key)
    return (names[0] if names else key.replace("_", " ")).upper()
