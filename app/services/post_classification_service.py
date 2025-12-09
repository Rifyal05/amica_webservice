import onnxruntime
import re
import os
import numpy as np
import pandas as pd
from ..utils.text_utils import preprocess_text
from nltk.tokenize import word_tokenize

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
            raise FileNotFoundError("Post classification ONNX model not found.")

        self.session = onnxruntime.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self._initialized = True
        
    def predict(self, text):
        processed_text = preprocess_text(text, remove_stopwords=True) 
        
        input_data = np.array([[processed_text]], dtype=object)
        
        prediction_result = self.session.run(None, {self.input_name: input_data})
        
        predicted_label = prediction_result[0][0]  # type: ignore
        
        if isinstance(predicted_label, np.ndarray):
             return predicted_label[0]
        
        return predicted_label
    
post_classifier = PostClassificationService()
