# 08 · Kiểm thử

Tài liệu này ghi lại **cách project đã được kiểm thử** và **cách bạn tự kiểm thử lại**. Có thể dùng trực tiếp cho chương "Kiểm thử và đánh giá" trong báo cáo.

## 1. Kiểm thử tự động có sẵn

```powershell
python -m tests.test_spelling
```

| Nhóm | Số ca | Nội dung |
|---|---|---|
| `test_tones` | 27 | Đặt dấu thanh đúng chính tả: hóa, múa, toán, quà, già, gì, người, việt, khuỷu… |
| `test_marks` | 11 | Dấu mũ / râu / trăng: â ê ô ơ ư ă, "uo" → "ươ", giữ nguyên dấu thanh khi thêm dấu phụ |
| `test_engine` | 7 | Luồng đánh vần "việt nam", chống lặp chữ, lặp chữ sau khi hạ tay, bỏ qua độ tin cậy thấp, cụm từ + lệnh `ctrl_delete`, hoàn tác, chữ Đ |
| `test_tts` | 5 | Tự chuyển backend khi lỗi, đọc trên thread nền, nhận diện giọng tiếng Việt |

Kết quả mong đợi: `ALL 50 CASES PASSED`.

## 2. Ma trận kiểm thử tương thích (đã thực hiện khi phát triển)

Mỗi phiên bản Python được cài trong một môi trường ảo riêng từ `requirements-lock.txt`, rồi chạy 4 bộ kiểm thử:

| Bộ kiểm thử | Nội dung |
|---|---|
| **Core** | Thu thập dữ liệu (collector), CSV, train 4 thuật toán, so sánh, lưu/nạp model, dự đoán, SQLite, xuất CSV, biểu đồ |
| **MediaPipe thật** | Model `gesture_recognizer.task` + ảnh 2 bàn tay → 21 landmark, Left/Right, gesture có sẵn, engine real-time, quay video, chụp ảnh, ghi lịch sử |
| **GUI** | Mở 8 màn hình, train từ giao diện, hiển thị frame, lưu cài đặt, màn hình Đánh vần (chữ → dấu → câu → đọc), phím tắt |
| **Spelling** | Bộ 50 ca ở mục 1 |

| Python | Core | MediaPipe | GUI | Spelling |
|---|---|---|---|---|
| 3.10 | ✓ | ✓ | ✓ | ✓ |
| 3.11 | ✓ | ✓ | ✓ | ✓ |
| 3.12 | ✓ | ✓ | ✓ | ✓ |
| 3.13 | ✓ | ✓ | ✓ | ✓ |
| 3.14 | ✓ | ✓ | ✓ | ✓ |
| 3.10 + **phiên bản thư viện thấp nhất** trong `requirements.txt` | ✓ | ✓ | ✓ | ✓ |

Ngoài ra, khả năng cài đặt trên **Windows x64** (có đủ wheel cho mọi thư viện) đã được xác minh cho Python 3.10–3.14 bằng `uv pip compile --python-platform x86_64-pc-windows-msvc --only-binary :all:`.

> Giới hạn: kiểm thử runtime được chạy trên Linux. Trên Windows mới xác minh khả năng cài đặt; chưa chạy với webcam thật và loa thật.

### Lỗi thật được phát hiện nhờ kiểm thử
| Phát hiện | Cách xử lý |
|---|---|
| Python 3.10 + Tcl/Tk 9: ComboBox lỗi `expected integer but got ""` | Bản vá tự động trong `utils/python_compatibility.py` |
| Matplotlib < 3.10 không nhúng được biểu đồ với Tk 9 | Nâng cận dưới `matplotlib>=3.10` |
| Pillow 10.0 không hiển thị được ảnh camera với Tk 9 | Nâng cận dưới `pillow>=10.1` |
| MediaPipe < 0.10.30 không có wheel cho Python 3.13+ | Quy tắc riêng trong `requirements.txt` và `dependency_checker` |
| Hai tay cùng nhãn "Left" → lịch sử ghi trùng 52 lần trong 2 giây | Định danh tay theo `Left_0`, `Left_1` |
| Nhãn gesture bị cắt khi tay chạm mép khung hình | Tự đặt nhãn vào trong khung |
| Gesture tên tiếng Việt bị đọc mất dấu ("cam on") | Dùng tên hiển thị người dùng đặt |

## 3. Kiểm thử thủ công với webcam

1. **Môi trường**: `python check_environment.py` → `Environment Status: READY`.
2. **7 ký hiệu có sẵn**: checklist 12 bước trong [04_KY_HIEU_CO_SAN.md](04_KY_HIEU_CO_SAN.md) mục 5.
3. **Dataset và train**: thu 3 gesture × 200 mẫu → *So sánh các mô hình* → accuracy và ma trận nhầm lẫn hiển thị đúng.
4. **Đánh vần**: bộ 13 từ trong [05_BANG_CHU_CAI_NNKH.md](05_BANG_CHU_CAI_NNKH.md) mục 5.
5. **Đọc thành tiếng**: bấm *Đọc* khi có mạng (gTTS) và khi tắt mạng (kỳ vọng: báo lỗi rõ ràng, chương trình không treo).
6. **Lịch sử / Thống kê**: số liệu khớp với những gì vừa làm; *Xuất CSV* mở được bằng Excel và hiển thị đúng tiếng Việt.

### Gợi ý đánh vần khách quan cho báo cáo
- Mời **người khác** (không tham gia thu dữ liệu) đánh vần 10–20 từ; ghi lại số chữ đúng / tổng số chữ.
- Đo **thời gian trung bình** để gõ một từ, với *Thời gian giữ* = 1,0 giây và 0,7 giây.
- Ghi lại các cặp chữ hay nhầm (từ ma trận nhầm lẫn) và cách bạn đã khắc phục.

---
[← Mục lục](../README.md#tài-liệu)
