"""
gui/dataset_view.py
===================
File này dùng để làm gì?
    Màn hình quản lý dataset: bảng Gesture | Số mẫu | Trạng thái, thêm/xóa
    gesture, xem dữ liệu, xóa toàn bộ, và thu thập dữ liệu bằng webcam
    (có xem trước camera + thanh tiến độ).

Dữ liệu đi vào từ đâu?
    - DatasetManager (đọc CSV + bảng gestures trong SQLite).
    - Trạng thái thu thập từ DataCollector (engine.collector.snapshot()).
    - Frame camera từ engine (on_frame).

Dữ liệu được xử lý như thế nào?
    Người dùng chọn gesture + số mẫu -> engine.start_collection() -> engine
    tự bật camera, đếm ngược, trích landmark, chuẩn hóa và ghi CSV.
    Khi xong, bảng được làm mới.

Dữ liệu được truyền sang module nào?
    core.engine (thu thập), dataset/dataset_manager.py (thêm/xóa gesture).

Kết quả trả về ở đâu?
    File data/hand_signs.csv và bảng hiển thị trên giao diện.
"""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from dataset.collector import CollectorState
from dataset.dataset_manager import DatasetError
from gui.camera_view import CameraView
from gui.common import BasePage, clear_table, make_table, title_label
from recognition.feature_extractor import CSV_COLUMNS
from utils.constants import display_gesture, tr
from utils.logger import get_logger

logger = get_logger(__name__)


class DatasetView(BasePage):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)
        title_label(self, tr("Dataset Management")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 6))

        # ----------------------------------------------------- bảng dữ liệu
        left = ctk.CTkFrame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        add_row = ctk.CTkFrame(left, fg_color="transparent")
        add_row.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.new_entry = ctk.CTkEntry(add_row, placeholder_text=tr("New gesture name"))
        self.new_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(add_row, text=tr("Add Gesture"), width=130, command=self._add_gesture).pack(side="left")
        ctk.CTkButton(add_row, text=tr("Add VSL alphabet"), width=170, fg_color="#6a1b9a",
                      hover_color="#4a148c", command=self._add_vsl).pack(side="left", padx=(6, 0))

        table_frame, self.tree = make_table(left, [
            ("gesture", tr("Gesture"), 150), ("display", tr("Display name"), 170),
            ("samples", tr("Number of Samples"), 130), ("status", tr("Status"), 110),
        ], height=14)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.summary_lbl = ctk.CTkLabel(left, text="", anchor="w", justify="left", wraplength=560)
        self.summary_lbl.grid(row=2, column=0, sticky="ew", padx=12, pady=6)

        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        for text, cmd, color in ((tr("Delete Gesture"), self._delete_gesture, "#c62828"),
                                 (tr("View Dataset"), self._view_dataset, None),
                                 (tr("Clear Dataset"), self._clear_dataset, "#8e0000"),
                                 (tr("Refresh"), self.refresh, None)):
            kw = {"fg_color": color} if color else {}
            ctk.CTkButton(btns, text=text, command=cmd, **kw).pack(side="left", padx=4, expand=True, fill="x")

        # ---------------------------------------------------- thu thập dữ liệu
        right = ctk.CTkFrame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        title_label(right, tr("Collect Data"), 17).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))
        self.camera_view = CameraView(right, min_size=(320, 240))
        self.camera_view.grid(row=1, column=0, sticky="nsew", padx=12)

        form = ctk.CTkFrame(right, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text=tr("Gesture")).grid(row=0, column=0, sticky="w", pady=4)
        self.gesture_combo = ctk.CTkComboBox(form, values=[""], state="readonly")
        self.gesture_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)
        ctk.CTkLabel(form, text=tr("Samples")).grid(row=1, column=0, sticky="w", pady=4)
        self.samples_entry = ctk.CTkEntry(form)
        self.samples_entry.insert(0, str(self.app.settings.get("collect_samples")))
        self.samples_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)

        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=12)
        actions.grid_columnconfigure((0, 1), weight=1)
        self.start_btn = ctk.CTkButton(actions, text=tr("Start Collecting"), fg_color="#2e7d32",
                                       hover_color="#1b5e20", command=self._start_collect)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(actions, text=tr("Cancel"), fg_color="gray40",
                      command=self._cancel_collect).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.progress = ctk.CTkProgressBar(right)
        self.progress.set(0)
        self.progress.grid(row=4, column=0, sticky="ew", padx=12, pady=(12, 4))
        self.collect_lbl = ctk.CTkLabel(right, text=tr("Idle"), anchor="w")
        self.collect_lbl.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 12))
        self._last_state = CollectorState.IDLE

    # ---------------------------------------------------------------- data
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        try:
            rows = self.app.dataset_manager.summary(self.app.settings.get("min_samples_ready"))
        except DatasetError as exc:
            messagebox.showerror(tr("Error"), str(exc))
            return
        clear_table(self.tree)
        for r in rows:
            self.tree.insert("", "end", iid=r["gesture"],
                             values=(r["gesture"], r["display"], r["count"], tr(str(r["status"]))))
        total = sum(int(r["count"]) for r in rows)
        ok, msgs = self.app.dataset_manager.validate()
        text = f"{tr('Total samples')}: {total}   |   {tr('Classes')}: {sum(1 for r in rows if r['count'])}"
        if msgs:
            text += "\n⚠ " + "\n⚠ ".join(msgs)
        self.summary_lbl.configure(text=text, text_color=("gray10", "gray90") if ok else ("#e65100", "#ffa726"))
        names = [r["gesture"] for r in rows]
        current = self.gesture_combo.get()
        self.gesture_combo.configure(values=names or [""])
        if current not in names:
            self.gesture_combo.set(names[0] if names else "")

    def _selected(self) -> str:
        sel = self.tree.selection()
        return sel[0] if sel else ""

    def _on_select(self, _event=None) -> None:
        g = self._selected()
        if g:
            self.gesture_combo.set(g)

    def _add_gesture(self) -> None:
        name = self.new_entry.get().strip()
        try:
            key = self.app.dataset_manager.add_gesture(name)
        except DatasetError as exc:
            messagebox.showerror(tr("Error"), str(exc))
            return
        self.new_entry.delete(0, "end")
        self.refresh()
        self.gesture_combo.set(key)

    def _add_vsl(self) -> None:
        from gui.spelling_view import vsl_alphabet_labels

        added, skipped = self.app.dataset_manager.add_gestures(vsl_alphabet_labels())
        self.refresh()
        messagebox.showinfo(tr("Information"), f"{tr('Added')}: {len(added)}\n"
                                               f"{len(skipped)} {tr('already existed')}")

    def _delete_gesture(self) -> None:
        g = self._selected()
        if not g:
            messagebox.showwarning(tr("Warning"), tr("Select a gesture first"))
            return
        if not messagebox.askyesno(tr("Confirm"), f"{tr('Delete all samples of gesture')} '{g}'?"):
            return
        try:
            n = self.app.dataset_manager.delete_gesture(g)
            logger.info("Deleted %s (%d samples)", g, n)
        except (DatasetError, OSError) as exc:
            messagebox.showerror(tr("Error"), str(exc))
        self.refresh()

    def _clear_dataset(self) -> None:
        if not messagebox.askyesno(tr("Confirm"), tr("Delete ALL dataset samples?")):
            return
        try:
            self.app.dataset_manager.clear()
        except OSError as exc:
            messagebox.showerror(tr("Error"), str(exc))
        self.refresh()

    def _view_dataset(self) -> None:
        try:
            df = self.app.dataset_manager.load()
        except DatasetError as exc:
            messagebox.showerror(tr("Error"), str(exc))
            return
        win = ctk.CTkToplevel(self)
        win.title(f"{tr('Dataset preview')} — {len(df)} rows (showing first 500)")
        win.geometry("1000x520")
        win.after(100, win.lift)
        cols = [("label", "label", 110)] + [(c, c, 75) for c in CSV_COLUMNS[:-1]]
        frame, tree = make_table(win, cols, height=20, horizontal=True)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        for _, row in df.head(500).iterrows():
            tree.insert("", "end", values=[row["label"]] + [f"{row[c]:.3f}" for c in CSV_COLUMNS[:-1]])

    # ---------------------------------------------------------- collection
    def _start_collect(self) -> None:
        label = self.gesture_combo.get().strip()
        if not label:
            messagebox.showwarning(tr("Warning"), tr("Select a gesture first"))
            return
        try:
            n = int(self.samples_entry.get())
            if not 10 <= n <= 5000:
                raise ValueError
        except ValueError:
            messagebox.showerror(tr("Error"), "Samples must be an integer between 10 and 5000.")
            return
        try:
            self.app.engine.start_collection(label, n)
        except ValueError as exc:
            messagebox.showerror(tr("Error"), str(exc))
            return
        self.progress.set(0)
        self.collect_lbl.configure(text=f"{tr('Get ready')}: {display_gesture(label)}")

    def _cancel_collect(self) -> None:
        self.app.engine.cancel_collection()
        self.refresh()

    def on_frame(self, result) -> None:
        self.camera_view.show_frame(result.frame)
        snap = self.app.engine.collector.snapshot()
        state = snap["state"]
        target = max(1, int(snap["target"] or 1))
        self.progress.set(min(1.0, int(snap["collected"]) / target))
        text = f"{tr(state.value)}"
        if snap["label"]:
            text += f" — {display_gesture(snap['label'])}: {snap['collected']}/{snap['target']}"
        if state == CollectorState.COUNTDOWN:
            text += f"  ({snap['countdown']:.1f}s)"
        if snap["message"]:
            text += f"\n{tr(str(snap['message']))}"
        self.collect_lbl.configure(text=text)

        if state != self._last_state:
            if state == CollectorState.DONE:
                self.refresh()
                messagebox.showinfo(tr("Information"),
                                    f"{tr('Collection finished')}: {snap['collected']} — {display_gesture(snap['label'])}")
            elif state in (CollectorState.CANCELLED, CollectorState.ERROR):
                self.refresh()
            self._last_state = state

    def on_camera_stopped(self) -> None:
        self.camera_view.show_placeholder()
        self.refresh()
