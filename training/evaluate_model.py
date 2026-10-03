"""
training/evaluate_model.py
==========================
File này dùng để làm gì?
    Đánh giá model và vẽ biểu đồ: Accuracy, Precision, Recall, F1-score,
    confusion matrix, báo cáo phân loại, biểu đồ so sánh thuật toán và
    phân bố dữ liệu.

Dữ liệu đi vào từ đâu?
    Nhãn thật (y_true) và nhãn dự đoán (y_pred) từ training/train_model.py,
    hoặc model đã lưu + dataset khi chạy độc lập.

Dữ liệu được xử lý như thế nào?
    - Accuracy  = số mẫu đoán đúng / tổng số mẫu.
    - Precision = TP / (TP + FP): trong các lần model nói "là X", bao nhiêu % đúng.
    - Recall    = TP / (TP + FN): trong các mẫu thực sự là X, model tìm ra bao nhiêu %.
    - F1        = trung bình điều hòa của Precision và Recall.
    Dùng trung bình "macro" (mỗi lớp có trọng số như nhau).
    Biểu đồ vẽ bằng matplotlib.figure.Figure (an toàn khi nhúng vào Tkinter).

Dữ liệu được truyền sang module nào?
    train_model.py, model_comparison.py, gui/training_view.py.

Kết quả trả về ở đâu?
    dict chỉ số, ma trận numpy, chuỗi báo cáo, hoặc Figure đã vẽ.
"""
from __future__ import annotations

import argparse
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from matplotlib.figure import Figure
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score,
)

from utils.constants import display_gesture


def compute_metrics(y_true: Sequence, y_pred: Sequence) -> Dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def evaluate(model, X_test: np.ndarray, y_test: np.ndarray,
             labels: Optional[List[str]] = None) -> Tuple[Dict[str, float], np.ndarray, str]:
    y_pred = model.predict(X_test)
    labels = labels or sorted(set(y_test) | set(y_pred))
    metrics = compute_metrics(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    report = classification_report(y_test, y_pred, labels=labels, zero_division=0, digits=4)
    return metrics, cm, report


# ------------------------------------------------------------------ plots
def plot_confusion_matrix(fig: Figure, cm: np.ndarray, labels: List[str], title: str = "Confusion Matrix") -> None:
    fig.clear()
    ax = fig.add_subplot(111)
    if cm is None or len(labels) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return
    cm = np.asarray(cm)
    im = ax.imshow(cm, cmap="Blues")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    names = [display_gesture(l, "en") for l in labels]
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    thresh = cm.max() / 2 if cm.size and cm.max() > 0 else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=8,
                    color="white" if cm[i, j] > thresh else "black")
    fig.tight_layout()


def plot_metrics_comparison(fig: Figure, results: List[Tuple[str, Dict[str, float]]]) -> None:
    fig.clear()
    ax = fig.add_subplot(111)
    if not results:
        ax.text(0.5, 0.5, "Run 'Compare All Models' to see this chart", ha="center", va="center")
        ax.axis("off")
        return
    keys = [("accuracy", "Accuracy"), ("precision", "Precision"), ("recall", "Recall"), ("f1", "F1-score")]
    x = np.arange(len(results))
    width = 0.2
    for k, (key, name) in enumerate(keys):
        values = [m.get(key, 0) * 100 for _, m in results]
        bars = ax.bar(x + (k - 1.5) * width, values, width, label=name)
        if key == "accuracy":
            for b, v in zip(bars, values):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.1f}", ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([n for n, _ in results])
    lo = min(m.get(k, 0) for _, m in results for k, _ in keys) * 100
    ax.set_ylim(max(0, lo - 10), 102)
    ax.set_ylabel("%")
    ax.set_title("Model comparison")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()


def plot_training_statistics(fig: Figure, class_counts: Dict[str, int],
                             history: List[Dict[str, object]]) -> None:
    fig.clear()
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    if class_counts:
        names = [display_gesture(k, "en") for k in class_counts]
        ax1.barh(names, list(class_counts.values()), color="#3b8ed0")
        ax1.set_title("Samples per gesture")
        ax1.tick_params(axis="y", labelsize=8)
    else:
        ax1.text(0.5, 0.5, "No data", ha="center", va="center")
        ax1.axis("off")
    runs = list(reversed(history))
    if runs:
        acc = [float(r.get("accuracy") or 0) * 100 for r in runs]
        ax2.plot(range(1, len(acc) + 1), acc, marker="o")
        ax2.set_title("Accuracy per training run")
        ax2.set_xlabel("Run")
        ax2.set_ylabel("%")
        ax2.grid(alpha=0.3)
    else:
        ax2.text(0.5, 0.5, "No training runs yet", ha="center", va="center")
        ax2.axis("off")
    fig.tight_layout()


# ------------------------------------------------------------- standalone
def main() -> None:
    """python -m training.evaluate_model : đánh giá model đã lưu trên toàn bộ dataset."""
    from config.config import MODEL_PATH, REPORT_DIR
    from dataset.dataset_manager import DatasetManager
    from recognition.feature_extractor import FEATURE_COLUMNS, LABEL_COLUMN
    from recognition.gesture_classifier import GestureClassifier

    parser = argparse.ArgumentParser(description="Evaluate the saved model on the dataset")
    parser.add_argument("--model", default=str(MODEL_PATH))
    args = parser.parse_args()

    clf = GestureClassifier(args.model)
    if not clf.load():
        raise SystemExit(f"Model not found: {args.model}. Train it first.")
    df = DatasetManager().load()
    if df.empty:
        raise SystemExit("Dataset is empty.")
    model = clf.info()
    metrics, cm, report = evaluate(clf._bundle["model"], df[FEATURE_COLUMNS].to_numpy(np.float32),
                                   df[LABEL_COLUMN].to_numpy(str), list(model["labels"]))
    print(report)
    print({k: round(v, 4) for k, v in metrics.items()})
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fig = Figure(figsize=(7, 6))
    plot_confusion_matrix(fig, cm, list(model["labels"]))
    out = REPORT_DIR / "confusion_matrix_full_dataset.png"
    fig.savefig(out, dpi=120)
    print("Saved", out)


if __name__ == "__main__":
    main()
