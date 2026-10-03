"""
gui/training_view.py
====================
File này dùng để làm gì?
    Màn hình huấn luyện: chọn thuật toán (KNN, SVM, Random Forest, MLP), chọn
    tỉ lệ test, train một model hoặc so sánh tất cả; hiển thị Accuracy,
    Precision, Recall, F1-score, confusion matrix, biểu đồ so sánh và thống kê.

Dữ liệu đi vào từ đâu?
    DatasetManager (CSV), lựa chọn của người dùng, thông tin model đã lưu
    (GestureClassifier.info()), lịch sử train (TrainingHistoryRepository).

Dữ liệu được xử lý như thế nào?
    Việc train chạy trên thread nền (không làm đơ giao diện); GUI kiểm tra
    kết quả định kỳ bằng after(). Train xong -> engine.reload_model() để
    nhận diện real-time dùng ngay model mới.

Dữ liệu được truyền sang module nào?
    training/train_model.py, training/model_comparison.py, core.engine.

Kết quả trả về ở đâu?
    models/hand_sign_model.pkl, bảng training_history và các biểu đồ trên màn hình.
"""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

from dataset.dataset_manager import DatasetError
from gui.common import BasePage, ChartPanel, InfoCard, title_label
from training.evaluate_model import plot_confusion_matrix, plot_metrics_comparison, plot_training_statistics
from training.model_comparison import compare_models
from training.train_model import ALGORITHMS, train_model
from utils.constants import tr
from utils.helpers import format_percent
from utils.logger import get_logger

logger = get_logger(__name__)
NAME_TO_KEY = {v: k for k, v in ALGORITHMS.items()}


class TrainingView(BasePage):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        title_label(self, tr("Training Dashboard")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 6))

        # ------------------------------------------------------- điều khiển
        left = ctk.CTkScrollableFrame(self, width=300)
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))

        ctk.CTkLabel(left, text=tr("Algorithm")).pack(anchor="w", padx=10, pady=(10, 2))
        self.algo_menu = ctk.CTkOptionMenu(left, values=list(ALGORITHMS.values()))
        self.algo_menu.set(ALGORITHMS["rf"])
        self.algo_menu.pack(fill="x", padx=10)

        self.test_lbl = ctk.CTkLabel(left, text=f"{tr('Test size')}: 20%")
        self.test_lbl.pack(anchor="w", padx=10, pady=(12, 2))
        self.test_slider = ctk.CTkSlider(left, from_=0.1, to=0.4, number_of_steps=6,
                                         command=lambda v: self.test_lbl.configure(text=f"{tr('Test size')}: {v * 100:.0f}%"))
        self.test_slider.set(0.2)
        self.test_slider.pack(fill="x", padx=10)

        self.train_btn = ctk.CTkButton(left, text=tr("Train Model"), height=38, command=self._train)
        self.train_btn.pack(fill="x", padx=10, pady=(16, 4))
        self.compare_btn = ctk.CTkButton(left, text=tr("Compare All Models"), height=38,
                                         fg_color="#6a1b9a", hover_color="#4a148c", command=self._compare)
        self.compare_btn.pack(fill="x", padx=10, pady=4)
        self.save_best = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(left, text=tr("Save best model"), variable=self.save_best).pack(anchor="w", padx=10, pady=6)

        self.progress = ctk.CTkProgressBar(left, mode="indeterminate")
        self.progress.pack(fill="x", padx=10, pady=(8, 2))
        self.progress.set(0)
        self.status_lbl = ctk.CTkLabel(left, text="", wraplength=260, justify="left", anchor="w")
        self.status_lbl.pack(fill="x", padx=10, pady=(0, 8))

        self.cards = {}
        for key, title in (("model", "Model"), ("dataset", "Dataset"), ("accuracy", "Accuracy"),
                           ("precision", "Precision"), ("recall", "Recall"), ("f1", "F1-score")):
            card = InfoCard(left, tr(title), value_size=18)
            card.pack(fill="x", padx=10, pady=4)
            self.cards[key] = card

        # --------------------------------------------------------- biểu đồ
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        self.tab_names = {k: tr(k) for k in ("Confusion Matrix", "Accuracy Comparison", "Training Statistics", "Report")}
        for name in self.tab_names.values():
            self.tabs.add(name)
        self.cm_chart = ChartPanel(self.tabs.tab(self.tab_names["Confusion Matrix"]), figsize=(5, 4))
        self.cm_chart.pack(fill="both", expand=True)
        self.cmp_chart = ChartPanel(self.tabs.tab(self.tab_names["Accuracy Comparison"]), figsize=(5, 4))
        self.cmp_chart.pack(fill="both", expand=True)
        self.stats_chart = ChartPanel(self.tabs.tab(self.tab_names["Training Statistics"]), figsize=(5, 3.5))
        self.stats_chart.pack(fill="both", expand=True)
        self.report_box = ctk.CTkTextbox(self.tabs.tab(self.tab_names["Report"]),
                                         font=ctk.CTkFont(family="Consolas", size=12))
        self.report_box.pack(fill="both", expand=True)

        self._job: Optional[threading.Thread] = None
        self._job_result = None
        self._job_error: Optional[str] = None
        self._job_status = ""
        self._comparison = []
        self.cmp_chart.draw(lambda fig: plot_metrics_comparison(fig, []))

    # ----------------------------------------------------------------- show
    def on_show(self) -> None:
        self._refresh_info()

    def _refresh_info(self) -> None:
        try:
            counts = self.app.dataset_manager.counts()
        except DatasetError as exc:
            counts = {}
            self.status_lbl.configure(text=str(exc))
        self.cards["dataset"].set(f"{sum(counts.values()):,} samples / {len(counts)} classes")
        clf = self.app.classifier
        if clf.is_loaded:
            info = clf.info()
            m = info.get("metrics", {})
            self.cards["model"].set(f"{info.get('algorithm_name', info['algorithm'])}\n{info.get('trained_at', '')}")
            for k in ("accuracy", "precision", "recall", "f1"):
                self.cards[k].set(format_percent(m.get(k)))
            if info.get("confusion_matrix") is not None:
                self.cm_chart.draw(lambda fig: plot_confusion_matrix(fig, info["confusion_matrix"], info["labels"],
                                                                     f"Confusion Matrix — {info.get('algorithm_name')}"))
            self._set_report(info.get("report", ""))
        else:
            self.cards["model"].set(tr("Not trained"))
            for k in ("accuracy", "precision", "recall", "f1"):
                self.cards[k].set("--")
            self.cm_chart.draw(lambda fig: plot_confusion_matrix(fig, None, []))
        history = self._safe_history()
        self.stats_chart.draw(lambda fig: plot_training_statistics(fig, counts, history))

    def _safe_history(self):
        try:
            return self.app.training_repo.all(50)
        except Exception as exc:
            logger.error("Cannot read training history: %s", exc)
            return []

    def _set_report(self, text: str) -> None:
        self.report_box.configure(state="normal")
        self.report_box.delete("1.0", "end")
        self.report_box.insert("1.0", text or "")
        self.report_box.configure(state="disabled")

    # ----------------------------------------------------------- run jobs
    def _check_dataset(self) -> bool:
        ok, msgs = self.app.dataset_manager.validate()
        if not ok:
            messagebox.showerror(tr("Training failed"), "\n".join(msgs))
        return ok

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.train_btn.configure(state=state)
        self.compare_btn.configure(state=state)
        if busy:
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.set(0)

    def _run_job(self, target) -> None:
        if self._job and self._job.is_alive():
            return
        self._job_result, self._job_error = None, None

        def worker():
            try:
                self._job_result = target()
            except (DatasetError, ValueError) as exc:
                self._job_error = str(exc)
            except Exception as exc:
                logger.exception("Training job failed")
                self._job_error = f"Unexpected error: {exc}"

        self._set_busy(True)
        self.status_lbl.configure(text=tr("Training..."))
        self._job = threading.Thread(target=worker, daemon=True)
        self._job.start()
        self.after(200, self._poll_job)

    def _progress_cb(self, text: str) -> None:
        self._job_status = text  # chỉ ghi biến; GUI đọc trong _poll_job

    def _poll_job(self) -> None:
        if self._job and self._job.is_alive():
            if self._job_status:
                self.status_lbl.configure(text=self._job_status)
            self.after(200, self._poll_job)
            return
        self._set_busy(False)
        if self._job_error:
            self.status_lbl.configure(text=f"{tr('Training failed')}: {self._job_error}")
            messagebox.showerror(tr("Training failed"), self._job_error)
            return
        self._on_job_done(self._job_result)

    def _train(self) -> None:
        if not self._check_dataset():
            return
        algo = NAME_TO_KEY[self.algo_menu.get()]
        test_size = round(float(self.test_slider.get()), 2)
        self._job_kind = "train"
        self._run_job(lambda: train_model(algo, test_size, dataset_manager=self.app.dataset_manager,
                                          training_repo=self.app.training_repo, progress_cb=self._progress_cb))

    def _compare(self) -> None:
        if not self._check_dataset():
            return
        test_size = round(float(self.test_slider.get()), 2)
        save_best = bool(self.save_best.get())
        self._job_kind = "compare"
        self._run_job(lambda: compare_models(test_size=test_size, dataset_manager=self.app.dataset_manager,
                                             save_best=save_best, training_repo=self.app.training_repo,
                                             progress_cb=self._progress_cb))

    def _on_job_done(self, result) -> None:
        if self._job_kind == "compare":
            comp = result
            self._comparison = [(r.algorithm_name, r.metrics) for r in comp.results]
            self.cmp_chart.draw(lambda fig: plot_metrics_comparison(fig, self._comparison))
            best = comp.best
            table = comp.to_dataframe().to_string(index=False)
            self._show_result(best)
            self._set_report(f"{table}\n\n{tr('Best model')}: {best.algorithm_name}\n\n{best.report}")
            self.tabs.set(self.tab_names["Accuracy Comparison"])
            msg = f"{tr('Comparison finished')}. {tr('Best model')}: {best.algorithm_name} " \
                  f"(F1 {best.metrics['f1'] * 100:.2f}%)"
        else:
            self._show_result(result)
            self._set_report(result.report)
            self.tabs.set(self.tab_names["Confusion Matrix"])
            msg = f"{tr('Training finished')}: {result.algorithm_name} — Accuracy {result.metrics['accuracy'] * 100:.2f}%"

        self.app.engine.reload_model()
        self.status_lbl.configure(text=msg)
        history = self._safe_history()
        counts = result.best.class_counts if self._job_kind == "compare" else result.class_counts
        self.stats_chart.draw(lambda fig: plot_training_statistics(fig, counts, history))
        messagebox.showinfo(tr("Information"), msg)

    def _show_result(self, r) -> None:
        self.cards["model"].set(r.algorithm_name)
        self.cards["dataset"].set(f"{r.num_samples:,} samples ({r.num_train} train / {r.num_test} test)")
        for k in ("accuracy", "precision", "recall", "f1"):
            self.cards[k].set(format_percent(r.metrics[k]))
        self.cm_chart.draw(lambda fig: plot_confusion_matrix(fig, r.confusion_matrix, r.labels,
                                                             f"Confusion Matrix — {r.algorithm_name}"))
