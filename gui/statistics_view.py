"""
gui/statistics_view.py
======================
File này dùng để làm gì?
    Màn hình thống kê: tổng số lần nhận diện, gesture xuất hiện nhiều nhất,
    độ tin cậy trung bình, accuracy của model (gần nhất / trung bình), biểu
    đồ số lần nhận diện theo gesture, theo tay và theo ngày.

Dữ liệu đi vào từ đâu?
    Bảng recognition_history và training_history trong SQLite.

Dữ liệu được xử lý như thế nào?
    Truy vấn GROUP BY / AVG bằng SQL rồi vẽ bằng matplotlib.

Dữ liệu được truyền sang module nào?
    Không truyền đi; chỉ hiển thị.

Kết quả trả về ở đâu?
    Thẻ số liệu và biểu đồ trên giao diện.
"""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from database.database import DatabaseError
from gui.common import BasePage, ChartPanel, InfoCard, title_label
from utils.constants import display_gesture, tr
from utils.helpers import format_percent


class StatisticsView(BasePage):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.grid_rowconfigure(2, weight=1)
        title_label(self, tr("Statistics")).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(14, 6))
        ctk.CTkButton(self, text=tr("Refresh"), width=110, command=self.refresh).grid(row=0, column=4, sticky="e", padx=16)

        self.cards = {}
        for i, (key, title) in enumerate((("total", "Total recognitions"), ("top", "Most frequent gesture"),
                                          ("conf", "Average confidence"), ("acc", "Latest model accuracy"),
                                          ("avg_acc", "Average model accuracy"))):
            card = InfoCard(self, tr(title), value_size=18)
            card.grid(row=1, column=i, sticky="nsew", padx=8, pady=8)
            self.cards[key] = card

        self.chart = ChartPanel(self, figsize=(7, 4.5))
        self.chart.grid(row=2, column=0, columnspan=5, sticky="nsew", padx=16, pady=(0, 16))

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        repo, train_repo = self.app.history_repo, self.app.training_repo
        try:
            total = repo.total_count()
            top = repo.most_common()
            avg_conf = repo.average_confidence()
            by_gesture = repo.count_by_gesture()
            by_hand = repo.count_by_hand()
            by_day = repo.count_by_day(14)
            latest = train_repo.latest()
            avg_acc = train_repo.average_accuracy()
        except DatabaseError as exc:
            messagebox.showerror(tr("Error"), str(exc))
            return

        self.cards["total"].set(f"{total:,}")
        self.cards["top"].set(f"{display_gesture(top[0])} ({top[1]})" if top else "--")
        self.cards["conf"].set(format_percent(avg_conf))
        self.cards["acc"].set(f"{format_percent(latest['accuracy'])}\n{latest['algorithm']}" if latest else "--")
        self.cards["avg_acc"].set(format_percent(avg_acc))

        def plot(fig):
            fig.clear()
            gs = fig.add_gridspec(2, 3)
            ax1 = fig.add_subplot(gs[0, :2])
            ax2 = fig.add_subplot(gs[0, 2])
            ax3 = fig.add_subplot(gs[1, :])
            if by_gesture:
                names = [display_gesture(g, "en") for g, _ in by_gesture]
                ax1.bar(names, [n for _, n in by_gesture], color="#3b8ed0")
                ax1.tick_params(axis="x", rotation=30, labelsize=8)
            else:
                ax1.text(0.5, 0.5, "No data", ha="center", va="center")
            ax1.set_title("Recognitions by gesture")
            if by_hand:
                ax2.pie([n for _, n in by_hand], labels=[h for h, _ in by_hand], autopct="%1.0f%%",
                        colors=["#ff8c00", "#3c3cff", "#888888"][:len(by_hand)])
            else:
                ax2.text(0.5, 0.5, "No data", ha="center", va="center")
                ax2.axis("off")
            ax2.set_title("Recognitions by hand")
            ax3.plot([d[5:] for d, _ in by_day], [n for _, n in by_day], marker="o", color="#2e7d32")
            ax3.set_title("Recognitions per day (last 14 days)")
            ax3.tick_params(axis="x", labelsize=8)
            ax3.grid(alpha=0.3)
            fig.tight_layout()

        self.chart.draw(plot)
