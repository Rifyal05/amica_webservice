from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, Notification
from ..extensions import limiter
notif_bp = Blueprint('notifications', __name__)

@notif_bp.route('/', methods=['GET'])
@limiter.limit("30 per minute")
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    
    notifs = Notification.query.filter_by(recipient_id=user_id)\
        .order_by(Notification.created_at.desc())\
        .limit(50)\
        .all()
        
    return jsonify([n.to_dict() for n in notifs]), 200

@notif_bp.route('/read-all', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required()
def mark_all_read():
    user_id = get_jwt_identity()
    Notification.query.filter_by(recipient_id=user_id, is_read=False)\
        .update({Notification.is_read: True})
    db.session.commit()
    return jsonify({"message": "Semua ditandai sudah dibaca"}), 200