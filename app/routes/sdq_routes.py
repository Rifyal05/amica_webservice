from flask import Blueprint, request, jsonify
from ..models import SdqResult
from ..database import db
from ..utils.decorators import token_required
from ..services.sdq_scoring_service import sdq_scorer
from ..services.interpretation_service import interpreter

sdq_bp = Blueprint('sdq', __name__)

@sdq_bp.route('/submit', methods=['POST'])
@token_required
def submit_sdq(current_user):
    data = request.get_json()
    answers = data.get('answers')

    if not answers or not isinstance(answers, list) or len(answers) != 25:
        return jsonify({"error": "Payload must contain an 'answers' array with 25 integers."}), 400

    try:
        calculated_scores = sdq_scorer.calculate_scores(answers)

        new_result = SdqResult()
        new_result.user_id = current_user.id
        new_result.answers = answers
        for key, value in calculated_scores.items():
            if hasattr(new_result, key):
                setattr(new_result, key, value)
        
        db.session.add(new_result)
        db.session.commit()

        full_interpretation = interpreter.generate_full_interpretation(calculated_scores)

        response_payload = {
            "scores": calculated_scores,
            "interpretation": full_interpretation
        }
        
        return jsonify(response_payload), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to process SDQ result", "details": str(e)}), 500

@sdq_bp.route('/history', methods=['GET'])
@token_required
def get_sdq_history(current_user):
    history = SdqResult.query.filter_by(user_id=current_user.id).order_by(SdqResult.created_at.desc()).all()

    results = []
    for result in history:
        total_score = result.total_difficulties_score
        level = interpreter._get_level('total', total_score)
        interpretation_title = interpreter.INTERPRETATION_TEXTS['total'][level]['title']
        results.append({
            "id": result.id,
            "date": result.created_at.isoformat(),
            "total_score": total_score,
            "interpretation_title": interpretation_title
        })

    return jsonify(results), 200