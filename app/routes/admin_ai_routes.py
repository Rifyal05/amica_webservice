from flask import Blueprint, jsonify, request, Response, stream_with_context
from app.services.ai_service import AIService
from app.utils.decorators import admin_required
from app.services.scoring_service import ScoringService
from app.models import db, RAGTestCase, RAGBenchmarkResult

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

# PINDAHKAN KE SINI (Pakai ai_bp)
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
        new_case = RAGTestCase(
            question=data.get('question'), # type: ignore
            expected_answer=data.get('expected_answer') # type: ignore
        )
        db.session.add(new_case)
        db.session.commit()
        return jsonify({"message": "Test case added"}), 201
    
    cases = RAGTestCase.query.all()
    return jsonify([{
        "id": c.id, 
        "q": c.question, 
        "a": c.expected_answer,
        "last_result": c.results[-1].llama_score if c.results else None
    } for c in cases])

@ai_bp.route('/test-cases/<int:id>', methods=['DELETE'])
@admin_required
def delete_test_case(current_user, id):
    case = RAGTestCase.query.get(id)
    if case:
        db.session.delete(case)
        db.session.commit()
    return jsonify({"message": "Deleted"})

@ai_bp.route('/run-benchmark', methods=['POST'])
@admin_required
def run_benchmark_endpoint(current_user):
    result = ScoringService.run_benchmark()
    return jsonify(result)

@ai_bp.route('/benchmark-results', methods=['GET'])
@admin_required
def get_benchmark_results(current_user):
    results = db.session.query(RAGBenchmarkResult, RAGTestCase)\
        .join(RAGTestCase, RAGBenchmarkResult.test_case_id == RAGTestCase.id)\
        .order_by(RAGBenchmarkResult.id.asc()).all()
    
    data = []
    for res, case in results:
        data.append({
            "question": case.question,
            "expected": case.expected_answer,
            "actual": res.ai_answer,
            "bleu": round(res.bleu_score, 2),
            "llama": res.llama_score,
            "latency": round(res.latency, 2)
        })
    return jsonify(data)