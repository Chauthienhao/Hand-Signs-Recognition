# 05 · Bảng chữ cái ngón tay – Ngôn ngữ ký hiệu Việt Nam (NNKH)

Tài liệu này giúp bạn chuẩn bị dữ liệu chữ cái cho chế độ **Đánh vần**: những ký hiệu nào làm được bằng camera, cách làm chúng, và cách kiểm thử.

## 1. Thông tin đã kiểm chứng

Theo nghiên cứu của Đại học Bách khoa Hà Nội (Tran Anh Vu và cộng sự, *Vietnamese Sign Language Alphabet Recognition Using Deep Learning and Mediapipe Methods*, JST: Smart Systems and Devices, tập 35, số 1, 2025). Nghiên cứu này dựa trên **quy định chuẩn quốc gia về ngôn ngữ ký hiệu do Bộ Giáo dục và Đào tạo ban hành năm 2020**:

| Nhóm | Ký hiệu | Đặc điểm | Trong chương trình |
|---|---|---|---|
| Chữ cái tĩnh | **23 chữ**: A B C D Đ E G H I K L M N O P Q R S T U V X Y | Một tư thế bàn tay | Nhận diện bằng camera |
| Dấu phụ tĩnh | **mũ `^`**, **móc/râu `’`** | Một tư thế bàn tay | Camera **hoặc** nút / phím tắt |
| Dấu có chuyển động | **trăng `˘`**, 5 dấu thanh **sắc, huyền, hỏi, ngã, nặng** | Cần chuyển động tay | **Nút bấm / phím tắt** (Ctrl+1..8) |

Ngoài ra:
- Bảng chữ cái NNKH **không có F, J, W, Z** (khác bảng tiếng Anh), nhưng có thêm chữ **Đ**.
- **11 chữ có tư thế giống hệt bảng chữ cái tiếng Anh (ASL)**: **A, B, C, G, L, O, P, Q, U, V, Y**.
- Các chữ **D, E, H, K, M, N, R, S, T, X** có hình dạng **khác** ASL.

## 2. Cách làm 11 chữ giống ASL

Mô tả theo góc nhìn của người làm ký hiệu, dùng tay thuận. Hãy luôn **dùng cùng một tay** khi thu dữ liệu và khi nhận diện.

| Chữ | Key trong chương trình | Cách làm |
|---|---|---|
| **A** | `letter_a` | Nắm tay; **ngón cái dựng sát cạnh ngón trỏ** (không gập vào lòng bàn tay); lòng bàn tay hướng ra trước |
| **B** | `letter_b` | Bốn ngón duỗi thẳng, **khép sát nhau** hướng lên; **ngón cái gập ngang lòng bàn tay** |
| **C** | `letter_c` | Các ngón và ngón cái **cong tạo hình chữ C**, như đang cầm một chiếc cốc; nhìn nghiêng thấy chữ C |
| **G** | `letter_g` | Ngón trỏ và ngón cái **duỗi song song, nằm ngang**, chỉ sang bên; các ngón khác nắm |
| **L** | `letter_l` | Ngón trỏ chỉ lên, ngón cái chỉ ngang, **tạo góc vuông chữ L**; các ngón khác nắm |
| **O** | `letter_o` | Tất cả các ngón **cong lại, đầu ngón chạm đầu ngón cái** tạo vòng tròn chữ O |
| **P** | `letter_p` | Ngón trỏ duỗi chỉ ra trước, **ngón giữa duỗi chỉ xuống dưới**, ngón cái đặt giữa hai ngón; bàn tay chúc xuống |
| **Q** | `letter_q` | Ngón cái và ngón trỏ **cùng chỉ xuống dưới** (giống G nhưng chúc xuống) |
| **U** | `letter_u` | Ngón trỏ và ngón giữa **duỗi thẳng, khép sát nhau** chỉ lên; ngón cái giữ ngón áp út và út |
| **V** | `letter_v` | Ngón trỏ và ngón giữa duỗi, **tách hình chữ V**; lòng bàn tay hướng ra trước (giống gesture *Chữ V* có sẵn) |
| **Y** | `letter_y` | **Ngón cái và ngón út duỗi** sang hai bên; ba ngón giữa nắm lại |

## 3. Các chữ và dấu cần tra cứu nguồn chính thức

Các chữ **D, Đ, E, H, I, K, M, N, R, S, T, X** cùng dấu **mũ `^`** và **móc/râu `’`** có hình dạng riêng theo chuẩn Việt Nam. Mình **không mô tả bằng chữ ở đây**, vì mô tả sai ký hiệu cho người Điếc là điều cần tránh, và hình ảnh minh họa chính xác hơn nhiều so với lời văn. Hãy học từ:

1. **Từ điển Ngôn ngữ ký hiệu Việt Nam**: https://tudienngonngukyhieu.com (có hình và video).
2. **Quy định chuẩn quốc gia về NNKH** do Bộ GD&ĐT ban hành năm 2020.
3. **Trung tâm, trường, câu lạc bộ người Điếc** ở địa phương. Đây là nguồn tốt nhất: vừa học đúng ký hiệu, vừa có người làm mẫu để thu dữ liệu.

> NNKH có **biến thể vùng miền** (Hà Nội, Hải Phòng, TP.HCM). Hãy chọn một chuẩn rõ ràng và ghi lại trong báo cáo.

## 4. Quy trình đưa bảng chữ cái vào chương trình

1. **Dữ liệu → Thêm bảng chữ cái NNKH**: tạo sẵn 25 nhãn (`letter_a` … `letter_y`, `letter_dd` = Đ, `mark_mu`, `mark_rau`).
2. Với mỗi nhãn: chọn nhãn → nhập **300** mẫu → **Bắt đầu thu thập** → giữ tư thế tay, nhích nhẹ góc, khoảng cách và vị trí trong khung hình.
   - Tốt nhất là thu từ **2–3 người khác nhau**, ở các điều kiện ánh sáng khác nhau.
   - Có thể bắt đầu với **11 chữ ở mục 2** trước, chưa cần đủ 25.
3. **Huấn luyện → So sánh các mô hình** → tick *Lưu mô hình tốt nhất*. Với khoảng 25 lớp, SVM hoặc MLP thường tốt nhất.
4. Mở tab **Ma trận nhầm lẫn**: ô ngoài đường chéo cho biết cặp chữ hay nhầm (ví dụ U và V, hay A và các chữ dạng nắm tay). Thu thêm mẫu cho những chữ đó rồi train lại.
5. Vào **Đánh vần** và thử (mục 5).

> **Kiểm thử phần mềm khác với kiểm chứng ngôn ngữ.** Để chứng minh *phần mềm* chạy đúng, chỉ cần tư thế bạn dùng khi thu dữ liệu **giống** tư thế khi test. Còn để hệ thống *dùng được với người Điếc*, các tư thế phải đúng chuẩn NNKH (mục 3) và nên được người dùng NNKH kiểm tra lại.

## 5. Bộ từ thử nghiệm (chỉ dùng 11 chữ ở mục 2)

Các từ dưới đây chỉ cần các chữ đã mô tả ở mục 2, cộng với nút dấu. Vì vậy bạn có thể test ngay sau khi train 11 chữ đó:

| Từ cần gõ | Ký hiệu chữ (camera) | Dấu (nút / phím tắt) | Kết quả mong đợi |
|---|---|---|---|
| ba | B → A | — | `ba` |
| bà | B → A | huyền (Ctrl+2) | `bà` |
| cá | C → A | sắc (Ctrl+1) | `cá` |
| gà | G → A | huyền (Ctrl+2) | `gà` |
| lá | L → A | sắc (Ctrl+1) | `lá` |
| bò | B → O | huyền (Ctrl+2) | `bò` |
| quà | Q → U → A | huyền (Ctrl+2) | `quà` (dấu đặt trên **a**, không phải u) |
| vua | V → U → A | — | `vua` |
| lúa | L → U → A | sắc (Ctrl+1) | `lúa` (dấu trên **u**) |
| bay | B → A → Y | — | `bay` |
| vậy | V → A → Y | mũ (Ctrl+6) → nặng (Ctrl+5) | `vậy` |
| bơ | B → O | râu (Ctrl+7) | `bơ` |
| cá bơ | C → A → sắc → *hạ tay* → B → O → râu | | `cá bơ` (tự thêm khoảng trắng khi hạ tay) |

Sau đó bấm **Đọc** (Enter) để nghe câu.

---
[← Mục lục](../README.md#tài-liệu)
