from flask import Blueprint, request, jsonify
from ..models import db, User
from ..services.email_service import send_otp_email
from ..routes.auth_routes import bcrypt
import random
import string
from datetime import datetime, timedelta, timezone

password_bp = Blueprint('password', __name__)

@password_bp.route('/forgot', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email', '').lower()
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"message": "Jika email terdaftar, kode OTP akan dikirim."}), 200
        
    otp = ''.join(random.choices(string.digits, k=6))
    
    user.reset_otp = otp
    user.reset_otp_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.session.commit()
    
    send_otp_email(user.email, user.display_name, otp)
        
    return jsonify({"message": "Kode OTP telah dikirim.", "temp_id": str(user.id)}), 200


@password_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email', '').lower()
    otp = data.get('otp')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.reset_otp or user.reset_otp != otp:
        return jsonify({"error": "Kode OTP salah"}), 400
        
    if user.reset_otp_expires < datetime.now(timezone.utc):
        return jsonify({"error": "Kode OTP sudah kadaluwarsa"}), 400
        
    return jsonify({"message": "OTP Valid"}), 200


@password_bp.route('/reset', methods=['POST'])
def reset_password_finish():
    data = request.get_json()
    email = data.get('email', '').lower()
    otp = data.get('otp')
    new_password = data.get('new_password')
    
    if len(new_password) < 6:
        return jsonify({"error": "Password minimal 6 karakter"}), 400

    user = User.query.filter_by(email=email).first()
    
    if not user or user.reset_otp != otp:
        return jsonify({"error": "Sesi tidak valid, ulangi dari awal"}), 400

    from .. import bcrypt 
    
    hashed = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.password_hash = hashed

    user.reset_otp = None
    user.reset_otp_expires = None
    db.session.commit()
    
    return jsonify({"message": "Password berhasil diubah. Silakan login."}), 200