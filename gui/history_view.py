"""
gui/history_view.py
===================
File này dùng để làm gì?
    Màn hình lịch sử nhận diện: xem, tìm kiếm theo gesture, lọc theo ngày và
    theo tay, xóa mục đã chọn / xóa tất cả, xuất CSV.

Dữ liệu đi vào từ đâu?
    Bảng recognition_history trong SQLite (qua HistoryRepository) và điều
    kiện lọc do người dùng nhập.

Dữ liệu được xử lý như thế nào?
    Kiểm tra định dạng ngày (YYYY-MM-DD) -> truy vấn có tham số -> hiển thị
    tối đa 2000 bản ghi mới nhất.

Dữ liệu được truyền sang module nào?
    database/history.py.

Kết quả trả về ở đâu?
    Bảng trên giao diện; file CSV do người dùng chọn.
"""
from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk

from database.database import DatabaseError
from gui.common import BasePage, clear_table, make_table, title_label
from utils.constants import display_gesture, tr
from utils.helpers import file_stamp, parse_date


class HistoryView(BasePage):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        title_label(self, tr("Recognition History")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        bar = ctk.CTkFrame(self)
        bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.search_entry = ctk.CTkEntry(bar, placeholder_text=tr("Search gesture"), width=170)
        self.search_entry.pack(side="left", padx=6, pady=10)
        self.from_entry = ctk.CTkEntry(bar, placeholder_text=tr("From (YYYY-MM-DD)"), width=170)
        self.from_entry.pack(side="left", padx=6)
        self.to_entry = ctk.CTkEntry(bar, placeholder_text=tr("To (YYYY-MM-DD)"), width=170)
        self.to_entry.pack(side="left", padx=6)
        self.hand_menu = ctk.CTkOptionMenu(bar, values=[tr("All"), "Left", "Right"], width=100)
        self.hand_menu.pack(side="left", padx=6)
        ctk.CTkButton(bar, text=tr("Search"), width=90, command=self.refresh).pack(side="left", padx=6)
        ctk.CTkButton(bar, text=tr("Reset"), width=80, fg_color="gray40", command=self._reset).pack(side="left", padx=6)

        table_frame, self.tree = make_table(self, [
            ("id", "ID", 70), ("gesture", tr("Gesture"), 200), ("confidence", tr("Confidence"), 120),
            ("hand", tr("Hand"), 100), ("source", tr("Source"), 100), ("timestamp", tr("Time"), 190),
        ], height=18, selectmode="extended")
        table_frame.grid(row=2, column=0, sticky="nsew", padx=16)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=16, pady=10)
        self.count_lbl = ctk.CTkLabel(bottom, text="")
        self.count_lbl.pack(side="left", padx=4)
        ctk.CTkButton(bottom, text=tr("Export CSV"), command=self._export).pack(side="right", padx=4)
        ctk.CTkButton(bottom, text=tr("Delete All"), fg_color="#8e0000", command=self._delete_all).pack(side="right", padx=4)
        ctk.CTkButton(bottom, text=tr("Delete Selected"), fg_color="#c62828", command=self._delete_selected).pack(side="right", padx=4)
        self._rows = []

    def on_show(self) -> None:
        self.refresh()

    def _filters(self):
        try:
            d_from = parse_date(self.from_entry.get())
            d_to = parse_date(self.to_entry.get())
        except ValueError:
            messagebox.showerror(tr("Error"), f"{tr('Invalid date')} (YYYY-MM-DD)")
            return None
        hand = self.hand_menu.get()
        return dict(gesture=self.search_entry.get().strip(), date_from=d_from, date_to=d_to,
                    hand="" if hand == tr("All") else hand)

    def refresh(self) -> None:
        filters = self._filters()
        if filters is None:
            return
        try:
            self._rows = self.app.history_repo.search(**filters)
        except DatabaseError as exc:
            messagebox.showerror(tr("Error"), str(exc))
            return
        clear_table(self.tree)
        for r in self._rows:
            self.tree.insert("", "end", iid=str(r["id"]), values=(
                r["id"], display_gesture(r["gesture"]), f"{r['confidence'] * 100:.2f}%",
                tr(r["hand"]), r["source"], r["timestamp"]))
        self.count_lbl.configure(text=f"{len(self._rows)} {tr('records')}")

    def _reset(self) -> None:
        for e in (self.search_entry, self.from_entry, self.to_entry):
            e.delete(0, "end")
        self.hand_menu.set(tr("All"))
        self.refresh()

    def _delete_selected(self) -> None:
        ids = [int(i) for i in self.tree.selection()]
        if not ids:
            return
        if messagebox.askyesno(tr("Confirm"), f"{tr('Delete Selected')}: {len(ids)} {tr('records')}?"):
            self.app.history_repo.delete_ids(ids)
            self.refresh()

    def _delete_all(self) -> None:
        if messagebox.askyesno(tr("Confirm"), tr("Delete all history?")):
            self.app.history_repo.clear()
            self.refresh()

    def _export(self) -> None:
        if not self._rows:
            messagebox.showwarning(tr("Warning"), tr("No data"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"recognition_history_{file_stamp()}.csv")
        if not path:
            return
        try:
            n = self.app.history_repo.export_csv(self._rows, path)
            messagebox.showinfo(tr("Information"), f"{tr('Exported')} {n} {tr('records')}:\n{path}")
        except OSError as exc:
            messagebox.showerror(tr("Error"), str(exc))
