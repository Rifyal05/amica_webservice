import gdown
import os

dependencies_to_download = [
    (
        "TF-IDF Vectorizer (for Post Classification)",
        "1UATj8Mg713cqBTd2sUpMxDYqRIBBKSdj",
        "models_ml/text/post/tfidf_vectorizer.joblib"
    ),
    (
        "Keras Tokenizer (for Feedback Sentiment)",
        "1uMR5yVOjWkSzFdF2_mukzyUDWQ5vlYj2",
        "models_ml/text/feedback/keras_tokenizer.joblib"
    )
]

def download_all_dependencies():
    print("Memulai proses pengunduhan dependensi model...")
    print("=" * 40)

    for name, file_id, dest_path in dependencies_to_download:
        print(f"\n-> Mengunduh: {name}")
        
        output_dir = os.path.dirname(dest_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"   Direktori dibuat: {output_dir}")

        try:
            gdown.download(id=file_id, output=dest_path, quiet=False)
            print(f"   ✅ Berhasil disimpan di: {dest_path}")
        except Exception as e:
            print(f"   ❌ GAGAL mengunduh. Error: {e}")

    print("\n" + "=" * 40)
    print("Semua proses pengunduhan dependensi selesai.")

if __name__ == "__main__":
    download_all_dependencies()