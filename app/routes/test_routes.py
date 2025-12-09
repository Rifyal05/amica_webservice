from flask import Blueprint, request, jsonify
from ..services.post_classification_service import post_classifier
from ..services.image_moderation_service import image_moderator
from ..services.feedback_sentiment_service import feedback_analyzer

test_bp = Blueprint('test', __name__)

@test_bp.route('/text', methods=['POST'])
def test_text_moderation():
    data = request.get_json()
    caption = data.get('text', '')
    if not caption:
        return jsonify({"error": "No text provided"}), 400

    category = post_classifier.predict(caption)
    status = "safe" if category == 'Bersih' else "unsafe"
    
    return jsonify({
        "status": status, 
        "reason": f"AI detected category: {category}"
    })

@test_bp.route('/image', methods=['POST'])
def test_image_moderation():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    image_file = request.files['image']
    image_bytes = image_file.read()
    status, category = image_moderator.predict(image_bytes)
    
    return jsonify({
        "status": status, 
        "reason": f"AI detected category: {category}" if category else "Image is safe"
    })

@test_bp.route('/feedback', methods=['POST'])
def test_feedback_sentiment():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "No text provided"}), 400

    sentiment = feedback_analyzer.predict(text)
    
    return jsonify({
        "sentiment": sentiment
    })