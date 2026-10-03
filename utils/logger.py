"""
utils/logger.py
===============
File này dùng để làm gì?
    Cấu hình hệ thống ghi log (logging) cho toàn bộ ứng dụng: ghi ra màn hình
    console và file logs/app.log (tự xoay vòng khi file lớn).

Dữ liệu đi vào từ đâu?
    Các thông điệp log từ mọi module thông qua get_logger(__name__).

Dữ liệu được xử lý như thế nào?
    Định dạng: thời gian | mức độ | tên module | nội dung.

Dữ liệu được truyền sang module nào?
    Không truyền đi; chỉ ghi ra console và file log.

Kết quả trả về ở đâu?
    File logs/app.log (dùng để debug và đưa vào báo cáo khi cần).
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from config.config import LOG_DIR

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    root = logging.getLogger()
    root.setLevel(level)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError as exc:  # không có quyền ghi -> vẫn chạy với console log
        root.warning("Cannot create log file: %s", exc)

    # Giảm log rác từ thư viện bên ngoài
    for noisy in ("matplotlib", "PIL", "absl"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
