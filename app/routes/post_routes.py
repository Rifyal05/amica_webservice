from flask import Blueprint, request, jsonify, current_app
from ..models import Post, User, PostLike, Connection, SavedPost, db
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.post_classification_service import post_classifier 
from ..services.image_moderation_service import image_moderator
from ..services.post_services import toggle_save_post 
import uuid
import os
import jwt
from werkzeug.utils import secure_filename
from datetime import datetime, timezone 

post_bp = Blueprint('post', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}
ALLOWED_TEXT_CATEGORIES = {'Bersih'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@post_bp.route('/', methods=['POST'])
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
    text_category = post_classifier.predict(caption)
    if text_category not in ALLOWED_TEXT_CATEGORIES:
        return jsonify({
            "error": "Post rejected by text moderation",
            "reason": f"Detected category: {text_category}"
        }), 403

    image_url_to_save = None
    moderation_details = {
        'text_status': 'safe',
        'text_category': text_category
    }

    if image_file:
        if not allowed_file(image_file.filename):
            return jsonify({"error": "Invalid image file type"}), 400
        
        image_bytes = image_file.read()
        
        image_status, image_category = image_moderator.predict(image_bytes)
        
        if image_status == 'unsafe':
            return jsonify({
                "error": "Post rejected by image moderation",
                "reason": f"Detected category: {image_category}"
            }), 403

        filename = secure_filename(f"{uuid.uuid4().hex}_{image_file.filename}")
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        image_path = os.path.join(upload_folder, filename)
        
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
            
        image_url_to_save = f"/static/uploads/{filename}"
        moderation_details['image_status'] = 'safe'
    
    new_post = Post()
    new_post.user_id = current_user.id
    new_post.caption = caption
    new_post.tags = tags
    new_post.image_url = image_url_to_save
    new_post.moderation_details = moderation_details
    new_post.moderation_status = 'approved' 
    
    db.session.add(new_post)
    db.session.commit()

    return jsonify({
        "message": "Post created successfully", 
        "post_id": str(new_post.id),
        "moderation_feedback": moderation_details
    }), 201

@post_bp.route('/', methods=['GET'])
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
                "is_following": is_following
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
        return jsonify({
            "message": "Success",
            "liked": liked,
            "likes_count": post.likes_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not process like", "details": str(e)}), 500
    

@post_bp.route('/<uuid:post_id>', methods=['DELETE'])
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