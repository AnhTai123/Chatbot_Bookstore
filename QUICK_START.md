# Quick Start Guide

Hướng dẫn nhanh để chạy BookStore Chatbot.

## Cài đặt nhanh

```bash
# 1. Cài đặt dependencies
pip install -r requirements.txt

# 2. Khởi tạo database
python init_database.py

# 3. Chạy ứng dụng
streamlit run simple_app.py --server.port 8502
```

## Truy cập ứng dụng
Mở trình duyệt và truy cập: http://localhost:8502

## Các câu hỏi mẫu

### Tìm kiếm sách
- "Tìm sách Gilead"
- "Sách Sidney Sheldon"
- "Sách về Fiction"
- "Giá dưới 100000"

### Tra cứu thông tin
- "Giá sách Gilead"
- "Sách Enduring Love có bao nhiêu cuốn"
- "Thông tin sách Gilead"

### Đặt hàng
- "Đặt mua Gilead"
- Sau đó làm theo hướng dẫn

### Gợi ý
- "Gợi ý sách hay"
- "Sách hay dưới 200000"

## Lưu ý
- Đảm bảo Python 3.8+ đã được cài đặt
- Port 8502 phải trống
- Database sẽ được tạo tự động lần đầu chạy
