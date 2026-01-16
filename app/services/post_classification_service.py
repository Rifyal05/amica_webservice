import onnxruntime
import numpy as np
import os
from ..utils.text_utils import post_preprocess_text

class PostClassificationService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostClassificationService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        model_path = "models_ml/text/post/post_classifier.onnx"
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Post classification ONNX model not found at {model_path}")

        self.session = onnxruntime.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self._initialized = True
        
    def predict(self, text):
        if not text or str(text).strip() == "":
            return "SAFE", 0.0

        processed_text = post_preprocess_text(text)
        input_data = np.array([[processed_text]], dtype=object)
        
        outputs = self.session.run(None, {self.input_name: input_data})
        
        predicted_label = outputs[0][0] # type: ignore
        prob_dict = outputs[1][0] # type: ignore
        confidence = float(prob_dict.get(predicted_label, 0.0))
        
        return str(predicted_label), confidence

post_classifier = PostClassificationService()