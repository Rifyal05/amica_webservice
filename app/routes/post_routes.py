from flask import Blueprint, request, jsonify, current_app
from ..models import Post, User, PostLike, Connection, SavedPost, db
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.post_classification_service import post_classifier 
from ..services.image_moderation_service import image_moderator
from ..services.post_services import toggle_save_post 
import uuid
import os
from ..services.notif_manager import create_notification
from werkzeug.utils import secure_filename
from datetime import datetime, timezone 
from ..extensions import limiter
post_bp = Blueprint('post', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}
ALLOWED_TEXT_CATEGORIES = {'SAFE', 'Bersih'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@post_bp.route('/', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required()
def create_post(): 
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404
    
    caption = request.form.get('caption', '').strip()
    tags = request.form.getlist('tags')
    image_file = request.files.get('image')
    
    if not caption:
        return jsonify({"error": "Caption wajib diisi."}), 400
    
    MAX_CAPTION_LENGTH = 2500
    if len(caption) > MAX_CAPTION_LENGTH:
        return jsonify({"error": f"Caption tidak boleh lebih dari {MAX_CAPTION_LENGTH} karakter"}), 400

    text_category, text_confidence = post_classifier.predict(caption)
    text_is_unsafe = text_category not in ALLOWED_TEXT_CATEGORIES

    image_url_to_save = None
    image_is_unsafe = False
    
    moderation_details = {
        'text_status': 'unsafe' if text_is_unsafe else 'safe',
        'text_category': text_category,
    }

    if image_file:
        if not allowed_file(image_file.filename):
            return jsonify({"error": "Invalid image file type"}), 400
        
        image_bytes = image_file.read()
        image_status, image_category = image_moderator.predict(image_bytes)
        image_is_unsafe = (image_status == 'unsafe')
        
        filename = secure_filename(f"{uuid.uuid4().hex}_{image_file.filename}")
        
        target_folder = 'reject' if (image_is_unsafe or text_is_unsafe) else 'uploads'
        upload_path = os.path.join(current_app.root_path, 'static', target_folder)
        os.makedirs(upload_path, exist_ok=True)
        
        with open(os.path.join(upload_path, filename), 'wb') as f:
            f.write(image_bytes)
            
        image_url_to_save = filename
        moderation_details['image_status'] = image_status
        moderation_details['image_category'] = image_category # type: ignore

    new_post = Post()
    new_post.user_id = current_user.id
    new_post.caption = caption
    new_post.tags = tags
    new_post.image_url = image_url_to_save
    new_post.moderation_details = moderation_details
    
    if text_is_unsafe or image_is_unsafe:
        new_post.moderation_status = 'rejected'
        db.session.add(new_post)
        db.session.commit()

        create_notification(
            recipient_id=current_user.id, 
            sender_id=current_user.id,    
            type='post_rejected',        
            reference_id=str(new_post.id),
            text="Postingan Anda ditolak karena melanggar aturan komunitas."
        )
        
        return jsonify({
            "message": "Postingan ditolak oleh moderasi otomatis, Anda dapat mengajukan banding di menu Pengaturan.",
            "post_id": str(new_post.id),
            "status": "rejected",
            "is_moderated": True,
            "moderation_details": moderation_details
        }), 200
    
    new_post.moderation_status = 'approved' 
    db.session.add(new_post)
    db.session.commit()

    return jsonify({
        "message": "Post created successfully", 
        "post_id": str(new_post.id),
        "status": "approved"
    }), 201


@post_bp.route('/', methods=['GET'])
@limiter.limit("60 per minute")
@jwt_required(optional=True) 
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    target_user_id = request.args.get('user_id')
    filter_type = request.args.get('filter', 'latest') 
    
    current_user_id = get_jwt_identity() 

    query = db.session.query(Post, User)\
        .join(User, Post.user_id == User.id)\
        .filter(Post.moderation_status == 'approved')
    
    if current_user_id:
        from ..models import BlockedUser
        blocked_users = BlockedUser.query.filter_by(blocker_id=current_user_id).all()
        blocked_ids = [b.blocked_id for b in blocked_users]
        if blocked_ids:
            query = query.filter(Post.user_id.notin_(blocked_ids))


    if target_user_id:
        try:
            uuid_obj = uuid.UUID(target_user_id)
            query = query.filter(Post.user_id == uuid_obj)
        except ValueError:
            return jsonify({
                "posts": [],
                "pagination": {"has_next": False}
            }), 200
    else:
        if filter_type == 'following':
            if current_user_id:
                query = query.join(Connection, Connection.following_id == Post.user_id)\
                             .filter(Connection.follower_id == current_user_id)
            else:
                return jsonify({
                    "posts": [],
                    "pagination": {"has_next": False}
                }), 200
            
    query = query.order_by(Post.created_at.desc())
    paginated_posts = query.paginate(page=page, per_page=per_page, error_out=False) # type: ignore
    
    results = []
    
    for post, post_author in paginated_posts.items:
        is_liked = False
        is_following = False
        is_saved = False
        
        if current_user_id:
            # Cek Like
            if PostLike.query.filter_by(user_id=current_user_id, post_id=post.id).first():
                is_liked = True

            # Cek Save
            if SavedPost.query.filter_by(user_id=current_user_id, post_id=post.id).first():
                is_saved = True

            # Cek Follow
            if str(post_author.id) != str(current_user_id):
                follow_exists = Connection.query.filter_by(
                    follower_id=current_user_id,
                    following_id=post_author.id
                ).first()
                if follow_exists:
                    is_following = True
        
        image_url = post.image_url
        if image_url and not image_url.startswith('http'):
            if 'static/uploads' not in image_url:
                image_url = f"static/uploads/{image_url}"

        avatar_url = post_author.avatar_url
        if avatar_url and not avatar_url.startswith('http'):
            if 'static/uploads' not in avatar_url:
                avatar_url = f"static/uploads/{avatar_url}"

        dt = post.created_at
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            created_at_str = dt.isoformat().replace('+00:00', 'Z')
        else:
            created_at_str = datetime.now(timezone.utc).isoformat()

        results.append({
            "id": str(post.id),
            "caption": post.caption,
            "tags": post.tags if post.tags else [],
            "image_url": image_url, 
            "created_at": created_at_str,
            "likes_count": post.likes_count,
            "comments_count": post.comments_count,
            "is_liked": is_liked,
            "is_saved": is_saved,
            "author": {
                "id": str(post_author.id),
                "display_name": post_author.display_name,
                "username": post_author.username,
                "avatar_url": avatar_url,
                "is_following": is_following,
                "is_verified": post_author.is_verified,

            }
        })
    
    return jsonify({
        "posts": results,
        "pagination": { 
            "total_pages": paginated_posts.pages,
            "current_page": paginated_posts.page,
            "has_next": paginated_posts.has_next
        }
    }), 200

@post_bp.route('/<uuid:post_id>/like', methods=['POST'])
@limiter.limit("30 per minute")
@jwt_required()
def toggle_like(post_id): 
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    like = PostLike.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    try:
        if like:
            db.session.delete(like)
            post.likes_count = max(0, post.likes_count - 1)
            liked = False
        else:
            new_like = PostLike()
            new_like.user_id = current_user.id
            new_like.post_id = post_id
            db.session.add(new_like)
            post.likes_count += 1
            liked = True
        
        db.session.commit()
        
        if liked:
            create_notification(
                recipient_id=post.user_id,
                sender_id=current_user.id,
                type='like',
                reference_id=str(post.id)
            )

        return jsonify({
            "message": "Success",
            "liked": liked,
            "likes_count": post.likes_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not process like", "details": str(e)}), 500
    

@post_bp.route('/<uuid:post_id>', methods=['DELETE'])
@limiter.limit("5 per minute") 
@jwt_required()
def delete_post(post_id):
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    post = Post.query.get(post_id)
    
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if post.user_id != current_user.id:
        return jsonify({"error": "Forbidden. You do not own this post."}), 403

    try:
        db.session.delete(post)
        db.session.commit()
        return jsonify({"message": f"Post {post_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete post", "details": str(e)}), 500
    

@post_bp.route('/<uuid:post_id>/save', methods=['POST'])
@jwt_required() 
def save_post(post_id): 
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    is_saved = toggle_save_post(current_user.id, post_id)
    message = "Postingan disimpan" if is_saved else "Postingan dihapus dari simpanan"
    return jsonify({"success": True, "is_saved": is_saved, "message": message}), 200


@post_bp.route('/detail/<uuid:post_id>', methods=['GET'])
@jwt_required(optional=True)
def get_single_post(post_id):
    current_user_id = get_jwt_identity()
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    post_author = User.query.get(post.user_id)

    from app.models import Appeal
    from datetime import timedelta

    appeal = Appeal.query.filter_by(content_id=post.id).first()
    is_liked = False
    is_following = False
    is_saved = False
    if current_user_id:
        if PostLike.query.filter_by(user_id=current_user_id, post_id=post.id).first():
            is_liked = True
        if SavedPost.query.filter_by(user_id=current_user_id, post_id=post.id).first():
            is_saved = True
        if str(post_author.id) != str(current_user_id):# type: ignore
            follow_exists = Connection.query.filter_by(
                follower_id=current_user_id,
                following_id=post_author.id# type: ignore
            ).first()
            if follow_exists:
                is_following = True
    image_url = post.image_url
    if image_url and not image_url.startswith('http'):
        folder = 'reject' if post.moderation_status in ['rejected', 'appealing', 'final_rejected'] else 'uploads'
        image_url = f"static/{folder}/{image_url}"
    avatar_url = post_author.avatar_url# type: ignore
    if avatar_url and not avatar_url.startswith('http'):
        avatar_url = f"static/uploads/{avatar_url}"
    dt = post.created_at
    if dt is not None:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        created_at_str = dt.isoformat().replace('+00:00', 'Z')
    else:
        created_at_str = datetime.now(timezone.utc).isoformat()
    result = {
        "id": str(post.id),
        "caption": post.caption,
        "tags": post.tags if post.tags else [],
        "image_url": image_url,
        "created_at": created_at_str,
        "likes_count": post.likes_count,
        "comments_count": post.comments_count,
        "is_liked": is_liked,
        "is_saved": is_saved,
        "status": post.moderation_status,
        "moderation_details": post.moderation_details,
        "expires_at": (post.created_at + timedelta(hours=24)).isoformat(),
        "appeal_status": appeal.status if appeal else None,
        "admin_note": appeal.admin_note if appeal else None,
        "author": {
            "id": str(post_author.id),# type: ignore
            "display_name": post_author.display_name, # type: ignore
            "username": post_author.username,# type: ignore
            "avatar_url": avatar_url,
            "is_following": is_following,
            "is_verified": post_author.is_verified,# type: ignore
        }
    }
    return jsonify(result), 200

@post_bp.route('/my-moderation', methods=['GET'])
@jwt_required()
def get_my_moderation():
    user_id = get_jwt_identity()
    posts = Post.query.filter(
        Post.user_id == user_id, 
        Post.moderation_status.notin_(['approved'])
    ).order_by(Post.created_at.desc()).all()
    
    results = []
    for p in posts:
        from app.models import Appeal
        from datetime import timedelta
        appeal = Appeal.query.filter_by(content_id=p.id).first()
        
        image_path = p.image_url
        if image_path:
            folder = 'reject' if p.moderation_status in ['rejected', 'appealing', 'final_rejected'] else 'uploads'
            image_path = f"static/{folder}/{image_path}"

        results.append({
            "id": str(p.id),
            "caption": p.caption,
            "image_url": image_path,
            "status": p.moderation_status,
            "moderation_details": p.moderation_details,
            "expires_at": (p.created_at + timedelta(hours=24)).isoformat(),
            "appeal_status": appeal.status if appeal else None,
            "admin_note": appeal.admin_note if appeal else None
        })
    return jsonify(results), 200


@post_bp.route('/<uuid:post_id>/appeal', methods=['POST'])
@jwt_required()
def submit_appeal(post_id):
    user_id = get_jwt_identity()
    post = Post.query.filter_by(id=post_id, user_id=user_id).first()
    
    if not post:
        return jsonify({"error": "Postingan tidak ditemukan"}), 404
    
    if post.moderation_status != 'rejected':
        return jsonify({"error": "Postingan ini tidak dalam status ditolak"}), 400

    data = request.get_json()
    justification = data.get('justification')
    
    if not justification:
        return jsonify({"error": "Alasan banding wajib diisi"}), 400

    from app.models import Appeal
    existing_appeal = Appeal.query.filter_by(content_id=post_id).first()
    if existing_appeal:
        return jsonify({"error": "Banding sudah diajukan"}), 400

    new_appeal = Appeal(
        user_id=user_id, # type: ignore
        content_type='post', # type: ignore
        content_id=post_id, # type: ignore
        justification=justification, # type: ignore
        status='pending' # type: ignore
    )
    
    post.moderation_status = 'appealing'
    db.session.add(new_appeal)
    db.session.commit()
    
    return jsonify({"message": "Banding berhasil diajukan, mohon tunggu review admin"}), 201


@post_bp.route('/<uuid:post_id>/acknowledge', methods=['DELETE'])
@jwt_required()
def acknowledge_rejection(post_id):
    user_id = get_jwt_identity()
    post = Post.query.filter_by(id=post_id, user_id=user_id).first()
    
    if not post:
        return jsonify({"error": "Postingan tidak ditemukan"}), 404
        
    if post.moderation_status not in ['rejected', 'appealing', 'final_rejected', 'quarantined']:
        return jsonify({"error": "Postingan ini tidak dalam masa moderasi atau sudah selesai."}), 400

    try:
        if post.image_url:
            reject_folder = os.path.join(current_app.root_path, 'static', 'reject')
            path = os.path.join(reject_folder, post.image_url)
            if os.path.exists(path):
                os.remove(path)
        
        from ..models import Appeal
        Appeal.query.filter_by(content_id=post.id).delete()
        
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({"message": "Postingan berhasil dihapus dan keputusan diterima."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500