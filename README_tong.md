# ✋ Hand Signs Recognition System
### Hệ thống nhận diện ký hiệu bàn tay bằng camera

Đồ án Python: nhận diện ký hiệu bàn tay theo thời gian thực bằng webcam, hỗ trợ **đánh vần bảng chữ cái ngôn ngữ ký hiệu Việt Nam** thành câu tiếng Việt có dấu và **đọc thành tiếng**. Hệ thống có giao diện đồ họa, dataset tự thu thập, huấn luyện Machine Learning, cơ sở dữ liệu lịch sử và thống kê.

## Giới thiệu

Ngôn ngữ ký hiệu là phương tiện giao tiếp chính của cộng đồng người Điếc, nhưng phần lớn người nghe không hiểu được. Hệ thống dùng camera thông thường (không cần găng tay cảm biến hay GPU) để:

1. Phát hiện bàn tay và trích xuất **21 điểm landmark** bằng MediaPipe.
2. Phân loại ký hiệu bằng **Machine Learning** (KNN, SVM, Random Forest, MLP).
3. Ghép các chữ cái thành **câu tiếng Việt có dấu** và **đọc thành tiếng**.

## Chức năng chính

| Màn hình | Chức năng |
|---|---|
| **Tổng quan** | Trạng thái camera, mô hình, dataset, số lượt nhận diện |
| **Nhận diện** | Camera real-time, 1–2 bàn tay; gesture, độ tin cậy, trái/phải, FPS; chụp ảnh, quay video |
| **Đánh vần** | Chữ cái → từ → câu tiếng Việt có dấu → 🔊 đọc thành tiếng |
| **Dữ liệu** | Thêm/xóa gesture, thêm nhanh bảng chữ cái NNKH, thu thập mẫu bằng webcam |
| **Huấn luyện** | 4 thuật toán, so sánh; Accuracy, Precision, Recall, F1; ma trận nhầm lẫn |
| **Lịch sử / Thống kê** | SQLite: tìm kiếm, lọc ngày, xuất CSV, biểu đồ |
| **Cài đặt** | Camera, ngưỡng, số tay, chế độ mô hình, đánh vần, đọc thành tiếng, Dark/Light, EN/VI |

Nhận diện được **ngay khi chưa train** 7 ký hiệu: Bàn tay mở, Nắm tay, Ngón cái lên/xuống, Chữ V, Chỉ lên, I Love You.

## Bắt đầu nhanh (Windows)

Yêu cầu: **Python 3.10 – 3.14, bản 64-bit**. Project được đặt trong thư mục **không dấu**, ví dụ `E:\DoAnPython\hand_sign_recognition`.

```powershell
cd E:\DoAnPython\hand_sign_recognition
.\install.bat        # tạo .venv + cài thư viện đã kiểm thử + kiểm tra môi trường
.\run.bat            # chạy chương trình
```
> Trong PowerShell bắt buộc gõ `.\` trước tên file. Trong CMD gõ `install.bat`, hoặc double-click file trong File Explorer.

Sau đó: **Nhận diện → Bắt đầu** → thử các ký hiệu trong [docs/04_KY_HIEU_CO_SAN.md](docs/04_KY_HIEU_CO_SAN.md).

## Tài liệu

Mỗi chủ đề nằm trong một file riêng ở thư mục [`docs/`](docs/):

| File | Nội dung | Tìm khi bạn muốn… |
|---|---|---|
| [01_CAI_DAT_MOI_TRUONG.md](docs/01_CAI_DAT_MOI_TRUONG.md) | Python, venv, bảng tương thích phiên bản, `install.bat` | cài đặt lần đầu, đổi phiên bản Python |
| [02_CAU_LENH.md](docs/02_CAU_LENH.md) | Mọi câu lệnh: PowerShell/CMD, chạy, kiểm tra, train CLI, dọn dẹp, phím tắt | tra nhanh một câu lệnh |
| [03_HUONG_DAN_SU_DUNG.md](docs/03_HUONG_DAN_SU_DUNG.md) | Hướng dẫn từng màn hình và từng thiết lập | biết nút nào làm gì |
| [04_KY_HIEU_CO_SAN.md](docs/04_KY_HIEU_CO_SAN.md) | 7 ký hiệu có sẵn, **I Love You hoạt động thế nào**, chế độ mô hình, checklist test | test chương trình lần đầu |
| [05_BANG_CHU_CAI_NNKH.md](docs/05_BANG_CHU_CAI_NNKH.md) | Bảng chữ cái ngôn ngữ ký hiệu Việt Nam, cách thu dữ liệu, bộ từ thử nghiệm | thêm ký hiệu cho người Điếc |
| [06_CHE_DO_DANH_VAN.md](docs/06_CHE_DO_DANH_VAN.md) | Đánh vần, dấu tiếng Việt, ký hiệu điều khiển, đọc thành tiếng | ghép câu và đọc |
| [07_DATASET_VA_TRAINING.md](docs/07_DATASET_VA_TRAINING.md) | Landmark, chuẩn hóa, định dạng CSV, thuật toán, chỉ số đánh giá | hiểu phần AI/ML, viết báo cáo |
| [08_KIEM_THU.md](docs/08_KIEM_THU.md) | Kiểm thử tự động, ma trận tương thích, lỗi đã phát hiện, kiểm thử thủ công | chương kiểm thử của báo cáo |
| [09_LOI_THUONG_GAP.md](docs/09_LOI_THUONG_GAP.md) | Lỗi cài đặt, PowerShell, camera, đánh vần, đọc thành tiếng | gặp lỗi |
| [10_KIEN_TRUC_HE_THONG.md](docs/10_KIEN_TRUC_HE_THONG.md) | Phân tích, Use Case, kiến trúc, luồng dữ liệu, ERD, class diagram, flowchart, cấu trúc thư mục | phần thiết kế của báo cáo |
| [11_HUONG_PHAT_TRIEN.md](docs/11_HUONG_PHAT_TRIEN.md) | Hướng mở rộng | phần kết luận / hướng phát triển |

## Công nghệ

Python 3.10–3.14 · OpenCV · MediaPipe Tasks (Gesture Recognizer) · NumPy · Pandas · Scikit-learn · Joblib · CustomTkinter · Pillow · Matplotlib · SQLite · pyttsx3 / gTTS

## Luồng xử lý

```
USER → GUI → CAMERA → OPENCV → MEDIAPIPE → 21 LANDMARKS → FEATURE EXTRACTION
     → ML CLASSIFIER → GESTURE → (Đánh vần: ghép dấu tiếng Việt → câu → 🔊) → GUI → SQLITE
```

Mỗi file `.py` mở đầu bằng docstring tiếng Việt giải thích: *file dùng để làm gì, dữ liệu vào từ đâu, xử lý thế nào, truyền sang module nào, kết quả trả về ở đâu.*
