"""
gui/camera_view.py
==================
File này dùng để làm gì?
    Widget hiển thị hình ảnh camera trong giao diện (dùng chung cho màn hình
    Recognition và Dataset).

Dữ liệu đi vào từ đâu?
    Frame BGR đã vẽ kết quả (FrameResult.frame) do MainWindow lấy từ
    core.engine và chuyển cho view đang hiển thị.

Dữ liệu được xử lý như thế nào?
    BGR -> RGB -> ảnh PIL -> co giãn vừa khung (giữ tỉ lệ) -> ImageTk.PhotoImage.
    Khi camera tắt thì hiển thị dòng chữ hướng dẫn.

Dữ liệu được truyền sang module nào?
    Không truyền đi; chỉ hiển thị.

Kết quả trả về ở đâu?
    Trên màn hình (tk.Label bên trong khung).
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk

from utils.constants import tr


class CameraView(ctk.CTkFrame):
    def __init__(self, master, min_size=(480, 360)) -> None:
        super().__init__(master, fg_color="black", corner_radius=10)
        self._photo = None
        self._min_w, self._min_h = min_size
        self.label = tk.Label(self, bg="black", fg="#bbbbbb", font=("Segoe UI", 13),
                              text=tr("Camera is off. Press Start to begin."))
        self.label.pack(fill="both", expand=True, padx=6, pady=6)

    def show_frame(self, frame: np.ndarray) -> None:
        if frame is None:
            return
        box_w = max(self.label.winfo_width(), self._min_w // 2)
        box_h = max(self.label.winfo_height(), self._min_h // 2)
        h, w = frame.shape[:2]
        scale = min(box_w / w, box_h / h)
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb).resize(new_size, Image.BILINEAR)
        self._photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self._photo, text="")

    def show_placeholder(self, text: str = "") -> None:
        self._photo = None
        self.label.configure(image="", text=text or tr("Camera is off. Press Start to begin."))
