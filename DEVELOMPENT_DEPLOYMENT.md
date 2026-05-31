# Panduan Operasional dan Deployment Produksi (Amica)

Dokumen ini berisi pedoman arsitektur operasional, konfigurasi server, dan standar peluncuran produksi (*deployment*) untuk memastikan sistem Amica berjalan dengan stabilitas tinggi, mampu menangani koneksi WebSocket secara paralel, serta menjaga privasi dan keamanan data tingkat lanjut.

---

## 1. Topologi Arsitektur

Arsitektur Amica dioptimalkan untuk memproses permintaan HTTP sinkron dan koneksi WebSocket asinkron (*real-time chat*) di bawah satu instance aplikasi yang ditenagai oleh Gevent.

```text
[ Client / Mobile App ]

           |
           | (HTTPS / WSS)
           v
[ Caddy Reverse Proxy ]  ---> Menangani enkripsi SSL/TLS & meneruskan header Upgrade WebSocket.

           |
           | (HTTP 1.1)
           v
[  Gunicorn Master  ]  ---> Mengelola GeventWebSocketWorker untuk lalu lintas data asinkron.

           |
           v
[ Flask Application ]  ---> Terhubung ke ONNX Models, PostgreSQL, dan Redis secara bersamaan.
```

---

## 2. Konfigurasi Variabel Lingkungan

Sistem membutuhkan pengaturan kredensial yang harus dideklarasikan ke dalam berkas `.env` di level sistem operasi produksi.

| Variabel Lingkungan | Tipe Data | Deskripsi Fungsi |
| :--- | :--- | :--- |
| `DATABASE_URL` | String | URI koneksi PostgreSQL (contoh: `postgresql://user:pass@localhost/amica`) |
| `REDIS_URL` | String | URI koneksi Redis untuk mekanisme *rate limiter* dan antrean pesan |
| `SECRET_KEY` | String | Kunci rahasia kriptografi Flask untuk token JWT dan sesi |
| `ENCRYPTION_KEY` | String | Kunci Fernet 32-byte (base64) untuk mengamankan dokumen profesional |
| `GROQ_API_KEYS` | String | Kunci API Groq untuk pemrosesan RAG (pisahkan dengan koma jika multi-kunci) |
| `LOCAL_ENGINE_URL` | String | Endpoint API untuk Model LLM Llama lokal (default: `http://127.0.0.1:7860`) |
| `FIREBASE_API_KEY` | String | Konfigurasi identifikasi Firebase Auth untuk integrasi SSO |
| `ONESIGNAL_APP_ID` | String | Kredensial distribusi Push Notification OneSignal |

---

## 3. Manajemen Migrasi Basis Data

Pembaruan skema basis data diatur ketat oleh mesin **Alembic**. Langkah ini wajib dieksekusi secara manual oleh administrator setiap kali terdapat rilis kode baru yang mengubah struktur tabel.

* **Instruksi pembentukan skema migrasi baru:**
  ```bash
  alembic revision --autogenerate -m "update_schema_produksi"
  ```

* **Instruksi penetapan migrasi ke dalam basis data aktif:**
  ```bash
  alembic upgrade head
  ```

---

## 4. Persyaratan Pustaka Model AI

Sebelum aplikasi dapat berjalan tanpa menghasilkan error pembacaan, direktori `models_ml` harus sudah dikonfigurasi dengan meletakkan berkas model ONNX dan file CSV yang relevan.


| Lokasi Direktori | Nama Berkas | Tanggung Jawab Inferensi |
| :--- | :--- | :--- |
| `models_ml/image/` | `gatekeeper.onnx` | Memfilter gambar umum menjadi aman atau tidak aman |
| `models_ml/image/` | `specialist.onnx` | Menentukan klasifikasi ancaman visual (NSFW/Violence) |
| `models_ml/text/post/` | `post_classifier.onnx` | Deteksi probabilitas toksisitas teks atau *caption* |
| `models_ml/text/feedback/` | `feedback_sentiment.onnx` | Analisis sentimen terhadap umpan balik pengguna |
| `models_ml/text/feedback/` | `feedback_vocab.csv` | Kamus referensi tokenisasi teks sentimen |

---

## 5. Standar Deployment Produksi (Linux/Ubuntu)

### A. Konfigurasi Gunicorn Service (Systemd)
Daftarkan program ke dalam manajer layanan sistem (Systemd) untuk memastikan aplikasi akan dimulai ulang secara otomatis bila server mengalami *reboot*. Buat berkas baru di `/etc/systemd/system/amica.service`.

```ini
[Unit]
Description=Amica Backend Service
After=network.target

[Service]
User=amica_user
Group=www-data
WorkingDirectory=/var/www/amica
Environment="PATH=/var/www/amica/venv/bin"
EnvironmentFile=/var/www/amica/.env
ExecStart=/var/www/amica/venv/bin/gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --threads 4 -b 127.0.0.1:5000 run:amica_app_obj
Restart=always

[Install]
WantedBy=multi-user.target
```

### B. Eksekusi dan Aktivasi Layanan
Jalankan perintah berikut di terminal untuk memuat ulang konfigurasi dan mengaktifkan servis:

```bash
sudo systemctl daemon-reload
sudo systemctl start amica
sudo systemctl enable amica
```

### C. Penyelarasan Reverse Proxy (Caddy)
Caddy dikonfigurasi sebagai garda terdepan untuk menangani HTTPS. Konfigurasi `flush_interval -1` bersifat wajib agar koneksi WebSocket tidak mengalami *buffer* yang menyebabkan penundaan (*delay*) atau pemutusan koneksi sepihak. Masukkan konfigurasi ini pada `/etc/caddy/Caddyfile`.

```caddy
api.amica.com {
    reverse_proxy 127.0.0.1:5000 {
        flush_interval -1
    }
}
```

Aktivasi ulang proxy jaringan untuk menerapkan perubahan:
```bash
sudo systemctl reload caddy
```

---

## 6. Protokol Pemeliharaan Latar Belakang

Sistem telah memiliki manajemen siklus pemeliharaannya sendiri yang diatur dalam modul `tasks.py` menggunakan integrasi `Flask-APScheduler`.

* **Siklus Pekerjaan**: Berjalan setiap 1 jam sekali (dijaga oleh `scheduler.lock` agar tidak terjadi duplikasi proses pada sistem multiprosesor).
* **Target Pembersihan**: Mencari baris pada tabel `Post` yang berstatus `rejected`. Jika umur baris tersebut melewati masa banding moderasi (24 jam), sistem akan menghapus data tersebut dari PostgreSQL sekaligus menghapus file gambar terkait dari dalam direktori `static/reject/`. 
* **Manajemen Log**: Log aplikasi dikelola secara natif oleh keluaran konsol Ubuntu. Pemantauan stabilitas server dapat diakses administrator dengan memanggil perintah berikut:
  ```bash
  journalctl -u amica -f -n 100
  ```

