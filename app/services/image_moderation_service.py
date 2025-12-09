import onnxruntime
import numpy as np
import cv2
import os

class ImageModerationService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ImageModerationService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, image_size=(320, 320)):
        if self._initialized:
            return

        gatekeeper_path = "models_ml/image/gatekeeper.onnx"
        specialist_path = "models_ml/image/specialist.onnx"
        
        if not os.path.exists(gatekeeper_path) or not os.path.exists(specialist_path):
            raise FileNotFoundError("Image moderation ONNX models not found.")

        self.gatekeeper_session = onnxruntime.InferenceSession(gatekeeper_path)
        self.specialist_session = onnxruntime.InferenceSession(specialist_path)
        
        self.image_size = image_size
        self.gatekeeper_classes = ['safe', 'unsafe']
        self.specialist_classes = ['disturbing', 'knife', 'nsfw', 'violence', 'weapon']
        
        self.gatekeeper_input_name = self.gatekeeper_session.get_inputs()[0].name
        self.specialist_input_name = self.specialist_session.get_inputs()[0].name
        self._initialized = True

    def _letterbox(self, img):
        shape = img.shape[:2]
        new_shape = self.image_size
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
        dw /= 2
        dh /= 2
        
        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
            
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        return img

    def _preprocess(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Could not decode image from bytes.")
        img_bgr = np.array(img, dtype=np.uint8)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        img_letterboxed = self._letterbox(img_rgb)
        img_array = np.expand_dims(img_letterboxed, axis=0).astype(np.float32)
        return img_array

    def predict(self, image_bytes):
        processed_image = self._preprocess(image_bytes)
        
        gatekeeper_result = self.gatekeeper_session.run(None, {self.gatekeeper_input_name: processed_image})
        gatekeeper_scores = gatekeeper_result[0][0] # type: ignore
        gatekeeper_prediction_index = np.argmax(gatekeeper_scores)
        gatekeeper_prediction = self.gatekeeper_classes[gatekeeper_prediction_index]

        if gatekeeper_prediction == 'safe':
            return "safe", None

        specialist_result = self.specialist_session.run(None, {self.specialist_input_name: processed_image})
        specialist_scores = specialist_result[0][0] # type: ignore
        specialist_prediction_index = np.argmax(specialist_scores)
        specialist_prediction = self.specialist_classes[specialist_prediction_index]
        
        return "unsafe", specialist_prediction

image_moderator = ImageModerationService()