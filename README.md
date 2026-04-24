# 🚦 Yogyakarta Intelligent Traffic Monitoring System (YITMS)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLO-v8%2Fv26-purple?logo=ultralytics)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-red?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Open Source](https://img.shields.io/badge/Open%20Source-❤️-orange)

**Sistem monitoring dan analitik lalu lintas real-time berbasis Computer Vision**  
menggunakan public CCTV Kota Yogyakarta, YOLO tracking, MQTT, dan Streamlit Dashboard.

[Demo Dashboard](#-analytics-dashboard) · [Arsitektur Sistem](#-arsitektur-sistem) · [Cara Setup](#-cara-setup) · [Kontribusi](#-kontribusi)

</div>

---

## 📖 Tentang Project

YITMS adalah sistem open-source yang memadukan **Computer Vision** dan **Data Analytics** untuk memantau kepadatan lalu lintas secara real-time di beberapa titik strategis Kota Yogyakarta. Project ini dirancang sebagai referensi pembelajaran untuk siapa saja yang ingin memahami implementasi CV inference pipeline end-to-end.

### Fitur Utama

| Fitur | Detail |
|-------|--------|
| 🎯 **Real-time Detection** | YOLO tracking pada stream HLS public CCTV Jogjakota |
| 🚗 **Multi-class** | Deteksi Motor, Mobil, Bus/Truk, dan Sepeda |
| 📡 **MQTT Publishing** | Data dikirim ke broker secara real-time |
| 🐳 **Dockerized** | Semua inference container siap deploy |
| 📊 **Dashboard Analytics** | Visualisasi interaktif dengan Streamlit + Plotly |
| 🔄 **Auto-reconnect** | Stream HLS reconnect otomatis saat putus |

### Lokasi CCTV yang Dipantau

| Camera | Lokasi | MQTT Topic |
|--------|--------|------------|
| `cam1` | Simpang Demangan | `/demangan/hasil_deteksi` |
| `cam2` | Lampu Merah Pingit | `/lampu_merah_pingit3/hasil_deteksi` |
| `cam3` | Jl. Yos Sudarso | `/yos_sudarso/hasil_deteksi` |
| `cam4` | Titik Nol KM | `/titik_nol/hasil_deteksi` |

---

## 🏗 Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────┐
│                     PUBLIC CCTV STREAMS                     │
│          cctvjss.jogjakota.go.id  (HLS / m3u8)             │
└──────────────┬──────────────────────────────────────────────┘
               │ 4x RTSP/HLS Streams
               ▼
┌─────────────────────────────────────────────────────────────┐
│                  INFERENCE ENGINE (Docker)                   │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  cam1    │ │  cam2    │ │  cam3    │ │  cam4    │      │
│  │ demangan │ │  pingit  │ │  yos-sud │ │ titiknol │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
│       │            │            │             │             │
│       └────────────┴────┬───────┴─────────────┘            │
│                   YOLO Tracking                             │
│              (ByteTrack + NMS Filter)                       │
└───────────────────────┬─────────────────────────────────────┘
                        │ JSON Payload via MQTT
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    MQTT BROKER (Mosquitto)                   │
│                  192.168.1.99 : 1883                        │
└───────────────────────┬─────────────────────────────────────┘
                        │ Subscribe & Store
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   DATA STORAGE (CSV / DB)                   │
│           data/data_cctv_clean_v1.csv  (181K rows)         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              ANALYTICS DASHBOARD (Streamlit)                │
│                                                             │
│   KPI Cards · Line Chart · Bar Chart · Donut · Heatmap     │
│        Stacked Bar · Filter by Date, Hour, Location        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Struktur Repository

```
yitms/
│
├── inference/                  # Computer Vision inference scripts
│   ├── cam1-demangan.py        # CCTV Simpang Demangan
│   ├── cam2-lampumerah-pingit.py
│   ├── cam3-yos-sudarso.py
│   ├── cam4-titiknol.py
│   ├── Dockerfile              # Docker image untuk inference
│   ├── docker-compose.yml      # Orchestrasi 4 container sekaligus
│   ├── requirements.txt        # Dependency inference (ultralytics, paho-mqtt)
│   ├── start.sh                # Helper: start semua container
│   └── stop.sh                 # Helper: stop semua container
│
├── dashboard/
│   └── app.py                  # Streamlit analytics dashboard
│
├── notebooks/
│   └── olahdata.ipynb          # Eksplorasi dan preprocessing data
│
├── data/
│   ├── sample_data.csv         # ✅ Sample 500 baris (untuk demo)
│   └── .gitkeep
│
├── models/                     # Letakkan model .pt di sini (di-.gitignore)
│   └── .gitkeep
│
├── .gitignore
├── requirements.txt            # Dependency dashboard
└── README.md
```

---

## ⚙️ Cara Setup

### Prasyarat

- Python 3.10+
- Docker & Docker Compose (untuk inference)
- NVIDIA GPU opsional (CPU tetap bisa, tapi lambat)
- MQTT Broker (Mosquitto) di jaringan lokal

### 1. Clone Repository

```bash
git clone https://github.com/username/yitms.git
cd yitms
```

### 2. Setup Analytics Dashboard

```bash
# Install dependency
pip install -r requirements.txt

# Letakkan file data lengkap (opsional, sample sudah tersedia)
cp /path/to/data_cctv_clean_v1.csv data/

# Jalankan dashboard
streamlit run dashboard/app.py
```

Dashboard akan terbuka di `http://localhost:8501`

### 3. Setup Inference Engine (Docker)

#### Siapkan Model & Tracker

```bash
# Download atau copy model YOLO ke folder models/
cp /path/to/yolo26n.pt models/
cp /path/to/custom_bytetrack.yaml models/
```

> 💡 **Model YOLO:** Project ini menggunakan model custom yang ditraining untuk kendaraan Indonesia.  
> Kamu bisa menggunakan model YOLO standar (`yolov8n.pt`) sebagai alternatif.

#### Konfigurasi MQTT Broker

Edit `inference/cam1-demangan.py` (dan file cam lainnya) sesuaikan IP broker:

```python
MQTT_BROKER = "192.168.1.99"   # Ganti dengan IP MQTT broker kamu
MQTT_PORT   = 1883
```

Atau gunakan environment variable:

```bash
export MQTT_BROKER=192.168.x.x
```

#### Deploy dengan Docker Compose

```bash
cd inference/

# Build & jalankan semua container
docker compose up -d --build

# Cek log real-time
docker compose logs -f

# Stop semua
docker compose down
```

#### Menjalankan Tanpa Docker (Local)

```bash
pip install -r inference/requirements.txt

# Set env vars
export MODEL_PATH=/path/to/models/yolo26n.pt
export TRACKER_PATH=/path/to/models/custom_bytetrack.yaml

# Jalankan satu kamera
python inference/cam1-demangan.py
```

---

## 📊 Analytics Dashboard

Dashboard Streamlit menampilkan:

| Visualisasi | Deskripsi |
|-------------|-----------|
| **KPI Cards** | Total volume, lokasi terpadat, kendaraan dominan, jam puncak |
| **Line Chart** | Tren volume per jam per lokasi |
| **Bar Chart** | Komparasi volume antar lokasi |
| **Donut Chart** | Komposisi jenis kendaraan |
| **Heatmap** | Intensitas trafik (lokasi × jam) |
| **Stacked Bar** | Komposisi kendaraan per lokasi |

**Filter yang tersedia:** Tanggal, rentang jam, lokasi, dan jenis kendaraan.

---

## 📡 Format Data MQTT

Setiap kali kendaraan baru terdeteksi dan dikonfirmasi (minimal terlihat `MIN_TRACK_AGE` frame), payload JSON dikirim ke broker:

```json
{
  "camera_id": "cam1",
  "timestamp": "2026-03-25 07:23:41",
  "new_tracks": [
    { "object": "motor",  "track_id": 42 },
    { "object": "mobil",  "track_id": 43 }
  ]
}
```

---

## 📈 Format Dataset

File CSV memiliki kolom berikut:

| Kolom | Tipe | Contoh |
|-------|------|--------|
| `camera_id` | string | `cam1` |
| `object` | string | `motor`, `mobil`, `bus_truk`, `sepeda` |
| `track_id` | int | `12345` |
| `detection_timestamp` | datetime (UTC) | `2026-03-25 07:23:41` |
| `created_at` | datetime | `2026-03-25 20:14:22` |
| `location` | string | `demangan` |

---

## 🤝 Kontribusi

Project ini sepenuhnya open-source dan menyambut kontribusi dari siapapun! 🙌

### Cara Berkontribusi

1. **Fork** repository ini
2. Buat branch fitur: `git checkout -b feature/nama-fitur`
3. Commit perubahan: `git commit -m 'feat: tambah fitur X'`
4. Push ke branch: `git push origin feature/nama-fitur`
5. Buat **Pull Request**

### Area yang Bisa Dikontribusikan

- [ ] Tambah support kamera CCTV baru
- [ ] Implementasi MQTT subscriber + database writer (SQLite/PostgreSQL)
- [ ] Ekspor laporan PDF dari dashboard
- [ ] Notifikasi alert saat volume melewati threshold
- [ ] Custom ByteTrack config optimizer
- [ ] Unit test untuk inference pipeline
- [ ] Dokumentasi lebih lengkap (bahasa Inggris & Indonesia)

### Pelaporan Bug / Saran

Silakan buka [GitHub Issue](https://github.com/username/yitms/issues) dengan label yang sesuai.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE) — bebas digunakan, dimodifikasi, dan didistribusikan.

---

## 🙏 Acknowledgements

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) — Object detection & tracking
- [Streamlit](https://streamlit.io) — Dashboard framework
- [CCTV Jogjakota](https://cctvjss.jogjakota.go.id) — Public CCTV stream
- [Eclipse Paho](https://github.com/eclipse/paho.mqtt.python) — MQTT client
- [Plotly](https://plotly.com/python/) — Interactive charts

---

<div align="center">
Made with ❤️ for the open-source community · Yogyakarta, Indonesia 🇮🇩
</div>
