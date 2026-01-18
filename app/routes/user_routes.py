from flask import Blueprint, jsonify, request, current_app
from ..services.user_action_service import UserActionService
from ..models import User, Connection, Post, db, SavedPost, PostLike
from flask_jwt_extended import jwt_required, get_jwt_identity 
from ..services.notif_manager import create_notification
from ..services.image_moderation_service import image_moderator
import uuid
import os
import jwt
from werkzeug.utils import secure_filename
from ..extensions import limiter

user_bp = Blueprint('user', __name__) 

user_action_service = UserActionService()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'avif', 'tif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def user_to_dict(user):
    from ..models import Post, Connection
    
    def get_only_filename(path):
        if not path: return None
        if path.startswith('http'): return path
        return path.split('/')[-1]

    avatar = get_only_filename(user.avatar_url)
    banner = get_only_filename(user.banner_url)
    
    posts_count = Post.query.filter_by(user_id=user.id, moderation_status='approved').count()
    followers_count = Connection.query.filter_by(following_id=user.id).count()

    return {
        'id': str(user.id), 
        'username': user.username, 
        'display_name': user.display_name,
        'avatar_url': avatar,
        'banner_url': banner,
        'is_verified': user.is_verified,
        'is_ai_moderation_enabled': getattr(user, 'is_ai_moderation_enabled', False),
        'stats': {
            'posts': posts_count,
            'followers': followers_count
        }
    }

@user_bp.route('/update', methods=['PUT'])
@limiter.limit("5 per minute")
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    display_name = request.form.get('display_name')
    bio = request.form.get('bio')
    username = request.form.get('username')
    
    if display_name:
        current_user.display_name = display_name
    
    if bio is not None: 
        current_user.bio = bio

    if username and username != current_user.username:
        existing = User.query.filter_by(username=username).first()
        if existing:
            return jsonify({"error": "Username sudah digunakan"}), 409
        current_user.username = username

    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and allowed_file(file.filename):
            file_bytes = file.read()
            status, reason = image_moderator.predict(file_bytes)
            
            if status == "unsafe":
                return jsonify({
                    "error": "Gambar avatar mengandung konten tidak aman",
                    "reason": reason
                }), 400
            
            file.seek(0)
            filename = secure_filename(f"avatar_{current_user.id}_{uuid.uuid4().hex[:6]}.{file.filename.rsplit('.', 1)[1]}")  # type: ignore
            file.save(os.path.join(upload_folder, filename))
            current_user.avatar_url = filename 

    if 'banner' in request.files:
        file = request.files['banner']
        if file and allowed_file(file.filename):
            file_bytes = file.read()
            status, reason = image_moderator.predict(file_bytes)
            
            if status == "unsafe":
                return jsonify({
                    "error": "Gambar banner mengandung konten tidak aman",
                    "reason": reason
                }), 400
            
            file.seek(0)
            filename = secure_filename(f"banner_{current_user.id}_{uuid.uuid4().hex[:6]}.{file.filename.rsplit('.', 1)[1]}")  # type: ignore
            file.save(os.path.join(upload_folder, filename))
            current_user.banner_url = filename

    try:
        db.session.commit()
        
        resp_avatar = current_user.avatar_url
        if resp_avatar and not resp_avatar.startswith(('http://', 'https://')):
            if 'static/' not in resp_avatar:
                resp_avatar = f"static/uploads/{resp_avatar}"

        resp_banner = current_user.banner_url
        if resp_banner and not resp_banner.startswith(('http://', 'https://')):
            if 'static/' not in resp_banner:
                resp_banner = f"static/uploads/{resp_banner}"

        return jsonify({
            "message": "Profil berhasil diperbarui",
            "user": {
                "display_name": current_user.display_name,
                "username": current_user.username,
                "bio": current_user.bio,
                "avatar_url": resp_avatar,
                "banner_url": resp_banner,
                'is_verified': current_user.is_verified,
                'is_ai_moderation_enabled': current_user.is_ai_moderation_enabled

            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Gagal menyimpan perubahan", "details": str(e)}), 500

@user_bp.route('/<string:user_id>', methods=['GET'])
@limiter.limit("60 per minute")
def get_user_profile(user_id):
    current_user_id = None
    if 'Authorization' in request.headers:
        token_str = request.headers['Authorization']
        if token_str.startswith('Bearer '):
            token = token_str.split(" ")[1]
            try:
                data = jwt.decode(token, os.environ.get('SECRET_KEY'), algorithms=["HS256"])  # type: ignore
                current_user_id = data.get('sub') 
                if not current_user_id:
                     current_user_id = data.get('user_id') 
            except:
                pass

    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        return jsonify({"error": "Invalid UUID format"}), 400

    user = User.query.get(target_uuid)
    if not user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    from ..models import BlockedUser, Connection, Post, ProfessionalProfile
    is_blocked_by_me = False
    i_am_blocked = False

    if current_user_id:
        is_blocked_by_me = BlockedUser.query.filter_by(blocker_id=current_user_id, blocked_id=target_uuid).first() is not None
        i_am_blocked = BlockedUser.query.filter_by(blocker_id=target_uuid, blocked_id=current_user_id).first() is not None

    resp_avatar = user.avatar_url
    if resp_avatar and not resp_avatar.startswith(('http://', 'https://')):
        if 'static/' not in resp_avatar:
            resp_avatar = f"static/uploads/{resp_avatar}"

    resp_banner = user.banner_url
    if resp_banner and not resp_banner.startswith(('http://', 'https://')):
        if 'static/' not in resp_banner:
            resp_banner = f"static/uploads/{resp_banner}"

    if is_blocked_by_me or i_am_blocked:
        return jsonify({
            "id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "bio": "Akun tidak tersedia" if i_am_blocked else "Anda telah memblokir akun ini",
            "avatar_url": resp_avatar,
            "banner_url": resp_banner,
            "is_verified": user.is_verified,
            "stats": {
                "posts": 0,
                "followers": 0,
                "following": 0
            },
            "status": {
                "is_me": False,
                "is_following": False,
                "is_saved_posts_public": False,
                "is_blocked": is_blocked_by_me,
                "i_am_blocked": i_am_blocked,
                "is_verified": user.is_verified,
            },
            "posts_hidden": True
        }), 200

    posts_count = Post.query.filter_by(user_id=user.id, moderation_status='approved').count()
    followers_count = Connection.query.filter_by(following_id=user.id).count()
    following_count = Connection.query.filter_by(follower_id=user.id).count()

    is_following = False
    is_me = False
    
    if current_user_id:
        if str(current_user_id) == str(user.id):
            is_me = True
        else:
            connection = Connection.query.filter_by(
                follower_id=current_user_id, 
                following_id=user.id
            ).first()
            if connection:
                is_following = True

    pro_data = {}
    if user.is_verified:
        pro = ProfessionalProfile.query.filter_by(user_id=user.id).first()
        if pro:
            pro_data = {
                "full_name": pro.full_name_with_title,
                "str_number": pro.str_number,
                "province": pro.province,
                "address": pro.practice_address,
                "schedule": pro.practice_schedule
            }

    is_saved_public = getattr(user, 'is_saved_posts_public', False) 

    res_body = {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio or "",
        "avatar_url": resp_avatar,
        "banner_url": resp_banner,
        "is_verified": user.is_verified,
        "is_ai_moderation_enabled": getattr(user, 'is_ai_moderation_enabled', False) if is_me else False,
        "stats": {
            "posts": posts_count,
            "followers": followers_count,
            "following": following_count
        },
        "status": {
            "is_me": is_me,
            "is_following": is_following,
            "is_saved_posts_public": is_saved_public,
            "is_blocked": False,
            "i_am_blocked": False,
            "is_verified": user.is_verified,
            "is_ai_moderation_enabled": getattr(user, 'is_ai_moderation_enabled', False) if is_me else False,
        }
    }
    
    res_body.update(pro_data)

    return jsonify(res_body), 200


@user_bp.route('/<string:user_id>/follow', methods=['POST'])
@limiter.limit("20 per minute")
@jwt_required()
def follow_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        return jsonify({"error": "Invalid UUID format"}), 400

    target_user = User.query.get(target_uuid)
    if not target_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    if str(current_user.id) == str(target_uuid):
        return jsonify({"error": "Tidak bisa mengikuti diri sendiri"}), 400

    existing_connection = Connection.query.filter_by(
        follower_id=current_user.id,
        following_id=target_uuid
    ).first()

    try:
        if existing_connection:
            db.session.delete(existing_connection)
            is_following = False
            message = f"Berhenti mengikuti {target_user.username}"
        else:
            new_connection = Connection(
                follower_id=current_user.id,   # type: ignore
                following_id=target_uuid  # type: ignore
            )
            db.session.add(new_connection)
            is_following = True
            message = f"Mulai mengikuti {target_user.username}"

        db.session.commit()

        if is_following:
            create_notification(
                    recipient_id=target_uuid,     
                    sender_id=current_user.id,    
                    type='follow',
                    reference_id=None             
                )

        return jsonify({
            "message": message,
            "is_following": is_following
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Gagal memproses request", "details": str(e)}), 500


@user_bp.route('/block/<string:target_uuid>', methods=['POST'])
@jwt_required()
def handle_block_user(target_uuid): 
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

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
@jwt_required()
def handle_unblock_user(target_uuid): 
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    try:
        blocker_id = current_user.id
        target_id = uuid.UUID(target_uuid)
    except ValueError:
        return jsonify({'error': 'Invalid UUID format for target user'}), 400
        
    success = user_action_service.unblock_user(blocker_id, target_id)
    
    if success:
        from ..models import ToxicMessageCounter
        ToxicMessageCounter.query.filter_by(
            sender_id=target_id, receiver_id=blocker_id
        ).delete()
        db.session.commit()
        
        return jsonify({'message': 'User unblocked successfully'}), 200
    return jsonify({'error': 'User was not found in blocked list or failed to unblock'}), 404


@user_bp.route('/blocked_list', methods=['GET'])
@limiter.limit("10 per minute")
@jwt_required()
def get_blocked_list(): 
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    blocker_id = current_user.id
    blocked_users = user_action_service.get_blocked_users(blocker_id)
    
    blocked_data = [user_to_dict(u) for u in blocked_users]
    
    return jsonify(blocked_data), 200

def serialize_post(post, current_user_id=None):
    image_url = post.image_url
    if image_url and not image_url.startswith('http'):
        if 'static/uploads' not in image_url:
            image_url = f"static/uploads/{image_url}"

    author_avatar = post.author.avatar_url
    if author_avatar and not author_avatar.startswith('http'):
        if 'static/uploads' not in author_avatar:
            author_avatar = f"static/uploads/{author_avatar}"

    is_liked = False
    is_saved = False

    if current_user_id:
        if PostLike.query.filter_by(user_id=current_user_id, post_id=post.id).first():
            is_liked = True
        if SavedPost.query.filter_by(user_id=current_user_id, post_id=post.id).first():
            is_saved = True

    return {
        'id': str(post.id),
        'caption': post.caption,
        'image_url': image_url,
        'created_at': post.created_at.isoformat(),
        'likes_count': post.likes_count,
        'comments_count': post.comments_count,
        'tags': post.tags,
        'is_liked': is_liked, 
        'is_saved': is_saved,  
        'author': {
            'id': str(post.author.id),
            'username': post.author.username,
            'display_name': post.author.display_name,
            'avatar_url': author_avatar,
            'is_verified': post.author.is_verified,
        }
    }


@user_bp.route('/<uuid:target_user_id>/saved-posts', methods=['GET'])
@jwt_required()
def get_saved_posts(target_user_id):
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)

        if not current_user:
            return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404

        target_user = User.query.get(target_user_id)
        if not target_user:
            return jsonify({'success': False, 'message': 'User target tidak ditemukan'}), 404

        is_me = str(current_user.id) == str(target_user_id)
        is_public_collection = getattr(target_user, 'is_saved_posts_public', False)

        if not is_me and not is_public_collection:
            return jsonify({
                'success': False, 
                'error': 'Koleksi Tersimpan bersifat pribadi.',
                'is_private': True
            }), 403

        saved_posts = db.session.query(Post).join(
            SavedPost, SavedPost.post_id == Post.id
        ).filter(
            SavedPost.user_id == target_user_id
        ).order_by(
            SavedPost.saved_at.desc()
        ).all()

        results = [serialize_post(post, current_user.id) for post in saved_posts]

        return jsonify({
            'success': True,
            'posts': results,
            'is_me': is_me
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': 'Terjadi kesalahan server'}), 500

@user_bp.route('/settings/privacy/saved-posts', methods=['PATCH'])
@jwt_required()
def update_saved_privacy():
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)

        if not current_user:
            return jsonify({"success": False, "error": "User tidak ditemukan"}), 404

        data = request.get_json()
        is_public = data.get('is_public')
        
        if is_public is None:
            return jsonify({"success": False, "error": "Data 'is_public' diperlukan"}), 400
            
        current_user.is_saved_posts_public = bool(is_public)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Pengaturan privasi diperbarui",
            "is_public": current_user.is_saved_posts_public
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/device-id', methods=['POST'])
@jwt_required()
def update_device_id():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        player_id = data.get('player_id')
        
        if not player_id:
            return jsonify({'error': 'Player ID required'}), 400
            
        User.query.filter(User.onesignal_player_id == player_id).update({User.onesignal_player_id: None})
        
        user = User.query.get(current_user_id)
        user.onesignal_player_id = player_id  # type: ignore
        db.session.commit()
        
        return jsonify({'message': 'Device ID updated and unified'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@user_bp.route('/<uuid:user_id>/followers', methods=['GET'])
@jwt_required()
def get_user_followers(user_id):
    current_user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search_query = request.args.get('q', '').lower()

    query = db.session.query(User).join(Connection, Connection.follower_id == User.id)\
        .filter(Connection.following_id == user_id)

    if search_query:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search_query}%'),
                User.display_name.ilike(f'%{search_query}%')
            )
        )

    paginated_data = query.paginate(page=page, per_page=per_page, error_out=False)  # type: ignore

    results = []
    for follower in paginated_data.items:
        is_following_back = Connection.query.filter_by(
            follower_id=current_user_id,
            following_id=follower.id
        ).first() is not None

        avatar = follower.avatar_url
        if avatar and not avatar.startswith(('http://', 'https://')):
            if 'static/' not in avatar:
                avatar = f"static/uploads/{avatar}"

        results.append({
            "id": str(follower.id),
            "username": follower.username,
            "display_name": follower.display_name,
            "avatar_url": avatar,
            "is_following": is_following_back,
            "is_me": str(follower.id) == str(current_user_id),
            "is_verified": follower.is_verified,
        })
            
    return jsonify({
        "users": results,
        "has_next": paginated_data.has_next
    }), 200

@user_bp.route('/<uuid:user_id>/following', methods=['GET'])
@jwt_required()
def get_user_following(user_id):
    current_user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search_query = request.args.get('q', '').lower()

    query = db.session.query(User).join(Connection, Connection.following_id == User.id)\
        .filter(Connection.follower_id == user_id)

    if search_query:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search_query}%'),
                User.display_name.ilike(f'%{search_query}%')
            )
        )

    paginated_data = query.paginate(page=page, per_page=per_page, error_out=False)  # type: ignore

    results = []
    for followed_user in paginated_data.items:
        is_following = Connection.query.filter_by(
            follower_id=current_user_id,
            following_id=followed_user.id
        ).first() is not None

        avatar = followed_user.avatar_url
        if avatar and not avatar.startswith(('http://', 'https://')):
            if 'static/' not in avatar:
                avatar = f"static/uploads/{avatar}"

        results.append({
            "id": str(followed_user.id),
            "username": followed_user.username,
            "display_name": followed_user.display_name,
            "avatar_url": avatar,
            "is_following": is_following,
            "is_me": str(followed_user.id) == str(current_user_id),
            "is_verified": followed_user.is_verified,
        })
            
    return jsonify({
        "users": results,
        "has_next": paginated_data.has_next
    }), 200

@user_bp.route('/mutual-friends', methods=['GET'])
@jwt_required()
def get_mutual_friends():
    current_user_id = get_jwt_identity()
    search_query = request.args.get('q', '').lower()

    following_subquery = db.session.query(Connection.following_id).filter_by(follower_id=current_user_id)
    followers_subquery = db.session.query(Connection.follower_id).filter_by(following_id=current_user_id)
    mutual_ids = following_subquery.intersect(followers_subquery)

    query = User.query.filter(User.id.in_(mutual_ids))

    if search_query:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search_query}%'),
                User.display_name.ilike(f'%{search_query}%')
            )
        )

    users = query.limit(50).all()
    return jsonify([user_to_dict(u) for u in users]), 200


@user_bp.route('/settings/moderation', methods=['PATCH'])
@jwt_required()
def toggle_moderation():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()
    
    user.is_ai_moderation_enabled = data.get('enabled', False) # type: ignore
    db.session.commit()
    return jsonify({"success": True, "enabled": user.is_ai_moderation_enabled}) # type: ignore