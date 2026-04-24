# Menggunakan base image python resmi yang ringan
FROM python:3.10-slim

WORKDIR /app

# Install dependency system yang dibutuhkan opencv
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 ffmpeg libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Install PyTorch dengan CUDA 11.8 (Mendukung GTX 1050 / compute capability 6.1)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install package MQTT, Ultralytics, dan dependensi tambahan
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt lapx

# Copy skrip inferensi
COPY . /app/infrensi/

# Default command (di-override per service di docker-compose)
CMD ["python", "-u", "infrensi/cam1-demangan.py"]
