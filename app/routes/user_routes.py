from flask import Blueprint, jsonify, request
from ..services.user_action_service import UserActionService
from ..utils.decorators import token_required 
from ..models import User, Connection, db
import uuid

user_bp = Blueprint('user', __name__) 

user_action_service = UserActionService()

def user_to_dict(user):
    return {
        'id': str(user.id), 
        'username': user.username, 
        'display_name': user.display_name,
        'avatar_url': user.avatar_url,
    }

@user_bp.route('/<string:user_id>/follow', methods=['POST'])
@token_required
def follow_user(current_user, user_id):
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        return jsonify({"error": "Invalid UUID format"}), 400

    target_user = User.query.get(target_uuid)
    if not target_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    if current_user.id == target_uuid:
        return jsonify({"error": "Tidak bisa mengikuti diri sendiri"}), 400

    existing_connection = Connection.query.filter_by(
        follower_id=current_user.id,
        following_id=target_uuid
    ).first()

    try:
        if existing_connection:
            # UNFOLLOW
            db.session.delete(existing_connection)
            is_following = False
            message = f"Berhenti mengikuti {target_user.username}"
        else:
            # FOLLOW
            new_connection = Connection(
                follower_id=current_user.id,  # type: ignore
                following_id=target_uuid # type: ignore
            )
            db.session.add(new_connection)
            is_following = True
            message = f"Mulai mengikuti {target_user.username}"

        db.session.commit()

        return jsonify({
            "message": message,
            "is_following": is_following
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Gagal memproses request", "details": str(e)}), 500



@user_bp.route('/block/<string:target_uuid>', methods=['POST'])
@token_required
def handle_block_user(current_user, target_uuid): 
    try:
        blocker_id = current_user.id
        target_id = uuid.UUID(target_uuid)
    except ValueError:
        return jsonify({'error': 'Invalid UUID format for target user'}), 400

    success = user_action_service.block_user(blocker_id, target_id)
    
    if success:
        return jsonify({'message': 'User blocked successfully'}), 200
    if blocker_id == target_id:
        return jsonify({'error': 'Cannot block yourself'}), 400
        
    return jsonify({'error': 'Failed to process block request'}), 500


@user_bp.route('/unblock/<string:target_uuid>', methods=['POST'])
@token_required
def handle_unblock_user(current_user, target_uuid): 
    try:
        blocker_id = current_user.id
        target_id = uuid.UUID(target_uuid)
    except ValueError:
        return jsonify({'error': 'Invalid UUID format for target user'}), 400
        
    success = user_action_service.unblock_user(blocker_id, target_id)
    
    if success:
        return jsonify({'message': 'User unblocked successfully'}), 200
    return jsonify({'error': 'User was not found in blocked list or failed to unblock'}), 404


@user_bp.route('/blocked_list', methods=['GET'])
@token_required
def get_blocked_list(current_user): 
    blocker_id = current_user.id
    blocked_users = user_action_service.get_blocked_users(blocker_id)
    
    blocked_data = [user_to_dict(u) for u in blocked_users]
    
    return jsonify(blocked_data), 200