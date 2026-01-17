import json
from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, BotChat, BotMessage
from sqlalchemy import desc
from datetime import datetime, timezone
from app.utils.decorators import admin_required
from app.services.ai_service import AIService

bot_bp = Blueprint('bot', __name__)

def construct_smart_history(bot_chat_id, exclude_msg_id=None, max_chars=5000):
    recent_messages = BotMessage.query.filter(
        BotMessage.bot_chat_id == bot_chat_id,
        BotMessage.id != exclude_msg_id
    ).order_by(desc(BotMessage.sent_at)).limit(40).all()
    history_parts = []
    current_char_count = 0
    for msg in recent_messages:
        formatted_msg = f"<start_of_turn>{msg.role}\n{msg.content}<end_of_turn>\n"
        msg_len = len(formatted_msg)
        if current_char_count + msg_len > max_chars:
            break
        history_parts.insert(0, formatted_msg)
        current_char_count += msg_len
    return "".join(history_parts)

@bot_bp.route('/ask-admin', methods=['POST'])
@admin_required
def ask_ai_admin(current_user):
    data = request.get_json()
    message = data.get('message', '')
    return Response(stream_with_context(AIService.chat_with_local_engine(message, history_text="")), mimetype='text/plain')

@bot_bp.route('/send', methods=['POST'])
@jwt_required()
def user_chat_with_bot():
    user_id = get_jwt_identity()
    data = request.get_json()
    user_text = data.get('message', '').strip()
    session_id = data.get('session_id')
    
    if not user_text:
        return jsonify({"error": "Pesan kosong"}), 400
    
    if session_id:
        chat = BotChat.query.filter_by(id=session_id, user_id=user_id).first()
        if not chat:
            return jsonify({"error": "Sesi tidak ditemukan"}), 404
    else:
        title_limit = 50
        title = user_text[:title_limit] + "..." if len(user_text) > title_limit else user_text
        chat = BotChat(user_id=user_id, title=title) # type: ignore
        db.session.add(chat)
        db.session.commit()
        session_id = str(chat.id)
    
    chat.updated_at = datetime.now(timezone.utc)
    
    user_msg = BotMessage(bot_chat_id=session_id, role='user', content=user_text) # type: ignore
    db.session.add(user_msg)
    db.session.commit()
    
    history_str = ""
    
    app = current_app._get_current_object() # type: ignore

    def generate():
        yield json.dumps({"session_id": session_id, "type": "meta"}) + "\n"
        
        with app.app_context():
            full_reply = ""
            for chunk in AIService.chat_with_local_engine(user_text, history_text=history_str):
                yield chunk
                if not chunk.startswith("[STATUS:") and chunk != "[HEARTBEAT]":
                    full_reply += chunk
            
            if full_reply.strip():
                bot_msg = BotMessage(bot_chat_id=session_id, role='model', content=full_reply) # type: ignore
                db.session.add(bot_msg)
                db.session.commit()

    return Response(stream_with_context(generate()), mimetype='text/plain')

@bot_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_chat_sessions():
    user_id = get_jwt_identity()
    sessions = BotChat.query.filter_by(user_id=user_id).order_by(desc(BotChat.updated_at)).all()
    results = []
    for s in sessions:
        results.append({
            "id": str(s.id),
            "title": s.title or "Percakapan Baru",
            "updated_at": s.updated_at.isoformat()
        })
    return jsonify(results)

@bot_bp.route('/history/<session_id>', methods=['GET'])
@jwt_required()
def get_session_history(session_id):
    user_id = get_jwt_identity()
    chat = BotChat.query.filter_by(id=session_id, user_id=user_id).first()
    if not chat:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404
        
    messages = BotMessage.query.filter_by(bot_chat_id=session_id).order_by(desc(BotMessage.sent_at)).limit(50).all()
    results = []
    for msg in messages:
        results.append({"id": str(msg.id), "role": msg.role, "text": msg.content, "sent_at": msg.sent_at.isoformat()})
    return jsonify(results[::-1])