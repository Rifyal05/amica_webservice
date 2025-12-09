import onnxruntime
import re
import os
import numpy as np
import pandas as pd
from ..utils.text_utils import preprocess_text

class FeedbackSentimentService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FeedbackSentimentService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_len=150):
        if self._initialized:
            return
            
        model_path = "models_ml/text/feedback/feedback_sentiment.onnx"
        vocab_path = "models_ml/text/feedback/feedback_vocab.csv"
        
        if not os.path.exists(model_path) or not os.path.exists(vocab_path):
            raise FileNotFoundError(
                "Feedback sentiment files (model/vocab) not found."
            )

        self.session = onnxruntime.InferenceSession(model_path)

        vocab_df = pd.read_csv(vocab_path)
        self.word_index = pd.Series(vocab_df['index'].values, index=vocab_df['word']).to_dict()

        self.input_name = self.session.get_inputs()[0].name
        self.max_len = max_len
        self._initialized = True

    def _texts_to_sequences(self, texts: list[str]) -> list[list[int]]:
        sequences = []
        for text in texts:
            seq = []
            words = text.split()
            for word in words:
                index = self.word_index.get(word)
                if index is not None:
                    seq.append(index)
            sequences.append(seq)
        return sequences

    def _manual_pad_sequences(self, sequences: list[list[int]], maxlen: int, padding='post', truncating='post') -> np.ndarray:
        padded = []
        for seq in sequences:
            if len(seq) > maxlen:
                seq = seq[:maxlen] if truncating == 'post' else seq[-maxlen:]
            
            num_padding = maxlen - len(seq)
            padding_zeros = [0] * num_padding
            
            if padding == 'pre':
                padded.append(padding_zeros + seq)
            else:
                padded.append(seq + padding_zeros)
        
        return np.array(padded, dtype=np.int64) 

    def predict(self, text: str) -> str:
        processed_text = preprocess_text(text, remove_stopwords=False)
        
        sequence = self._texts_to_sequences([processed_text])
        
        input_data = self._manual_pad_sequences(sequence, maxlen=self.max_len)
        
        result = self.session.run(None, {self.input_name: input_data})
        
        probability = result[0][0][0] # type: ignore
        
        return "positive" if probability > 0.5 else "negative"

feedback_analyzer = FeedbackSentimentService()
