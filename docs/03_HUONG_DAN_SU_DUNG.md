# 03 · Hướng dẫn sử dụng các màn hình

Thanh menu bên trái gồm: **Tổng quan · Nhận diện · Đánh vần · Dữ liệu · Huấn luyện · Lịch sử · Thống kê · Cài đặt**, cùng các nút **Bật camera / Tắt camera / Thoát**. Thanh trạng thái phía dưới cho biết camera, FPS, mô hình đang dùng và chế độ mô hình.

## 1. Tổng quan (Dashboard)
Hiển thị trạng thái camera, mô hình nhận diện (*Có sẵn (MediaPipe)* hoặc tên thuật toán đã train), số mẫu dataset, tổng lượt nhận diện, kèm các nút đi nhanh tới các màn hình khác.

## 2. Nhận diện (Recognition)
1. Bấm **Bắt đầu**. Lần đầu chương trình tải model MediaPipe (~8 MB), thanh trạng thái hiện *Downloading…*.
2. Đưa 1–2 bàn tay vào khung hình, cách camera khoảng 40–80 cm, đủ sáng.
3. Bảng bên phải hiển thị:
   - **Ký hiệu**: chữ xanh lá nghĩa là đã chắc chắn; chữ cam *Không xác định* nghĩa là độ tin cậy thấp hơn ngưỡng.
   - **Độ tin cậy**, **Bàn tay** (Trái/Phải), **FPS**, **Số bàn tay**, **Nguồn** (`builtin` = gesture có sẵn của MediaPipe, `ml` = mô hình bạn tự train).
   - **Chi tiết**: kết quả của từng bàn tay khi có 2 tay.
4. **Chụp ảnh** lưu vào `captures\`; **Quay video** lưu vào `recordings\` (bấm lần nữa để dừng).

Mỗi khi ký hiệu của một bàn tay *thay đổi*, kết quả được lưu vào Lịch sử (không lưu lặp lại ở mỗi frame).

Nên thử gì đầu tiên? Xem [04_KY_HIEU_CO_SAN.md](04_KY_HIEU_CO_SAN.md): 7 ký hiệu nhận diện được ngay, chưa cần train.

## 3. Đánh vần (Spelling)
Làm ký hiệu chữ cái → hệ thống ghép thành từ/câu tiếng Việt có dấu → bấm **Đọc** để phát thành tiếng. Hướng dẫn đầy đủ ở [06_CHE_DO_DANH_VAN.md](06_CHE_DO_DANH_VAN.md).

## 4. Dữ liệu (Dataset)
- **Bảng gesture**: tên, tên hiển thị, số mẫu, trạng thái (*Trống* / *Chưa đủ* / *Sẵn sàng*; ngưỡng *Sẵn sàng* chỉnh ở Cài đặt).
- **Thêm gesture**: nhập tên rồi bấm *Thêm gesture*.
- **Thêm bảng chữ cái NNKH**: thêm một lần 23 chữ cái + 2 dấu tĩnh (`letter_a` … `letter_y`, `letter_dd` = Đ, `mark_mu` = ^, `mark_rau` = ’).
- **Thu thập dữ liệu**: chọn gesture, nhập số mẫu, bấm *Bắt đầu thu thập* → đếm ngược 3 giây → giữ tư thế tay, nhích nhẹ góc và khoảng cách.
- **Xem dữ liệu**, **Xóa gesture**, **Xóa toàn bộ dữ liệu**, **Làm mới**.

Chi tiết về dữ liệu và chuẩn hóa: [07_DATASET_VA_TRAINING.md](07_DATASET_VA_TRAINING.md).

## 5. Huấn luyện (Training)
Chọn thuật toán (KNN, SVM, Random Forest, Neural Network MLP) và tỉ lệ test, rồi bấm:
- **Huấn luyện**: train một thuật toán, lưu vào `models\hand_sign_model.pkl`, được dùng ngay cho nhận diện.
- **So sánh các mô hình**: train cả 4 thuật toán trên cùng một cách chia dữ liệu; tick *Lưu mô hình tốt nhất* để lưu model có F1 cao nhất.

Các tab kết quả: *Ma trận nhầm lẫn*, *So sánh độ chính xác*, *Thống kê huấn luyện*, *Báo cáo* (precision/recall theo từng lớp).

## 6. Lịch sử (History)
Tìm theo tên gesture, lọc theo ngày (`YYYY-MM-DD`) và theo tay; có thể xóa mục đã chọn, xóa tất cả, hoặc **Xuất CSV** (mở được bằng Excel, giữ đúng tiếng Việt).

## 7. Thống kê (Statistics)
Tổng lượt nhận diện, gesture xuất hiện nhiều nhất, độ tin cậy trung bình, accuracy của mô hình gần nhất và accuracy trung bình; kèm biểu đồ theo gesture, theo tay và theo ngày (14 ngày gần nhất).

## 8. Cài đặt (Settings)

| Nhóm | Thiết lập | Ghi chú |
|---|---|---|
| Camera | Chỉ số camera, *Quét camera*, độ phân giải, FPS mục tiêu, lật ảnh (gương) | Tắt camera trước khi quét |
| Nhận diện | Số bàn tay (1/2), ngưỡng phát hiện tay, **ngưỡng tin cậy**, cửa sổ làm mượt, **chế độ mô hình** | Chế độ mô hình: xem [04_KY_HIEU_CO_SAN.md](04_KY_HIEU_CO_SAN.md) mục 4 |
| Đánh vần | Thời gian giữ, tự cách sau, bộ đọc (`auto`/`pyttsx3`/`gtts`), ngôn ngữ đọc (`vi`/`en`) | |
| Hiển thị | Hiện landmark, khung bao, lưu lịch sử, số mẫu mỗi gesture, giao diện Dark/Light, ngôn ngữ EN/VI | Đổi ngôn ngữ cần khởi động lại |

Cài đặt được lưu vào `config\settings.json`.

---
[← Mục lục](../README.md#tài-liệu)
