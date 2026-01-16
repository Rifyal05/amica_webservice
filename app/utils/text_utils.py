import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import re
import os
import html
import emoji

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)

try:
    NORM_DF = pd.read_csv('kamus_normalisasi.csv')
    NORMALIZATION_MAPPING = pd.Series(NORM_DF.expansion.values, index=NORM_DF.contraction).to_dict()
except:
    NORMALIZATION_MAPPING = {}

STOP_WORDS = set(stopwords.words('indonesian'))

POST_SPECIAL_VOWEL = ['siapa', 'apa', 'mana', 'dia', 'kenapa', 'ada', 'bawa', 'sana', 'sini', 'begitu']
POST_LEET_MAP = {'0': 'o', '1': 'i', '2': 'z', '3': 'e', '4': 'a', '5': 's', '6': 'g', '7': 't', '8': 'b', '9': 'g', '@': 'a', '$': 's'}
POST_CUSTOM_STOPWORDS = [
    'yang', 'untuk', 'pada', 'ke', 'dari', 'dalam', 'dan', 'atau', 'dengan', 'adalah', 'yaitu', 'yakni', 
    'merupakan', 'bahwa', 'oleh', 'sebuah', 'tersebut', 'adapun', 'begitu', 'begini', 'serta', 'maka', 
    'ialah', 'itu', 'ini', 'bahwasanya', 'demi', 'suatu', 'para', 'sang', 'si', 'sebagaimana', 'sehubungan', 
    'terkait', 'perihal', 'hingga', 'sampai', 'sejak', 'saat', 'ketika', 'kemudian', 'lalu', 'setelah', 
    'sesudah', 'before', 'supaya', 'agar', 'jikalau', 'apabila', 'andaikata', 'manakala'
]

try:
    POST_NORM_DF = pd.read_csv('indonesian_norm.csv', on_bad_lines='skip', engine='python')
    POST_NORM_DICT = dict(zip(POST_NORM_DF['contraction'], POST_NORM_DF['expansion']))
except:
    POST_NORM_DICT = {}

def post_preprocess_text(text: str) -> str:
    text = str(text)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = text.lower()
    text = html.unescape(text)
    text = re.sub(r'\\x[a-zA-Z0-9]+', ' ', text)
    text = re.sub(r'\b(rt|user)\b', ' ', text)
    text = re.sub(r'http\S+|www\.\S+', ' ', text)
    text = re.sub(r'\s*&\s*', ' dan ', text)
    text = re.sub(r'\s*/\s*', ' atau ', text)
    text = text.replace('_', ' ')
    text = emoji.demojize(text, delimiters=(" :", ": "))
    
    for word in POST_SPECIAL_VOWEL:
        text = re.sub(rf'\b{word}luh?\b', f'{word} lu', text)
    text = re.sub(r'([^aeiou\s])luh?\b', r'\1 lu', text)
    
    words = text.split()
    new_words = []
    for word in words:
        if word in POST_NORM_DICT:
            new_words.append(POST_NORM_DICT[word])
        elif word.isdigit():
            new_words.append(word)
        else:
            temp_word = word
            for char, repl in POST_LEET_MAP.items():
                temp_word = re.sub(f"(?<=[a-z]){re.escape(char)}|{re.escape(char)}(?=[a-z])", repl, temp_word)
            new_words.append(POST_NORM_DICT.get(temp_word, temp_word))
    
    cleaned_tokens = [w for w in new_words if w not in POST_CUSTOM_STOPWORDS]
    text = ' '.join(cleaned_tokens)
    text = re.sub(r'(?<=[a-zA-Z])\.(?=[a-zA-Z])', '', text) 
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', '', text)
    text = re.sub(r'(!)\1+', r'\1', text) 
    text = re.sub(r'(\?)\1+', r'\1', text) 
    text = re.sub(r'(\.)\1+', r'\1', text) 
    text = re.sub(r'(.)\1{2,}', r'\1\1', text) 
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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