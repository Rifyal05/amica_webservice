echo "1. Memulai Proses Migrasi Alembic"

ALEMBIC_EXEC="./venv/bin/alembic"

if [ ! -f "$ALEMBIC_EXEC" ]; then
    echo "ERROR: Executable Alembic tidak ditemukan di $ALEMBIC_EXEC"
    echo "Pastikan Anda sudah menginstal Alembic: pip install alembic"
    exit 1
fi

echo "Mengatur baseline database..."
ALEMBIC_RUNNING=true $ALEMBIC_EXEC stamp head

echo "Mencari perubahan model dan membuat skrip migrasi..."
ALEMBIC_RUNNING=true $ALEMBIC_EXEC revision --autogenerate -m "auto_migration_$(date +%Y%m%d%H%M)"

echo "Menerapkan semua migrasi yang tertunda..."
ALEMBIC_RUNNING=true $ALEMBIC_EXEC upgrade head

echo "Migrasi Selesai!"