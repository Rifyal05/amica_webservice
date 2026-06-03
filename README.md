# Amica - AI-Based Anti-Bullying Education Platform

Amica adalah platform edukasi kesehatan mental dan anti-perundungan (anti-bullying) yang dirancang untuk memberikan edukasi terkait bullying. Platform ini menggabungkan ekosistem backend Python dengan kecerdasan buatan (AI) lokal untuk menciptakan ruang digital yang aman, inklusif, dan nyaman bagi penggunanya.

## Arsitektur dan Modul Utama

Proyek ini dibangun menggunakan pola arsitektur modular yang memisahkan antara Routing (Controller), Services (Business Logic), dan Models (Data Access).

### 1. Database Models (Skema Relasional)
Sistem ini menggunakan PostgreSQL dengan SQLAlchemy ORM. Entitas utama meliputi:
*   Users: Menyimpan data pengguna, kredensial terenkripsi (Bcrypt), OAuth Google UID, dan pengaturan privasi.
*   Posts dan Comments: Entitas sosial dengan metrik keterlibatan (likes, comments count) dan riwayat status moderasi.
*   Chats, ChatParticipants, dan Messages: Relasi kompleks untuk mendukung percakapan pribadi (Direct Message) dan grup, termasuk manajemen jumlah pesan belum dibaca dan status pengiriman (delivered/read).
*   SdqResults: Menyimpan riwayat jawaban kuesioner Strengths and Difficulties Questionnaire (SDQ) beserta skor kalkulasi.
*   ProfessionalProfiles: Menyimpan data spesifik psikolog (STR, KTP) yang telah dienkripsi secara simetris.
*   AuditLogs dan QuarantinedItems: Sistem pencatatan aktivitas manajerial dan penyimpanan memori isolasi untuk konten yang melanggar.

### 2. Services (Logika Bisnis)
*   ai_service.py: Menangani integrasi RAG (Retrieval-Augmented Generation) menggunakan LLM untuk menjawab pertanyaan seputar anti-perundungan berdasarkan pemotongan dataset artikel yang divalidasi.
*   image_moderation_service.py dan post_classification_service.py: Memuat model AI berformat ONNX secara lokal untuk melakukan inferensi (klasifikasi aman atau tidak aman) terhadap teks dan gambar dalam hitungan milidetik tanpa bergantung pada API pihak ketiga.
*   sdq_scoring_service.py dan interpretation_service.py: Menganalisis 25 metrik jawaban pengguna untuk menghasilkan tingkat risiko klinis spesifik (Normal, Borderline, Abnormal).
*   notification_service.py: Menjembatani komunikasi sistem dengan API OneSignal untuk mendistribusikan Push Notification berdasarkan identitas spesifik perangkat.

### 3. API Routes (Endpoints)
*   /api/auth: Autentikasi JWT dengan skema akses dan penyegaran (access/refresh tokens), integrasi Firebase Auth untuk Google Login, dan manajemen sistem PIN tambahan.
*   /api/posts dan /api/comments: Titik akses interaksi sosial yang dilindungi oleh validasi middleware otomatis dari AI Moderation Service.
*   /api/sdq: Titik akses pengiriman jawaban kuesioner klinis dan pengambilan riwayat rekam medis digital pengguna.
*   /api/chats: Endpoint HTTP untuk memuat struktur daftar kontak (Inbox) dan riwayat pesan dengan paginasi asinkron.
*   /admin: Dasbor kontrol pusat dengan hak akses berlapis untuk peninjauan laporan keamanan, manajemen pemblokiran pengguna (suspend/unsuspend), pengujian algoritma RAG, dan persetujuan profil profesional.

## Alur Sistem Khusus (Advanced Flows)

### Real-time Messenger dan AI Ghosting
Sistem perpesanan instan beroperasi menggunakan WebSockets (Flask-SocketIO) melalui perutean asinkron Gevent.
Event koneksi utama meliputi transmisi join_chat, send_message, typing, mark_read, dan message_received.
Mekanisme Pertahanan Otomatis: Jika seorang pengguna berupaya mengirimkan pesan teks toksik kepada penerima yang mengaktifkan perlindungan Moderasi AI, pesan tersebut akan terkena status ghosting (tampak terkirim secara visual di layar pengirim, namun ditolak oleh database dan tidak muncul di layar penerima). Pelanggaran dicatat secara diam-diam dalam ToxicMessageCounter. Pelanggaran batas maksimal (10 kali dalam satu hari) memicu isolasi blokir otomatis terhadap akun tersebut.

### Kriptografi Dokumen Profesional Berbasis Memori
Modul keamanan internal (utils/security.py) mengadopsi algoritma AES dari pustaka kriptografi terapan Fernet. Saat psikolog mengunggah foto STR dan KTP, berkas biner tersebut dienkripsi secara acak sebelum ditulis secara fisik ke dalam penyimpanan disk server. Saat administrator meninjau dokumen permohonan melalui endpoint khusus, sistem akan membaca berkas terenkripsi dari disk, mendekripsinya murni di dalam isolasi memori server (RAM), dan mengirimkannya ke peramban tanpa pernah menyimpan kembali salinan tak terenkripsi di hard drive.

## Tech Stack

*   Language: Python 3.10+
*   Framework: Flask 3.x
*   Asynchronous Server: Gevent dan Gunicorn
*   WebSockets: Flask-SocketIO dan gevent-websocket
*   Database: PostgreSQL
*   ORM dan Migrations: SQLAlchemy 2.x dan Alembic
*   Caching dan Message Broker: Redis
*   Rate Limiting: Flask-Limiter
*   Machine Learning: ONNX Runtime, Scikit-learn, NLTK, Langchain Text Splitters
*   Authentication: Flask-JWT-Extended, Flask-Bcrypt, Firebase Admin SDK

## Persyaratan Sistem dan Variabel Lingkungan

### Prerequisites
*   Python 3.10 atau lebih tinggi
*   PostgreSQL Server (Berjalan dan menerima koneksi pada port 5432)
*   Redis Server (Berjalan dan menerima koneksi pada port 6379)

### Konfigurasi Variabel Lingkungan (.env)
File .env mutlak diatur sebelum inisiasi server. Variabel krusial yang diperlukan meliputi:
*   DATABASE_URL (Rantai koneksi penuh PostgreSQL)
*   SECRET_KEY (Kunci master untuk hash sesi Flask dan token JWT)
*   REDIS_URL (Rantai koneksi Redis untuk manajemen state dan rate limiter)
*   ENCRYPTION_KEY (Kunci enkripsi simetris Fernet berupa 32 byte URL-safe base64-encoded)
*   FIREBASE_* dan ONESIGNAL_* (Kredensial identifikasi SDK pihak ketiga)
*   GROQ_API_KEYS dan AI_ENGINE_KEY (Jalur otorisasi inferensi LLM eksternal dan lokal)
*   MAIL_* (Kredensial protokol SMTP untuk transmisi OTP surel)

### Langkah Instalasi dan Menjalankan Proyek

Salin dan jalankan perintah berikut di terminal Anda:

```bash
# Clone repositori
git clone <URL_REPOSITORI_ANDA>
cd amica-backend

# aktifkan Lingkungan Virtual (Virtual Environment)
python -m venv venv
source venv/bin/activate

# SinkronisasiDependensi
pip install --upgrade pip
pip install -r requirements.txt

# Terapkan Skema Basis Data
chmod +x db_migrate.sh
./db_migrate.sh

# Eksekusi Server (dev)
python run.py
```

## Panduan Deployment (Produksi)

Dalam lingkungan operasi publik, infrastruktur aplikasi dilarang dijalankan menggunakan server bawaan Werkzeug. Konfigurasi mutlak menggunakan Gunicorn bersama Gevent worker untuk mengatur stabilitas interkoneksi WebSocket dan HTTP secara paralel.

1. Eksekusi Gunicorn:
    ```bash 
    gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 run:amica_app_obj -b 0.0.0.0:5000
    ```

2. Penyelarasan Reverse Proxy (Caddy/Nginx):
    Administrator jaringan harus memastikan konfigurasi reverse proxy memiliki izin penuh untuk meng-upgrade header koneksi (Connection: Upgrade). Buffer pemrosesan wajib dinonaktifkan untuk menjaga akurasi latensi real-time (contoh: implementasi nilai flush_interval -1 pada Caddyfile).

3. Registrasi Systemd Service:
    Sangat direkomendasikan untuk mendaftarkan parameter Gunicorn ke dalam file eksekusi Systemd Service Linux. Ini menjamin aplikasi berstatus daemon persisten di latar belakang dan memiliki otoritas melakukan reboot otomatis bila terjadi kelebihan beban atau crash memori yang tidak terduga.

## Keamanan dan Pemeliharaan Berkala

*   Rate Limiting Dinamis: Mekanisme pembatasan ini dikendalikan oleh Redis. Endpoint publik dialokasikan kapasitas per menit, sementara endpoint otorisasi sensitif (seperti Forgot Password OTP atau titik masuk Login) dibekukan dalam batasan sangat ketat berbasis waktu (per jam) untuk mencegah penetrasi brute-force. Pemeriksa kualitas memegang hak memotong batasan ini lewat penyisipan token khusus X-Load-Test-Token selama sesi pengujian tekanan tinggi (Load Testing) menggunakan Locust.
*   Pembersihan Sampah Data Otomatis: Task scheduler internal (Flask-APScheduler) bertugas secara asinkron di latar belakang. Ia mengunci sistem pembersihan (scheduler.lock) dan menghapus permanen segala entitas tak terpakai, meliputi gambar maupun dokumen teks berstatus rejected (ditolak moderasi) yang melampaui usia 24 jam agar stabilitas ruang penyimpanan server terus terjaga.


## Dokumentasi Lanjutan

Untuk memahami sistem ini secara menyeluruh hingga ke tingkat mikroskopis, silakan pelajari pedoman teknis berikut yang telah dipisahkan agar lebih terstruktur:

*   [Spesifikasi Endpoint API & Kontrak WebSockets](API_CONTRACT.md)
*   [Panduan Operasional & Deployment Produksi Lanjutan](DEVELOPMENT_DEPLOYMENT.md)

---

## Proyek Terkait
* **[Amica Mobile](https://github.com/Rifyal05/Amica_Mobile)** — Repositori aplikasi *mobile* dan antarmuka pengguna Amica.
* **[Amica AI Engine](https://github.com/fajar123j/amica_ai_engine)** — Engine AI Amica
