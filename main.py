"""
main.py
=======
File này dùng để làm gì?
    Điểm khởi động của chương trình. Kiểm tra phiên bản Python và thư viện,
    khởi tạo logging, cấu hình, database, dataset, model, engine nhận diện,
    rồi mở giao diện chính.

Dữ liệu đi vào từ đâu?
    config/settings.json, database/hand_signs.db, data/hand_signs.csv,
    models/hand_sign_model.pkl (nếu đã train).

Dữ liệu được xử lý như thế nào?
    Tạo các đối tượng dịch vụ theo thứ tự phụ thuộc:
      Settings -> Database -> Repositories -> DatasetManager
      -> GestureClassifier -> RecognitionEngine -> MainWindow

Dữ liệu được truyền sang module nào?
    Các đối tượng trên được "tiêm" (inject) vào gui/main_window.py.

Kết quả trả về ở đâu?
    Cửa sổ ứng dụng. Mọi lỗi khởi động được ghi log và báo bằng hộp thoại.

Chạy:
    python main.py
"""
from __future__ import annotations

import os
import sys

# Đảm bảo import được các package khi chạy từ thư mục khác
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils import python_compatibility as pc  # noqa: E402


def show_message(message: str, error: bool = True) -> None:
    print(("ERROR: " if error else "WARNING: ") + message, file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        (messagebox.showerror if error else messagebox.showwarning)("Hand Signs Recognition", message)
        root.destroy()
    except Exception:
        pass


def show_fatal(message: str) -> None:
    show_message(message, error=True)


def check_environment() -> bool:
    """Kiểm tra Python + thư viện trước khi tạo giao diện.

    - Python cũ hơn mức tối thiểu / 32-bit  -> báo lỗi, KHÔNG chạy.
    - Python mới hơn bản đã kiểm thử         -> cảnh báo, vẫn chạy.
    - Thiếu thư viện bắt buộc                -> báo lỗi kèm lệnh cài, KHÔNG chạy.
    - MediaPipe lỗi/không tương thích        -> cảnh báo, chạy với camera bị vô hiệu.
    """
    py = pc.check_python()
    if not py.ok:
        show_fatal(f"Python {py.version}: {py.status}.\n{py.note}\n\n"
                   f"Recommended: Python {pc.RECOMMENDED_PYTHON}\n\n{pc.venv_instructions()}")
        return False

    from utils import dependency_checker as dc

    results = dc.check_all()
    blocking = [r for r in results if r.blocking]
    if blocking:
        details = "\n\n".join(f"- {r.message}\n  Fix: {r.fix}" for r in blocking)
        show_fatal(f"Python: {sys.executable} ({py.version})\n\n{details}\n\n"
                   "Install all dependencies in the SAME environment:\n"
                   "    python -m pip install -r requirements.txt\n"
                   "Then verify with:  python check_environment.py")
        return False

    warnings = []
    if py.status != pc.STATUS_SUPPORTED:
        warnings.append(f"Python {py.version}: {py.note}\nRecommended: Python {pc.RECOMMENDED_PYTHON}")
    mp_res = next(r for r in results if r.dep.module == "mediapipe")
    if not mp_res.ok:
        warnings.append(f"{mp_res.message}\nFix: {mp_res.fix}\n"
                        "Camera / recognition will be disabled; other screens still work.")
    else:
        api_ok, msg = dc.check_mediapipe_tasks_api()
        if not api_ok:
            warnings.append(msg + "\nCamera / recognition will be disabled.")
    if warnings:
        show_message("\n\n".join(warnings) + "\n\nDetails: python check_environment.py", error=False)
    return True


def main() -> int:
    if not check_environment():
        return 1

    import customtkinter as ctk

    from config.config import settings
    from core.engine import RecognitionEngine
    from database.database import Database, DatabaseError, GestureRepository
    from database.history import HistoryRepository, TrainingHistoryRepository
    from dataset.dataset_manager import DatasetError, DatasetManager
    from gui.main_window import MainWindow
    from recognition.gesture_classifier import GestureClassifier
    from utils.constants import APP_NAME, APP_VERSION, set_language
    from utils.logger import get_logger

    logger = get_logger("main")
    patches = pc.apply_runtime_patches()
    if patches:
        logger.info("Compatibility patches applied: %s", ", ".join(patches))
    logger.info("Starting %s v%s (Python %s)", APP_NAME, APP_VERSION, sys.version.split()[0])

    set_language(settings.get("language"))
    ctk.set_appearance_mode(settings.get("theme"))
    ctk.set_default_color_theme("blue")

    try:
        db = Database()
        gesture_repo = GestureRepository(db)
        history_repo = HistoryRepository(db)
        training_repo = TrainingHistoryRepository(db)
        dataset_manager = DatasetManager(gesture_repo=gesture_repo)
        classifier = GestureClassifier()
        engine = RecognitionEngine(settings, classifier, dataset_manager, history_repo)
    except (DatabaseError, DatasetError, OSError) as exc:
        logger.exception("Initialization failed")
        show_fatal(f"Initialization failed:\n{exc}")
        return 1

    try:
        app = MainWindow(settings, engine, classifier, dataset_manager, history_repo, training_repo)
        app.mainloop()
    except Exception as exc:
        logger.exception("Fatal GUI error")
        engine.shutdown()
        show_fatal(f"Unexpected error:\n{exc}")
        return 1
    logger.info("Application closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
