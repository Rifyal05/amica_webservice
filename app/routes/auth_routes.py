import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from flask import Blueprint, request, jsonify
from ..models import User
from ..extensions import db
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone
import os
import uuid
import secrets
from sqlalchemy import or_

from flask_jwt_extended import (
    jwt_required, 
    get_jwt_identity, 
    create_access_token, 
    create_refresh_token
)

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

cred_path = 'serviceAccountKey.json'
if not firebase_admin._apps:
    try:
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
    except Exception:
        pass

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        current_user_id = get_jwt_identity()

        new_access_token = create_access_token(identity=current_user_id)
        
        return jsonify({
            "access_token": new_access_token
        }), 200
    except Exception as e:
        return jsonify({"error": "Sesi telah berakhir, silakan login ulang.", "details": str(e)}), 401

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body tidak valid"}), 400
        
        if not all(key in data for key in ['email', 'password', 'username', 'display_name']):
            return jsonify({"error": "Semua field (display_name, username, email, password) harus diisi"}), 400

        password = data.get('password', '').strip()
        if not password or len(password) < 6:
            return jsonify({"error": "Password minimal 6 karakter dan tidak boleh kosong"}), 400
        
        if not data.get('username').strip() or not data.get('display_name').strip():
            return jsonify({"error": "Username dan Display Name tidak boleh kosong"}), 400

        email = data.get('email').lower()
        username = data.get('username').lower()

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email sudah terdaftar"}), 409

        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username sudah digunakan"}), 409

        hashed_password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')

        new_user = User(
            id=uuid.uuid4(),# type: ignore
            email=email,# type: ignore
            username=username,# type: ignore
            password_hash=hashed_password,# type: ignore
            display_name=data.get('display_name'),# type: ignore
            role='user'# type: ignore
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Terjadi kesalahan di server", "details": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    login_input = data.get('email') 
    password = data.get('password')

    if not login_input or not password:
        return jsonify({"error": "Username/Email dan password harus diisi"}), 400
  
    login_input = login_input.lower()
    
    user = User.query.filter(
        or_(User.email == login_input, User.username == login_input)
    ).first()
    
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Username/Email atau password salah"}), 401
    
    if user.is_suspended:
        if user.suspended_until and user.suspended_until <= datetime.now(timezone.utc):
            user.is_suspended = False
            user.suspended_until = None
            db.session.commit()
        else:
            if user.suspended_until.year == 9999:
                msg = "Akun ini telah dibanned secara PERMANEN."
            else:
                until_str = user.suspended_until.strftime('%d %B %Y')
                msg = f"Akun dibekukan hingga {until_str}."
            return jsonify({'error': msg, 'status': 'suspended'}), 403

    if user.security_pin_hash: 
        return jsonify({
            'status': 'pin_required', 
            'temp_id': str(user.id) 
        }), 200

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,  
        "refresh_token": refresh_token,
        "token": access_token,          
        "user": {
            "id": str(user.id),
            "display_name": user.display_name,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "role": user.role,               
            "email": user.email,
            "auth_provider": user.auth_provider,
            "google_uid": user.google_uid,
            "has_pin": bool(user.security_pin_hash),
            "is_verified": user.is_verified,

        }
    }), 200


@auth_bp.route('/verify-pin', methods=['POST'])
def verify_pin():
    try:
        data = request.get_json()
        user_id = data.get('temp_id')
        pin = data.get('pin')
        
        user = User.query.get(user_id)
        
        if not user or not user.security_pin_hash:
            return jsonify({'error': 'Request tidak valid'}), 400

        if bcrypt.check_password_hash(user.security_pin_hash, pin):

            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))

            return jsonify({
                "message": "Login verified",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token": access_token,
                "user": {
                    "id": str(user.id),
                    "display_name": user.display_name,
                    "username": user.username,
                    "avatar_url": user.avatar_url,
                    "role": user.role,               
                    "email": user.email,
                    "auth_provider": user.auth_provider, 
                    "google_uid": user.google_uid,       
                    "has_pin": bool(user.security_pin_hash),
                    "is_verified": user.is_verified,

                }
            }), 200
        else:
            return jsonify({'error': 'PIN Salah!'}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/google-login', methods=['POST'])
def google_login():
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token tidak ditemukan'}), 400

        try:
            decoded_token = firebase_auth.verify_id_token(token)
            uid = decoded_token['uid']
            email = decoded_token['email']
            name = decoded_token.get('name', 'User')
            picture = decoded_token.get('picture', '')
        except Exception:
            return jsonify({'error': 'Token Google tidak valid'}), 401

        user = User.query.filter((User.google_uid == uid) | (User.email == email)).first()

        if user:
            updated = False
            if not user.google_uid:
                user.google_uid = uid
                user.auth_provider = 'google'
                updated = True
            if not user.avatar_url and picture:
                user.avatar_url = picture
                updated = True
            if updated:
                db.session.commit()
        else:
            base_username = email.split('@')[0]
            clean_username = "".join(c for c in base_username if c.isalnum() or c == '_')[:20]
            final_username = clean_username
            counter = 1
            while User.query.filter_by(username=final_username).first():
                final_username = f"{clean_username}{counter}"
                counter += 1

            random_password = secrets.token_urlsafe(16)
            hashed_password = bcrypt.generate_password_hash(random_password).decode('utf-8')

            user = User(
                id=uuid.uuid4(),# type: ignore
                email=email,# type: ignore
                username=final_username,# type: ignore
                display_name=name,# type: ignore
                password_hash=hashed_password,# type: ignore
                google_uid=uid,# type: ignore
                auth_provider='google',# type: ignore
                avatar_url=picture,# type: ignore
                role='user'# type: ignore
            )
            db.session.add(user)
            db.session.commit()

        if user.is_suspended:
            if user.suspended_until and user.suspended_until <= datetime.now(timezone.utc):
                user.is_suspended = False
                user.suspended_until = None
                db.session.commit()
            else:
                if user.suspended_until.year == 9999:
                    msg = "Akun ini telah dibanned secara PERMANEN."
                else:
                    until_str = user.suspended_until.strftime('%d %B %Y')
                    msg = f"Akun dibekukan hingga {until_str}."
                return jsonify({'error': msg, 'status': 'suspended'}), 403

        if user.security_pin_hash:
             return jsonify({
                'status': 'pin_required', 
                'temp_id': str(user.id) 
            }), 200
        
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            "message": "Google login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token": access_token, # Fallback
            "user": {
                "id": str(user.id),
                "display_name": user.display_name,
                "username": user.username,
                "avatar_url": user.avatar_url,
                "role": user.role,               
                "email": user.email,
                "auth_provider": user.auth_provider, 
                "google_uid": user.google_uid,       
                "has_pin": bool(user.security_pin_hash),
                # "is_verified": user.is_verified,

            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Terjadi kesalahan server", "details": str(e)}), 500
    
@auth_bp.route('/user-google-login', methods=['POST'])
def google_user_login():
    try:    
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "Data JSON tidak terbaca"}), 400
            
        id_token = data.get('id_token')
        if not id_token:
            return jsonify({"error": "ID Token tidak ditemukan"}), 400

        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
            google_email = decoded_token.get('email').lower()
            google_uid = decoded_token.get('uid')
            display_name = decoded_token.get('name', 'User')
            avatar_url = decoded_token.get('picture')
        except Exception as ve:
            print(f"!!! Error Verifikasi Token: {ve}")
            return jsonify({"error": "Token tidak valid", "details": str(ve)}), 401

        user = User.query.filter_by(email=google_email).first()
        needs_password_set = False

        if not user:
            base_username = google_email.split('@')[0][:15]
            unique_username = f"{base_username}_{secrets.token_hex(3)}"

            user = User(
                id=uuid.uuid4(), # type: ignore
                email=google_email, # type: ignore
                username=unique_username, # type: ignore
                display_name=display_name, # type: ignore
                password_hash=None, # type: ignore
                avatar_url=avatar_url, # type: ignore
                auth_provider='google', # type: ignore
                google_uid=google_uid, # type: ignore
                role='user' # type: ignore
            )
            db.session.add(user)
            db.session.commit()
            needs_password_set = True
        else:
            if user.password_hash is None:
                needs_password_set = True
            
            if not user.google_uid:
                user.google_uid = google_uid
                db.session.commit()

        if user.security_pin_hash:
            return jsonify({
                'status': 'pin_required', 
                'temp_id': str(user.id),
                'email': user.email,
                'needs_password_set': needs_password_set
            }), 200

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            "message": "Login berhasil",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "needs_password_set": needs_password_set,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "role": user.role,
                "auth_provider": user.auth_provider,
                "has_pin": False,
                "is_verified": user.is_verified,

            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Kesalahan server", "details": str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'User tidak ditemukan'}), 404

        avatar = user.avatar_url
        if avatar and not avatar.startswith('http'):
            if 'static/uploads' not in avatar:
                avatar = f"static/uploads/{avatar}"

        return jsonify({
            "success": True,
            "user": {
                "id": str(user.id),
                "display_name": user.display_name,
                "username": user.username,
                "avatar_url": avatar,
                "role": user.role,
                "email": user.email,
                "auth_provider": user.auth_provider,
                "google_uid": user.google_uid,
                "has_pin": bool(user.security_pin_hash),
                "is_verified": user.is_verified,

            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Terjadi kesalahan", "details": str(e)}), 500

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    return jsonify({"message": "Logout berhasil"}), 200

@auth_bp.route('/user/pin', methods=['PUT'])
@jwt_required()
def update_user_pin():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    data = request.get_json()
    old_pin = data.get('old_pin')
    new_pin = data.get('new_pin')
    
    if not new_pin or len(new_pin) != 6 or not new_pin.isdigit():
        return jsonify({'error': 'PIN harus 6 digit angka.'}), 400

    if user.security_pin_hash: # type: ignore
        if not old_pin:
            return jsonify({'error': 'Masukkan PIN lama untuk verifikasi.'}), 400
        if not bcrypt.check_password_hash(user.security_pin_hash, old_pin):# type: ignore
            return jsonify({'error': 'PIN lama salah.'}), 400
            
    user.security_pin_hash = bcrypt.generate_password_hash(new_pin).decode('utf-8') # type: ignore
    db.session.commit()
    
    return jsonify({
        'message': 'PIN Keamanan berhasil diatur!',
        'has_pin': True
    })

@auth_bp.route('/user/pin/check', methods=['POST'])
@jwt_required()
def check_pin_access():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    data = request.get_json()
    input_pin = data.get('pin')
    
    if not user.security_pin_hash: # type: ignore
        return jsonify({'status': 'no_pin_set'}), 400
        
    if bcrypt.check_password_hash(user.security_pin_hash, input_pin):# type: ignore
        return jsonify({'status': 'valid'})
    else:
        return jsonify({'status': 'invalid'}), 401
    
@auth_bp.route('/set-password', methods=['POST'])
@jwt_required()
def set_password():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        new_password = data.get('password')

        if not new_password or len(new_password) < 6:
            return jsonify({"error": "Password minimal 6 karakter"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User tidak ditemukan"}), 404

        if user.password_hash is not None:
             return jsonify({"error": "Password sudah diatur sebelumnya"}), 400

        user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()

        return jsonify({"message": "Password berhasil diatur. Sekarang akun Anda aman!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Gagal mengatur password", "details": str(e)}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not user.password_hash: # type: ignore
        return jsonify({"error": "Akun Google tidak bisa ganti password di sini"}), 400
        
    if not bcrypt.check_password_hash(user.password_hash, old_password): # type: ignore
        return jsonify({"error": "Password lama salah"}), 400
        
    if len(new_password) < 6:
        return jsonify({"error": "Password baru minimal 6 karakter"}), 400

    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8') # type: ignore
    db.session.commit()
    
    return jsonify({"message": "Password berhasil diubah"}), 200

@auth_bp.route('/change-email', methods=['POST'])
@jwt_required()
def change_email():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    data = request.get_json()
    new_email = data.get('new_email').lower()
    password = data.get('password')
    
    if not new_email or not password:
        return jsonify({"error": "Data tidak lengkap"}), 400
        
    # Cek Password
    if not user.password_hash or not bcrypt.check_password_hash(user.password_hash, password): # type: ignore
        return jsonify({"error": "Password salah"}), 400
        
    # Cek Email Unik
    if User.query.filter_by(email=new_email).first():
        return jsonify({"error": "Email sudah digunakan orang lain"}), 409
        
    user.email = new_email # type: ignore
    db.session.commit()
    
    return jsonify({"message": "Email berhasil diubah"}), 200


@auth_bp.route('/logout-device', methods=['POST'])
@jwt_required()
def logout_device():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user:
        user.onesignal_player_id = None
        db.session.commit()
    return jsonify({"message": "Device ID cleared"}), 200

@auth_bp.route('/set-pin', methods=['POST'])
@jwt_required()
def set_pin():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    data = request.get_json()
    new_pin = data.get('pin')
    
    if not new_pin or len(new_pin) < 6: 
        return jsonify({"error": "Format PIN tidak valid"}), 400

    hashed_pin = bcrypt.generate_password_hash(new_pin).decode('utf-8')
    
    user.security_pin_hash = hashed_pin # type: ignore
    db.session.commit()
    
    return jsonify({"message": "PIN keamanan berhasil diaktifkan/diubah"}), 200

auth_bp.route('/remove-pin', methods=['POST'])
@jwt_required()
def remove_pin():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    data = request.get_json()
    current_pin = data.get('current_pin') 
    
    if not user.security_pin_hash: # type: ignore
        return jsonify({"message": "PIN memang belum aktif"}), 200

    if not current_pin or not bcrypt.check_password_hash(user.security_pin_hash, current_pin): # type: ignore
        return jsonify({"error": "PIN salah, gagal menonaktifkan."}), 400
    
    user.security_pin_hash = None # type: ignore
    db.session.commit()
    
    return jsonify({"message": "PIN keamanan berhasil dinonaktifkan"}), 200

@auth_bp.route('/reset-pin-by-otp', methods=['POST'])
def reset_pin_by_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_pin = data.get('new_pin')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or user.reset_otp != otp:
        return jsonify({"error": "Sesi tidak valid/OTP salah"}), 400
        
    if new_pin:
        hashed = bcrypt.generate_password_hash(new_pin).decode('utf-8')
        user.security_pin_hash = hashed
        msg = "PIN baru berhasil diatur. Silakan login."
    else:
        user.security_pin_hash = None 
        msg = "PIN berhasil dihapus. Silakan login tanpa PIN."

    user.reset_otp = None
    user.reset_otp_expires = None
    db.session.commit()
    
    return jsonify({"message": msg}), 200