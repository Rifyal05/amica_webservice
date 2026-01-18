from flask import request, current_app
from flask_socketio import emit, join_room, leave_room, disconnect
from .extensions import socketio, db
from .models import User, Chat, Message, ChatParticipant, ToxicMessageCounter, BlockedUser
from .config import Config
from .services.notification_service import NotificationService
from .services.post_classification_service import post_classifier
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
            payload = jwt.decode(token, secret_key, algorithms=["HS256"]) # type: ignore
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
        if not token and hasattr(request, 'event') and request.event: # type: ignore
            auth = request.event.get('auth', {}) # type: ignore
            if auth: token = auth.get('token')

        if not token: return None
        
        secret_key = current_app.config.get('JWT_SECRET_KEY') or Config.SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=["HS256"]) # type: ignore
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

        is_ghosted = False
        is_toxic = False
        counter = None
        receiver = None 

        if not chat.is_group:
            recipient_part = ChatParticipant.query.filter(
                ChatParticipant.chat_id == chat_id, 
                ChatParticipant.user_id != sender.id
            ).first()
            
            if recipient_part:
                receiver = User.query.get(recipient_part.user_id)
                is_blocked = BlockedUser.query.filter_by(blocker_id=recipient_part.user_id, blocked_id=sender.id).first() is not None
                
                if receiver and receiver.is_ai_moderation_enabled and msg_type == 'text':
                    category, _ = post_classifier.predict(text)
                    if category not in {'Bersih', 'SAFE'}:
                        is_toxic = True
                        today = datetime.now(timezone.utc).date()
                        counter = ToxicMessageCounter.query.filter_by(
                            sender_id=sender.id, receiver_id=receiver.id, date=today
                        ).first()
                        
                        if not counter:
                            counter = ToxicMessageCounter(sender_id=sender.id, receiver_id=receiver.id, date=today, count=1) # type: ignore
                            db.session.add(counter)
                        else:
                            counter.count += 1
                        
                        db.session.commit()

                        if counter.count >= 10:
                            if not BlockedUser.query.filter_by(blocker_id=receiver.id, blocked_id=sender.id).first():
                                db.session.add(BlockedUser(blocker_id=receiver.id, blocked_id=sender.id)) # type: ignore
                                db.session.commit()
                                socketio.emit('moderation_blocked', {
                                    'chat_id': str(chat_id),
                                    'user_name': sender.display_name,
                                    'user_id': str(sender.id)
                                }, to=str(receiver.id))
                                is_ghosted = True
                
                if is_blocked or is_ghosted:
                    is_ghosted = True

        if is_ghosted:
            ghost_time = datetime.now(timezone.utc).isoformat()
            
            response_data = {
                'id': str(uuid.uuid4()),
                'chat_id': str(chat_id),
                'text': text,
                'sender_id': str(sender.id),
                'sender_name': sender.display_name,
                'sender_avatar': get_full_url(sender.avatar_url),
                'sender_is_verified': sender.is_verified,
                'sent_at': ghost_time,
                'type': msg_type,
                'is_read': False,
                'is_delivered': False,
                'reply_to': None
            }
            socketio.emit('new_message', response_data, to=str(sender.id))
            
            socketio.emit('inbox_update', {
                'chat_id': str(chat_id),
                'last_message': text,
                'last_sender_name': sender.display_name,
                'time': ghost_time,
                'unread_count': 0
            }, to=str(sender.id))

            if is_toxic and receiver and receiver.is_ai_moderation_enabled and counter and counter.count < 10:
                warning_message = f"🚫 Pesan Anda terdeteksi melanggar pedoman. Penerima mengaktifkan Moderasi AI. Anda akan diblokir otomatis jika melanggar {10 - counter.count} kali lagi hari ini."
                
                socketio.emit('moderation_warning', {
                    'chat_id': str(chat_id),
                    'warning': warning_message
                }, to=str(sender.id))
            
            return

        new_message = Message(
            id=uuid.uuid4(),# type: ignore
            chat_id=chat_id,# type: ignore
            sender_id=sender.id,# type: ignore
            text=text,# type: ignore
            type=msg_type,# type: ignore
            sent_at=datetime.now(timezone.utc),# type: ignore
            reply_to_id=reply_to_id  # type: ignore
        )
        db.session.add(new_message)

        chat.last_message_text = text if msg_type == 'text' else '📷 Mengirim gambar'
        chat.last_message_time = new_message.sent_at
        
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
            'is_delivered': False,
            'reply_to': reply_info
        }
        
        participants = ChatParticipant.query.filter_by(chat_id=chat_id).all()
        blocked_by_ids = []
        if chat.is_group:
            blocks = BlockedUser.query.filter_by(blocked_id=sender.id).all()
            blocked_by_ids = [str(b.blocker_id) for b in blocks]

        for p in participants:
            pid = str(p.user_id)
            p.is_hidden = False
            
            if pid == str(sender.id):
                socketio.emit('new_message', response_data, to=pid)
                continue

            if chat.is_group and pid in blocked_by_ids:
                continue
                
            if not chat.is_group:
                is_blocking = BlockedUser.query.filter_by(blocker_id=p.user_id, blocked_id=sender.id).first()
                if is_blocking: continue

            p.unread_count += 1
            socketio.emit('new_message', response_data, to=pid)
            
            socketio.emit('inbox_update', {
                'chat_id': str(chat_id),
                'last_message': chat.last_message_text,
                'last_sender_name': sender.display_name,
                'time': chat.last_message_time.isoformat(),
                'unread_count': p.unread_count
            }, to=pid)

            receiver_user = User.query.get(p.user_id)
            if receiver_user and receiver_user.onesignal_player_id:
                notif_title = chat.name if chat.is_group else sender.display_name
                base_content = text if msg_type == 'text' else '📷 Mengirim gambar'
                notif_content = f"{sender.display_name}: {base_content}" if chat.is_group else base_content
                NotificationService().send_chat_notification(
                    recipient_ids=[receiver_user.onesignal_player_id],
                    title=notif_title,
                    content=notif_content,
                    chat_id=chat.id,        
                    is_group=chat.is_group, 
                    sender_avatar_path=sender.avatar_url,
                    message_id=new_message.id
                )
        
        db.session.commit()
    except Exception:
        db.session.rollback()

@socketio.on('message_received')
def handle_message_received(data):
    try:
        msg_id = data.get('message_id')
        chat_id = data.get('chat_id')
        sender_id = data.get('sender_id')
        
        msg = Message.query.get(msg_id)
        if msg:
            if not msg.is_delivered:
                msg.is_delivered = True 
                try:
                    db.session.add(msg)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                finally:
                    db.session.remove()

            socketio.emit('message_delivered', {
                'message_id': str(msg_id),
                'chat_id': str(chat_id)
            }, to=str(sender_id))
    except Exception:
        pass
        
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
        unread_messages = Message.query.filter(Message.chat_id == chat_id, Message.sender_id != reader.id, Message.is_read_by_all == False).all()
        if unread_messages:
            changed = False
            for msg in unread_messages:
                other_participants = ChatParticipant.query.filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id != msg.sender_id).all()
                all_eligible_read = True
                for p in other_participants:
                    is_blocking_sender = BlockedUser.query.filter_by(blocker_id=p.user_id, blocked_id=msg.sender_id).first() is not None
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