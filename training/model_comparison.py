"""
training/model_comparison.py
============================
File này dùng để làm gì?
    So sánh nhiều thuật toán (KNN, SVM, Random Forest, MLP) trên CÙNG một
    cách chia train/test để so sánh công bằng Accuracy, Precision, Recall,
    F1-score và thời gian train; có thể lưu model tốt nhất.

Dữ liệu đi vào từ đâu?
    Dataset CSV (qua DatasetManager), danh sách thuật toán, tỉ lệ test.

Dữ liệu được xử lý như thế nào?
    Đọc dữ liệu 1 lần -> chia 1 lần -> lần lượt train từng thuật toán bằng
    train_model.fit_and_evaluate -> chọn model có F1 (rồi Accuracy) cao nhất.

Dữ liệu được truyền sang module nào?
    gui/training_view.py (bảng + biểu đồ), file model nếu save_best=True.

Kết quả trả về ở đâu?
    ComparisonResult; khi chạy dòng lệnh in bảng và lưu ảnh reports/model_comparison.png.

Chạy độc lập:
    python -m training.model_comparison
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import pandas as pd

from config.config import MODEL_PATH, REPORT_DIR
from dataset.dataset_manager import DatasetError, DatasetManager
from training.train_model import (
    ALGORITHMS, TrainResult, fit_and_evaluate, load_dataset, save_model, split_data,
)
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ComparisonResult:
    results: List[TrainResult]
    best: TrainResult

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "Algorithm": r.algorithm_name,
            "Accuracy": round(r.metrics["accuracy"] * 100, 2),
            "Precision": round(r.metrics["precision"] * 100, 2),
            "Recall": round(r.metrics["recall"] * 100, 2),
            "F1-score": round(r.metrics["f1"] * 100, 2),
            "Train time (s)": round(r.train_time, 3),
        } for r in self.results])


def compare_models(algorithms: Optional[List[str]] = None, test_size: float = 0.2,
                   random_state: int = 42, dataset_manager: Optional[DatasetManager] = None,
                   save_best: bool = False, training_repo=None,
                   progress_cb: Optional[Callable[[str], None]] = None) -> ComparisonResult:
    algorithms = algorithms or list(ALGORITHMS)
    X, y, counts = load_dataset(dataset_manager)
    X_train, X_test, y_train, y_test = split_data(X, y, test_size, random_state)

    results: List[TrainResult] = []
    for i, algo in enumerate(algorithms, 1):
        if progress_cb:
            progress_cb(f"[{i}/{len(algorithms)}] Training {ALGORITHMS[algo]}...")
        res = fit_and_evaluate(algo, X_train, X_test, y_train, y_test, random_state)
        res.class_counts = counts
        results.append(res)
        if training_repo is not None:
            try:
                training_repo.add(res.algorithm_name, res.metrics, res.num_samples, len(res.labels),
                                  res.test_size, str(MODEL_PATH) if save_best else "")
            except Exception as exc:
                logger.error("Cannot save training history: %s", exc)

    best = max(results, key=lambda r: (r.metrics["f1"], r.metrics["accuracy"]))
    if save_best:
        save_model(best)
    logger.info("Best model: %s (F1=%.4f)", best.algorithm_name, best.metrics["f1"])
    return ComparisonResult(results, best)


def main() -> None:
    from matplotlib.figure import Figure
    from training.evaluate_model import plot_metrics_comparison

    try:
        comp = compare_models(progress_cb=print)
    except (DatasetError, ValueError) as exc:
        raise SystemExit(f"Comparison failed: {exc}")
    print(comp.to_dataframe().to_string(index=False))
    print("Best:", comp.best.algorithm_name)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fig = Figure(figsize=(8, 5))
    plot_metrics_comparison(fig, [(r.algorithm_name, r.metrics) for r in comp.results])
    out = REPORT_DIR / "model_comparison.png"
    fig.savefig(out, dpi=120)
    comp.to_dataframe().to_csv(REPORT_DIR / "model_comparison.csv", index=False)
    print("Saved", out)


if __name__ == "__main__":
    main()
