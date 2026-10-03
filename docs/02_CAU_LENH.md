# 02 · Các câu lệnh

Tổng hợp mọi câu lệnh dùng trong project. Trừ khi ghi chú khác, các lệnh đều chạy **trong thư mục `hand_sign_recognition`**.

## 1. PowerShell và CMD khác nhau thế nào?

Terminal mặc định của VS Code trên Windows là **PowerShell** (dấu nhắc bắt đầu bằng `PS`).

| Việc cần làm | PowerShell | CMD (Command Prompt) |
|---|---|---|
| Chạy file `.bat` trong thư mục hiện tại | `.\install.bat` | `install.bat` |
| Kích hoạt môi trường ảo | `.\.venv\Scripts\Activate.ps1` (hoặc `.\.venv\Scripts\activate`) | `.venv\Scripts\activate` |
| Xóa thư mục `.venv` | `Remove-Item -Recurse -Force .venv` | `rmdir /s /q .venv` |
| Xem file trong thư mục | `dir` hoặc `ls` | `dir` |

> PowerShell **không** tự chạy file nằm trong thư mục hiện tại vì lý do bảo mật, nên bắt buộc phải có `.\` phía trước tên file.

## 2. Di chuyển đến thư mục project
```powershell
cd "E:\DoAnPython\hand_sign_recognition"   # nên dùng đường dẫn không dấu
dir                                          # phải thấy main.py, install.bat, run.bat
```

## 3. Script tiện ích (.bat)

| Lệnh (PowerShell) | Tác dụng |
|---|---|
| `.\install.bat` | Kiểm tra Python → tạo `.venv` → cài thư viện đã kiểm thử → kiểm tra môi trường |
| `.\install.bat 3.12` | Giống trên nhưng dùng Python 3.12 (qua Python Launcher `py -3.12`) |
| `.\run.bat` | Chạy chương trình bằng Python trong `.venv` |
| `.\check_environment.bat` | In báo cáo môi trường (READY / NOT READY) |

## 4. Python và môi trường ảo

```powershell
python --version                      # phiên bản Python mặc định
py --list                             # tất cả phiên bản Python trên máy
py -3.12 -m venv .venv                # tạo môi trường ảo bằng Python 3.12
.\.venv\Scripts\activate              # kích hoạt (dấu nhắc hiện "(.venv)")
deactivate                            # thoát môi trường ảo
python -c "import sys; print(sys.executable)"   # Python đang dùng thực sự nằm ở đâu
```

## 5. Cài đặt / sửa thư viện (trong `.venv`)

```powershell
python -m pip install --upgrade pip
pip install -r requirements-lock.txt     # đúng phiên bản đã kiểm thử (khuyến nghị)
pip install -r requirements.txt          # cho phép bản vá mới hơn trong khoảng đã kiểm thử
pip list                                 # liệt kê thư viện đã cài
pip install --force-reinstall "mediapipe>=0.10.14,<1.1"   # cài lại một thư viện bị lỗi
```

Tải trước model MediaPipe (~8 MB, cần Internet):
```powershell
python -m detection.hand_detector
```
Nếu không có mạng, tải thủ công file dưới đây rồi đặt vào thư mục `models\`:
```
https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task
```

## 6. Kiểm tra môi trường

```powershell
python check_environment.py              # báo cáo đầy đủ: Python, thư viện, xung đột, MediaPipe API
python utils\python_compatibility.py     # chỉ kiểm tra phiên bản Python
```

## 7. Chạy chương trình
```powershell
python main.py                           # khi đã activate .venv
.\.venv\Scripts\python.exe main.py       # không cần activate
.\run.bat
```

## 8. Huấn luyện và đánh giá bằng dòng lệnh

```powershell
python -m training.train_model --algo rf --test-size 0.2   # knn | svm | rf | mlp
python -m training.model_comparison                        # so sánh 4 thuật toán -> reports\model_comparison.png/.csv
python -m training.evaluate_model                          # đánh giá model đã lưu trên toàn bộ dataset
```

## 9. Kiểm thử tự động
```powershell
python -m tests.test_spelling            # bộ ghép dấu tiếng Việt + bộ máy đánh vần + logic TTS
```

## 10. Dọn dẹp / đặt lại

| Muốn | Lệnh (PowerShell) |
|---|---|
| Cài lại môi trường từ đầu | `Remove-Item -Recurse -Force .venv` rồi `.\install.bat` |
| Xóa model đã train | `Remove-Item models\hand_sign_model.pkl` |
| Xóa toàn bộ dataset | Màn hình **Dữ liệu → Xóa toàn bộ dữ liệu** (hoặc xóa `data\hand_signs.csv`) |
| Xóa lịch sử nhận diện | Màn hình **Lịch sử → Xóa tất cả** |
| Khôi phục cài đặt mặc định | **Cài đặt → Khôi phục mặc định** (hoặc xóa `config\settings.json`) |
| Xem log lỗi | Mở `logs\app.log` |

## 11. Phím tắt trong chương trình (màn hình Đánh vần)

| Phím | Tác dụng |
|---|---|
| `Enter` | Đọc câu thành tiếng (khi không đang gõ trong ô văn bản) |
| `Ctrl+Space` | Thêm khoảng trắng |
| `Ctrl+Backspace` | Xóa lùi 1 ký tự |
| `Ctrl+Z` | Hoàn tác |
| `Ctrl+1` … `Ctrl+5` | Dấu sắc, huyền, hỏi, ngã, nặng |
| `Ctrl+0` | Bỏ dấu thanh |
| `Ctrl+6` / `Ctrl+7` / `Ctrl+8` | Dấu mũ `^` / móc–râu `’` / trăng `˘` |

---
[← Mục lục](../README.md#tài-liệu)
