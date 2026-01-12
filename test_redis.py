import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Coba konek
try:
    r = redis.from_url(os.getenv("REDIS_URL"))
    
    # Test Nulis
    r.set("amica_test", "Halo Redis!")
    
    # Test Baca
    value = r.get("amica_test")
    
    print(f"Sukses! Redis menjawab: {value}")
    
    # Bersihkan
    r.delete("amica_test")
    
except Exception as e:
    print(f"Gagal konek ke Redis: {str(e)}")
    print("Pastikan server redis sudah nyala (sudo systemctl start redis)")