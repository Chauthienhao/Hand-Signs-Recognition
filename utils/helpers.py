"""
utils/helpers.py
================
File này dùng để làm gì?
    Các hàm tiện ích dùng chung: thời gian, tạo thư mục, lưu ảnh an toàn trên
    Windows (đường dẫn có dấu tiếng Việt), tải file, chuyển frame OpenCV
    sang ảnh PIL để hiển thị trên giao diện, kiểm tra ngày tháng.

Dữ liệu đi vào từ đâu?
    Tham số do các module khác truyền vào (frame, đường dẫn, URL, chuỗi ngày).

Dữ liệu được xử lý như thế nào?
    Mỗi hàm thực hiện một nhiệm vụ nhỏ, độc lập, có xử lý ngoại lệ.

Dữ liệu được truyền sang module nào?
    camera, detection, core.engine, database, gui.

Kết quả trả về ở đâu?
    Giá trị trả về của hàm (chuỗi, bool, ảnh PIL, đường dẫn...).
"""
from __future__ import annotations

import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"


def now_str() -> str:
    return datetime.now().strftime(TIMESTAMP_FMT)


def file_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_date(text: str) -> Optional[date]:
    """'2026-10-01' -> date; chuỗi rỗng -> None; sai định dạng -> ValueError."""
    text = (text or "").strip()
    if not text:
        return None
    return datetime.strptime(text, "%Y-%m-%d").date()


def save_image(path: Path, image: np.ndarray) -> bool:
    """Lưu ảnh bằng imencode + tofile để hỗ trợ đường dẫn Unicode trên Windows."""
    path = Path(path)
    ensure_dir(path.parent)
    ext = path.suffix or ".png"
    ok, buffer = cv2.imencode(ext, image)
    if not ok:
        return False
    buffer.tofile(str(path))
    return True


def bgr_to_pil(frame: np.ndarray):
    from PIL import Image

    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


def download_file(
    url: str,
    dest: Path,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    timeout: int = 60,
) -> Path:
    """Tải file về file tạm rồi đổi tên, tránh để lại file hỏng khi mất mạng."""
    dest = Path(dest)
    ensure_dir(dest.parent)
    tmp = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "HandSignsRecognition/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response, open(tmp, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress_cb:
                progress_cb(done, total)
    tmp.replace(dest)
    return dest


def format_percent(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "--"
    return f"{value * 100:.{digits}f}%"
