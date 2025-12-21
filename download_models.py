import gdown
import os

models_to_download = [
    (
        "Gatekeeper (Image Classification)",
        "1b9KWdgMMCOWJ_Hm6-zoOSf1erVVEwbo8",
        "models_ml/image/gatekeeper.onnx"
    ),
    (
        "Specialist (Image Classification)",
        "1y0KbigAg1pnxVggPuYgfc_tOpL3BtEX8",
        "models_ml/image/specialist.onnx"
    ),
    (
        "Post Classification (Text)",
        "1UATj8Mg713cqBTd2sUpMxDYqRIBBKSdj",
        "models_ml/text/post/post_classifier.onnx"
    ),
    (
        "Feedback Sentiment (Text)",
        "1uMR5yVOjWkSzFdF2_mukzyUDWQ5vlYj2",
        "models_ml/text/feedback/feedback_sentiment.onnx"
    )
]

def download_all_models():
    print("Memulai proses pengunduhan model AI...")
    print("=" * 40)

    for name, file_id, dest_path in models_to_download:
        print(f"\n-> Mengunduh: {name}")
        
        output_dir = os.path.dirname(dest_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"   Direktori dibuat: {output_dir}")

        try:
            gdown.download(id=file_id, output=dest_path, quiet=False)
            print(f"Berhasil disimpan di: {dest_path}")
        except Exception as e:
            print(f"GAGAL mengunduh model. Error: {e}")
            print(f"Pastikan link Google Drive untuk '{name}' sudah di-set 'Anyone with the link can view'.")

    print("\n" + "=" * 40)
    print("Semua proses pengunduhan model selesai.")

if __name__ == "__main__":
    download_all_models()