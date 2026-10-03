# 09 · Lỗi thường gặp và cách khắc phục

Bước đầu tiên cho mọi lỗi cài đặt: `python check_environment.py`.

| Lỗi | Nguyên nhân / Cách khắc phục |
|---|---|
| `Missing libraries: ...` dù đã `pip install` | Cài vào một Python, chạy bằng Python khác. Kiểm tra `python -c "import sys; print(sys.executable)"` phải nằm trong `.venv`; trong VS Code chọn đúng interpreter ([01_CAI_DAT_MOI_TRUONG.md](01_CAI_DAT_MOI_TRUONG.md) mục 3.3). |
| `ERROR: Operation cancelled by user` | Quá trình cài bị ngắt (Ctrl+C / bấm vào terminal). Chạy lại lệnh cài và đợi đến `Successfully installed`. |
| `No matching distribution found for mediapipe` | Python không được hỗ trợ (quá cũ, 32-bit, hoặc quá mới so với MediaPipe hiện có) → tạo venv bằng `py -3.12 -m venv .venv`. |
| `[✗] Python ... older than the minimum` | Dùng Python 3.10–3.14 (khuyến nghị 3.12) qua venv. |
| `[!] Python ... not verified` | Python mới hơn bản đã kiểm thử. Có thể dùng tiếp nếu mọi thư viện `[✓]`; nếu lỗi, chuyển sang Python 3.12. |
| `[!] Conflict: Several OpenCV packages` | Gỡ gói thừa theo lệnh *Fix* in ra (chỉ trong `.venv`). |
| `ImportError: DLL load failed` (cv2/mediapipe) | Cài *Microsoft Visual C++ Redistributable 2015–2022 (x64)*. |
| `Failed to load Tcl_SetVar` | Matplotlib/Pillow quá cũ so với Tcl/Tk 9 → `pip install -r requirements.txt` (yêu cầu matplotlib ≥ 3.10, pillow ≥ 10.1). |
| `No module named 'tkinter'` | Cài lại Python, tích chọn *tcl/tk and IDLE*. |
| `Cannot open camera 0` | Webcam đang được Zoom/Teams dùng; kiểm tra *Windows Settings → Privacy → Camera*; thử camera khác ở *Settings → Scan cameras*. |
| `Cannot download the MediaPipe model` | Không có Internet → tải file `.task` thủ công ([02_CAU_LENH.md](02_CAU_LENH.md) mục 5). |
| Lỗi với đường dẫn có dấu tiếng Việt | Chuyển project sang thư mục không dấu, ví dụ `E:\DoAnPython\hand_sign_recognition`, xóa `.venv` và cài lại. |
| Training báo thiếu mẫu | Mỗi gesture cần ≥ 10 mẫu (khuyến nghị ≥ 200) và ít nhất 2 gesture. |
| Nhận diện hay nhầm | Thu thêm dữ liệu đa dạng; tăng *Confidence threshold*; xem confusion matrix. |
| FPS thấp | Giảm độ phân giải xuống 640x480, *Number of hands* = 1. |
| Model báo không hợp lệ | Xóa `models/hand_sign_model.pkl` và train lại. |
| Muốn xem chi tiết lỗi | Mở `logs/app.log`. |

## Lỗi riêng của PowerShell

| Lỗi | Cách khắc phục |
|---|---|
| `install.bat : The term 'install.bat' is not recognized...` | PowerShell không tự chạy file trong thư mục hiện tại → gõ `.\install.bat` (có `.\`), và kiểm tra đang đứng **trong** thư mục `hand_sign_recognition` (`dir` phải thấy file `install.bat`). |
| `...running scripts is disabled on this system` khi `activate` | Chạy một lần: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, hoặc gọi thẳng `.\.venv\Scripts\python.exe main.py`. |

## Lỗi của chế độ Đánh vần / đọc thành tiếng

| Lỗi | Cách khắc phục |
|---|---|
| Màn hình Đánh vần không ra chữ, chỉ ra tên gesture | Chưa train các chữ cái. Xem [05_BANG_CHU_CAI_NNKH.md](05_BANG_CHU_CAI_NNKH.md). |
| Chữ bị lặp hoặc gõ quá nhanh | Tăng *Thời gian giữ* (thanh trượt trên màn hình Đánh vần). |
| Không gõ được 2 chữ giống nhau liên tiếp ("oo") | Đây là cơ chế chống lặp: **hạ tay ra khỏi khung hình** rồi giơ lại. |
| Tự chèn khoảng trắng ngoài ý muốn | Tăng hoặc tắt *Tự cách sau* (kéo về 0). |
| `Speech error: No Vietnamese voice installed` + `gTTS ... check the Internet` | Windows không có giọng tiếng Việt cho SAPI5 **và** không có mạng. Kết nối Internet (gTTS), hoặc xem [06_CHE_DO_DANH_VAN.md](06_CHE_DO_DANH_VAN.md) mục 5. |
| Đọc bằng giọng tiếng Anh | Đặt *Ngôn ngữ đọc* = `vi` trong Cài đặt, và *Bộ đọc* = `auto` hoặc `gtts`. |
| Sau khi train chữ cái, các gesture có sẵn (I Love You...) không còn nhận ra | Xem [04_KY_HIEU_CO_SAN.md](04_KY_HIEU_CO_SAN.md) mục 4. |


---
[← Mục lục](../README.md#tài-liệu)
