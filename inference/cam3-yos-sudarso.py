import os
import cv2
from ultralytics import YOLO
from collections import defaultdict
import time
from datetime import datetime, timezone, timedelta
import json
import threading
import paho.mqtt.client as mqtt

# ─── MQTT Configuration ──────────────────────────────────────────────────────
MQTT_BROKER = "192.168.1.99"
MQTT_PORT = 1883
MQTT_TOPIC = "/yos_sudarso/hasil_deteksi"

try:
    mqtt_client = mqtt.Client()
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"⚠️ Warning: Tidak dapat terhubung ke MQTT broker ({e})")
    mqtt_client = None

# Mapping kelas kendaraan
CLASS_NAMES = {
    1: "sepeda",
    2: "mobil",
    3: "motor",
    5: "bus_truk"
}

# Paths — override via env var or set directly when running locally
# Docker  : set via docker-compose.yml environment section
# Local   : export MODEL_PATH=/path/to/yolo26n.pt
MODEL_PATH   = os.environ.get("MODEL_PATH",   "/app/model/yolo26n.pt")
TRACKER_PATH = os.environ.get("TRACKER_PATH", "/app/model/custom_bytetrack.yaml")
model = YOLO(MODEL_PATH)

URL = "https://cctvjss.jogjakota.go.id/kotabaru/ANPR-Jl-Yos-Sudarso.stream/playlist.m3u8"
TARGET_CLASSES = [1, 2, 3, 5]

# ─── Tuning Parameter ────────────────────────────────────────────────────────
PROCESS_EVERY_N_FRAMES = 3
RESIZE_INFERENCE = 0.95
MIN_TRACK_AGE = 3       # Track harus terlihat minimal N frame sebelum dikirim MQTT
# ─────────────────────────────────────────────────────────────────────────────

# ─── Stream Configuration ─────────────────────────────────────────────────────
RECONNECT_DELAY = 5             # Detik tunggu sebelum reconnect
MAX_CONSECUTIVE_FAIL = 2        # Cukup 2 gagal (~60s) → langsung reconnect
MAX_RECONNECT_ATTEMPTS = 999
# ──────────────────────────────────────────────────────────────────────────────

class StreamReader:
    """Baca frame HLS di background thread. Main thread tidak pernah di-block."""

    def __init__(self, url):
        self.url = url
        self.frame = None
        self.stopped = False
        self.lock = threading.Lock()
        self.reconnect_count = 0

        self.cap = cv2.VideoCapture(url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        consecutive_fail = 0
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                consecutive_fail += 1
                if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
                    self.reconnect_count += 1
                    if self.reconnect_count > MAX_RECONNECT_ATTEMPTS:
                        self.stopped = True
                        break
                    ts = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S")
                    print(f"[{ts}] 🔄 Stream terputus! Reconnect #{self.reconnect_count}...")
                    self.cap.release()
                    time.sleep(RECONNECT_DELAY)
                    self.cap = cv2.VideoCapture(self.url)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if self.cap.isOpened():
                        ts = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S")
                        print(f"[{ts}] ✅ Reconnect berhasil!")
                        consecutive_fail = 0
                    else:
                        print(f"   ⚠️ Reconnect gagal, coba lagi...")
                time.sleep(0.1)
                continue

            consecutive_fail = 0
            with self.lock:
                self.frame = frame
            # Throttle ~30fps agar buffer tidak menumpuk
            time.sleep(0.033)

    def read(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return True, self.frame.copy()

    def is_opened(self):
        return self.cap.isOpened()

    def release(self):
        self.stopped = True
        self.thread.join(timeout=3)
        self.cap.release()


def now_str():
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")


def main():
    stream = StreamReader(URL)

    if not stream.is_opened():
        print("❌ Stream error, mencoba ulang...")
        stream.release()
        for _ in range(3):
            time.sleep(RECONNECT_DELAY)
            stream = StreamReader(URL)
            if stream.is_opened():
                break
        if not stream.is_opened():
            print("❌ Gagal total membuka stream.")
            return

    print(f"[{now_str()}] 🔥 Deteksi berjalan (headless mode)")
    print(f"   Target  : bicycle, car, motorcycle, bus")
    print(f"   Inferensi : 1/{PROCESS_EVERY_N_FRAMES} frame  |  Resize: {int(RESIZE_INFERENCE*100)}%")
    print(f"   Tekan Ctrl+C untuk berhenti\n")

    frame_idx        = 0
    detect_count     = 0
    is_stabilizing   = True
    last_boxes       = None
    scale_factor     = 1.0 / RESIZE_INFERENCE
    status_timer     = time.time()

    total_unique_tracks = set()
    reported_tracks     = set()
    track_seen_count    = defaultdict(int)

    while True:
        ret, frame = stream.read()
        if not ret:
            time.sleep(0.01)
            continue

        frame_idx += 1
        current_skip = 1 if is_stabilizing else PROCESS_EVERY_N_FRAMES

        if frame_idx % current_skip == 0:
            detect_count += 1

            if is_stabilizing and detect_count >= 5:
                is_stabilizing = False
                print(f"[{now_str()}] ✅ Stabilisasi selesai! Deteksi aktif.")

            h, w = frame.shape[:2]
            small = cv2.resize(frame, (int(w * RESIZE_INFERENCE), int(h * RESIZE_INFERENCE)))

            results = model.track(
                small,
                persist=True,
                classes=TARGET_CLASSES,
                conf=0.30,
                iou=0.6,
                tracker=TRACKER_PATH,
                verbose=False,
                agnostic_nms=True,
            )

            boxes = results[0].boxes
            last_boxes = boxes

            if boxes is not None and boxes.id is not None:
                new_payload_tracks = []
                track_ids = boxes.id.int().cpu().tolist()
                class_ids = boxes.cls.int().cpu().tolist()

                for track_id, cls_id in zip(track_ids, class_ids):
                    total_unique_tracks.add(track_id)
                    track_seen_count[track_id] += 1

                    if track_id not in reported_tracks and track_seen_count[track_id] >= MIN_TRACK_AGE:
                        reported_tracks.add(track_id)
                        obj_name = CLASS_NAMES.get(cls_id, "unknown")
                        new_payload_tracks.append({
                            "object": obj_name,
                            "track_id": track_id
                        })

                if new_payload_tracks and mqtt_client is not None:
                    payload = {
                        "camera_id": "cam3",
                        "timestamp": now_str(),
                        "new_tracks": new_payload_tracks
                    }
                    try:
                        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
                        print(f"[{now_str()}] 📤 MQTT: {json.dumps(new_payload_tracks)}")
                    except Exception:
                        pass

        # Log status setiap 30 detik
        if time.time() - status_timer >= 30:
            n_tracked = len(last_boxes.id) if last_boxes is not None and last_boxes.id is not None else 0
            n_unique  = len(total_unique_tracks)
            print(f"[{now_str()}] 📊 Tracked:{n_tracked}  Unique:{n_unique}  Reconnect:{stream.reconnect_count}")
            status_timer = time.time()

    stream.release()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{now_str()}] ⏹️ Dihentikan oleh pengguna.")