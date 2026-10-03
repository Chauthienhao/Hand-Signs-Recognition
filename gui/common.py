"""
gui/common.py
=============
File này dùng để làm gì?
    Các thành phần giao diện dùng chung: lớp BasePage (mọi màn hình kế thừa),
    InfoCard (thẻ hiển thị số liệu), ChartPanel (nhúng biểu đồ matplotlib),
    hàm tạo bảng Treeview có thanh cuộn và đổi màu bảng theo theme.

Dữ liệu đi vào từ đâu?
    Tham số do các view truyền vào (tiêu đề, giá trị, cột bảng, Figure...).

Dữ liệu được xử lý như thế nào?
    Đóng gói widget CustomTkinter/ttk để các màn hình viết ngắn gọn, đồng nhất.

Dữ liệu được truyền sang module nào?
    Tất cả file trong gui/.

Kết quả trả về ở đâu?
    Widget được đặt trực tiếp lên màn hình gọi nó.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Sequence, Tuple

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from utils.constants import tr


class BasePage(ctk.CTkFrame):
    """Lớp cha của mọi màn hình. MainWindow gọi các hook bên dưới."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app

    def on_show(self) -> None:
        """Gọi khi màn hình được hiển thị."""

    def on_hide(self) -> None:
        """Gọi khi chuyển sang màn hình khác."""

    def on_frame(self, result) -> None:
        """Gọi mỗi khi có frame mới từ engine (chỉ với màn hình đang hiển thị)."""

    def on_camera_stopped(self) -> None:
        """Gọi khi camera vừa tắt."""


def title_label(master, text: str, size: int = 22) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=text, font=ctk.CTkFont(size=size, weight="bold"), anchor="w")


class InfoCard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: str = "--", value_size: int = 22) -> None:
        super().__init__(master, corner_radius=10)
        self.title_lbl = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=12), text_color="gray60")
        self.title_lbl.pack(anchor="w", padx=12, pady=(10, 0))
        self.value_lbl = ctk.CTkLabel(self, text=value, font=ctk.CTkFont(size=value_size, weight="bold"),
                                      anchor="w", justify="left")
        self.value_lbl.pack(anchor="w", padx=12, pady=(0, 10), fill="x")

    def set(self, value: str) -> None:
        self.value_lbl.configure(text=value)


class ChartPanel(ctk.CTkFrame):
    """Khung chứa 1 Figure matplotlib; gọi draw(fn) với fn(fig) để vẽ lại."""

    def __init__(self, master, figsize=(6, 4)) -> None:
        super().__init__(master)
        self.figure = Figure(figsize=figsize, dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def draw(self, plot_fn: Callable[[Figure], None]) -> None:
        try:
            plot_fn(self.figure)
        except Exception as exc:  # không để lỗi vẽ làm hỏng giao diện
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Chart error: {exc}", ha="center", va="center", wrap=True)
            ax.axis("off")
        self.canvas.draw_idle()


def apply_treeview_style() -> None:
    """Tô màu ttk.Treeview cho hợp với theme sáng/tối của CustomTkinter."""
    dark = ctk.get_appearance_mode() == "Dark"
    bg, fg, sel, head = ("#2b2b2b", "#e8e8e8", "#1f6aa5", "#1f538d") if dark else \
        ("#ffffff", "#111111", "#3b8ed0", "#3b8ed0")
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, rowheight=26,
                    borderwidth=0, font=("Segoe UI", 10))
    style.map("Treeview", background=[("selected", sel)], foreground=[("selected", "white")])
    style.configure("Treeview.Heading", background=head, foreground="white", relief="flat",
                    font=("Segoe UI", 10, "bold"))
    style.map("Treeview.Heading", background=[("active", sel)])


def make_table(master, columns: Sequence[Tuple[str, str, int]], height: int = 12,
               selectmode: str = "browse", horizontal: bool = False) -> Tuple[ctk.CTkFrame, ttk.Treeview]:
    """columns: [(id, tiêu đề, độ rộng)]. Trả (frame chứa, treeview)."""
    frame = ctk.CTkFrame(master)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings",
                        height=height, selectmode=selectmode)
    for cid, heading, width in columns:
        tree.heading(cid, text=heading)
        tree.column(cid, width=width, anchor="center", stretch=not horizontal)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb = ctk.CTkScrollbar(frame, command=tree.yview)
    vsb.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=vsb.set)
    if horizontal:
        hsb = ctk.CTkScrollbar(frame, orientation="horizontal", command=tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        tree.configure(xscrollcommand=hsb.set)
    return frame, tree


def clear_table(tree: ttk.Treeview) -> None:
    tree.delete(*tree.get_children())


def translate_status(status: str) -> str:
    return tr(status)
