FROM python:3.10-slim

# Cài đặt Tesseract OCR và ngôn ngữ tiếng Việt
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy các file dự án vào container
COPY . /app

# Cài đặt thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

# Khởi chạy ứng dụng Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
