from flask import request
from flask_socketio import emit, join_room, leave_room
from .socket_instance import socketio
from .models import db, User, Chat, Message, ChatParticipant
from .config import Config
from .services.notification_service import send_push_notification
import jwt
import uuid
from datetime import datetime, timezone

def get_user_from_token():
    token = request.args.get('token')
    if not token:
        print("Socket Auth Gagal: Token tidak dikirim")
        return None
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"]) # type: ignore
        user_id = payload.get('sub') 
        
        if not user_id:
            print("Socket Auth Gagal: Claim 'sub' tidak ditemukan di token")
            return None
            
        user = User.query.get(user_id)
        return user
    except Exception as e:
        print(f"Socket Auth Gagal: Error tidak terduga: {str(e)}")
    return None


@socketio.on('connect')
def handle_connect():
    user = get_user_from_token()
    if not user:
        print("Menolak koneksi socket karena autentikasi gagal.")
        return False 
    
    join_room(str(user.id))
    print(f"Socket Terhubung: {user.username} (Room ID: {user.id})")

@socketio.on('join_chat')
def handle_join_chat(data):
    user = get_user_from_token()
    if not user: return
    
    chat_id = data.get('chat_id')
    
    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=user.id).first()
    if participant:
        join_room(chat_id)
        participant.unread_count = 0
        db.session.commit()

@socketio.on('send_message')
def handle_send_message(data):
    sender = get_user_from_token()
    if not sender: return

    chat_id = data.get('chat_id')
    text = data.get('text')
    msg_type = data.get('type', 'text')

    new_message = Message(
        id=uuid.uuid4(), # type: ignore
        chat_id=chat_id, # type: ignore
        sender_id=sender.id,# type: ignore
        text=text,# type: ignore
        type=msg_type,# type: ignore
        sent_at=datetime.now(timezone.utc)# type: ignore
    )
    db.session.add(new_message)

    chat = Chat.query.get(chat_id)
    if chat:
        chat.last_message_text = text if msg_type == 'text' else '📷 Mengirim gambar'
        chat.last_message_time = datetime.now(timezone.utc)
    
    participants = ChatParticipant.query.filter_by(chat_id=chat_id).all()
    for p in participants:
        if str(p.user_id) != str(sender.id):
            p.unread_count += 1
            
            receiver = User.query.get(p.user_id)
            if receiver and receiver.onesignal_player_id:
                send_push_notification(
                    player_ids=[receiver.onesignal_player_id],
                    title=f"{sender.display_name}",
                    content=text if msg_type == 'text' else '📷 Mengirim gambar',
                    data={"chat_id": chat_id, "type": "chat_message"}
                )

    db.session.commit()

    response_data = {
        'id': str(new_message.id),
        'text': new_message.text,
        'sender_id': str(sender.id),
        'sender_name': sender.username,
        'sender_avatar': sender.avatar_url,
        'sent_at': new_message.sent_at.isoformat(),
        'type': msg_type,
        'is_read': False
    }
    
    emit('new_message', response_data, to=chat_id)
    
    for p in participants:
        if str(p.user_id) != str(sender.id):
            emit('inbox_update', {
                'chat_id': chat_id,
                'last_message': chat.last_message_text,# type: ignore
                'time': chat.last_message_time.isoformat(),# type: ignore
                'unread_count': p.unread_count
            }, to=str(p.user_id))

@socketio.on('typing')
def handle_typing(data):
    chat_id = data.get('chat_id')
    is_typing = data.get('is_typing')
    sender = get_user_from_token()
    
    if sender:
        emit('user_typing', {
            'user_id': str(sender.id),
            'username': sender.username,
            'is_typing': is_typing
        }, to=chat_id, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    pass



@socketio.on('mark_read')
def handle_mark_read(data):
    reader = get_user_from_token()
    if not reader: return

    chat_id = data.get('chat_id')
    
    unread_messages = Message.query.filter(
        Message.chat_id == chat_id,
        Message.sender_id != reader.id,
        Message.is_read_by_all == False
    ).all()
    
    if not unread_messages:
        return

    for msg in unread_messages:
        msg.is_read_by_all = True

    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=reader.id).first()
    if participant:
        participant.unread_count = 0
    
    db.session.commit()
    emit('messages_read', {
        'chat_id': chat_id,
        'reader_id': str(reader.id)
    }, to=chat_id) 