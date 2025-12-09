import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import re
import os

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)

try:
    NORM_DF = pd.read_csv('kamus_normalisasi.csv')
    NORMALIZATION_MAPPING = pd.Series(NORM_DF.expansion.values, index=NORM_DF.contraction).to_dict()
except FileNotFoundError:
    NORMALIZATION_MAPPING = {}

STOP_WORDS = set(stopwords.words('indonesian'))

def preprocess_text(text: str, remove_stopwords: bool = True) -> str:
    text = text.lower()
    text = text.replace('user', '') 
    text = re.sub(r'[^a-z\s]', '', text)
    tokens = word_tokenize(text)
    
    normalized_tokens = [NORMALIZATION_MAPPING.get(token, token) for token in tokens]
    
    if remove_stopwords:
        cleaned_tokens = [token for token in normalized_tokens if token not in STOP_WORDS]
    else:
        cleaned_tokens = normalized_tokens
        
    return " ".join(cleaned_tokens)