"""
gui/recognition_view.py
=======================
File này dùng để làm gì?
    Màn hình nhận diện thời gian thực. Bên trái: camera. Bên phải: gesture
    nhận diện được, độ tin cậy, tay trái/phải, FPS, số bàn tay, nguồn dự đoán
    và các nút Start / Stop / Capture / Record.

Dữ liệu đi vào từ đâu?
    FrameResult (frame + list[Prediction] + fps) từ core.engine thông qua
    MainWindow._tick() -> on_frame().

Dữ liệu được xử lý như thế nào?
    Chọn dự đoán chính (tin cậy cao nhất), hiển thị tên gesture theo ngôn ngữ
    đang chọn, cập nhật thanh tiến trình độ tin cậy, liệt kê chi tiết từng tay.

Dữ liệu được truyền sang module nào?
    Lệnh người dùng -> core.engine (start, stop, capture, toggle_recording).

Kết quả trả về ở đâu?
    Hiển thị trên giao diện; ảnh/video lưu vào captures/ và recordings/.
"""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from gui.camera_view import CameraView
from gui.common import BasePage, title_label
from utils.constants import display_gesture, tr


class RecognitionView(BasePage):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1, minsize=320)
        self.grid_rowconfigure(1, weight=1)

        title_label(self, tr("Recognition")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        self.camera_view = CameraView(self)
        self.camera_view.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))

        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        panel.grid_columnconfigure(0, weight=1)

        title_label(panel, tr("Recognition result"), 17).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(panel, text=tr("Gesture"), text_color="gray60").grid(row=1, column=0, sticky="w", padx=16)
        self.gesture_lbl = ctk.CTkLabel(panel, text="---", font=ctk.CTkFont(size=28, weight="bold"),
                                        anchor="w", wraplength=290, justify="left")
        self.gesture_lbl.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 8))

        self.conf_lbl = ctk.CTkLabel(panel, text=f"{tr('Confidence')}: --", anchor="w")
        self.conf_lbl.grid(row=3, column=0, sticky="w", padx=16)
        self.conf_bar = ctk.CTkProgressBar(panel)
        self.conf_bar.set(0)
        self.conf_bar.grid(row=4, column=0, sticky="ew", padx=16, pady=(2, 10))

        self.info_labels = {}
        for i, key in enumerate(("Hand", "FPS", "Detected hands", "Source")):
            lbl = ctk.CTkLabel(panel, text=f"{tr(key)}: --", anchor="w", font=ctk.CTkFont(size=14))
            lbl.grid(row=5 + i, column=0, sticky="w", padx=16, pady=2)
            self.info_labels[key] = lbl

        ctk.CTkLabel(panel, text=tr("Details"), text_color="gray60").grid(row=9, column=0, sticky="w", padx=16, pady=(10, 0))
        self.details = ctk.CTkTextbox(panel, height=110, font=ctk.CTkFont(family="Consolas", size=12))
        self.details.grid(row=10, column=0, sticky="ew", padx=16, pady=(2, 10))
        self.details.configure(state="disabled")
        self._details_text = ""

        btns = ctk.CTkFrame(panel, fg_color="transparent")
        btns.grid(row=11, column=0, sticky="ew", padx=12, pady=(4, 14))
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text=tr("Start"), fg_color="#2e7d32", hover_color="#1b5e20",
                      command=self.app.start_camera).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btns, text=tr("Stop"), fg_color="#c62828", hover_color="#8e0000",
                      command=self.app.stop_camera).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btns, text=tr("Capture"), command=self._capture).grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        self.record_btn = ctk.CTkButton(btns, text=tr("Record"), command=self._record)
        self.record_btn.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

    # ---------------------------------------------------------------- hooks
    def on_frame(self, result) -> None:
        self.camera_view.show_frame(result.frame)
        primary = result.primary()
        if primary is None:
            self.gesture_lbl.configure(text=tr("No hand"), text_color=("gray40", "gray60"))
            self.conf_lbl.configure(text=f"{tr('Confidence')}: --")
            self.conf_bar.set(0)
            hand = "--"
            source = self.app.engine.predictor.active_source
        else:
            name = display_gesture(primary.gesture) if primary.accepted else tr("Unknown")
            color = ("#1b5e20", "#66bb6a") if primary.accepted else ("#e65100", "#ffa726")
            self.gesture_lbl.configure(text=name.upper(), text_color=color)
            self.conf_lbl.configure(text=f"{tr('Confidence')}: {primary.confidence * 100:.2f}%")
            self.conf_bar.set(max(0.0, min(1.0, primary.confidence)))
            hand = tr(primary.hand.handedness)
            source = primary.source

        self.info_labels["Hand"].configure(text=f"{tr('Hand')}: {hand}")
        self.info_labels["FPS"].configure(text=f"{tr('FPS')}: {result.fps:.1f}")
        self.info_labels["Detected hands"].configure(text=f"{tr('Detected hands')}: {result.num_hands}")
        self.info_labels["Source"].configure(text=f"{tr('Source')}: {source}")

        lines = []
        for p in result.predictions:
            g = display_gesture(p.gesture) if p.accepted else tr("Unknown")
            lines.append(f"{tr(p.hand.handedness):<6} | {g:<16} | {p.confidence * 100:5.1f}%")
        text = "\n".join(lines) or tr("No hand")
        if text != self._details_text:
            self._details_text = text
            self.details.configure(state="normal")
            self.details.delete("1.0", "end")
            self.details.insert("1.0", text)
            self.details.configure(state="disabled")
        self.record_btn.configure(text=tr("Stop Recording") if self.app.engine.is_recording else tr("Record"))

    def on_camera_stopped(self) -> None:
        self.camera_view.show_placeholder()
        self.gesture_lbl.configure(text="---", text_color=("gray10", "gray90"))
        self.conf_lbl.configure(text=f"{tr('Confidence')}: --")
        self.conf_bar.set(0)
        self.record_btn.configure(text=tr("Record"))

    # -------------------------------------------------------------- actions
    def _capture(self) -> None:
        if not self.app.engine.is_running:
            messagebox.showwarning(tr("Warning"), tr("Camera is not running"))
            return
        path = self.app.engine.capture()
        if path:
            messagebox.showinfo(tr("Information"), f"{tr('Image saved')}:\n{path}")

    def _record(self) -> None:
        if not self.app.engine.is_running:
            messagebox.showwarning(tr("Warning"), tr("Camera is not running"))
            return
        saved = self.app.engine.toggle_recording()
        if saved:
            messagebox.showinfo(tr("Information"), f"{tr('Video saved')}:\n{saved}")
        self.record_btn.configure(text=tr("Stop Recording") if self.app.engine.is_recording else tr("Record"))
