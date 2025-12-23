from functools import wraps
from flask import request, jsonify
import jwt
import os
from ..models import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2:
                token = parts[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, os.environ.get('SECRET_KEY'), algorithms=["HS256"]) # type: ignore
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Ambil token dari Header
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2:
                token = parts[1]
        
        if not token:
            return jsonify({'message': 'Authentication token is missing!'}), 401

        try:
            secret = os.environ.get('SECRET_KEY')

            data = jwt.decode(token, secret, algorithms=["HS256"]) # type: ignore

            user_id = data.get('sub') 
            if not user_id:
                user_id = data.get('user_id')
                
            if not user_id:
                return jsonify({'message': 'Token payload invalid (no user ID)'}), 401

            current_user = User.query.get(user_id)
            
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
            
            if current_user.is_suspended:
                return jsonify({'message': 'Akun Anda telah dibekukan. Akses ditolak.'}), 403

            if current_user.role not in ['admin', 'owner']:
                return jsonify({'message': 'Access denied. Admins only.'}), 403
                 
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except Exception as e:
            print(f"Admin Decorator Error: {e}") 
            return jsonify({'message': 'Token invalid', 'error': str(e)}), 401

        return f(current_user, *args, **kwargs)

    return decorated