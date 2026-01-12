ALEMBIC_EXEC="./venv/bin/alembic"

if [ ! -f "$ALEMBIC_EXEC" ]; then
    echo "ERROR: Executable Alembic tidak ditemukan di $ALEMBIC_EXEC"
    echo "Pastikan virtual environment sudah dibuat dan dependencies terinstall."
    exit 1
fi

echo "🚀 Memulai Proses Update Database (Migration)..."

ALEMBIC_RUNNING=true $ALEMBIC_EXEC upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrasi Berhasil! Database sudah up-to-date."
else
    echo "💀 Migrasi Gagal! Cek pesan error di atas."
    exit 1
fi