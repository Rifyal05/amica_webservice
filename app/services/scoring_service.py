import time
import requests
import os
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from ..models import db, RAGTestCase, RAGBenchmarkResult
from .ai_service import AIService

class ScoringService:
    @staticmethod
    def calculate_math_score(reference, hypothesis):
        ref_tokens = reference.lower().split()
        hyp_tokens = hypothesis.lower().split()
        
        # BLEU Score
        cc = SmoothingFunction()
        bleu = sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=cc.method1)
        
        # ROUGE Score
        scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        scores = scorer.score(reference, hypothesis)
        rouge = scores['rougeL'].fmeasure
        
        return (bleu + rouge) / 2 

    @staticmethod
    def get_llama_judge_score(question, expected, actual):
        url = f"{os.getenv('LOCAL_ENGINE_URL')}/v1/audit/grade"
        headers = {"X-Amica-Key": os.getenv("AI_ENGINE_KEY")}
        payload = {
            "question": question,
            "context": expected, 
            "answer": actual
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return float(data.get('score', 0)), data.get('reason', 'No reason provided')
        except:
            pass
        return 0.0, "Audit Failed"
    
    

    @classmethod
    def run_benchmark(cls):
        test_cases = RAGTestCase.query.all()
        if not test_cases:
            return {"status": "empty", "message": "Belum ada soal ujian (Test Cases)."}
        
        summary = {"total": 0, "avg_bleu": 0.0, "avg_llama": 0.0, "avg_latency": 0.0}
        
        # Hapus hasil lama biar bersih (Opsional)
        db.session.query(RAGBenchmarkResult).delete()
        db.session.commit()

        for case in test_cases:
            start_t = time.time()
            
            # 1. Generate Jawaban dari Gemma Lokal
            ai_response = ""
            for chunk in AIService.chat_with_local_engine(case.question, ""):
                if not chunk.startswith("[STATUS:"):
                    ai_response += chunk
            
            latency = time.time() - start_t
            
            math_score = cls.calculate_math_score(case.expected_answer, ai_response)

            llama_score, llama_reason = cls.get_llama_judge_score(case.question, case.expected_answer, ai_response)
            
        
            # 4. Simpan
            res = RAGBenchmarkResult(
                test_case_id=case.id, # type: ignore
                ai_answer=ai_response, # type: ignore
                bleu_score=math_score, # type: ignore
                llama_score=llama_score, # type: ignore
                llama_reason=llama_reason, # type: ignore
                latency=latency  # type: ignore
            )
            db.session.add(res)
            
            summary["total"] += 1
            summary["avg_bleu"] += math_score
            summary["avg_llama"] += llama_score
            summary["avg_latency"] += latency

        if summary["total"] > 0:
            summary["avg_bleu"] /= summary["total"]
            summary["avg_llama"] /= summary["total"]
            summary["avg_latency"] /= summary["total"]
            
        db.session.commit()
        return {"status": "success", "summary": summary}