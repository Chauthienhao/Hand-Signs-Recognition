# 01 · Cài đặt môi trường

Tài liệu này hướng dẫn chuẩn bị Python, tạo môi trường ảo và cài thư viện. Các câu lệnh dùng hằng ngày được tổng hợp riêng trong [02_CAU_LENH.md](02_CAU_LENH.md).

## 1. Tóm tắt nhanh (Windows)

Mở PowerShell **trong thư mục `hand_sign_recognition`**, sau đó chạy:
```powershell
.\install.bat          # dùng Python mặc định của máy
.\run.bat              # chạy chương trình
```
Lưu ý: PowerShell bắt buộc có `.\` trước tên file. Trong CMD thì gõ `install.bat` là đủ, hoặc double-click file trong File Explorer.

**Khuyến nghị:** đặt project trong thư mục **không dấu**, ví dụ `E:\DoAnPython\hand_sign_recognition`.

## 2. Tương thích Python và thư viện

> Project được thiết kế để hỗ trợ **Python 3.10 – 3.14 (64-bit)** với các dependency trong `requirements.txt` / `requirements-lock.txt`.
> Các phiên bản này **đã được kiểm thử thực tế** (xem phương pháp bên dưới). Phiên bản Python mới hơn 3.14 sẽ được chương trình phát hiện và cảnh báo là *chưa xác minh*.

### 2.1. Bảng tương thích Python

| Python | Trạng thái | Ghi chú |
|---|---|---|
| ≤ 3.9 | **Not supported** | Đã hết vòng đời (EOL); chương trình báo lỗi và hướng dẫn dùng bản khác |
| 3.10 | Supported | Đã kiểm thử. Bản cũ nhất được hỗ trợ; tự áp dụng bản vá tkinter khi dùng Tcl/Tk 9 |
| 3.11 | Supported – **Recommended** | Đã kiểm thử |
| 3.12 | Supported – **Recommended** | Đã kiểm thử |
| 3.13 | Supported | Đã kiểm thử. Bắt buộc `mediapipe>=0.10.30` (bản cũ hơn không có wheel) |
| 3.14 | Supported | Đã kiểm thử. Bắt buộc `mediapipe>=0.10.30` |
| > 3.14 | Not verified | Có thể chạy nếu cài được thư viện; chạy `python check_environment.py` để kiểm tra |

Python 32-bit **không** được hỗ trợ (MediaPipe chỉ có bản 64-bit).

### 2.2. Khoảng phiên bản thư viện đã kiểm thử

| Thư viện | Khoảng trong `requirements.txt` | Phiên bản khóa (lock) | Lý do giới hạn |
|---|---|---|---|
| opencv-contrib-python | `>=4.8,<5` | 4.14.0.94 | OpenCV 5.x chưa đưa vào kiểm thử. Dùng gói *contrib* vì MediaPipe phụ thuộc gói này |
| mediapipe | `>=0.10.14,<1.1` (Python 3.13+: `>=0.10.30`) | 1.0.1 | 0.10.14–0.10.21 chỉ có wheel tới Python 3.12 |
| numpy | `>=1.24,<3` | 2.2.6 / 2.4.6 / 2.5.3 (theo Python) | NumPy 3 chưa phát hành / chưa kiểm thử |
| pandas | `>=2.0,<4` | 2.3.3 / 3.0.6 | |
| scikit-learn | `>=1.3,<2` | 1.7.2 / 1.9.1 | |
| matplotlib | `>=3.10,<4` | 3.10.9 / 3.11.2 | **< 3.10 lỗi `Failed to load Tcl_SetVar`** khi nhúng biểu đồ với Tcl/Tk 9 |
| customtkinter | `>=5.2,<7` | 6.0.0 | |
| joblib | `>=1.3,<2` | 1.6.0 | |
| pillow | `>=10.1,<13` | 12.3.0 | **10.0 lỗi hiển thị ảnh camera** với Tcl/Tk 9 |

### 2.3. Phương pháp kiểm thử (đã thực hiện)
1. **Windows x64:** dùng `uv pip compile --python-platform x86_64-pc-windows-msvc --only-binary :all:` cho từng Python 3.10–3.14 → xác nhận mọi thư viện đều có wheel (file cài sẵn) cho Windows, không cần trình biên dịch C++.
2. **Chạy thực tế** (Linux x86_64, tạo môi trường ảo riêng cho từng Python 3.10, 3.11, 3.12, 3.13, 3.14) với 3 bộ kiểm thử:
   - *Core:* thu thập dữ liệu, CSV, train KNN/SVM/Random Forest/MLP, so sánh, lưu/nạp model, dự đoán, SQLite, xuất CSV, biểu đồ.
   - *MediaPipe thật:* model `gesture_recognizer.task` + ảnh 2 bàn tay → 21 landmark, Left/Right, gesture, engine real-time, quay video, chụp ảnh, ghi lịch sử.
   - *GUI:* mở toàn bộ 7 màn hình, train từ giao diện, hiển thị frame, lưu cài đặt (EN và VI).
3. **Cận dưới:** cài đúng phiên bản thấp nhất của mọi thư viện (`--resolution lowest-direct`) trên Python 3.10 và chạy lại 3 bộ test. Nhờ bước này đã phát hiện và nâng cận dưới của Matplotlib (3.10) và Pillow (10.1).
4. **Tổ hợp đặc biệt:** MediaPipe 0.10.21 + NumPy 1.26 (Python 3.12) và MediaPipe 0.10.30 (Python 3.13).

> Giới hạn: kiểm thử runtime được chạy trên Linux; trên Windows đã xác minh khả năng cài đặt (wheel) nhưng chưa chạy với webcam thật. Nếu gặp lỗi, chạy `python check_environment.py` và xem `logs/app.log`.

Thư viện đọc thành tiếng `pyttsx3` (`>=2.90,<3`) và `gTTS` (`>=2.3,<3`) là **tùy chọn**. Chúng đã được kiểm thử trên cùng ma trận Python 3.10–3.14; nếu thiếu, chỉ riêng nút *Đọc* của chế độ Đánh vần không hoạt động.

## 3. Cài đặt

### 3.1. Kiểm tra Python đang có trên máy
Máy có thể có **nhiều phiên bản Python** cùng lúc. Kiểm tra:
```bat
python --version
py --list
```
`py --list` (Python Launcher) liệt kê mọi phiên bản đã cài, ví dụ `-V:3.14 *`, `-V:3.12`. Nếu chưa có bản phù hợp, tải **bản 64-bit** tại https://www.python.org/downloads/windows/ (tích *Add python.exe to PATH*). Không cần gỡ Python đang có.

### 3.2. Cách nhanh: dùng script
```bat
install.bat          :: dùng lệnh "python" mặc định
install.bat 3.12     :: chọn đúng Python 3.12 qua py launcher
run.bat              :: chạy chương trình
check_environment.bat
```
`install.bat` kiểm tra phiên bản Python → tạo `.venv` → cài `requirements-lock.txt` (nếu lỗi thì dùng `requirements.txt`) → chạy `check_environment.py`. Script **không** thay đổi Python hệ thống, PATH hay gói đã cài ngoài thư mục project.

### 3.3. Cách thủ công: virtual environment
Luôn cài vào **môi trường ảo riêng của project**, không cài vào Python hệ thống:
```bat
cd hand_sign_recognition
py -3.12 -m venv .venv            :: hoặc: python -m venv .venv  /  py -3.11 -m venv .venv
.venv\Scripts\activate
python --version                  :: phải đúng phiên bản vừa chọn
python -m pip install --upgrade pip
pip install -r requirements-lock.txt      :: môi trường đã kiểm thử (khuyến nghị)
::  hoặc: pip install -r requirements.txt  (cho phép bản vá mới hơn trong khoảng đã kiểm thử)
python check_environment.py
```
PowerShell báo lỗi *running scripts is disabled* khi activate? Chạy một lần: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, hoặc dùng trực tiếp `.venv\Scripts\python.exe main.py`.

**VS Code:** `Ctrl+Shift+P` → *Python: Select Interpreter* → chọn `.\.venv\Scripts\python.exe`. Nếu không, nút ▶ Run sẽ dùng Python hệ thống và báo thiếu thư viện.

### 3.4. Kiểm tra môi trường
```bat
python check_environment.py
```
Ví dụ kết quả:
```
HAND SIGN RECOGNITION
ENVIRONMENT CHECK
Python version   : 3.12.7
Architecture     : AMD64 (64-bit)
[✓] Python 3.12.7  (Tested. Recommended.)
[✓] OpenCV         4.14.0.94
[✓] MediaPipe      1.0.1
...
[✓] MediaPipe API  MediaPipe Tasks API available
Environment Status: READY
```
Khi có lỗi, mỗi dòng `[✗]` kèm **Reason**, **Recommended Python version** và lệnh **Fix**. Các module liên quan: `utils/python_compatibility.py` (phiên bản Python, bản vá tương thích) và `utils/dependency_checker.py` (thư viện, phiên bản, xung đột gói). `main.py` cũng tự chạy các kiểm tra này khi khởi động.

---
[← Mục lục](../README.md#tài-liệu)
