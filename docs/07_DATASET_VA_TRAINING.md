# 07 · Dataset, đặc trưng và huấn luyện mô hình

## 1. Landmark là gì?
MediaPipe trả về **21 điểm mốc** (landmark) trên mỗi bàn tay: cổ tay, các khớp và đầu ngón tay. Mỗi điểm có `(x, y, z)`: `x, y` chuẩn hóa theo kích thước ảnh trong khoảng [0, 1], còn `z` là độ sâu tương đối so với cổ tay.

```
          8   12  16  20        0     : cổ tay (WRIST)
          |   |   |   |         1–4   : ngón cái  (4 = đầu ngón)
          7   11  15  19        5–8   : ngón trỏ  (8 = đầu ngón)
          |   |   |   |         9–12  : ngón giữa
   4      6   10  14  18        13–16 : ngón áp út
    \     |   |   |   |         17–20 : ngón út
     3    5---9---13--17
      \    \          /
       2    \        /
        \    \      /
         1----0----
```

## 2. Vì sao dùng landmark thay vì ảnh RGB?

| | Ảnh RGB | Landmark |
|---|---|---|
| Kích thước mỗi mẫu | 640×480×3 ≈ 921.600 số | **63 số** |
| Ảnh hưởng của nền, ánh sáng, màu da | Lớn | Gần như không (MediaPipe đã lọc bỏ) |
| Dữ liệu cần | Hàng chục nghìn ảnh / lớp | **Vài trăm mẫu / lớp** |
| Mô hình | CNN, thường cần GPU | KNN/SVM/RF/MLP, chạy trên CPU, train vài giây |

## 3. Chuẩn hóa tọa độ (`recognition/feature_extractor.py`)
1. **Bù tỉ lệ khung hình**: `x, z *= width/height`, để 1 đơn vị trục x bằng 1 đơn vị trục y.
2. **Tịnh tiến**: `P_i = P_i − P_0`, lấy cổ tay làm gốc → không phụ thuộc vị trí tay trong khung hình.
3. **Lật tay trái**: nếu là tay trái thì `x = −x` → một mô hình dùng được cho cả hai tay.
4. **Co giãn**: chia cho `max ‖P_i‖` → không phụ thuộc kích thước tay hay khoảng cách tới camera.

**Vector đặc trưng:** làm phẳng thành `[x0, y0, z0, …, x20, y20, z20]`, gồm 63 chiều. Cùng một hàm này được dùng khi thu dữ liệu, khi train và khi nhận diện, nên dữ liệu luôn nhất quán.

## 4. Định dạng dataset
File `data\hand_signs.csv`, mỗi dòng là một mẫu **đã chuẩn hóa**:
```
x0,y0,z0,x1,y1,z1,...,x20,y20,z20,label
0.000000,0.000000,0.000000,0.563120,-0.610233,...,letter_a
```
Danh sách gesture (kể cả gesture chưa có mẫu) được lưu trong bảng `gestures` của `database\hand_signs.db`.

### Quy ước đặt tên nhãn
| Tiền tố | Ý nghĩa | Ví dụ |
|---|---|---|
| `letter_` | Chữ cái (chế độ Đánh vần) | `letter_a`, `letter_dd` (= Đ) |
| `mark_` | Dấu phụ / dấu thanh | `mark_mu`, `mark_rau`, `mark_sac` |
| `ctrl_` | Lệnh điều khiển | `ctrl_space`, `ctrl_speak` |
| (khác) | Gesture / từ thông thường | `thumb_up`, `i_love_you`, `cam_on` |

Tên tiếng Việt khi *Thêm gesture* được tự chuyển thành không dấu: "Cảm ơn" → `cam_on`.

## 5. Thu thập dữ liệu tốt
- **300–500 mẫu** mỗi gesture; tối thiểu 10 mẫu mới train được.
- Trong lúc thu: **nhích nhẹ** góc xoay, khoảng cách và vị trí tay trong khung hình.
- Thu từ **nhiều người** và trong nhiều điều kiện ánh sáng.
- Dùng **cùng một tay thuận** cho ngôn ngữ ký hiệu.
- Cân bằng số mẫu giữa các lớp.

## 6. Huấn luyện
Pipeline: `StandardScaler` (chuẩn hóa thang đo) + bộ phân loại, chia train/test có **stratify** (giữ nguyên tỉ lệ các lớp).

| Thuật toán | Cấu hình | Đặc điểm |
|---|---|---|
| KNN | k = 5, weights = distance | Đơn giản, train tức thì |
| SVM | RBF, C = 10, probability = True | Thường chính xác nhất với dữ liệu ít chiều |
| Random Forest | 200 cây | Ổn định, ít cần tinh chỉnh |
| Neural Network (MLP) | 128–64 nơ-ron | Mạnh khi có nhiều lớp và nhiều dữ liệu |

Model được lưu thành một "bundle" `models\hand_sign_model.pkl` (joblib), gồm: pipeline, danh sách nhãn, chỉ số đánh giá, ma trận nhầm lẫn và báo cáo. Lệnh dòng lệnh tương ứng xem ở [02_CAU_LENH.md](02_CAU_LENH.md) mục 8.

## 7. Đánh giá
Các chỉ số là trung bình **macro**, tức mỗi lớp có trọng số như nhau:
- **Accuracy** = số mẫu đúng / tổng số mẫu.
- **Precision** = TP / (TP + FP): khi model nói "là X", bao nhiêu phần trăm là đúng.
- **Recall** = TP / (TP + FN): trong các mẫu thật sự là X, model tìm ra bao nhiêu phần trăm.
- **F1** = 2·P·R / (P + R).
- **Ma trận nhầm lẫn**: hàng là nhãn thật, cột là nhãn dự đoán; các ô ngoài đường chéo là các cặp hay nhầm.

> Accuracy 100% trên tập test **không** có nghĩa là hệ thống hoàn hảo, nếu dữ liệu train và test được thu từ cùng một người trong cùng một buổi. Khi viết báo cáo, nên test thêm với **người khác** hoặc **buổi khác** để đánh giá khả năng tổng quát.

---
[← Mục lục](../README.md#tài-liệu)
