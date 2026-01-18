from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, Chat, ChatParticipant, Message, User, GroupBannedUser, GroupInvite
from sqlalchemy import desc, func
from werkzeug.utils import secure_filename
from ..extensions import socketio, limiter

import uuid
import os
import json
import secrets
from datetime import datetime, timezone, timedelta

chat_bp = Blueprint('chat', __name__)

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

@chat_bp.route('/inbox', methods=['GET'])
@limiter.limit("30 per minute")
@jwt_required()
def get_inbox():
    user_id = get_jwt_identity()
    
    participations = ChatParticipant.query.filter_by(user_id=user_id).all()
    chat_ids = [p.chat_id for p in participations]
    
    chats = Chat.query.filter(Chat.id.in_(chat_ids)).order_by(desc(Chat.last_message_time)).all()
    
    from ..models import BlockedUser
    blocked_ids = [str(b.blocked_id) for b in BlockedUser.query.filter_by(blocker_id=user_id).all()]
    i_am_blocked_by = [str(b.blocker_id) for b in BlockedUser.query.filter_by(blocked_id=user_id).all()]
    
    results = []
    for chat in chats:
        my_p_info = ChatParticipant.query.filter_by(chat_id=chat.id, user_id=user_id).first()
        if not my_p_info: continue

        other_participant = None
        is_blocked_by_me = False

        if not chat.is_group:
            other_p = ChatParticipant.query.filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id != user_id).first()
            if other_p:
                target_uid_str = str(other_p.user_id)
                is_blocked_by_me = target_uid_str in blocked_ids
                other_participant = User.query.get(other_p.user_id)

        last_msg_obj = Message.query.filter_by(chat_id=chat.id).order_by(desc(Message.sent_at)).first()
        
        last_msg_text = chat.last_message_text
        last_sender_name = ""

        if my_p_info.last_cleared_at and last_msg_obj:
            if last_msg_obj.sent_at <= my_p_info.last_cleared_at:
                last_msg_text = ""
            else:
                last_msg_text = last_msg_obj.text if not last_msg_obj.is_deleted else "🚫 Pesan ini telah dihapus"
                last_sender_name = "Anda" if str(last_msg_obj.sender_id) == str(user_id) else (last_msg_obj.sender.display_name if last_msg_obj.sender else "")
        elif last_msg_obj:
            last_msg_text = last_msg_obj.text if not last_msg_obj.is_deleted else "🚫 Pesan ini telah dihapus"
            last_sender_name = "Anda" if str(last_msg_obj.sender_id) == str(user_id) else (last_msg_obj.sender.display_name if last_msg_obj.sender else "")

        raw_image = chat.image_url if chat.is_group else (other_participant.avatar_url if other_participant else "")

        target_user_verified = False
        if not chat.is_group and other_participant:
            target_user_verified = other_participant.is_verified

        results.append({
            "id": str(chat.id),
            "is_group": chat.is_group,
            "name": chat.name if chat.is_group else (other_participant.display_name if other_participant else "User"),
            "target_user_id": str(other_participant.id) if (not chat.is_group and other_participant) else None,
            "target_username": other_participant.username if (not chat.is_group and other_participant) else None,
            "image_url": get_full_url(raw_image),
            "last_message_text": last_msg_text,
            "last_sender_name": last_sender_name,
            "last_message_time": chat.last_message_time.isoformat() if chat.last_message_time else None,
            "unread_count": my_p_info.unread_count if my_p_info else 0,
            "is_hidden": my_p_info.is_hidden,
            "is_blocked_by_me": is_blocked_by_me,
            "target_user": {
                "is_verified": target_user_verified
            }
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
@limiter.limit("60 per minute")
@jwt_required()
def get_messages(chat_id):
    user_id = get_jwt_identity()
    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    
    query = Message.query.filter_by(chat_id=chat_id)
    
    if participant and participant.last_cleared_at:
        query = query.filter(Message.sent_at > participant.last_cleared_at)

    from ..models import BlockedUser
    blocked_users = BlockedUser.query.filter_by(blocker_id=user_id).all()
    blocked_ids = [b.blocked_id for b in blocked_users]
    
    if blocked_ids:
        query = query.filter(Message.sender_id.notin_(blocked_ids))
        
    messages = query.order_by(desc(Message.sent_at)).limit(50).all()
    results = []
    
    for msg in messages:
        sender_name = "Unknown"
        sender_avatar = None
        sender_username = None

        sender_verified = False

        
        if msg.sender:
            sender_name = msg.sender.display_name
            sender_verified = msg.sender.is_verified
            sender_username = msg.sender.username
            sender_avatar = get_full_url(msg.sender.avatar_url)

        reply_data = None
        if msg.reply_to:
            reply_text = msg.reply_to.text
            if msg.reply_to.is_deleted:
                reply_text = "Pesan dihapus"
            
            reply_data = {
                "id": str(msg.reply_to.id),
                "text": reply_text,
                "sender_name": msg.reply_to.sender.display_name if msg.reply_to.sender else "Unknown"
            }

        final_text = msg.text
        if msg.is_deleted:
            final_text = "🚫 Pesan ini telah dihapus"

        results.append({
            "id": str(msg.id),
            "chat_id": str(msg.chat_id),
            "sender_id": str(msg.sender_id) if msg.sender_id else None,
            "sender_name": sender_name,
            "sender_is_verified": sender_verified,
            "sender_username": sender_username,
            "sender_avatar": sender_avatar, 
            "text": final_text,
            "type": msg.type,
            "sent_at": msg.sent_at.isoformat(),
            "is_read": msg.is_read_by_all,
            "is_deleted": msg.is_deleted,
            "reply_to": reply_data
        })
    return jsonify(results), 200

@chat_bp.route('/group/create', methods=['POST'])
@limiter.limit("5 per hour")
@jwt_required()
def create_group():
    user_id = get_jwt_identity()
    
    name = request.form.get('name')
    members_json = request.form.get('members', '[]')
    allow_invites = request.form.get('allow_invites') == 'true'
    image_file = request.files.get('image')

    if not name:
        return jsonify({"error": "Nama grup wajib diisi"}), 400

    new_group = Chat(
        id=uuid.uuid4(), # type: ignore
        is_group=True, # type: ignore
        name=name, # type: ignore
        created_by=user_id, # type: ignore
        allow_member_invites=allow_invites # type: ignore
    )
    
    if image_file:
        filename = secure_filename(f"grp_{uuid.uuid4().hex[:8]}_{image_file.filename}")
        path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        image_file.save(path)
        new_group.image_url = filename

    db.session.add(new_group)
    db.session.add(ChatParticipant(chat_id=new_group.id, user_id=user_id, is_admin=True)) # type: ignore

    try:
        member_ids = json.loads(members_json)
        for mid in member_ids:
            if str(mid) == str(user_id): continue
            if not GroupBannedUser.query.filter_by(group_id=new_group.id, user_id=mid).first():
                db.session.add(ChatParticipant(chat_id=new_group.id, user_id=mid)) # type: ignore
    except:
        pass

    db.session.commit()
    return jsonify({"success": True, "chat_id": str(new_group.id)}), 201

@chat_bp.route('/group/<uuid:chat_id>/invite', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required()
def invite_to_group(chat_id):
    sender_id = get_jwt_identity()
    data = request.get_json()
    target_user_id = data.get('target_user_id')

    is_member = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=sender_id).first()
    if not is_member:
        return jsonify({"error": "Anda bukan anggota grup ini"}), 403

    existing = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=target_user_id).first()
    if existing:
        return jsonify({"error": "User sudah ada di grup"}), 400

    if GroupBannedUser.query.filter_by(group_id=chat_id, user_id=target_user_id).first():
        return jsonify({"error": "User ini telah diblokir dari grup"}), 400

    chat_info = Chat.query.get(chat_id)
    return jsonify({
        "success": True, 
        "group_name": chat_info.name, # type: ignore
        "invite_code": str(chat_id) 
    }), 200

@chat_bp.route('/group/<uuid:chat_id>/join', methods=['POST'])
@jwt_required()
def join_group(chat_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if GroupBannedUser.query.filter_by(group_id=chat_id, user_id=user_id).first():
        return jsonify({"error": "Anda telah diblokir dari grup ini."}), 403

    chat = Chat.query.get(chat_id)
    if not chat: return jsonify({"error": "Grup tidak ditemukan"}), 404

    if ChatParticipant.query.filter_by(chat_id=chat_id, user_id=user_id).first():
        return jsonify({"message": "Sudah bergabung"}), 200

    new_member = ChatParticipant(chat_id=chat_id, user_id=user_id) # type: ignore
    db.session.add(new_member)
    
    sys_msg = Message(
        id=uuid.uuid4(), chat_id=chat_id, type='system', # type: ignore
        text=f"{user.display_name} bergabung ke grup.", sent_at=datetime.now(timezone.utc) # type: ignore
    )
    db.session.add(sys_msg)
    
    db.session.commit()
    return jsonify({"success": True}), 200

@chat_bp.route('/group/<uuid:chat_id>/leave', methods=['POST'])
@jwt_required()
def leave_group(chat_id):
    user_id = get_jwt_identity()
    p = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    
    if not p: return jsonify({"error": "Bukan anggota"}), 400
    
    user = User.query.get(user_id)
    db.session.delete(p)
    
    sys_msg = Message(
        id=uuid.uuid4(), chat_id=chat_id, type='system', # type: ignore
        text=f"{user.display_name} keluar dari grup.", sent_at=datetime.now(timezone.utc) # type: ignore
    )
    db.session.add(sys_msg)
    db.session.commit()
    
    return jsonify({"message": "Berhasil keluar"}), 200

@chat_bp.route('/group/<uuid:chat_id>/details', methods=['GET'])
@jwt_required()
def get_group_details(chat_id):
    current_user_id = get_jwt_identity()
    
    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({"error": "Chat tidak ditemukan"}), 404

    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    if not me:
        return jsonify({"error": "Akses ditolak"}), 403

    participants = db.session.query(ChatParticipant, User)\
        .join(User, ChatParticipant.user_id == User.id)\
        .filter(ChatParticipant.chat_id == chat_id).all()

    members_data = []
    for part, user in participants:
        avatar = get_full_url(user.avatar_url)
            
        role = 'member'
        if str(chat.created_by) == str(user.id):
            role = 'owner'
        elif part.is_admin:
            role = 'admin'

        members_data.append({
            "id": str(user.id),
            "display_name": user.display_name,
            "username": user.username,
            "avatar_url": avatar,
            "role": role,
            "joined_at": part.joined_at.isoformat(),
            "is_verified": user.is_verified,
        })

    group_image = get_full_url(chat.image_url)

    return jsonify({
        "id": str(chat.id),
        "name": chat.name,
        "image_url": group_image,
        "is_group": chat.is_group,
        "members": members_data,
        "my_role": 'owner' if str(chat.created_by) == current_user_id else ('admin' if me.is_admin else 'member'),
        "allow_member_invites": chat.allow_member_invites 
    }), 200

@chat_bp.route('/group/<uuid:chat_id>/update', methods=['PUT'])
@jwt_required()
def update_group_info(chat_id):
    current_user_id = get_jwt_identity()

    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    if not participant or not participant.is_admin:
        chat = Chat.query.get(chat_id)
        if str(chat.created_by) != current_user_id: # type: ignore
             return jsonify({"error": "Hanya admin yang bisa ubah info grup"}), 403

    chat = Chat.query.get(chat_id)
    data = request.form
    name = data.get('name')
    
    if name:
        chat.name = name # type: ignore

    if 'image' in request.files:
        file = request.files['image']
        if file:
            filename = secure_filename(f"group_{chat_id}_{uuid.uuid4().hex[:6]}.jpg")
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            chat.image_url = filename # type: ignore

    db.session.commit()
    return jsonify({"message": "Info grup diperbarui", "name": chat.name}), 200 # type: ignore


@chat_bp.route('/group/<uuid:chat_id>/add_members', methods=['POST'])
@jwt_required()
def add_group_members(chat_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    target_user_ids = data.get('user_ids', [])

    if not ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first():
        return jsonify({"error": "Anda bukan anggota grup"}), 403

    added_count = 0
    banned_users = []
    existing_users = []

    for uid in target_user_ids:
        user = User.query.get(uid)
        if not user: continue

        if GroupBannedUser.query.filter_by(group_id=chat_id, user_id=uid).first():
            banned_users.append(user.display_name)
            continue

        exists = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=uid).first()
        if exists:
            existing_users.append(user.display_name)
            continue
            
        new_member = ChatParticipant(chat_id=chat_id, user_id=uid) # type: ignore
        db.session.add(new_member)
        added_count += 1
    
    db.session.commit()
    
    message_parts = []
    if added_count > 0:
        message_parts.append(f"{added_count} anggota ditambahkan.")
    
    if banned_users:
        message_parts.append(f"Gagal (Banned): {', '.join(banned_users)}.")
        
    if existing_users:
        message_parts.append(f"Sudah bergabung: {', '.join(existing_users)}.")

    final_message = " ".join(message_parts) if message_parts else "Tidak ada perubahan."

    return jsonify({
        "message": final_message,
        "added": added_count,
        "banned": banned_users,     # List nama yang dibanned
        "existing": existing_users  # List nama yang sudah ada
    }), 200
@chat_bp.route('/group/<uuid:chat_id>/set-role', methods=['POST'])
@jwt_required()
def set_group_role(chat_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    target_user_id = data.get('user_id')
    new_role = data.get('role')

    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({"error": "Grup tidak ditemukan"}), 404

    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    if not me or (not me.is_admin and str(chat.created_by) != current_user_id):
        return jsonify({"error": "Hanya Admin/Owner yang bisa mengubah peran"}), 403

    target = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=target_user_id).first()
    if not target:
        return jsonify({"error": "User bukan anggota grup"}), 404

    if str(chat.created_by) == str(target_user_id):
        return jsonify({"error": "Peran Pemilik Grup bersifat permanen"}), 400

    target.is_admin = (new_role == 'admin')
    db.session.commit()
    
    return jsonify({"message": f"Berhasil mengubah peran menjadi {new_role}"}), 200

@chat_bp.route('/group/<uuid:chat_id>/kick', methods=['POST'])
@jwt_required()
def kick_member(chat_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    target_user_id = data.get('user_id')

    chat = Chat.query.get(chat_id)
    if not chat: return jsonify({"error": "Grup tidak ditemukan"}), 404

    if str(chat.created_by) == str(target_user_id):
        return jsonify({"error": "Pemilik grup tidak dapat dikeluarkan"}), 403

    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    
    is_owner = (str(chat.created_by) == current_user_id)
    if not me or (not me.is_admin and not is_owner):
        return jsonify({"error": "Akses ditolak"}), 403

    target = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=target_user_id).first()
    if target and target.is_admin and not is_owner:
        return jsonify({"error": "Hanya Pemilik yang bisa mengeluarkan sesama Admin"}), 403

    if target:
        db.session.delete(target)
        db.session.commit()
        return jsonify({"message": "Anggota berhasil dikeluarkan"}), 200
    
    return jsonify({"error": "Anggota tidak ditemukan"}), 404

@chat_bp.route('/group/<uuid:chat_id>/preview', methods=['GET'])
@jwt_required()
def group_preview(chat_id):
    current_user_id = get_jwt_identity()
    
    chat = Chat.query.get(chat_id)
    if not chat or not chat.is_group:
        return jsonify({"error": "Grup tidak ditemukan"}), 404

    is_member = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first() is not None

    return jsonify({
        "id": str(chat.id),
        "name": chat.name,
        "image_url": get_full_url(chat.image_url),
        "member_count": len(chat.participants),
        "is_member": is_member
    }), 200

@chat_bp.route('/invite-info/<token>', methods=['GET'])
def get_invite_info(token):
    invite = GroupInvite.query.filter_by(token=token).first()
    if not invite:
        return jsonify({"error": "Link tidak valid"}), 404
        
    chat = Chat.query.get(invite.group_id)
    if not chat:
        return jsonify({"error": "Grup tidak ditemukan"}), 404
        
    return jsonify({
        "id": str(chat.id),
        "name": chat.name,
        "image_url": get_full_url(chat.image_url),
        "member_count": len(chat.participants),
    }), 200

@chat_bp.route('/group/<uuid:chat_id>/ban', methods=['POST'])
@jwt_required()
def ban_member(chat_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    target_user_id = data.get('user_id')

    chat = Chat.query.get(chat_id)
    if not chat: return jsonify({"error": "Grup tidak ditemukan"}), 404

    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    is_owner = str(chat.created_by) == current_user_id
    
    if not me or (not me.is_admin and not is_owner):
        return jsonify({"error": "Akses ditolak"}), 403

    if str(chat.created_by) == str(target_user_id):
        return jsonify({"error": "Pemilik tidak bisa dibanned"}), 403

    ChatParticipant.query.filter_by(chat_id=chat_id, user_id=target_user_id).delete()
    
    existing_ban = GroupBannedUser.query.filter_by(group_id=chat_id, user_id=target_user_id).first()
    if not existing_ban:
        new_ban = GroupBannedUser(group_id=chat_id, user_id=target_user_id) # type: ignore
        db.session.add(new_ban)
    
    db.session.commit()
    return jsonify({"message": "User berhasil dibanned"}), 200

@chat_bp.route('/group/<uuid:chat_id>/unban', methods=['POST'])
@jwt_required()
def unban_member_group(chat_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    target_id = data.get('user_id')

    chat = Chat.query.get(chat_id)
    if not chat: return jsonify({"error": "Grup tidak ditemukan"}), 404

    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    is_owner = str(chat.created_by) == current_user_id
    
    if not me or (not me.is_admin and not is_owner):
        return jsonify({"error": "Akses ditolak"}), 403

    GroupBannedUser.query.filter_by(group_id=chat_id, user_id=target_id).delete()
    db.session.commit()
    return jsonify({"message": "User di-unban"}), 200

@chat_bp.route('/group/<uuid:chat_id>/banned', methods=['GET'])
@jwt_required()
def get_banned_list(chat_id):
    current_user_id = get_jwt_identity()
    chat = Chat.query.get(chat_id)
    
    if not chat: return jsonify({"error": "Grup tidak ditemukan"}), 404

    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    is_owner = str(chat.created_by) == current_user_id
    
    if not me or (not me.is_admin and not is_owner):
        return jsonify({"error": "Akses ditolak"}), 403

    banned = db.session.query(GroupBannedUser, User)\
        .join(User, GroupBannedUser.user_id == User.id)\
        .filter(GroupBannedUser.group_id == chat_id).all()
        
    results = [{"id": str(u.id), "name": u.display_name, "username": u.username, "avatar_url": get_full_url(u.avatar_url)} for b, u in banned]
    return jsonify(results), 200

@chat_bp.route('/group/<uuid:chat_id>/settings', methods=['PATCH'])
@jwt_required()
def update_group_settings(chat_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    chat = Chat.query.get(chat_id)
    if not chat: return jsonify({"error": "Grup tidak ditemukan"}), 404

    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    if not me or not me.is_admin:
        if str(chat.created_by) != current_user_id:
            return jsonify({"error": "Hanya admin yang bisa mengubah pengaturan"}), 403

    if 'allow_member_invites' in data:
        chat.allow_member_invites = data['allow_member_invites']

    db.session.commit()
    return jsonify({"message": "Pengaturan diperbarui", "allow_member_invites": chat.allow_member_invites}), 200

@chat_bp.route('/group/<uuid:chat_id>/invite-link', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required()
def generate_invite_link(chat_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    type = data.get('type')

    chat = Chat.query.get(chat_id)
    if not chat: return jsonify({"error": "Grup tidak ditemukan"}), 404

    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    if not me: return jsonify({"error": "Bukan anggota"}), 403

    is_admin_or_owner = me.is_admin or (str(chat.created_by) == current_user_id)
    
    if not is_admin_or_owner and not chat.allow_member_invites:
        return jsonify({"error": "Hanya admin yang boleh mengundang"}), 403

    token = secrets.token_urlsafe(16)
    expires_at = None
    max_uses = None

    if type == '24h':
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    elif type == '1x':
        max_uses = 1
    
    invite = GroupInvite(
        token=token, # type: ignore
        group_id=chat_id, # type: ignore
        created_by=current_user_id, # type: ignore
        expires_at=expires_at, # type: ignore
        max_uses=max_uses # type: ignore
    )
    db.session.add(invite)
    db.session.commit()

    return jsonify({"url": f"{request.host_url}join/{token}"}), 200

@chat_bp.route('/join/<token>', methods=['POST'])
@jwt_required()
def join_group_via_token(token):
    current_user_id = get_jwt_identity()
    
    invite = GroupInvite.query.filter_by(token=token).first()
    if not invite:
        return jsonify({"error": "Link tidak valid"}), 404

    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        return jsonify({"error": "Link kadaluwarsa"}), 400

    if invite.max_uses and invite.current_uses >= invite.max_uses:
        return jsonify({"error": "Link sudah mencapai batas penggunaan"}), 400

    chat_id = invite.group_id
    
    if GroupBannedUser.query.filter_by(group_id=chat_id, user_id=current_user_id).first():
        return jsonify({"error": "Anda telah diblokir dari grup ini"}), 403

    existing = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    if existing:
        return jsonify({"message": "Sudah bergabung", "chat_id": str(chat_id)}), 200

    new_member = ChatParticipant(chat_id=chat_id, user_id=current_user_id) # type: ignore
    db.session.add(new_member)
    
    invite.current_uses += 1
    db.session.commit()

    return jsonify({"success": True, "chat_id": str(chat_id)}), 200

@chat_bp.route('/group/<uuid:chat_id>/invites', methods=['GET'])
@jwt_required()
def get_group_invites(chat_id):
    current_user_id = get_jwt_identity()
    
    me = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user_id).first()
    chat = Chat.query.get(chat_id)
    
    is_owner = str(chat.created_by) == current_user_id # type: ignore
    if not me or (not me.is_admin and not is_owner):
        return jsonify({"error": "Hanya admin yang bisa melihat daftar link"}), 403

    invites = db.session.query(GroupInvite, User).join(User, GroupInvite.created_by == User.id)\
        .filter(GroupInvite.group_id == chat_id).all()

    active_invites = []
    for inv, creator in invites:
        if inv.expires_at and inv.expires_at < datetime.now(timezone.utc):
            continue 
        if inv.max_uses and inv.current_uses >= inv.max_uses:
            continue

        active_invites.append({
            "token": inv.token,
            "url": f"{request.host_url}join/{inv.token}",
            "created_by": creator.display_name,
            "created_at": inv.created_at.isoformat(),
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else "Selamanya",
            "uses": f"{inv.current_uses} / {inv.max_uses if inv.max_uses else '∞'}"
        })

    return jsonify(active_invites), 200

@chat_bp.route('/invite/<token>', methods=['DELETE'])
@jwt_required()
def revoke_invite(token):
    current_user_id = get_jwt_identity()
    
    invite = GroupInvite.query.filter_by(token=token).first()
    if not invite: return jsonify({"error": "Link tidak ditemukan"}), 404

    me = ChatParticipant.query.filter_by(chat_id=invite.group_id, user_id=current_user_id).first()
    chat = Chat.query.get(invite.group_id)
    is_owner = str(chat.created_by) == current_user_id # type: ignore

    if not me or (not me.is_admin and not is_owner):
        return jsonify({"error": "Akses ditolak"}), 403

    db.session.delete(invite)
    db.session.commit()
    return jsonify({"message": "Link berhasil dicabut"}), 200

@chat_bp.route('/<uuid:chat_id>/clear', methods=['POST'])
@jwt_required()
def clear_chat(chat_id):
    user_id = get_jwt_identity()
    p = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    if p:
        p.last_cleared_at = datetime.now(timezone.utc)
        db.session.commit()
    return jsonify({"message": "Chat dibersihkan"}), 200

@chat_bp.route('/message/<uuid:msg_id>', methods=['DELETE'])
@jwt_required()
def delete_message(msg_id):
    user_id = get_jwt_identity()
    msg = Message.query.get(msg_id)
    
    if not msg: return jsonify({"error": "Pesan tidak ada"}), 404
    if str(msg.sender_id) != user_id:
        return jsonify({"error": "Bukan pesan Anda"}), 403
        
    msg.is_deleted = True
    db.session.commit()
    
    socketio.emit('message_deleted', {'msg_id': str(msg_id), 'chat_id': str(msg.chat_id)}, to=str(msg.chat_id))
    return jsonify({"message": "Pesan dihapus"}), 200


@chat_bp.route('/<uuid:chat_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(chat_id):
    user_id = get_jwt_identity()
    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    
    if not participant:
        return jsonify({"error": "Percakapan tidak ditemukan"}), 404

    try:
        participant.is_hidden = True
        participant.last_cleared_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({"message": "Percakapan berhasil dihapus dari daftar Anda"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500