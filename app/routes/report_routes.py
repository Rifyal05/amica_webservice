from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import User
from ..services.report_service import create_report
import uuid
from .. extensions import limiter
report_bp = Blueprint('report', __name__)

@report_bp.route('', methods=['POST'])
@limiter.limit("10 per hour")
@jwt_required()
def submit_report():
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    data = request.get_json()
    
    target_type = data.get('target_type') # 'post', 'comment', atau 'user'
    target_id = data.get('target_id')
    reason = data.get('reason', 'Tidak ada alasan spesifik.')
    
    if not target_type or not target_id:
        return jsonify({"error": "Target laporan (tipe dan ID) harus disertakan."}), 400
    
    try:
        if target_type != 'user':
             uuid.UUID(target_id) 
    except ValueError:
        return jsonify({"error": "Format ID target tidak valid."}), 400

    success, message = create_report(
        reporter_id=current_user.id,
        target_type=target_type,
        target_id=target_id,
        reason=reason
    )
    
    if success:
        return jsonify({"message": message}), 201
    else:
        return jsonify({"error": message}), 500