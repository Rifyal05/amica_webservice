import time
import requests
import os
import json
import re 
from ..models import db, RAGTestCase, RAGBenchmarkResult
from .ai_service import AIService

class ScoringService:
    
    @classmethod
    def generate_test_cases_from_jsonl(cls, limit=20):
        """
        Membaca dataset_rag_final.jsonl dan mengambil FAQ (Format Q: ... A: ...)
        """
        jsonl_path = AIService.JSONL_PATH
        if not os.path.exists(jsonl_path):
            return {"status": "error", "message": "Dataset tidak ditemukan."}

        db.session.query(RAGTestCase).delete()
        db.session.commit()
        
        count = 0
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if count >= limit: break
                if not line.strip(): continue
                
                try:
                    data = json.loads(line)
                    meta = data.get("metadata", {})
                    
                    if meta.get("chunk_type") != "knowledge_core":
                        continue

                    content = data.get("page_content", "")
                    
                    if "## FAQ" in content:
                        faq_section = content.split("## FAQ")[1]

                        matches = re.findall(r"Q:\s*(.*?)\n+A:\s*(.*?)(?=\n+Q:|$)", faq_section, re.DOTALL)
                        
                        for q, a in matches:
                            if count >= limit: break
                            
                            clean_q = q.strip()
                            clean_a = a.strip()
                            
                            if clean_q and clean_a:
                                new_case = RAGTestCase(
                                    question=clean_q,# type: ignore
                                    expected_answer=clean_a,# type: ignore
                                    target_article_id=str(meta.get('article_id'))# type: ignore
                                )
                                db.session.add(new_case)
                                count += 1
                except Exception as e:
                    print(f"Error parsing line: {e}")
                    continue
        
        db.session.commit()
        return {"status": "success", "count": count, "message": f"{count} soal ujian berhasil dibuat dari FAQ!"}

    @staticmethod
    def calculate_mrr(query, target_id):
        if not target_id: return 0.0, []
        url = f"{os.getenv('LOCAL_ENGINE_URL')}/v1/search"
        headers = {"X-Amica-Key": os.getenv("AI_ENGINE_KEY")}
        
        try:
            res = requests.post(url, json={"query": query}, headers=headers).json()
            results = res.get('results', [])
            found_ids = [str(r['article_id']) for r in results]
            
            try:
                rank = found_ids.index(str(target_id)) + 1
                return 1.0 / rank, found_ids
            except ValueError:
                return 0.0, found_ids
        except:
            return 0.0, []

    @staticmethod
    def get_llama_judge_score(question, expected, actual):
        url = f"{os.getenv('LOCAL_ENGINE_URL')}/v1/audit/grade"
        headers = {"X-Amica-Key": os.getenv("AI_ENGINE_KEY")}
        payload = {
            "question": f"Pertanyaan: {question}\nKunci Jawaban: {expected}\nJawaban AI: {actual}",
            "context": expected
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return float(data.get('score', 0)), data.get('reason', '')
        except: pass
        return 0.0, "Audit Failed"

    @classmethod
    def run_benchmark(cls):
        test_cases = RAGTestCase.query.all()
        if not test_cases:
            return {"status": "empty", "message": "Belum ada soal. Jalankan 'Generate Test Cases' dulu."}
        
        summary = {"total": 0, "avg_mrr": 0.0, "avg_llama": 0.0, "avg_latency": 0.0}
        
        db.session.query(RAGBenchmarkResult).delete()
        db.session.commit() # Commit delete dulu
        
        for case in test_cases:
            start_t = time.time()
            
            # A. Hitung MRR
            mrr, retrieved_ids = cls.calculate_mrr(case.question, case.target_article_id)

            # B. Generate Jawaban
            ai_response = ""
            for chunk in AIService.chat_with_local_engine(case.question, ""):
                if not chunk.startswith("[STATUS:"): ai_response += chunk
            
            latency = time.time() - start_t
            
            # C. Judge
            llama_score, llama_reason = cls.get_llama_judge_score(case.question, case.expected_answer, ai_response)

            res = RAGBenchmarkResult(
                test_case_id=case.id,# type: ignore
                ai_answer=ai_response,# type: ignore
                llama_score=llama_score,# type: ignore
                llama_reason=llama_reason,# type: ignore
                mrr_score=mrr, # type: ignore
                retrieved_ids=retrieved_ids, # type: ignore
                latency=latency # type: ignore
            )
            db.session.add(res)
            
            summary["total"] += 1
            summary["avg_mrr"] += mrr
            summary["avg_llama"] += llama_score
            summary["avg_latency"] += latency

        if summary["total"] > 0:
            summary["avg_mrr"] /= summary["total"]
            summary["avg_llama"] /= summary["total"]
            summary["avg_latency"] /= summary["total"]
            
        db.session.commit()
        return {"status": "success", "summary": summary}