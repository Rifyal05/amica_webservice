from flask import Blueprint, jsonify
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
    data = AIService.get_rag_preview()
    return jsonify({"data": data})

@ai_bp.route('/sync-cloud', methods=['POST'])
@admin_required
def sync_cloud(current_user):
    result = AIService.sync_to_cloud()
    status_code = 200 if result.get('status') == 'success' else 500
    return jsonify(result), status_code
