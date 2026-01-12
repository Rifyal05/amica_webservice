from flask import request, current_app
from flask_socketio import emit, join_room, leave_room, disconnect
from .extensions import socketio, db
from .models import User, Chat, Message, ChatParticipant
from .config import Config
from .services.notification_service import NotificationService
import jwt
import uuid
from datetime import datetime, timezone

def get_full_url(path):
    if not path:
        return ""
    if path.startswith(('http://', 'https://')):
        return path
    base_url = request.host_url.rstrip('/')
    clean_path = path.lstrip('/')
    if not clean_path.startswith('static/'):
        clean_path = f"static/uploads/{clean_path}"
    return f"{base_url}/{clean_path}"

@socketio.on('connect')
def handle_connect(auth=None):
    try:
        token = request.args.get('token')
        
        if not token and auth:
            token = auth.get('token')
        
        if not token:
            return False

        secret_key = current_app.config.get('JWT_SECRET_KEY') or Config.SECRET_KEY
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])# type: ignore
        except:
            return False
            
        user_id = payload.get('sub')
        if not user_id:
            return False
        
        with current_app.app_context():
            user = User.query.get(user_id)
            if not user:
                return False
            
            join_room(str(user.id))
            return True

    except Exception:
        return False

def get_current_socket_user():
    try:
        token = request.args.get('token')
        if not token and hasattr(request, 'event') and request.event:# type: ignore
            auth = request.event.get('auth', {})# type: ignore
            if auth: token = auth.get('token')

        if not token: return None
        
        secret_key = current_app.config.get('JWT_SECRET_KEY') or Config.SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])# type: ignore
        return User.query.get(payload.get('sub'))
    except:
        return None

@socketio.on('join_chat')
def handle_join_chat(data):
    user = get_current_socket_user()
    if not user: return
    
    chat_id = data.get('chat_id')
    if not chat_id: return
    
    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=user.id).first()
    if participant:
        join_room(chat_id)
        participant.unread_count = 0
        db.session.commit()

@socketio.on('send_message')
def handle_send_message(data):
    try:
        sender = get_current_socket_user()
        if not sender: return

        chat_id = data.get('chat_id')
        text = data.get('text')
        msg_type = data.get('type', 'text')
        reply_to_id = data.get('reply_to_id')

        if not chat_id or not text: return
        
        chat = Chat.query.get(chat_id)
        if not chat: return

        if not chat.is_group:
            recipient_part = ChatParticipant.query.filter(
                ChatParticipant.chat_id == chat_id, 
                ChatParticipant.user_id != sender.id
            ).first()
            
            if recipient_part:
                from .models import BlockedUser
                is_blocked = BlockedUser.query.filter_by(
                    blocker_id=recipient_part.user_id, 
                    blocked_id=sender.id
                ).first()
                pass 

        new_message = Message(
            id=uuid.uuid4(), # type: ignore
            chat_id=chat_id, # type: ignore
            sender_id=sender.id, # type: ignore
            text=text, # type: ignore
            type=msg_type, # type: ignore
            sent_at=datetime.now(timezone.utc), # type: ignore
            reply_to_id=reply_to_id  # type: ignore
        )
        db.session.add(new_message)

        if chat:
            chat.last_message_text = text if msg_type == 'text' else '📷 Mengirim gambar'
            chat.last_message_time = new_message.sent_at
        
        participants = ChatParticipant.query.filter_by(chat_id=chat_id).all()
        
        blocked_by_ids = []
        if chat.is_group:
            from .models import BlockedUser
            blocks = BlockedUser.query.filter_by(blocked_id=sender.id).all()
            blocked_by_ids = [str(b.blocker_id) for b in blocks]

        for p in participants:
            pid = str(p.user_id).lower()
            sid = str(sender.id).lower()

            p.is_hidden = False

            if pid != sid:
                if chat.is_group and pid in blocked_by_ids:
                    continue
                
                if not chat.is_group:
                    from .models import BlockedUser
                    is_blocked = BlockedUser.query.filter_by(blocker_id=p.user_id, blocked_id=sender.id).first()
                    if is_blocked:
                        continue

                p.unread_count += 1
                receiver = User.query.get(p.user_id)
                
                if receiver and receiver.onesignal_player_id:

                    notif_title = chat.name if chat.is_group else sender.display_name

                    base_content = text if msg_type == 'text' else '📷 Mengirim gambar'
                    
                    if chat.is_group:
                        notif_content = f"{sender.display_name}: {base_content}"
                    else:
                        notif_content = base_content

                    NotificationService().send_chat_notification(
                        recipient_ids=[receiver.onesignal_player_id],
                        title=notif_title,
                        content=notif_content,
                        chat_id=chat.id,        
                        is_group=chat.is_group, 
                        sender_avatar_path=sender.avatar_url
                    )
            
        db.session.commit()

        reply_info = None
        if reply_to_id:
            parent = Message.query.get(reply_to_id)
            if parent:
                reply_text = parent.text if not parent.is_deleted else "Pesan dihapus"
                reply_info = {
                    "id": str(parent.id),
                    "text": reply_text,
                    "sender_name": parent.sender.display_name if parent.sender else "Unknown"
                }

        response_data = {
            'id': str(new_message.id),
            'chat_id': str(chat_id),
            'text': new_message.text,
            'sender_id': str(sender.id),
            'sender_name': sender.display_name,
            'sender_avatar': get_full_url(sender.avatar_url),
            'sender_is_verified': sender.is_verified,
            'sent_at': new_message.sent_at.isoformat(),
            'type': msg_type,
            'is_read': False,
            'reply_to': reply_info
        }
        
        if chat.is_group:
             for p in participants:
                pid = str(p.user_id)
                if pid == str(sender.id) or pid not in blocked_by_ids:
                     socketio.emit('new_message', response_data, to=pid)
        else:
            socketio.emit('new_message', response_data, to=str(sender.id))
            
            recipient_part = ChatParticipant.query.filter(
                ChatParticipant.chat_id == chat_id, 
                ChatParticipant.user_id != sender.id
            ).first()
            
            if recipient_part:
                from .models import BlockedUser
                is_blocked = BlockedUser.query.filter_by(blocker_id=recipient_part.user_id, blocked_id=sender.id).first()
                if not is_blocked:
                    socketio.emit('new_message', response_data, to=str(recipient_part.user_id))

        
        for p in participants:
            pid = str(p.user_id).lower()
            if pid != str(sender.id).lower():
                if chat.is_group and pid in blocked_by_ids:
                    continue
                if not chat.is_group:
                     from .models import BlockedUser
                     is_blocked = BlockedUser.query.filter_by(blocker_id=p.user_id, blocked_id=sender.id).first()
                     if is_blocked: continue

                emit('inbox_update', {
                    'chat_id': str(chat_id),
                    'last_message': chat.last_message_text,
                    'last_sender_name': sender.display_name,
                    'time': chat.last_message_time.isoformat(),
                    'unread_count': p.unread_count
                }, to=pid)

    except Exception:
        db.session.rollback()
        
@socketio.on('typing')
def handle_typing(data):
    chat_id = data.get('chat_id')
    is_typing = data.get('is_typing')
    sender = get_current_socket_user()
    
    if sender and chat_id:
        emit('user_typing', {
            'chat_id': chat_id,
            'user_id': str(sender.id),
            'username': sender.username,
            'is_typing': is_typing
        }, to=chat_id, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    pass

@socketio.on('mark_read')
def handle_mark_read(data):
    try:
        reader = get_current_socket_user()
        if not reader: return

        chat_id = data.get('chat_id')
        if not chat_id: return
        
        participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=reader.id).first()
        if participant:
            participant.unread_count = 0
            db.session.commit()
        
        unread_messages = Message.query.filter(
            Message.chat_id == chat_id,
            Message.sender_id != reader.id,
            Message.is_read_by_all == False
        ).all()

        if unread_messages:
            from .models import BlockedUser
            changed = False
            for msg in unread_messages:
                other_participants = ChatParticipant.query.filter(
                    ChatParticipant.chat_id == chat_id, 
                    ChatParticipant.user_id != msg.sender_id
                ).all()
                
                all_eligible_read = True
                for p in other_participants:
                    is_blocking_sender = BlockedUser.query.filter_by(
                        blocker_id=p.user_id, 
                        blocked_id=msg.sender_id
                    ).first() is not None
                    
                    if not is_blocking_sender and p.unread_count > 0:
                        all_eligible_read = False
                        break
                
                if all_eligible_read:
                    msg.is_read_by_all = True
                    changed = True
            
            if changed:
                db.session.commit()
                emit('messages_read', {'chat_id': chat_id}, to=chat_id)
    except Exception:
        pass