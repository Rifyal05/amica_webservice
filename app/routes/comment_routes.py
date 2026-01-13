from flask import Blueprint, request, jsonify
from ..models import Comment, Post, User 
from ..extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.post_classification_service import post_classifier
from ..services.notif_manager import create_notification
from ..extensions import db, limiter 

comment_bp = Blueprint('comment', __name__)

ALLOWED_COMMENT_CATEGORIES = {'Bersih'}

@comment_bp.route('/<uuid:post_id>/comments', methods=['POST'])
@limiter.limit("20 per minute")
@jwt_required() 
def create_comment(post_id): 
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    data = request.get_json()
    text = data.get('text', '').strip()
    parent_comment_id = data.get('parent_comment_id')
    
    if not text:
        return jsonify({"error": "Comment text cannot be empty"}), 400
    
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    text_category = post_classifier.predict(text)
    
    moderation_status = 'approved'
    moderation_details = {'category': text_category}

    if text_category not in ALLOWED_COMMENT_CATEGORIES:
        moderation_status = 'rejected'
        
        rejected_comment = Comment(
            post_id=post_id, # type: ignore
            user_id=current_user.id, # type: ignore
            parent_comment_id=parent_comment_id,# type: ignore
            text=text,# type: ignore
            moderation_status=moderation_status,# type: ignore
            moderation_details=moderation_details# type: ignore
        )
        db.session.add(rejected_comment)
        db.session.commit()
        
        
        return jsonify({
            "message": "Comment rejected by moderation filter.",
            "status": moderation_status,
            "reason": f"Detected category: {text_category}"
        }), 403

    new_comment = Comment(
        post_id=post_id, # type: ignore
        user_id=current_user.id,# type: ignore
        parent_comment_id=parent_comment_id,# type: ignore
        text=text,# type: ignore
        moderation_status=moderation_status# type: ignore
    )
    
    db.session.add(new_comment)
    post.comments_count += 1 
    db.session.commit()

    create_notification(
        recipient_id=post.user_id,    
        sender_id=current_user.id,     
        type='comment',
        reference_id=str(post.id),     
        text=text                      
    )

    return jsonify({
        "message": "Comment created successfully",
        "comment_id": str(new_comment.id),
        "status": moderation_status
    }), 201

@comment_bp.route('/<uuid:post_id>/comments', methods=['GET'])
@limiter.limit("30 per minute")
def get_comments(post_id):
    root_comments = Comment.query.filter_by(
        post_id=post_id, 
        parent_comment_id=None,
        moderation_status='approved'
    ).order_by(Comment.created_at.desc()).all()

    results = []
    for comment in root_comments:
        results.append(serialize_comment(comment))

    return jsonify(results), 200

def serialize_comment(comment):
    """Helper rekursif untuk menyusun komentar dan balasannya"""
    replies = []
    if comment.replies:
        approved_replies = [r for r in comment.replies if r.moderation_status == 'approved']
        approved_replies.sort(key=lambda x: x.created_at)
        for reply in approved_replies:
            replies.append(serialize_comment(reply))
            
    avatar = comment.author.avatar_url 
    if avatar and not avatar.startswith('http'):
        if not 'static/uploads' in avatar:
            avatar = f"static/uploads/{avatar}"

    return {
        'id': str(comment.id),
        'text': comment.text,
        'created_at': comment.created_at.isoformat(),
        'parent_comment_id': str(comment.parent_comment_id) if comment.parent_comment_id else None,
        'user': {
            'id': str(comment.author.id),              
            'username': comment.author.username,       
            'display_name': comment.author.display_name, 
            'avatar_url': avatar,
            'is_verified': comment.author.is_verified 
        },
        'replies': replies
    }


@comment_bp.route('/<uuid:comment_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
@jwt_required()
def delete_comment(comment_id):
    user_id = get_jwt_identity()
    comment = Comment.query.get(comment_id)
    
    if not comment:
        return jsonify({"error": "Komentar tidak ditemukan"}), 404
        
    post = Post.query.get(comment.post_id)
    is_post_owner = str(post.user_id) == user_id if post else False
    is_comment_owner = str(comment.user_id) == user_id
    
    if not is_comment_owner and not is_post_owner:
        return jsonify({"error": "Anda tidak memiliki izin untuk menghapus komentar ini"}), 403

    try:
        db.session.delete(comment)
        
        if post and post.comments_count > 0:
            post.comments_count -= 1 

        db.session.commit()
        return jsonify({"message": "Komentar berhasil dihapus"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Gagal menghapus komentar", "details": str(e)}), 500