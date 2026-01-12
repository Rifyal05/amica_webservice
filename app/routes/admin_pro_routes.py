import os
from flask import Blueprint, jsonify, request, send_file, current_app, render_template
import io
from ..models import db, ProfessionalProfile, User
from ..services.professional_service import ProfessionalService
from ..utils.decorators import admin_required

admin_pro_bp = Blueprint('admin_pro', __name__, url_prefix='/api/admin/pro')
pro_service = ProfessionalService()

@admin_pro_bp.route('/manage', methods=['GET'])
@admin_required
def manage_professionals(current_user):
    return render_template('admin/dashboard.html', active_tab='professionals')

@admin_pro_bp.route('/detail/<uuid:pro_id>', methods=['GET'])
@admin_required
def get_application_detail(current_user, pro_id):
    pro = ProfessionalProfile.query.get(pro_id)
    if not pro:
        return jsonify({"error": "Data tidak ditemukan"}), 404
    
    return jsonify({
        "id": str(pro.id),
        "full_name": pro.full_name_with_title,
        "username": pro.user.username,
        "display_name": pro.user.display_name,
        "email": pro.user.email,
        "avatar_url": pro.user.avatar_url,
        "str_number": pro.str_number,
        "province": pro.province,
        "address": pro.practice_address,
        "schedule": pro.practice_schedule,
        "str_image": f"/api/admin/pro/view-document/{pro.str_image_path}",
        "ktp_image": f"/api/admin/pro/view-document/{pro.ktp_image_path}",
        "selfie_image": f"/api/admin/pro/view-document/{pro.selfie_image_path}",
        "verified_at": pro.verified_at.isoformat() if pro.verified_at else None
    }), 200

@admin_pro_bp.route('/pending', methods=['GET'])
@admin_required
def get_pending_applications(current_user):
    pending_list = ProfessionalProfile.query.filter_by(status='pending').order_by(ProfessionalProfile.created_at.asc()).all()
    results = []
    for p in pending_list:
        results.append({
            "pro_id": str(p.id),
            "user_id": str(p.user_id),
            "username": p.user.username,
            "full_name": p.full_name_with_title,
            "str_number": p.str_number,
            "province": p.province,
            "applied_at": p.created_at.isoformat()
        })
    return jsonify(results), 200

@admin_pro_bp.route('/view-document/<string:filename>', methods=['GET'])
@admin_required
def view_encrypted_document(current_user, filename):
    upload_folder = os.path.join(current_app.root_path, 'static', 'verifications')
    file_path = os.path.join(upload_folder, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File tidak ditemukan"}), 404

    try:
        with open(file_path, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = pro_service._decrypt(encrypted_data)
        return send_file(
            io.BytesIO(decrypted_data),
            mimetype='image/jpeg',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({"error": f"Gagal membuka dokumen: {str(e)}"}), 500

@admin_pro_bp.route('/approve/<uuid:pro_id>', methods=['POST'])
@admin_required
def approve_pro(current_user, pro_id):
    success, msg = pro_service.approve_application(pro_id)
    if success:
        return jsonify({"message": msg}), 200
    return jsonify({"error": msg}), 400

@admin_pro_bp.route('/reject/<uuid:pro_id>', methods=['POST'])
@admin_required
def reject_pro(current_user, pro_id):
    success, msg = pro_service.reject_application(pro_id)
    if success:
        return jsonify({"message": msg}), 200
    return jsonify({"error": msg}), 400

@admin_pro_bp.route('/approved', methods=['GET'])
@admin_required
def get_approved_applications(current_user):
    approved_list = ProfessionalProfile.query.filter_by(status='approved').order_by(ProfessionalProfile.verified_at.desc()).all()
    results = []
    for p in approved_list:
        results.append({
            "pro_id": str(p.id),
            "user_id": str(p.user_id),
            "username": p.user.username,
            "full_name": p.full_name_with_title,
            "str_number": p.str_number,
            "province": p.province,
            "verified_at": p.verified_at.isoformat() if p.verified_at else None
        })
    return jsonify(results), 200

@admin_pro_bp.route('/revoke/<uuid:pro_id>', methods=['POST'])
@admin_required
def revoke_pro(current_user, pro_id):
    success, msg = pro_service.revoke_verification(pro_id)
    if success:
        return jsonify({"message": msg}), 200
    return jsonify({"error": msg}), 400