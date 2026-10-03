# 11 · Hướng phát triển

- **Ngôn ngữ ký hiệu / ASL alphabet:** thêm 26 chữ cái làm gesture, thu thập dữ liệu, dùng SVM/MLP; thêm đặc trưng góc giữa các khớp ngón để phân biệt chữ gần giống nhau.
- **Ký hiệu động & chuỗi liên tục:** lưu chuỗi 30 frame landmark → LSTM/GRU/Transformer (TensorFlow/PyTorch); nhận diện chữ J, Z và từ vựng có chuyển động.
- **Speech-to-Text** (Whisper, `speech_recognition`): người nghe nói → hiển thị chữ cho người Điếc đọc (chiều ngược lại của chế độ Đánh vần).
- **Nhiều bàn tay / hai tay kết hợp:** nối 2 vector (126 chiều) cho ký hiệu dùng cả hai tay.
- **REST API bằng FastAPI:** endpoint nhận ảnh/landmark và trả gesture; tái sử dụng `recognition/`.
- **Web frontend React** + MediaPipe JS chạy landmark ngay trên trình duyệt, gửi vector 63 chiều lên API.
- **Deploy server:** Docker + Uvicorn/Gunicorn, lưu dữ liệu bằng PostgreSQL.
- **Mobile app:** MediaPipe Android/iOS hoặc Flutter, xuất model sang TensorFlow Lite / ONNX.
- **Nhận diện dấu động bằng camera:** dấu trăng và 5 dấu thanh trong NNKH là ký hiệu có chuyển động. Có thể lưu chuỗi khoảng 30 frame landmark và phân loại bằng LSTM/GRU, hoặc bằng DTW (Dynamic Time Warping) với scikit-learn, thay cho nút bấm hiện tại.
- **Gợi ý từ (autocomplete):** dùng từ điển tiếng Việt để gợi ý từ khi đánh vần, giảm số ký hiệu cần làm.
- **Đặc trưng hình học bổ sung:** góc giữa các đốt ngón tay, khoảng cách giữa các đầu ngón… giúp phân biệt các chữ có hình dạng gần nhau.
- **Hợp tác với cộng đồng người Điếc:** thu dữ liệu từ người dùng NNKH thật, đánh giá khả năng sử dụng (usability) với người dùng mục tiêu.


---
[← Mục lục](../README.md#tài-liệu)
