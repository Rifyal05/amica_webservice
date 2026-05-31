# API_CONTRACT.md

Dokumen ini mendefinisikan spesifikasi API HTTP dan kontrak event WebSocket untuk sistem Amica. Seluruh komunikasi data menggunakan format JSON, kecuali untuk transmisi berkas (file upload) yang menggunakan `multipart/form-data`.

## Konfigurasi Dasar
*   Base URL: `http://<host>:5000`
*   Authentication: Bearer Token (JWT) dikirim melalui header `Authorization: Bearer <token>`.
*   Rate Limiting: Diatur secara dinamis per endpoint. Jika melampaui batas, sistem akan mengembalikan status `429 Too Many Requests`.

---

## 1. Modul Autentikasi (/api/auth)

### 1.1. Registrasi Akun
*   Endpoint: `POST /api/auth/register`
*   Rate Limit: 20 per jam
*   Payload (JSON):
    ```json
    {
        "email": "user@test.com",
        "password": "securepassword",
        "username": "usertest",
        "display_name": "User Test"
    }
    ```
*   Response (201 Created):
    ```json
    { "message": "User registered successfully" }
    ```

### 1.2. Autentikasi Dasar (Login)
*   Endpoint: `POST /api/auth/login`
*   Rate Limit: 5 per menit
*   Payload (JSON):
    ```json
    {
        "email": "user@test.com",
        "password": "securepassword"
    }
    ```
*   Response (200 OK - Jika PIN aktif):
    ```json
    {
        "status": "pin_required",
        "temp_id": "<uuid>"
    }
    ```
*   Response (200 OK - Jika sukses murni):
    ```json
    {
        "message": "Login successful",
        "access_token": "<jwt_access>",
        "refresh_token": "<jwt_refresh>",
        "user": {
            "id": "<uuid>",
            "display_name": "User Test",
            "username": "usertest",
            "role": "user",
            "is_verified": false
        }
    }
    ```

### 1.3. Verifikasi PIN Keamanan
*   Endpoint: `POST /api/auth/verify-pin`
*   Payload (JSON):
    ```json
    {
        "temp_id": "<uuid>",
        "pin": "123456"
    }
    ```
*   Response (200 OK): Mengembalikan objek token dan user yang sama seperti 1.2.

---

## 2. Modul Pengguna (/api/users)

### 2.1. Profil Pengguna
*   Endpoint: `GET /api/users/<user_id>`
*   Auth: Opsional (Jika diakses dengan JWT, sistem akan memperhitungkan status blokir dan *follow*).
*   Response (200 OK):
    ```json
    {
        "id": "<uuid>",
        "username": "usertest",
        "display_name": "User Test",
        "bio": "Halo dunia",
        "is_verified": false,
        "stats": {
            "posts": 10,
            "followers": 5,
            "following": 3
        },
        "status": {
            "is_me": false,
            "is_following": true,
            "is_blocked": false
        }
    }
    ```

### 2.2. Pembaruan Profil
*   Endpoint: `PUT /api/users/update`
*   Auth: Wajib (JWT)
*   Payload (multipart/form-data):
    *   `display_name` (string)
    *   `bio` (string)
    *   `username` (string)
    *   `avatar` (file - dilakukan pemindaian AI otomatis)
    *   `banner` (file - dilakukan pemindaian AI otomatis)
*   Response (200 OK):
    ```json
    {
        "message": "Profil berhasil diperbarui",
        "user": { ... }
    }
    ```
    *Catatan: Mengembalikan `400 Bad Request` jika AI mendeteksi konten gambar tidak aman.*

### 2.3. Manajemen Koneksi dan Pemblokiran
*   `POST /api/users/<user_id>/follow`: Mengikuti atau berhenti mengikuti pengguna (Toggle).
*   `POST /api/users/block/<user_id>`: Memblokir pengguna.
*   `POST /api/users/unblock/<user_id>`: Membuka blokir pengguna.
*   `GET /api/users/blocked_list`: Melihat daftar pengguna yang diblokir.

---

## 3. Modul Postingan dan Moderasi (/api/posts)

### 3.1. Buat Postingan Baru
*   Endpoint: `POST /api/posts/`
*   Auth: Wajib (JWT)
*   Payload (multipart/form-data):
    *   `caption` (string, maks 2500 karakter)
    *   `tags` (list of strings)
    *   `image` (file opsional)
*   Response (201 Created - Lolos Moderasi):
    ```json
    {
        "message": "Post created successfully",
        "post_id": "<uuid>",
        "status": "approved"
    }
    ```
*   Response (200 OK - Ditolak Moderasi AI Lokal):
    ```json
    {
        "message": "Postingan ditolak oleh moderasi otomatis...",
        "post_id": "<uuid>",
        "status": "rejected",
        "is_moderated": true,
        "moderation_details": {
            "text_status": "safe",
            "text_category": "Bersih",
            "image_status": "unsafe",
            "image_category": "nsfw"
        }
    }
    ```

### 3.2. Penarikan Data (Feed)
*   Endpoint: `GET /api/posts/?page=1&per_page=10&filter=latest`
*   Filter didukung: `latest`, `following`. Parameter `user_id` dapat ditambahkan untuk profil spesifik.
*   Response (200 OK):
    ```json
    {
        "posts": [ ...array_of_posts... ],
        "pagination": {
            "total_pages": 5,
            "current_page": 1,
            "has_next": true
        }
    }
    ```

### 3.3. Banding Moderasi (Appeals)
*   Endpoint: `POST /api/posts/<post_id>/appeal`
*   Payload (JSON):
    ```json
    {
        "justification": "Gambar ini adalah seni medis, bukan pelanggaran."
    }
    ```
*   Response (201 Created): Mengirimkan banding ke Dasbor Admin.

---

## 4. Modul SDQ - Psikologis Klinis (/api/sdq)

### 4.1. Pengiriman Kuesioner
*   Endpoint: `POST /api/sdq/submit`
*   Auth: Wajib (JWT)
*   Payload (JSON):
    ```json
    {
        "answers": [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0]
    }
    ```
    *Catatan: Harus presisi 25 integer yang merepresentasikan nilai 0, 1, atau 2.*
*   Response (200 OK):
    ```json
    {
        "scores": {
            "conduct": 3,
            "emotional": 5,
            "hyperactivity": 4,
            "peer": 2,
            "prosocial": 8,
            "total_difficulties_score": 14
        },
        "interpretation": {
            "total_score": 14,
            "total_level": "borderline",
            "overall_summary": { ... },
            "detailed_breakdown": [ ... ]
        }
    }
    ```

---

## 5. Modul Asisten AI Lokal (/api/bot)

### 5.1. Komunikasi Asisten AI (Streaming)
*   Endpoint: `POST /api/bot/send`
*   Auth: Wajib (JWT)
*   Payload (JSON):
    ```json
    {
        "message": "Apa itu cyberbullying?",
        "session_id": "<uuid opsional>"
    }
    ```
*   Response (200 OK - Text/Stream):
    Sistem merespons menggunakan `text/plain` stream (Chunked Transfer Encoding) agar tampilan antarmuka dapat merender balasan kata demi kata secara *real-time*.

---

## 6. Kontrak Real-time WebSockets (Socket.IO)

Koneksi klien ke server WebSocket diotorisasi secara langsung menggunakan token JWT yang diinjeksikan pada *query string* (contoh: `?token=<jwt>`).

### 6.1. Client-to-Server Events (Emit)

| Event Name | Payload (JSON) | Deskripsi |
| :--- | :--- | :--- |
| `join_chat` | `{"chat_id": "<uuid>"}` | Mendaftarkan sesi koneksi klien ke dalam *room* obrolan spesifik untuk mereset *unread_count*. |
| `send_message` | `{"chat_id": "<uuid>", "text": "halo", "type": "text", "reply_to_id": "<uuid_opsional>"}` | Mengirim pesan. Proses ini secara asinkron memicu *AI Toxicity Check* sebelum didistribusikan. |
| `message_received`| `{"message_id": "<uuid>", "chat_id": "<uuid>", "sender_id": "<uuid>"}` | Konfirmasi status pengiriman ganda (*delivered status/double tick*). |
| `mark_read` | `{"chat_id": "<uuid>"}` | Menandai seluruh pesan dari pihak lain sebagai telah dibaca (*read status/blue tick*). |
| `typing` | `{"chat_id": "<uuid>", "is_typing": true}` | Indikator *real-time typing*. |

### 6.2. Server-to-Client Events (Listen)

| Event Name | Payload (JSON) | Deskripsi |
| :--- | :--- | :--- |
| `new_message` | Objekt *Message* (id, chat_id, text, sender_id, dll) | Menerima pesan baru secara langsung. Jika pesan masuk dalam radar toksik dan penerima mengaktifkan Moderasi AI, pesan ini hanya akan terpancar ke pengirim (AI Ghosting). |
| `inbox_update` | `{"chat_id": "<uuid>", "last_message": "...", "unread_count": 1}` | Pembaruan data *list inbox* pada menu beranda *chat*. |
| `moderation_blocked`| `{"chat_id": "<uuid>", "user_id": "<uuid>"}` | Sinyal peringatan bahwa batas toksisitas tercapai (10 kali) dan otomatis menghentikan akses ruangan obrolan tersebut. |
| `message_delivered`| `{"message_id": "<uuid>"}` | Pengakuan bahwa lawan bicara telah menerima pesan. |

---

## 7. Modul Obrolan dan Grup API (/api/chats)

Selain WebSocket, Amica menyediakan antarmuka HTTP RESTful untuk operasi asinkron yang berkaitan dengan pembuatan dan penarikan data obrolan.

### 7.1. Penarikan Daftar Kotak Masuk (Inbox)
*   Endpoint: `GET /api/chats/inbox`
*   Auth: Wajib (JWT)
*   Response (200 OK):
    ```json
    [
        {
            "id": "<chat_uuid>",
            "is_group": false,
            "name": "User Test",
            "target_user_id": "<target_uuid>",
            "image_url": "http://localhost:5000/static/uploads/avatar.jpg",
            "last_message_text": "Halo, apa kabar?",
            "last_message_time": "2026-06-01T12:00:00Z",
            "unread_count": 2,
            "is_hidden": false,
            "is_blocked_by_me": false
        }
    ]
    ```

### 7.2. Inisiasi Obrolan Personal (DM)
*   Endpoint: `POST /api/chats/get-or-create/<target_user_id>`
*   Auth: Wajib (JWT)
*   Deskripsi: Mencari riwayat obrolan dengan pengguna spesifik. Jika belum ada, sistem akan membuat entitas obrolan baru.
*   Response (200/201):
    ```json
    {
        "chat_id": "<chat_uuid>",
        "success": true
    }
    ```

### 7.3. Pembuatan Grup Obrolan
*   Endpoint: `POST /api/chats/group/create`
*   Rate Limit: 5 per jam
*   Payload (multipart/form-data):
    *   `name` (string)
    *   `members` (JSON string array, contoh: `["<uuid_1>", "<uuid_2>"]`)
    *   `allow_invites` (boolean string, "true"/"false")
    *   `image` (file opsional)
*   Response (201 Created):
    ```json
    {
        "success": true,
        "chat_id": "<group_chat_uuid>"
    }
    ```

### 7.4. Pembangkitan Tautan Undangan (Invite Link)
*   Endpoint: `POST /api/chats/group/<chat_id>/invite-link`
*   Payload (JSON):
    ```json
    {
        "type": "24h" 
    }
    ```
    *Keterangan tipe: "24h" (kedaluwarsa dalam 24 jam), "1x" (sekali pakai), null (permanen).*
*   Response (200 OK):
    ```json
    {
        "url": "http://localhost:5000/join/<token_unik>"
    }
    ```

---

## 8. Modul Verifikasi Profesional Psikolog (/api/pro)

Modul ini menangani pengajuan verifikasi dari tenaga profesional dengan implementasi enkripsi asimetris di level penyimpanan (Fernet).

### 8.1. Pengajuan Verifikasi
*   Endpoint: `POST /api/pro/apply`
*   Rate Limit: 3 per jam
*   Payload (multipart/form-data):
    *   `full_name` (string, berserta gelar)
    *   `str_number` (string, Nomor Surat Tanda Registrasi)
    *   `province` (string)
    *   `address` (string)
    *   `schedule` (string)
    *   `str_image` (file, enkripsi instan saat diunggah)
    *   `ktp_image` (file, enkripsi instan saat diunggah)
    *   `selfie_image` (file, enkripsi instan saat diunggah)
*   Response (201 Created):
    ```json
    { "message": "Permohonan verifikasi terkirim" }
    ```

### 8.2. Pengecekan Status Profesional
*   Endpoint: `GET /api/pro/status`
*   Auth: Wajib (JWT)
*   Response (200 OK):
    ```json
    {
        "status": "pending",
        "applied_at": "2026-06-01T10:00:00Z"
    }
    ```

---

## 9. Modul Dasbor Manajemen Admin (/admin)

Modul administratif yang diproteksi ketat menggunakan JWT role-based (Role `admin` atau `owner`).

### 9.1. Laporan dan Penindakan (Moderation & Quarantine)
*   Endpoint Penarikan Laporan: `GET /admin/reports?type=post` (type: post, comment, user)
*   Endpoint Eksekusi Karantina Post: `POST /admin/reports/action/quarantine-post`
*   Payload (JSON):
    ```json
    {
        "target_id": "<post_uuid>",
        "reason": "Mengandung unsur kekerasan visual."
    }
    ```
*   Deskripsi: Memindahkan gambar ke `static/quarantine/`, menghapus data gambar dari tabel `Post`, dan mencatatnya ke tabel `QuarantinedItem`.

### 9.2. Pembersihan Akun Bermasalah (Sanitize User)
*   Endpoint: `POST /admin/reports/action/sanitize-user`
*   Payload (JSON):
    ```json
    {
        "target_id": "<user_uuid>",
        "fields": ["avatar", "banner", "bio", "display_name"],
        "reason": "Profil memuat atribut tidak senonoh"
    }
    ```
*   Response (200 OK): Mengembalikan status sukses beserta detail lapangan (fields) yang berhasil diatur ulang (reset) oleh sistem.

### 9.3. Pemrosesan Banding Moderasi (Appeals)
*   Endpoint Penarikan: `GET /admin/appeals`
*   Endpoint Eksekusi: `POST /admin/appeals/<appeal_id>/action`
*   Payload (JSON):
    ```json
    {
        "action": "approved",
        "admin_note": "Kesalahan deteksi AI, postingan aman untuk diterbitkan kembali."
    }
    ```
    *Keterangan action: "approved" (pemulihan dari karantina), "rejected" (penghapusan permanen dari server).*

### 9.4. Manajemen Verifikasi Profesional
*   Penarikan Daftar Tunggu: `GET /api/admin/pro/pending`
*   Persetujuan Dokumen: `POST /api/admin/pro/approve/<pro_id>`
*   Deskripsi: Menyetujui pendaftaran, menghapus berkas KTP dan Selfie dari penyimpanan demi privasi (Hanya menyimpan STR), dan mengubah status *user_verified* menjadi `True`.

### 9.5. Operasi RAG dan Sinkronisasi AI Lokal (AI Lab)
*   Ekstraksi Auto-Ingest: `POST /admin/ai/ingest-auto`
    *   Sistem membaca artikel publik yang belum diindeks, mengirimkannya ke *Groq LLM* untuk diringkas (Q&A/Poin Kunci), lalu menyimpannya ke `dataset_rag_final.jsonl`.
*   Sinkronisasi ke Engine Lokal: `POST /admin/ai/sync-local`
    *   Membaca berkas `jsonl` dan menyuntikkannya ke *Local Vector Database* pada port AI Engine via API `/v1/ingest`.
*   Uji Eksekusi Benchmark RAG: `POST /admin/ai/run-benchmark`
    *   Menjalankan pengujian Mean Reciprocal Rank (MRR) untuk memastikan efektivitas penarikan mesin pencari referensi.

### 9.6. Catatan Aktivitas Audit (Audit Logs)
*   Endpoint Penarikan: `GET /admin/activity-logs?filter=14d`
*   Endpoint Pengembalian Aksi (Revert): `POST /admin/activity-logs/<log_id>/revert`
*   Deskripsi: Hanya entitas `owner` yang berwenang mengeksekusi metode *Revert*. Sistem akan membatalkan status atau perubahan spesifik dari *admin* (seperti Suspend atau modifikasi profil) kembali ke nilai *old_value* yang terekam.

## 10. Modul Artikel (/api/articles & /admin/articles)

Modul ini menangani konten edukasi yang menjadi sumber pengetahuan (Knowledge Base) bagi sistem RAG dan pengguna umum.

### 10.1. Tarik Daftar Artikel Publik
*   Endpoint: `GET /api/articles?page=1&limit=10&q=bullying&category=edukasi`
*   Rate Limit: 30 per menit
*   Response (200 OK):
    ```json
    {
        "articles": [
            {
                "id": 1,
                "title": "Memahami Cyberbullying",
                "category": "Edukasi",
                "author": "Lensa Team",
                "image_url": "art_abc123.jpg",
                "read_time": 5,
                "tags": ["cyberbullying", "internet"]
            }
        ],
        "pagination": {
            "total": 50,
            "pages": 5,
            "current_page": 1,
            "has_next": true,
            "has_prev": false
        }
    }
    ```

### 10.2. Pencarian Artikel via URL (Lookup)
*   Endpoint: `POST /api/discover/articles/lookup`
*   Payload (JSON):
    ```json
    {
        "url": "https://sumber-referensi.com/artikel-bullying"
    }
    ```
*   Response (200 OK): Mengembalikan status boolean `found` dan detail artikel jika URL sudah pernah diindeks oleh sistem.

### 10.3. Manajemen Artikel (Khusus Admin)
*   Endpoint Pembuatan: `POST /admin/articles/`
*   Payload (multipart/form-data): `title`, `content`, `category`, `tags`, `source_name`, `source_url`, `is_featured`, dan `image`.
*   Endpoint Pembaruan: `POST /admin/articles/<article_id>`
*   Endpoint Penghapusan: `DELETE /admin/articles/<article_id>`

---

## 11. Modul Eksplorasi dan Pencarian (/api/discover)

Modul ini memberikan rekomendasi pintar dan fitur pencarian global.

### 11.1. Dasbor Discover Utama
*   Endpoint: `GET /api/discover/`
*   Auth: Opsional (JWT)
*   Response (200 OK): Mengembalikan daftar trending tags (dihitung secara cerdas menggunakan Redis cache berdasarkan aktivitas 30 hari terakhir), rekomendasi pengguna terverifikasi, dan cuplikan artikel terbaru.

### 11.2. Pencarian Global (Search)
*   Endpoint: `GET /api/discover/search?q=kesehatan`
*   Rate Limit: 10 per menit
*   Response (200 OK):
    ```json
    {
        "users": [ ... ],
        "posts": [ ... ],
        "articles": [ ... ]
    }
    ```
    *Catatan: Algoritma pencarian memprioritaskan pencocokan nama pengguna, caption postingan, judul artikel, dan tag spesifik.*

---

## 12. Modul Komentar (/api/comments)

### 12.1. Tambah Komentar Baru
*   Endpoint: `POST /api/comments/<post_id>/comments`
*   Auth: Wajib (JWT)
*   Payload (JSON):
    ```json
    {
        "text": "Terima kasih atas informasinya!",
        "parent_comment_id": null
    }
    ```
*   Deskripsi: Sistem langsung melewatkan `text` ke layanan `post_classifier.onnx`. Jika diklasifikasikan sebagai teks berbahaya, komentar ditolak dan dicatat di database dengan status `rejected`.
*   Response (201 Created - Lolos Moderasi):
    ```json
    {
        "message": "Comment created successfully",
        "comment_id": "<uuid>",
        "status": "approved"
    }
    ```
*   Response (403 Forbidden - Gagal Moderasi):
    ```json
    {
        "message": "Komentar melanggar pedoman komunitas.",
        "status": "rejected",
        "reason": "Toxic"
    }
    ```

### 12.2. Tarik Data Komentar
*   Endpoint: `GET /api/comments/<post_id>/comments`
*   Response (200 OK): Mengembalikan representasi JSON hierarkis rekursif (komentar utama beserta balasan di dalam properti `replies`). Sistem otomatis menyaring komentar yang berstatus selain `approved`.

---

## 13. Modul Pengiriman Laporan & Umpan Balik

### 13.1. Pengiriman Laporan Pelanggaran (Report)
*   Endpoint: `POST /api/report`
*   Auth: Wajib (JWT)
*   Payload (JSON):
    ```json
    {
        "target_type": "post",
        "target_id": "<uuid_post_atau_comment_atau_user>",
        "reason": "Mengandung informasi yang menyesatkan."
    }
    ```
*   Response (201 Created): Laporan masuk ke antrean Dasbor Admin (`pending`).

### 13.2. Pengiriman Umpan Balik (Feedback)
*   Endpoint: `POST /api/feedback/`
*   Auth: Wajib (JWT)
*   Payload (JSON):
    ```json
    {
        "feedback_text": "Aplikasi ini sangat membantu saya. UI-nya bagus!"
    }
    ```
*   Deskripsi: Memicu `feedback_sentiment.onnx` untuk mengidentifikasi apakah umpan balik ini bersifat `positive` atau `negative` sebelum disimpan.
*   Response (201 Created):
    ```json
    {
        "message": "Feedback submitted successfully. Thank you!",
        "sentiment_detected": "positive"
    }
    ```

---

## 14. Modul Notifikasi (/api/notifications)

### 14.1. Tarik Riwayat Notifikasi
*   Endpoint: `GET /api/notifications/`
*   Auth: Wajib (JWT)
*   Response (200 OK):
    ```json
    [
        {
            "id": "<uuid>",
            "sender_name": "AMICA",
            "type": "post_rejected",
            "text": "Postingan Anda ditahan karena melanggar pedoman komunitas.",
            "is_read": false,
            "created_at": "2026-06-01T15:00:00Z"
        }
    ]
    ```

### 14.2. Tandai Semua Dibaca
*   Endpoint: `POST /api/notifications/read-all`
*   Auth: Wajib (JWT)
*   Response (200 OK): Mengubah semua status `is_read` milik pengguna menjadi `true`.

---

## 15. Modul Reset Password & Keamanan (/api/password)

### 15.1. Permintaan OTP Lupa Sandi
*   Endpoint: `POST /api/password/forgot`
*   Rate Limit: 5 per jam
*   Payload (JSON):
    ```json
    {
        "email": "user@test.com"
    }
    ```
*   Deskripsi: Sistem membangkitkan 6 digit OTP acak, menyimpannya di entitas User dengan masa berlaku 15 menit, lalu mengirimkannya via utas `Flask-Mail` secara asinkron.

### 15.2. Verifikasi OTP
*   Endpoint: `POST /api/password/verify-otp`
*   Rate Limit: 15 per jam
*   Payload (JSON):
    ```json
    {
        "email": "user@test.com",
        "otp": "123456"
    }
    ```
*   Response (200 OK / 400 Bad Request): Melakukan validasi kesesuaian sandi sekali pakai dan batas waktu kedaluwarsa.

### 15.3. Finalisasi Pengubahan Sandi
*   Endpoint: `POST /api/password/reset`
*   Rate Limit: 3 per jam
*   Payload (JSON):
    ```json
    {
        "email": "user@test.com",
        "otp": "123456",
        "new_password": "newsecurepassword123"
    }
    ```
*   Deskripsi: Memeriksa kembali OTP, menghancurkan kolom OTP di tabel pengguna, dan menimpa *Bcrypt hash* yang lama dengan sandi baru.
