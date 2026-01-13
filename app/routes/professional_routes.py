from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.professional_service import ProfessionalService
from ..extensions import limiter

pro_bp = Blueprint('professional', __name__, url_prefix='/api/pro')
pro_service = ProfessionalService()

@pro_bp.route('/apply', methods=['POST'])
@limiter.limit("3 per hour")
@jwt_required()
def apply_professional():
    user_id = get_jwt_identity()
    success, msg = pro_service.submit_application(user_id, request.form, request.files)
    if success:
        return jsonify({"message": "Permohonan verifikasi terkirim"}), 201
    return jsonify({"error": msg}), 400

@pro_bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    user_id = get_jwt_identity()
    from ..models import ProfessionalProfile
    pro = ProfessionalProfile.query.filter_by(user_id=user_id).first()
    if not pro:
        return jsonify({"status": "none"}), 200
    return jsonify({
        "status": pro.status,
        "applied_at": pro.created_at.isoformat()
    }), 200

@pro_bp.route('/admin/approve/<uuid:pro_id>', methods=['POST'])
@jwt_required()
def approve_pro(pro_id):
    success, msg = pro_service.approve_application(pro_id)
    if success:
        return jsonify({"message": msg}), 200
    return jsonify({"error": msg}), 400


@pro_bp.route('/update', methods=['PUT'])
@limiter.limit("10 per hour")
@jwt_required()
def update_pro_data():
    user_id = get_jwt_identity()
    data = request.form if request.form else request.json 
    
    success, msg = pro_service.update_professional_info(user_id, data)
    
    if success:
        return jsonify({"message": msg}), 200
    return jsonify({"error": msg}), 400