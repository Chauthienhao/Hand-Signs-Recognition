# 04 · 7 ký hiệu có sẵn và cách chúng hoạt động (I Love You, Thumb Up…)

Ngay sau khi cài đặt, **chưa cần thu thập dữ liệu hay train**, chương trình đã nhận diện được 7 ký hiệu dưới đây. Đây là cách nhanh nhất để kiểm tra camera, MediaPipe và giao diện có chạy đúng hay không.

## 1. Cách làm từng ký hiệu

Cách làm chung: giơ tay trước camera, cách khoảng 40–80 cm, **lòng bàn tay hướng về camera** (trừ khi ghi khác), giữ yên khoảng 1 giây.

| # | Ký hiệu (key) | Tên hiển thị | Cách làm | Mẹo |
|---|---|---|---|---|
| 1 | `open_palm` | Bàn tay mở | Xòe cả 5 ngón, duỗi thẳng | Dễ nhất, nên thử đầu tiên |
| 2 | `closed_fist` | Nắm tay | Nắm chặt cả 5 ngón | Mặt trước nắm tay hướng camera |
| 3 | `pointing_up` | Chỉ lên | Ngón trỏ duỗi thẳng chỉ lên trời, các ngón còn lại nắm lại | Giữ ngón cái gập sát |
| 4 | `thumb_up` | Ngón cái lên | Nắm tay, ngón cái dựng thẳng lên | Nghiêng bàn tay để camera thấy rõ ngón cái |
| 5 | `thumb_down` | Ngón cái xuống | Nắm tay, ngón cái chỉ thẳng xuống | Như trên |
| 6 | `victory` | Chữ V | Ngón trỏ và ngón giữa duỗi, tách hình chữ V; các ngón khác nắm | Tách rộng hai ngón |
| 7 | `i_love_you` | I Love You | **Ngón cái, ngón trỏ, ngón út duỗi; ngón giữa và áp út gập xuống** | Xem mục 2 |

## 2. Ký hiệu "I Love You" là gì?

"I Love You" (thường viết tắt **ILY**) là một ký hiệu nổi tiếng có nguồn gốc từ **ngôn ngữ ký hiệu Mỹ (ASL)**. Nó ghép hình dạng của ba chữ cái ASL vào một bàn tay:

```
   I  = ngón út        →  "I"
   L  = ngón cái + trỏ →  "Love"
   Y  = ngón cái + út  →  "You"
   ────────────────────────────────
   ILY = ngón cái + trỏ + út duỗi, ngón giữa + áp út gập
```

Cách làm:
1. Nắm hờ bàn tay.
2. Duỗi **ngón cái** sang ngang, **ngón trỏ** lên trên, **ngón út** lên trên.
3. Giữ **ngón giữa và ngón áp út** gập vào lòng bàn tay.
4. Lòng bàn tay hướng về camera và giữ yên.

> Lưu ý: ILY là ký hiệu của ASL, đã trở nên phổ biến quốc tế. Đây **không** phải ký hiệu chính thức cho "tôi yêu bạn" trong ngôn ngữ ký hiệu Việt Nam. Chương trình hỗ trợ ký hiệu này vì nó nằm trong bộ gesture có sẵn của MediaPipe.

## 3. Bên trong chương trình nhận diện ký hiệu này như thế nào?

MediaPipe **Gesture Recognizer** (file `models\gesture_recognizer.task`) là model do Google huấn luyện sẵn. Bên trong nó gồm hai bước:

```
Frame camera
   │
   ▼
[1] Phát hiện bàn tay + 21 landmark   (hand landmark model)
   │        x, y, z của cổ tay, các khớp, đầu ngón tay
   ▼
[2] Bộ phân loại cử chỉ có sẵn         (canned gesture classifier)
   │        mạng nơ-ron nhỏ đọc 21 landmark → 8 lớp:
   │        None, Closed_Fist, Open_Palm, Pointing_Up,
   │        Thumb_Down, Thumb_Up, Victory, ILoveYou
   ▼
"ILoveYou", score 0.87
```

Sau đó, mã nguồn của project xử lý tiếp như sau:

| Bước | File | Việc làm |
|---|---|---|
| 1 | `detection/hand_detector.py` | Gửi frame vào MediaPipe, nhận kết quả thô |
| 2 | `detection/landmark_extractor.py` | Đổi `"ILoveYou"` thành key `i_love_you` (bảng `BUILTIN_GESTURE_MAP` trong `utils/constants.py`), đóng gói thành `HandInfo` |
| 3 | `recognition/predictor.py` | Chọn nguồn dự đoán (mục 4); **làm mượt** bằng cách bỏ phiếu trên 5 frame gần nhất; so với **ngưỡng tin cậy** (mặc định 60%) |
| 4 | `core/engine.py` | Vẽ khung xương + nhãn lên ảnh, lưu Lịch sử khi ký hiệu thay đổi |
| 5 | `gui/recognition_view.py` | Hiển thị "I LOVE YOU", độ tin cậy, tay trái/phải |

Ký hiệu bị báo *Không xác định* khi độ tin cậy trung bình thấp hơn ngưỡng. Muốn hệ thống "dễ tính" hơn, giảm *Ngưỡng tin cậy* trong Cài đặt (ví dụ xuống 0.50).

## 4. ⚠ Chế độ mô hình: vì sao sau khi train, I Love You "biến mất"?

Cài đặt **Chế độ mô hình** quyết định nguồn dự đoán:

| Chế độ | Nguồn dự đoán | Nhận diện được |
|---|---|---|
| `builtin` | Luôn dùng gesture có sẵn của MediaPipe | Chỉ 7 ký hiệu ở mục 1 |
| `ml` | Luôn dùng model bạn tự train (`hand_sign_model.pkl`) | Chỉ những gesture có trong dataset của bạn |
| `auto` (mặc định) | Có model tự train thì dùng `ml`, chưa có thì dùng `builtin` | Tùy trường hợp |

Vì vậy, nếu bạn **train một model chỉ gồm các chữ cái**, chế độ `auto` sẽ chuyển sang dùng model đó. Từ lúc này, I Love You và 6 ký hiệu có sẵn **không còn được nhận ra**, vì model của bạn không biết chúng. Hai cách giải quyết:

1. **Đổi chế độ khi cần**: đặt *Chế độ mô hình = builtin* để dùng 7 ký hiệu có sẵn, và `auto`/`ml` khi đánh vần.
2. **Gộp vào một model**: 7 gesture có sẵn đã nằm trong bảng ở màn hình *Dữ liệu*. Hãy thu thập dữ liệu cho chúng giống như các chữ cái rồi train lại; model mới sẽ biết cả hai nhóm. Cần lưu ý hình dạng dễ trùng: *Chữ V* trùng chữ cái **V**, *Bàn tay mở* gần giống chữ **B**.

## 5. Danh sách kiểm thử nhanh (checklist)

Đặt *Chế độ mô hình = builtin* (hoặc giữ `auto` khi chưa train), vào màn hình **Nhận diện** → **Bắt đầu**:

| # | Thao tác | Kết quả mong đợi | Đạt? |
|---|---|---|---|
| 1 | Không đưa tay vào | "Không có tay", Số bàn tay = 0 | ☐ |
| 2 | Bàn tay mở | BÀN TAY MỞ, chữ xanh, độ tin cậy > 60%, khung xương 21 điểm | ☐ |
| 3 | Nắm tay | NẮM TAY | ☐ |
| 4 | Chỉ lên | CHỈ LÊN | ☐ |
| 5 | Ngón cái lên / xuống | NGÓN CÁI LÊN / NGÓN CÁI XUỐNG | ☐ |
| 6 | Chữ V | CHỮ V | ☐ |
| 7 | I Love You | I LOVE YOU | ☐ |
| 8 | Hai tay cùng lúc (mở + nắm) | Số bàn tay = 2, mục *Chi tiết* có 2 dòng | ☐ |
| 9 | Đổi tay trái/phải | Mục *Bàn tay* đổi Trái/Phải đúng (khi bật *Lật ảnh*) | ☐ |
| 10 | Tư thế lạ (bắt chéo ngón) | KHÔNG XÁC ĐỊNH (chữ cam) | ☐ |
| 11 | Mở **Lịch sử** | Mỗi lần đổi ký hiệu có đúng 1 dòng mới | ☐ |
| 12 | **Chụp ảnh** / **Quay video** | File xuất hiện trong `captures\` / `recordings\` | ☐ |

## 6. Thử ngay chế độ Đánh vần với 7 ký hiệu này

Khi chưa train chữ cái, màn hình **Đánh vần** ghép 7 ký hiệu có sẵn thành **cụm từ DEMO** để bạn thử luồng ghép câu và đọc thành tiếng:

| Ký hiệu | Cụm từ demo |
|---|---|
| Bàn tay mở | xin chào |
| Ngón cái lên | tốt |
| Ngón cái xuống | không tốt |
| Chữ V | chiến thắng |
| Chỉ lên | chú ý |
| Nắm tay | dừng lại |
| I Love You | tôi yêu bạn |

Ví dụ: giữ *I Love You* 1 giây, rồi *Ngón cái lên* 1 giây, sau đó bấm **Đọc** → máy đọc "tôi yêu bạn tốt".

> Đây chỉ là bảng **minh họa** để kiểm thử phần mềm, **không phải** nghĩa trong ngôn ngữ ký hiệu Việt Nam. Bảng nằm trong biến `PHRASES` của `recognition/spelling.py` và có thể sửa tùy ý.

---
[← Mục lục](../README.md#tài-liệu)
