from flask import Blueprint, request, jsonify
from ..models import Comment, Post
from ..database import db
from ..utils.decorators import token_required
from ..services.post_classification_service import post_classifier
import uuid

comment_bp = Blueprint('comment', __name__)

ALLOWED_COMMENT_CATEGORIES = {'Bersih'}

@comment_bp.route('/<uuid:post_id>/comments', methods=['POST'])
@token_required
def create_comment(current_user, post_id):
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
            parent_comment_id=parent_comment_id, # type: ignore
            text=text, # type: ignore
            moderation_status=moderation_status, # type: ignore
            moderation_details=moderation_details # type: ignore
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
        user_id=current_user.id, # type: ignore
        parent_comment_id=parent_comment_id, # type: ignore
        text=text, # type: ignore
        moderation_status=moderation_status # type: ignore
    )
    
    db.session.add(new_comment)
    post.comments_count += 1 
    db.session.commit()

    return jsonify({
        "message": "Comment created successfully",
        "comment_id": str(new_comment.id),
        "status": moderation_status
    }), 201