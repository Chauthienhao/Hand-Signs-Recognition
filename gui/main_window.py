"""
gui/main_window.py
==================
File này dùng để làm gì?
    Cửa sổ chính của ứng dụng: thanh menu bên trái (Dashboard, Recognition,
    Dataset, Training, History, Statistics, Settings, Start/Stop Camera, Exit),
    vùng nội dung ở giữa và thanh trạng thái phía dưới. Chứa luôn màn hình
    Dashboard (HomeView).

Dữ liệu đi vào từ đâu?
    - Các service khởi tạo trong main.py: engine, dataset_manager,
      history_repo, training_repo, classifier, settings.
    - FrameResult mới nhất từ core.engine (lấy định kỳ 30 ms bằng after()).

Dữ liệu được xử lý như thế nào?
    _tick(): lấy lỗi từ engine -> hiện messagebox; lấy frame mới -> chuyển
    cho màn hình đang mở (on_frame); cập nhật thanh trạng thái.
    Mọi thao tác widget đều chạy trên thread giao diện (Tkinter không thread-safe).

Dữ liệu được truyền sang module nào?
    Các view trong gui/ (recognition_view, dataset_view, ...).

Kết quả trả về ở đâu?
    Hiển thị trên giao diện người dùng.
"""
from __future__ import annotations

from tkinter import messagebox
from typing import Dict

import customtkinter as ctk

from config.config import Settings
from gui.common import BasePage, InfoCard, apply_treeview_style, title_label
from gui.dataset_view import DatasetView
from gui.history_view import HistoryView
from gui.recognition_view import RecognitionView
from gui.settings_view import SettingsView
from gui.spelling_view import SpellingView
from gui.statistics_view import StatisticsView
from gui.training_view import TrainingView
from utils.constants import APP_NAME, APP_VERSION, tr
from utils.logger import get_logger

logger = get_logger(__name__)


class HomeView(BasePage):
    """Màn hình Dashboard: tổng quan hệ thống + nút bắt đầu nhanh."""

    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        title_label(self, tr("Hand Signs Recognition System"), 26).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(self, text=f"{APP_NAME} v{APP_VERSION} — OpenCV • MediaPipe • Scikit-learn • SQLite",
                     text_color="gray60").grid(row=1, column=0, columnspan=4, sticky="w", padx=20)

        self.card_camera = InfoCard(self, tr("Camera status"))
        self.card_model = InfoCard(self, tr("Recognition model"), value_size=18)
        self.card_dataset = InfoCard(self, tr("Dataset samples"))
        self.card_history = InfoCard(self, tr("Total recognitions"))
        for i, card in enumerate((self.card_camera, self.card_model, self.card_dataset, self.card_history)):
            card.grid(row=2, column=i, sticky="nsew", padx=10, pady=20)

        quick = ctk.CTkFrame(self)
        quick.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
        title_label(quick, tr("Quick start"), 16).pack(anchor="w", padx=14, pady=(10, 6))
        btns = ctk.CTkFrame(quick, fg_color="transparent")
        btns.pack(fill="x", padx=10, pady=(0, 12))
        for text, page in (("Recognition", "recognition"), ("Spelling", "spelling"), ("Dataset", "dataset"),
                           ("Training", "training"), ("Statistics", "statistics")):
            ctk.CTkButton(btns, text=tr(text), height=40,
                          command=lambda p=page: app.show_page(p)).pack(side="left", padx=6, expand=True, fill="x")

        flow = ctk.CTkFrame(self)
        flow.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
        title_label(flow, tr("Processing pipeline"), 16).pack(anchor="w", padx=14, pady=(10, 4))
        pipeline = ("Camera  →  OpenCV  →  MediaPipe  →  21 Landmarks  →  Feature Extraction"
                    "  →  ML Classifier  →  Gesture  →  GUI  →  SQLite")
        ctk.CTkLabel(flow, text=pipeline, font=ctk.CTkFont(size=14), wraplength=900,
                     justify="left").pack(anchor="w", padx=14, pady=(0, 14))

    def on_show(self) -> None:
        engine = self.app.engine
        self.card_camera.set(tr("Running") if engine.is_running else tr("Stopped"))
        clf = self.app.classifier
        if clf.is_loaded:
            acc = clf.info().get("metrics", {}).get("accuracy")
            self.card_model.set(f"{clf.algorithm}\nAccuracy {acc * 100:.1f}%" if acc else str(clf.algorithm))
        else:
            self.card_model.set(tr("Built-in (MediaPipe)"))
        try:
            counts = self.app.dataset_manager.counts()
            self.card_dataset.set(f"{sum(counts.values())}  ({len(counts)} {tr('gestures')})")
        except Exception as exc:
            self.card_dataset.set("--")
            logger.error("Dataset error: %s", exc)
        try:
            self.card_history.set(str(self.app.history_repo.total_count()))
        except Exception:
            self.card_history.set("--")


class MainWindow(ctk.CTk):
    NAV = [
        ("home", "Dashboard"), ("recognition", "Recognition"), ("spelling", "Spelling"), ("dataset", "Dataset"),
        ("training", "Training"), ("history", "History"), ("statistics", "Statistics"),
        ("settings", "Settings"),
    ]

    def __init__(self, settings: Settings, engine, classifier, dataset_manager,
                 history_repo, training_repo) -> None:
        super().__init__()
        self.settings = settings
        self.engine = engine
        self.classifier = classifier
        self.dataset_manager = dataset_manager
        self.history_repo = history_repo
        self.training_repo = training_repo

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1320x800")
        self.minsize(1120, 700)
        apply_treeview_style()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.status_bar = ctk.CTkLabel(self, text="", anchor="w", height=26, fg_color=("gray85", "gray17"))
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

        page_classes = {
            "home": HomeView, "recognition": RecognitionView, "spelling": SpellingView, "dataset": DatasetView,
            "training": TrainingView, "history": HistoryView, "statistics": StatisticsView,
            "settings": SettingsView,
        }
        self.pages: Dict[str, BasePage] = {}
        for name, cls in page_classes.items():
            page = cls(self.content, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page

        self.current = ""
        self._last_frame_id = -1
        self._was_running = False
        self.show_page("home")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(30, self._tick)

    # ------------------------------------------------------------ sidebar
    def _build_sidebar(self) -> None:
        bar = ctk.CTkFrame(self, width=210, corner_radius=0)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)
        ctk.CTkLabel(bar, text="✋ Hand Signs", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(24, 2))
        ctk.CTkLabel(bar, text="Recognition System", text_color="gray60").pack(pady=(0, 18))

        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        for name, text in self.NAV:
            btn = ctk.CTkButton(bar, text=tr(text), anchor="w", height=38, corner_radius=8,
                                fg_color="transparent", text_color=("gray10", "gray90"),
                                hover_color=("gray75", "gray25"),
                                command=lambda n=name: self.show_page(n))
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[name] = btn

        ctk.CTkFrame(bar, height=2, fg_color=("gray70", "gray30")).pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(bar, text="▶  " + tr("Start Camera"), fg_color="#2e7d32", hover_color="#1b5e20",
                      command=self.start_camera).pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(bar, text="■  " + tr("Stop Camera"), fg_color="#c62828", hover_color="#8e0000",
                      command=self.stop_camera).pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(bar, text=tr("Exit"), fg_color="gray40", hover_color="gray30",
                      command=self.on_close).pack(side="bottom", fill="x", padx=12, pady=16)

    def show_page(self, name: str) -> None:
        if name == self.current:
            return
        if self.current:
            self.pages[self.current].on_hide()
            self.nav_buttons[self.current].configure(fg_color="transparent")
        self.current = name
        self.nav_buttons[name].configure(fg_color=("gray75", "gray25"))
        page = self.pages[name]
        page.tkraise()
        try:
            page.on_show()
        except Exception as exc:
            logger.exception("Error showing page %s", name)
            messagebox.showerror(tr("Error"), str(exc))

    # ------------------------------------------------------------- camera
    def start_camera(self) -> None:
        self.engine.start()

    def stop_camera(self) -> None:
        self.engine.stop()

    # --------------------------------------------------------------- loop
    def _tick(self) -> None:
        try:
            for err in self.engine.pop_errors():
                messagebox.showerror(tr("Error"), err)

            running = self.engine.is_running
            if running:
                result = self.engine.get_latest()
                if result is not None and result.frame_id != self._last_frame_id:
                    self._last_frame_id = result.frame_id
                    self.pages[self.current].on_frame(result)
            elif self._was_running:
                for page in self.pages.values():
                    page.on_camera_stopped()
            self._was_running = running
            self._update_status_bar()
        except Exception:
            logger.exception("GUI tick error")
        finally:
            self.after(30, self._tick)

    def _update_status_bar(self) -> None:
        engine = self.engine
        model = self.classifier.algorithm if self.classifier.is_loaded else tr("Built-in (MediaPipe)")
        cam = f"{tr('Running')} (#{self.settings.get('camera_index')})" if engine.is_running else tr("Stopped")
        text = (f"   {tr('Camera')}: {cam}   |   FPS: {engine.fps:.1f}   |   {tr('Model')}: {model}"
                f"   |   {tr('Model mode')}: {self.settings.get('model_mode')}   |   {tr('Status')}: {engine.status}")
        if engine.is_recording:
            text += "   |   ● REC"
        self.status_bar.configure(text=text)

    def on_close(self) -> None:
        if not messagebox.askyesno(tr("Confirm"), tr("Do you want to exit?")):
            return
        try:
            self.engine.shutdown()
        except Exception:
            logger.exception("Error during shutdown")
        self.destroy()
