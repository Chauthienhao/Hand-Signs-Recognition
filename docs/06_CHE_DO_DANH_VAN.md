# 06 · Chế độ Đánh vần: ghép chữ thành câu và đọc thành tiếng

Chế độ Đánh vần biến chuỗi ký hiệu trước camera thành **văn bản tiếng Việt có dấu**, rồi **đọc thành tiếng**. Mục tiêu là hỗ trợ người Điếc giao tiếp với người nghe không biết ngôn ngữ ký hiệu.

```
Ký hiệu tay ──► MediaPipe ──► 21 landmark ──► Mô hình ML ──► "letter_a"
                                                              │
        Nút / phím tắt: ^ ’ ˘ sắc huyền hỏi ngã nặng ─────────┤
                                                              ▼
                                         SpellingEngine (giữ ≥ 1 giây → chốt)
                                                              │
                                    VietnameseComposer (ghép dấu đúng chính tả)
                                                              ▼
                                                    "việt nam" ──► 🔊 Đọc
```

## 1. Bắt đầu nhanh

**Chưa train chữ cái?** Bạn vẫn thử được luồng ghép câu bằng 7 ký hiệu có sẵn (chúng ra *cụm từ demo*), xem [04_KY_HIEU_CO_SAN.md](04_KY_HIEU_CO_SAN.md) mục 6.

**Đã train chữ cái** (theo [05_BANG_CHU_CAI_NNKH.md](05_BANG_CHU_CAI_NNKH.md)):
1. Menu **Đánh vần** → **Bắt đầu**.
2. Làm ký hiệu một chữ và **giữ yên** đến khi thanh *Giữ* chạy hết (mặc định 1 giây) → chữ được thêm vào ô **Câu**.
3. Chuyển sang chữ tiếp theo. Muốn gõ **hai chữ giống nhau liên tiếp**, phải **hạ tay ra khỏi khung hình** rồi giơ lại.
4. Thêm dấu bằng nút hoặc phím tắt (mục 3).
5. Hết một từ thì **hạ tay** khoảng 1,5 giây → tự thêm khoảng trắng. Cũng có thể bấm *Cách* hoặc Ctrl+Space.
6. Bấm **Đọc** (hoặc Enter) → máy đọc câu.

## 2. Các thành phần trên màn hình

| Vùng | Ý nghĩa |
|---|---|
| **Ký hiệu hiện tại** | Ký hiệu đang thấy + độ tin cậy |
| **Thanh Giữ** | Tiến độ chốt ký hiệu; đầy thanh nghĩa là đã chốt |
| Dòng gợi ý màu cam | Ví dụ *Hạ tay để lặp lại ký hiệu*, *Đã sao chép*… |
| **Câu** | Văn bản đang soạn; có thể **sửa trực tiếp bằng bàn phím** |
| **Cách / Xóa lùi / Hoàn tác / Xóa hết** | Chỉnh sửa văn bản |
| **Dấu phụ**: ^ mũ, ’ râu, ˘ trăng, đ | Thêm dấu phụ vào nguyên âm phù hợp gần cuối từ |
| **Dấu thanh**: sắc, huyền, hỏi, ngã, nặng, bỏ dấu | Đặt dấu thanh cho từ đang gõ |
| **Đọc / Sao chép / Lưu .txt** | Đọc thành tiếng, sao chép vào clipboard, lưu ra file |
| **Ký hiệu gần đây** | 12 ký hiệu vừa chốt (để tự kiểm tra) |
| Thanh trượt **Thời gian giữ / Tự cách sau** | Chỉnh nhanh tốc độ gõ (lưu luôn vào Cài đặt) |

## 3. Dấu tiếng Việt

### 3.1. Vì sao có dấu phải bấm nút?
Theo chuẩn NNKH, **dấu trăng `˘` và 5 dấu thanh là ký hiệu có chuyển động**, mà mô hình hiện tại chỉ nhận diện tư thế tĩnh (từng frame). Vì vậy chúng được nhập bằng nút hoặc phím tắt. Còn **dấu mũ `^` và móc/râu `’` là tư thế tĩnh**, nên có thể làm bằng camera (sau khi train `mark_mu`, `mark_rau`) hoặc bấm nút.

| Dấu | Nút | Phím tắt | Ví dụ |
|---|---|---|---|
| mũ `^` | ^ mũ | Ctrl+6 | a→â, e→ê, o→ô |
| móc/râu `’` | ’ râu | Ctrl+7 | o→ơ, u→ư, **uo→ươ** |
| trăng `˘` | ˘ trăng | Ctrl+8 | a→ă |
| sắc | ´ sắc | Ctrl+1 | ca → cá |
| huyền | ` huyền | Ctrl+2 | ba → bà |
| hỏi | ? hỏi | Ctrl+3 | ca → cả |
| ngã | ~ ngã | Ctrl+4 | ga → gã |
| nặng | . nặng | Ctrl+5 | ta → tạ |
| bỏ dấu thanh | bỏ dấu | Ctrl+0 | cá → ca |

Bấm một dấu thanh khác lên từ đã có dấu sẽ **thay** dấu cũ (cá → Ctrl+2 → cà).

### 3.2. Quy tắc đặt dấu thanh (tự động)
Bạn chỉ cần bấm dấu **sau khi gõ xong các chữ của từ**; chương trình tự đặt dấu vào đúng nguyên âm (kiểu truyền thống):

| Quy tắc | Ví dụ |
|---|---|
| Có nguyên âm mang dấu phụ (ă â ê ô ơ ư) → đặt vào đó; với "ươ" đặt vào **ơ** | việt, muốn, người, cứu |
| Có phụ âm cuối → nguyên âm **cuối** của cụm | toán, hoàn |
| Vần mở 2 nguyên âm → nguyên âm **đầu** | hóa, múa, tái, lúa |
| Vần mở 3 nguyên âm → nguyên âm **giữa** | khoái, khuỷu |
| "qu", "gi" + nguyên âm: u / i thuộc phụ âm đầu | quà, già (nhưng: gì) |

Thứ tự gõ dấu phụ và dấu thanh **không quan trọng**: `v-a-y` + mũ + nặng hay + nặng + mũ đều cho **vậy**.

## 4. Ký hiệu điều khiển (tùy chọn)

Nếu muốn điều khiển hoàn toàn bằng tay, hãy tự tạo thêm các gesture với **đúng tên** dưới đây (màn hình *Dữ liệu → Thêm gesture*), chọn một tư thế tay **không trùng** với chữ cái nào, thu dữ liệu và train:

| Tên gesture | Tác dụng |
|---|---|
| `ctrl_space` | Thêm khoảng trắng |
| `ctrl_delete` | Xóa lùi 1 ký tự |
| `ctrl_speak` | Đọc câu thành tiếng |
| `ctrl_clear` | Xóa hết |

Tương tự, `mark_sac`, `mark_huyen`, `mark_hoi`, `mark_nga`, `mark_nang`, `mark_trang` cũng được hiểu là dấu, nếu bạn muốn dùng một **tư thế tĩnh thay thế** (lưu ý đây **không** phải cách làm dấu chuẩn NNKH). Mọi gesture khác (không bắt đầu bằng `letter_`, `mark_`, `ctrl_`) được thêm vào câu như **một từ**, theo tên hiển thị của gesture.

## 5. Đọc thành tiếng (Text-to-Speech)

| Bộ đọc (Cài đặt → *Bộ đọc*) | Cần gì | Tiếng Việt |
|---|---|---|
| `gtts` | Internet | Tốt |
| `pyttsx3` | Giọng đọc của Windows (offline) | Chỉ khi Windows có giọng tiếng Việt dùng được qua SAPI5 |
| `auto` (mặc định) | — | Dùng `pyttsx3` nếu tìm thấy giọng Việt, nếu không thì dùng `gtts` |

Ghi chú về giọng tiếng Việt offline: Windows có giọng Việt (ví dụ *Microsoft An*) trong gói ngôn ngữ Vietnamese (*Settings → Time & Language → Language & region → Add a language → Tiếng Việt*, chọn cài *Speech*). Tuy nhiên, một số giọng chỉ dành cho ứng dụng hiện đại của Windows và **không hiện** với `pyttsx3`. Khi đó chế độ `auto` tự chuyển sang `gtts`, nên bạn chỉ cần có Internet.

Ngôn ngữ đọc (`vi` / `en`) chỉnh ở **Cài đặt → Ngôn ngữ đọc**.

## 6. Mẹo để đánh vần trơn tru

- Tăng **Thời gian giữ** (1,2–1,5 giây) nếu hay bị chốt nhầm khi đang chuyển tay; giảm (0,6–0,8 giây) khi đã quen.
- Tăng **Ngưỡng tin cậy** (Cài đặt) nếu chữ lạ hay chen vào câu.
- Đặt **Số bàn tay = 1** khi đánh vần để tránh tay thứ hai gây nhiễu.
- Xem **Ký hiệu gần đây** để biết hệ thống đã hiểu những gì.

## 7. Mã nguồn liên quan

| File | Vai trò |
|---|---|
| `recognition/spelling.py` | `VietnameseComposer` (ghép dấu), `SpellingEngine` (giữ → chốt → câu), bảng `PHRASES` |
| `utils/tts.py` | `TextToSpeech`: pyttsx3 / gTTS, chạy nền, tự chọn backend |
| `gui/spelling_view.py` | Giao diện, nút, phím tắt |
| `tests/test_spelling.py` | Kiểm thử tự động: 38 ca ghép dấu + 7 ca luồng đánh vần + 5 ca TTS |

---
[← Mục lục](../README.md#tài-liệu)
