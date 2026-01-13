from flask import Blueprint, jsonify, request, Response, stream_with_context
from app.services.ai_service import AIService
from app.utils.decorators import admin_required

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