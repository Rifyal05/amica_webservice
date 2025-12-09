from flask import Blueprint, request, jsonify, current_app
from ..models import Post, User, PostLike, Connection, db
from ..utils.decorators import token_required
from ..services.post_classification_service import post_classifier 
from ..services.image_moderation_service import image_moderator
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
@token_required
def create_post(current_user):
    
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
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    current_user_id = None
    token = None
    
    # 1. SOFT AUTHENTICATION
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
    
    if token:
        try:
            data = jwt.decode(token, os.environ.get('SECRET_KEY'), algorithms=["HS256"])
            current_user_id = data.get('user_id')
        except:
            current_user_id = None

    # 2. QUERY DATABASE
    posts_query = db.session.query(
        Post.id, Post.caption, Post.tags, Post.image_url, Post.created_at, Post.likes_count, Post.comments_count,
        User.id.label('user_id'), User.display_name, User.username, User.avatar_url
    ).join(User, Post.user_id == User.id).filter(Post.moderation_status == 'approved').order_by(Post.created_at.desc())

    paginated_posts = posts_query.paginate(page=page, per_page=per_page, error_out=False) # type: ignore
    
    results = []
    for post in paginated_posts.items:
        # 3. CEK LIKE & FOLLOW
        is_liked = False
        is_following = False
        
        if current_user_id:
            like_exists = PostLike.query.filter_by(
                user_id=current_user_id, 
                post_id=post.id
            ).first()
            if like_exists:
                is_liked = True

            if str(post.user_id) != str(current_user_id):
                follow_exists = Connection.query.filter_by(
                    follower_id=current_user_id,
                    following_id=post.user_id
                ).first()
                if follow_exists:
                    is_following = True
        
        dt = post.created_at
        
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            created_at_str = dt.isoformat().replace('+00:00', 'Z')
        else:
            created_at_str = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


        results.append({
            "id": str(post.id),
            "caption": post.caption,
            "tags": post.tags,
            "image_url": post.image_url,
            "created_at": created_at_str,
            "likes_count": post.likes_count,
            "comments_count": post.comments_count,
            "is_liked": is_liked,
            "author": {
                "id": str(post.user_id),
                "display_name": post.display_name,
                "username": post.username,
                "avatar_url": post.avatar_url,
                "is_following": is_following
            }
        })
    
    return jsonify({
        "posts": results,
        "total_pages": paginated_posts.pages,
        "current_page": paginated_posts.page,
        "has_next": paginated_posts.has_next
    }), 200
@post_bp.route('/<uuid:post_id>/like', methods=['POST'])
@token_required
def toggle_like(current_user, post_id):
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    like = PostLike.query.filter_by(user_id=current_user.id, post_id=post_id).first()

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
@token_required
def delete_post(current_user, post_id):
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