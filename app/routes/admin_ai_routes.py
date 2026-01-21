from flask import Blueprint, jsonify, request, Response, stream_with_context
from app.services.ai_service import AIService
from app.services.scoring_service import ScoringService
from app.utils.decorators import admin_required
from app.models import db, RAGTestCase, RAGBenchmarkResult
from app.models import Article

ai_bp = Blueprint('admin_ai', __name__, url_prefix='/admin/ai')

@ai_bp.route('/ingest-auto', methods=['POST'])
@admin_required
def ingest_auto(current_user):
    result = AIService.run_smart_ingest(batch_size=5)
    return jsonify(result)

@ai_bp.route('/stats', methods=['GET'])
@admin_required
def get_ai_stats(current_user):
    return jsonify(AIService.get_stats())

@ai_bp.route('/rag-data', methods=['GET'])
@admin_required
def get_rag_data(current_user):
    return jsonify({"data": AIService.get_rag_preview()})

@ai_bp.route('/sync-local', methods=['POST'])
@admin_required
def sync_local_engine(current_user):
    result = AIService.sync_all_to_local()
    status_code = 200 if result and result.get('status') == 'success' else 500
    return jsonify(result), status_code

@ai_bp.route('/ask-admin', methods=['POST'])
@admin_required
def ask_ai_admin(current_user):
    data = request.get_json()
    message = data.get('message', '')
    return Response(stream_with_context(AIService.chat_with_local_engine(message)), mimetype='text/plain')
    
@ai_bp.route('/test-cases', methods=['GET', 'POST'])
@admin_required
def manage_test_cases(current_user):
    if request.method == 'POST':
        data = request.get_json()
        limit = data.get('limit', 20)
        target_id = data.get('target_article_id')
        return jsonify(ScoringService.generate_test_cases_from_jsonl(limit=limit, target_article_id=target_id))

    cases = RAGTestCase.query.all()
    return jsonify([{
        "id": c.id,
        "question": c.question,
        "expected_answer": c.expected_answer,
        "target_article_id": c.target_article_id,
        "target_title": f"Artikel {c.target_article_id}"
    } for c in cases])

@ai_bp.route('/run-benchmark', methods=['POST'])
@admin_required
def run_benchmark_endpoint(current_user):
    data = request.get_json() or {}
    limit = data.get('limit')
    include_llm = data.get('include_llm', False)

    result = ScoringService.run_benchmark(limit=limit, include_llm=include_llm)
    return jsonify(result)

@ai_bp.route('/benchmark-results', methods=['GET'])
@admin_required
def get_benchmark_results(current_user):
    results = db.session.query(RAGBenchmarkResult, RAGTestCase)\
        .join(RAGTestCase, RAGBenchmarkResult.test_case_id == RAGTestCase.id)\
        .order_by(RAGBenchmarkResult.id.asc()).all()

    data = []
    for res, case in results:
        title_display = f"ID: {case.target_article_id}"
        
        if case.target_article_id and case.target_article_id.isdigit():
            article = Article.query.get(int(case.target_article_id))
            if article:
                title_display = article.title

        data.append({
            "question": case.question,
            "expected": case.expected_answer,
            "actual": res.ai_answer,
            "llama_score": res.llama_score,
            "llama_reason": res.llama_reason,
            "mrr_score": res.mrr_score,
            "retrieved_ids": res.retrieved_ids,
            "target_title": title_display,
            "found_rank": int(1.0/res.mrr_score) if res.mrr_score > 0 else 0,
            "latency": round(res.latency, 2)
        })
    return jsonify(data)

@ai_bp.route('/benchmark-results', methods=['DELETE'])
@admin_required
def clear_benchmark_results(current_user):
    try:
        num_deleted = db.session.query(RAGBenchmarkResult).delete()
        db.session.commit()
        return jsonify({'message': f'Berhasil menghapus {num_deleted} riwayat benchmark.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@ai_bp.route('/article-list', methods=['GET'])
@admin_required
def get_article_list(current_user):
    articles = Article.query.with_entities(Article.id, Article.title).order_by(Article.created_at.desc()).all()
    result = [{'id': str(a.id), 'title': a.title} for a in articles]
    return jsonify(result)