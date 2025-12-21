from flask import Blueprint, request, jsonify
from ..models import Feedback, User 
from ..database import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.feedback_sentiment_service import feedback_analyzer

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('/', methods=['POST'])
@jwt_required() 
def submit_feedback(): 
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    data = request.get_json()
    feedback_text = data.get('feedback_text', '')
    
    if not feedback_text:
        return jsonify({"error": "Feedback text is required"}), 400

    MAX_LENGTH = 2500
    if len(feedback_text) > MAX_LENGTH:
        return jsonify({"error": f"Feedback cannot exceed {MAX_LENGTH} characters"}), 400
        
    try:
        sentiment_result = feedback_analyzer.predict(feedback_text)
        
        new_feedback = Feedback(
            user_id=current_user.id, # type: ignore
            feedback_text=feedback_text,# type: ignore
            sentiment=sentiment_result,# type: ignore
            status='new'# type: ignore
        )
        
        db.session.add(new_feedback)
        db.session.commit()
        
        return jsonify({
            "message": "Feedback submitted successfully. Thank you!",
            "sentiment_detected": sentiment_result
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to submit feedback due to a server error", "details": str(e)}), 500