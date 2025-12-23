import os
import json
import time
import requests
from datetime import datetime, timezone
from groq import Groq, RateLimitError
from flask import current_app
from app.extensions import db
from app.models import Article
from gradio_client import Client, handle_file
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
            if self.current_index == 0:
                return False
            return True
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
    def sync_to_cloud(cls):
        if not os.path.exists(cls.JSONL_PATH):
            return {"status": "error", "message": "Dataset tidak ditemukan lokal"}

        hf_url = current_app.config.get('HF_SPACE_URL')
        api_key = current_app.config.get('AMICA_API_KEY')

        if not hf_url or not api_key:
            return {"status": "error", "message": "Konfigurasi HF Space/API Key hilang"}

        try:

            endpoint = hf_url.rstrip('/') + "/chat"
            client = Client(endpoint)

            result = client.predict(
                file=handle_file(cls.JSONL_PATH),
                token=api_key,
                api_name="/ui_upload"
            )
            
            return {
                "status": "success", 
                "message": "Sinkronisasi berhasil!", 
                "details": str(result)
            }

        except Exception as e:
            print(f"Sync Error: {str(e)}")
            return {"status": "error", "message": f"Gagal Sync: {str(e)}"}