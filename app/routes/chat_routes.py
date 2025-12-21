from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, Chat, ChatParticipant, Message, User
from sqlalchemy import desc, func
import uuid
from datetime import datetime, timezone

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/inbox', methods=['GET'])
@jwt_required()
def get_inbox():
    user_id = get_jwt_identity()
    participations = ChatParticipant.query.filter_by(user_id=user_id).all()
    chat_ids = [p.chat_id for p in participations]
    
    chats = Chat.query.filter(Chat.id.in_(chat_ids)).order_by(desc(Chat.last_message_time)).all()
    
    results = []
    for chat in chats:
        other_participant = None
        if not chat.is_group:
            other_p = ChatParticipant.query.filter(
                ChatParticipant.chat_id == chat.id, 
                ChatParticipant.user_id != user_id
            ).first()
            if other_p:
                other_participant = User.query.get(other_p.user_id)

        my_p_info = ChatParticipant.query.filter_by(chat_id=chat.id, user_id=user_id).first()

        results.append({
            "id": str(chat.id),
            "is_group": chat.is_group,
            "name": chat.name if chat.is_group else (other_participant.display_name if other_participant else "User"),
            "image_url": chat.image_url if chat.is_group else (other_participant.avatar_url if other_participant else ""),
            "last_message_text": chat.last_message_text,
            "last_message_time": chat.last_message_time.isoformat() if chat.last_message_time else None,
            "unread_count": my_p_info.unread_count if my_p_info else 0
        })

    return jsonify(results), 200

@chat_bp.route('/get-or-create/<target_user_id>', methods=['POST'])
@jwt_required()
def get_or_create_chat(target_user_id):
    my_id = get_jwt_identity()
    
    if str(my_id) == str(target_user_id):
        return jsonify({"error": "Tidak bisa chat dengan diri sendiri"}), 400

    existing_chat = db.session.query(Chat).join(ChatParticipant).filter(
        Chat.is_group == False,
        ChatParticipant.user_id.in_([my_id, target_user_id])
    ).group_by(Chat.id).having(func.count(ChatParticipant.user_id) == 2).first()

    if existing_chat:
        return jsonify({"chat_id": str(existing_chat.id), "success": True}), 200
    
    new_chat = Chat()
    new_chat.id = uuid.uuid4()
    new_chat.is_group = False
    db.session.add(new_chat)
    
    p1 = ChatParticipant()
    p1.chat_id = new_chat.id
    p1.user_id = my_id
    
    p2 = ChatParticipant()
    p2.chat_id = new_chat.id
    p2.user_id = target_user_id
    
    db.session.add_all([p1, p2])
    db.session.commit()
    
    return jsonify({"chat_id": str(new_chat.id), "success": True}), 201

@chat_bp.route('/<chat_id>/messages', methods=['GET'])
@jwt_required()
def get_messages(chat_id):
    messages = Message.query.filter_by(chat_id=chat_id).order_by(desc(Message.sent_at)).limit(50).all()
    
    results = []
    for msg in messages:
        results.append({
            "id": str(msg.id),
            "chat_id": str(msg.chat_id),
            "sender_id": str(msg.sender_id) if msg.sender_id else None,
            "text": msg.text,
            "type": msg.type,
            "sent_at": msg.sent_at.isoformat()
        })
    
    return jsonify(results), 200