import os
import json
import time
import requests
import redis
from datetime import datetime, timezone
from groq import Groq, RateLimitError
from dotenv import load_dotenv
from app.extensions import db
from app.models import Article

load_dotenv()

class GroqKeyManager:
    def __init__(self):
        keys_str = os.environ.get("GROQ_API_KEYS", "")
        self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        self.current_index = 0

    def get_client(self):
        if not self.keys:
            return None
        return Groq(api_key=self.keys[self.current_index])

    def rotate_key(self):
        if len(self.keys) > 1:
            self.current_index = (self.current_index + 1) % len(self.keys)
            return True if self.current_index != 0 else False
        return False

key_manager = GroqKeyManager()

class AIService:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RAG_DIR = os.path.join(BASE_DIR, 'static', 'uploads', 'rag')
    JSONL_FILENAME = 'dataset_rag_final.jsonl'
    JSONL_PATH = os.path.join(RAG_DIR, JSONL_FILENAME)

    @classmethod
    def _ensure_directory(cls):
        if not os.path.exists(cls.RAG_DIR):
            os.makedirs(cls.RAG_DIR)

    @classmethod
    def get_stats(cls):
        db.session.expire_all()
        total = Article.query.count()
        ingested = Article.query.filter(Article.is_ingested == True).count()
        remaining = Article.query.filter((Article.is_ingested == False) | (Article.is_ingested == None)).count()
        return {"total": total, "ingested": ingested, "remaining": remaining}

    @staticmethod
    def process_article_with_ai(article, client):
        system_prompt = "Kamu adalah Data Curator untuk RAG Gemma 3 1B. Ekstrak informasi mendalam menjadi format Markdown terstruktur."
        user_prompt = f"""
        DATA:
        Judul: {article.title}
        Isi: {article.content[:25000]}
        
        TUGAS JSON:
        1. "summary": Ringkasan komprehensif 2 paragraf.
        2. "key_points": 7 poin kunci sari artikel.
        3. "faq": 10 pasang Q&A detail.
        """
        try:
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=4096
            )
            return json.loads(completion.choices[0].message.content)
        except RateLimitError:
            raise
        except Exception:
            return None

    @classmethod
    def save_to_jsonl(cls, enriched_data, article):
        cls._ensure_directory()
        src_url = article.source_url if article.source_url else ""
        
        faq_text = "\n".join([f"- {item}" for item in enriched_data.get('faq', [])])
        points_text = "\n".join([f"* {kp}" for kp in enriched_data.get('key_points', [])])
        
        core_content = f"# {article.title}\nKategori: {article.category}\n\n## Ringkasan Komprehensif\n{enriched_data.get('summary', '')}\n\n## Poin Utama\n{points_text}\n\n## FAQ\n{faq_text}"
        cls._write_line(core_content, article, src_url, "knowledge_core")

        words = article.content.split()
        chunk_size = 800
        for i in range(0, len(words), chunk_size):
            segment = " ".join(words[i:i + chunk_size])
            detail = f"# {article.title}\n## Detail Referensi (Bagian {i//chunk_size + 1})\n{segment}"
            cls._write_line(detail, article, src_url, f"reference_part_{i//chunk_size + 1}")

    @classmethod
    def _write_line(cls, content, article, url, chunk_type):
        data = {
            "page_content": content,
            "metadata": {
                "article_id": article.id,
                "title": article.title,
                "source_url": url,
                "category": article.category,
                "chunk_type": chunk_type,
                "ingested_at": datetime.now(timezone.utc).isoformat()
            }
        }
        with open(cls.JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    @classmethod
    def run_smart_ingest(cls, batch_size=1):
        db.session.expire_all()
        articles = Article.query.filter((Article.is_ingested == False) | (Article.is_ingested == None)).limit(batch_size).all()
        if not articles:
            return {"status": "done", "processed": 0, "remaining": 0, "total_ingested": cls.get_stats()['ingested']}
        processed_count = 0
        client = key_manager.get_client()
        for art in articles:
            try:
                enriched = cls.process_article_with_ai(art, client)
                if enriched:
                    cls.save_to_jsonl(enriched, art)
                    art.is_ingested = True
                    art.ingested_at = datetime.now(timezone.utc)
                    db.session.commit()
                    processed_count += 1
                    time.sleep(2)
            except RateLimitError:
                if key_manager.rotate_key():
                    return {"status": "partial", "processed": processed_count, "remaining": cls.get_stats()['remaining'], "total_ingested": cls.get_stats()['ingested'], "message": "Rotating Key"}
                else:
                    return {"status": "rate_limited", "processed": processed_count, "remaining": cls.get_stats()['remaining'], "total_ingested": cls.get_stats()['ingested']}
            except Exception:
                continue
        stats = cls.get_stats()
        return {"status": "partial" if stats['remaining'] > 0 else "done", "processed": processed_count, "remaining": stats['remaining'], "total_ingested": stats['ingested']}

    @classmethod
    def get_rag_preview(cls, limit=50):
        if not os.path.exists(cls.JSONL_PATH): return []
        data = []
        try:
            with open(cls.JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip(): data.append(json.loads(line))
            return data[-limit:][::-1]
        except: return []

    @classmethod
    def chat_with_local_engine(cls, message, history_text=""):
        url = f"{os.getenv('LOCAL_ENGINE_URL', 'http://127.0.0.1:7860')}/v1/chat/stream"
        headers = {"X-Amica-Key": os.getenv("AI_ENGINE_KEY"), "Content-Type": "application/json"}
        payload = {"message": message, "history": history_text}
        try:
            response = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=None):
                    if chunk: yield chunk.decode('utf-8')
            else:
                yield f"[STATUS:ERROR] Engine Lokal ({response.status_code})"
        except Exception as e:
            yield f"[STATUS:ERROR] Koneksi Terputus: {str(e)}"

    @classmethod
    def sync_to_local_engine(cls, articles_data):
        url = f"{os.getenv('LOCAL_ENGINE_URL', 'http://127.0.0.1:7860')}/v1/ingest"
        headers = {"X-Amica-Key": os.getenv("AI_ENGINE_KEY")}
        try:
            res = requests.post(url, json={"articles": articles_data}, headers=headers, timeout=60)
            return res.json()
        except:
            return {"status": "error"}

    @classmethod
    def sync_all_to_local(cls):
        if not os.path.exists(cls.JSONL_PATH):
            return {"status": "error", "message": "File JSONL tidak ditemukan."}

        articles_to_sync = []
        try:
            with open(cls.JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    
                    raw_data = json.loads(line)
                    meta = raw_data.get("metadata", {})
                    
                    articles_to_sync.append({
                        "id": meta.get("article_id"),
                        "title": meta.get("title"),
                        "content": raw_data.get("page_content"),
                        "chunk_type": meta.get("chunk_type"), 
                        "source_url": meta.get("source_url")
                    })
            
            if articles_to_sync:
                return cls.sync_to_local_engine(articles_to_sync)
            
            return {"status": "error", "message": "File JSONL kosong."}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}