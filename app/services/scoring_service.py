import time
import requests
import os
import json
import re 
import random 
from ..models import db, RAGTestCase, RAGBenchmarkResult
from .ai_service import AIService

class ScoringService:
    
    @classmethod
    def generate_test_cases_from_jsonl(cls, limit=20, target_article_id=None):
        jsonl_path = AIService.JSONL_PATH
        if not os.path.exists(jsonl_path):
            return {"status": "error", "message": "Dataset tidak ditemukan."}

        candidates = []
        article_found = False

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    meta = data.get("metadata", {})
                    current_id = str(meta.get('article_id'))
                    
                    if target_article_id and current_id != str(target_article_id):
                        continue
                        
                    article_found = True

                    if meta.get("chunk_type") == "knowledge_core":
                        content = data.get("page_content", "")
                        if "## FAQ" in content:
                            faq_section = content.split("## FAQ")[1]
                            matches = re.findall(r"Q:\s*(.*?)\n+A:\s*(.*?)(?=\n+Q:|$)", faq_section, re.DOTALL)
                            
                            for q, a in matches:
                                if q.strip() and a.strip():
                                    candidates.append({
                                        "question": q.strip(),
                                        "expected_answer": a.strip(),
                                        "target_article_id": current_id
                                    })
                except: continue
        
        if target_article_id and not article_found:
             return {"status": "warning", "message": f"Artikel ID {target_article_id} tidak ditemukan."}

        random.shuffle(candidates)
        final_cases = candidates[:limit]
        
        db.session.query(RAGTestCase).delete()
        
        for case in final_cases:
            new_case = RAGTestCase(
                question=case['question'], # type: ignore
                expected_answer=case['expected_answer'], # type: ignore
                target_article_id=case['target_article_id'] # type: ignore
            )
            db.session.add(new_case)
        
        db.session.commit()
        return {"status": "success", "count": len(final_cases), "message": f"{len(final_cases)} soal berhasil dibuat secara acak!"}

    @staticmethod
    def calculate_mrr(query, target_id):
        if not target_id: return 0.0, []
        url = f"{os.getenv('LOCAL_ENGINE_URL')}/v1/search"
        headers = {"X-Amica-Key": os.getenv("AI_ENGINE_KEY")}
        
        try:
            res = requests.post(url, json={"query": query}, headers=headers, timeout=5).json()
            results = res.get('results', [])
            found_ids = [str(r['article_id']) for r in results]
            target_str = str(target_id)
            
            if target_str in found_ids:
                rank = found_ids.index(target_str) + 1
                return 1.0 / rank, found_ids
            
            return 0.0, found_ids
        except:
            return 0.0, []

    @staticmethod
    def get_llama_judge_score(question, expected, actual):
        url = f"{os.getenv('LOCAL_ENGINE_URL')}/v1/audit/grade"
        headers = {"X-Amica-Key": os.getenv("AI_ENGINE_KEY")}
        payload = {
            "question": question,
            "expected": expected,
            "actual": actual
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=45)
            if res.status_code == 200:
                data = res.json()
                return float(data.get('score', 0)), data.get('reason', '')
        except: pass
        return 0.0, "Audit Failed"

    @classmethod
    def run_benchmark(cls, limit=None, include_llm=False):
        query = RAGTestCase.query
        if limit:
            test_cases = query.limit(limit).all()
        else:
            test_cases = query.all()

        if not test_cases:
            return {"status": "empty", "message": "Belum ada soal ujian. Generate dulu!"}

        db.session.query(RAGBenchmarkResult).delete()
        db.session.commit()

        summary = {"total": 0, "avg_mrr": 0.0, "avg_llama": 0.0, "avg_latency": 0.0}

        for case in test_cases:
            start_t = time.time()
            
            mrr, retrieved_ids = cls.calculate_mrr(case.question, case.target_article_id)

            ai_response = "Evaluasi LLM Dinonaktifkan"
            llama_score = 0.0
            llama_reason = "Hanya mengecek MRR."

            if include_llm:
                ai_response = ""
                for chunk in AIService.chat_with_local_engine(case.question, ""):
                    if not chunk.startswith("[STATUS:"): ai_response += chunk
                
                llama_score, llama_reason = cls.get_llama_judge_score(case.question, case.expected_answer, ai_response)
            
            latency = time.time() - start_t
            
            res = RAGBenchmarkResult(
                test_case_id=case.id, # type: ignore
                ai_answer=ai_response, # type: ignore
                llama_score=llama_score, # type: ignore
                llama_reason=llama_reason, # type: ignore
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