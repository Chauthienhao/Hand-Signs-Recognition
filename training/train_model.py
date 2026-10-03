"""
training/train_model.py
=======================
File này dùng để làm gì?
    Huấn luyện model phân loại gesture từ dataset CSV:
    đọc dữ liệu -> tiền xử lý -> chia train/test -> train -> đánh giá
    -> lưu model (models/hand_sign_model.pkl) -> ghi lịch sử train vào SQLite.

Dữ liệu đi vào từ đâu?
    data/hand_signs.csv (qua DatasetManager); thuật toán và tỉ lệ test do
    người dùng chọn ở gui/training_view.py hoặc tham số dòng lệnh.

Dữ liệu được xử lý như thế nào?
    - Kiểm tra dataset: ≥ 2 gesture, mỗi gesture ≥ 10 mẫu.
    - train_test_split có stratify (giữ tỉ lệ các lớp giống nhau ở train/test).
    - Pipeline scikit-learn: StandardScaler (chuẩn hóa thang đo) + classifier.
      Thuật toán: KNN, SVM (RBF), Random Forest, Neural Network (MLP).
    - Đánh giá trên tập test bằng training/evaluate_model.py.

Dữ liệu được truyền sang module nào?
    File model -> recognition/gesture_classifier.py (nhận diện real-time).
    Kết quả -> gui/training_view.py; lịch sử -> database/history.py.

Kết quả trả về ở đâu?
    Đối tượng TrainResult và file .pkl.

Chạy độc lập:
    python -m training.train_model --algo rf --test-size 0.2
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from config.config import MODEL_PATH
from dataset.dataset_manager import MIN_SAMPLES_FOR_TRAINING, DatasetError, DatasetManager
from recognition.feature_extractor import FEATURE_COLUMNS, LABEL_COLUMN
from training.evaluate_model import evaluate
from utils.constants import FEATURE_DIM
from utils.helpers import now_str
from utils.logger import get_logger

logger = get_logger(__name__)

ALGORITHMS: Dict[str, str] = {
    "knn": "KNN",
    "svm": "SVM",
    "rf": "Random Forest",
    "mlp": "Neural Network (MLP)",
}


@dataclass
class TrainResult:
    algorithm: str
    algorithm_name: str
    model: object
    metrics: Dict[str, float]
    confusion_matrix: np.ndarray
    labels: List[str]
    report: str
    num_samples: int
    num_train: int
    num_test: int
    test_size: float
    train_time: float
    class_counts: Dict[str, int] = field(default_factory=dict)
    saved_path: Optional[str] = None


def build_model(algorithm: str, random_state: int = 42) -> Pipeline:
    if algorithm == "knn":
        clf = KNeighborsClassifier(n_neighbors=5, weights="distance")
    elif algorithm == "svm":
        clf = SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=random_state)
    elif algorithm == "rf":
        clf = RandomForestClassifier(n_estimators=200, random_state=random_state, n_jobs=-1)
    elif algorithm == "mlp":
        # early_stopping=False: tránh lỗi của một số bản scikit-learn khi nhãn là chuỗi
        clf = MLPClassifier(hidden_layer_sizes=(128, 64), alpha=1e-4, max_iter=1000,
                            random_state=random_state)
    else:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Choose from: {', '.join(ALGORITHMS)}")
    return Pipeline([("scaler", StandardScaler()), ("clf", clf)])


def load_dataset(dataset_manager: Optional[DatasetManager] = None,
                 min_per_class: int = MIN_SAMPLES_FOR_TRAINING) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    dm = dataset_manager or DatasetManager()
    ok, msgs = dm.validate(min_per_class)
    if not ok:
        raise DatasetError("\n".join(msgs))
    df = dm.load()
    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[LABEL_COLUMN].to_numpy(dtype=str)
    counts = {str(k): int(v) for k, v in df[LABEL_COLUMN].value_counts().sort_index().items()}
    logger.info("Loaded dataset: %d samples, %d classes", len(y), len(counts))
    return X, y, counts


def split_data(X: np.ndarray, y: np.ndarray, test_size: float = 0.2, random_state: int = 42):
    if not 0.05 <= test_size <= 0.5:
        raise ValueError("Test size must be between 0.05 and 0.5")
    try:
        return train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)
    except ValueError as exc:
        raise DatasetError(f"Cannot split dataset: {exc}. Collect more samples per gesture.") from exc


def fit_and_evaluate(algorithm: str, X_train, X_test, y_train, y_test,
                     random_state: int = 42) -> TrainResult:
    model = build_model(algorithm, random_state)
    t0 = time.perf_counter()
    model.fit(X_train, y_train)
    train_time = time.perf_counter() - t0
    labels = sorted({str(v) for v in y_train} | {str(v) for v in y_test})
    metrics, cm, report = evaluate(model, X_test, y_test, labels)
    logger.info("%s: acc=%.4f f1=%.4f (%.2fs)", ALGORITHMS[algorithm], metrics["accuracy"], metrics["f1"], train_time)
    return TrainResult(
        algorithm=algorithm, algorithm_name=ALGORITHMS[algorithm], model=model, metrics=metrics,
        confusion_matrix=cm, labels=labels, report=report,
        num_samples=len(y_train) + len(y_test), num_train=len(y_train), num_test=len(y_test),
        test_size=len(y_test) / (len(y_train) + len(y_test)), train_time=train_time,
    )


def save_model(result: TrainResult, path: Path = MODEL_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": result.model,
        "labels": result.labels,
        "algorithm": result.algorithm,
        "algorithm_name": result.algorithm_name,
        "feature_dim": FEATURE_DIM,
        "metrics": result.metrics,
        "confusion_matrix": result.confusion_matrix,
        "report": result.report,
        "num_samples": result.num_samples,
        "class_counts": result.class_counts,
        "test_size": result.test_size,
        "trained_at": now_str(),
    }
    tmp = path.with_suffix(".tmp")
    joblib.dump(bundle, tmp)
    tmp.replace(path)
    result.saved_path = str(path)
    logger.info("Model saved to %s", path)
    return path


def train_model(algorithm: str = "rf", test_size: float = 0.2, random_state: int = 42,
                dataset_manager: Optional[DatasetManager] = None, save: bool = True,
                model_path: Path = MODEL_PATH, training_repo=None,
                progress_cb: Optional[Callable[[str], None]] = None) -> TrainResult:
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm '{algorithm}'")
    if progress_cb:
        progress_cb("Loading dataset...")
    X, y, counts = load_dataset(dataset_manager)
    X_train, X_test, y_train, y_test = split_data(X, y, test_size, random_state)
    if progress_cb:
        progress_cb(f"Training {ALGORITHMS[algorithm]}...")
    result = fit_and_evaluate(algorithm, X_train, X_test, y_train, y_test, random_state)
    result.class_counts = counts
    if save:
        save_model(result, model_path)
        if training_repo is not None:
            try:
                training_repo.add(result.algorithm_name, result.metrics, result.num_samples,
                                  len(result.labels), result.test_size, str(model_path))
            except Exception as exc:
                logger.error("Cannot save training history: %s", exc)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the hand sign classifier")
    parser.add_argument("--algo", choices=list(ALGORITHMS), default="rf")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    from database.database import Database, GestureRepository
    from database.history import TrainingHistoryRepository

    db = Database()
    dm = DatasetManager(gesture_repo=GestureRepository(db))
    try:
        result = train_model(args.algo, args.test_size, dataset_manager=dm,
                             training_repo=TrainingHistoryRepository(db), progress_cb=print)
    except (DatasetError, ValueError) as exc:
        raise SystemExit(f"Training failed: {exc}")
    print(result.report)
    for k, v in result.metrics.items():
        print(f"{k:>10}: {v * 100:.2f}%")
    print("Model saved to", result.saved_path)


if __name__ == "__main__":
    main()
