import gdown
import os

files_to_download = [
    (
        "Kamus Normalisasi (Global)",
        "1aEd78xkIJ2Q0lR4HvNf-2fjs7xKfzJXA",
        "kamus_normalisasi.csv"
    ),
    (
        "Post Vocab & IDF (Post Classification)",
        "1R1peNdi6QrBN9ccE5R3TuvpmwoVdC2Ol",
        "models_ml/text/post/post_vocab_idf.csv"
    ),
    (
        "Feedback Vocab (Sentiment Analysis)",
        "11Ul8z1J6iYgLtVVZz84ScGPR04lkJ-r_",
        "models_ml/text/feedback/feedback_vocab.csv"
    )
]

def download_vocab_dependencies():
    print("Memulai proses pengunduhan dependensi kosakata (CSV)...")
    print("=" * 50)

    for name, file_id, dest_path in files_to_download:
        print(f"\n-> Mengunduh: {name}")
        
        output_dir = os.path.dirname(dest_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            gdown.download(id=file_id, output=dest_path, quiet=False)
            print(f"   ✅ Berhasil disimpan di: {dest_path}")
        except Exception as e:
            print(f"   ❌ GAGAL mengunduh file. Periksa ID Google Drive Anda. Error: {e}")

    print("\n" + "=" * 50)
    print("Semua proses pengunduhan dependensi selesai.")

if __name__ == "__main__":
    download_vocab_dependencies()