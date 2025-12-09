import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from flask import Blueprint, request, jsonify
from ..models import User
from ..database import db
from flask_bcrypt import Bcrypt
import jwt
from datetime import datetime, timedelta, timezone
import os
import uuid
import secrets
from flask_jwt_extended import jwt_required, get_jwt_identity # type: ignore

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

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body tidak valid"}), 400
        
        if not all(key in data for key in ['email', 'password', 'username', 'display_name']):
            return jsonify({"error": "Semua field (display_name, username, email, password) harus diisi"}), 400

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
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email dan password harus diisi"}), 400
    
    email = data.get('email').lower()
    user = User.query.filter_by(email=email).first()
    
    if not user or not bcrypt.check_password_hash(user.password_hash, data.get('password')):
        return jsonify({"error": "Email atau password salah"}), 401
    
    if user.is_suspended:
        # Cek tanggal unban
        if user.suspended_until and user.suspended_until <= datetime.now(timezone.utc):
            user.is_suspended = False
            user.suspended_until = None
            db.session.commit()
        else:
            # Siapkan pesan error
            if user.suspended_until.year == 9999:
                msg = "Akun ini telah dibanned secara PERMANEN."
            else:
                until_str = user.suspended_until.strftime('%d %B %Y')
                msg = f"Akun dibekukan hingga {until_str}."
            
            return jsonify({'error': msg, 'status': 'suspended'}), 403

    if user.security_pin_hash: # type: ignore
        return jsonify({
            'status': 'pin_required', 
            'temp_id': str(user.id) 
        }), 200

    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        return jsonify({"error": "Konfigurasi server bermasalah (SECRET_KEY missing)"}), 500

    token = jwt.encode({
        'user_id': str(user.id),
        'exp': datetime.now(timezone.utc) + timedelta(days=30)
    }, secret_key, algorithm="HS256")
    
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "id": str(user.id),
            "display_name": user.display_name,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "role": user.role,               
            "email": user.email,
            "auth_provider": user.auth_provider, # PENTING
            "google_uid": user.google_uid,       # PENTING
            "has_pin": bool(user.security_pin_hash)
        }
    }), 200

@auth_bp.route('/verify-pin', methods=['POST'])
def verify_pin():
    try:
        data = request.get_json()
        user_id = data.get('temp_id')
        pin = data.get('pin')
        
        user = User.query.get(user_id)
        
        if not user or not user.security_pin_hash: # type: ignore
            return jsonify({'error': 'Request tidak valid'}), 400
            
        # Cek PIN
        if bcrypt.check_password_hash(user.security_pin_hash, pin): # type: ignore
            secret_key = os.environ.get('SECRET_KEY')
            if not secret_key:
                return jsonify({"error": "Konfigurasi server bermasalah"}), 500

            token = jwt.encode({
                'user_id': str(user.id),
                'exp': datetime.now(timezone.utc) + timedelta(days=30)
            }, secret_key, algorithm="HS256")

            return jsonify({
                "message": "Login verified",
                "token": token,
                "user": {
                    "id": str(user.id),
                    "display_name": user.display_name,
                    "username": user.username,
                    "avatar_url": user.avatar_url,
                    "role": user.role,               
                    "email": user.email,
                    "auth_provider": user.auth_provider, # PENTING
                    "google_uid": user.google_uid,       # PENTING
                    "has_pin": bool(user.security_pin_hash)
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
            # Update data user jika ada perubahan
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
            # Register user baru via Google
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
        
        secret_key = os.environ.get('SECRET_KEY')
        jwt_token = jwt.encode({
            'user_id': str(user.id),
            'exp': datetime.now(timezone.utc) + timedelta(days=30)
        }, secret_key, algorithm="HS256") # type: ignore

        return jsonify({
            "message": "Google login successful",
            "token": jwt_token,
            "user": {
                "id": str(user.id),
                "display_name": user.display_name,
                "username": user.username,
                "avatar_url": user.avatar_url,
                "role": user.role,               
                "email": user.email,
                "auth_provider": user.auth_provider, # PENTING
                "google_uid": user.google_uid,       # PENTING
                "has_pin": bool(user.security_pin_hash)
                }
        }), 200

    except Exception as e:
        return jsonify({"error": "Terjadi kesalahan server", "details": str(e)}), 500    
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
        if not bcrypt.check_password_hash(user.security_pin_hash, old_pin): # type: ignore
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
        
    if bcrypt.check_password_hash(user.security_pin_hash, input_pin): # type: ignore
        return jsonify({'status': 'valid'})
    else:
        return jsonify({'status': 'invalid'}), 401