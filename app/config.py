import os
from dotenv import load_dotenv
from datetime import timedelta

IS_ALEMBIC_RUNNING = os.environ.get('ALEMBIC_RUNNING') == 'true'

if not IS_ALEMBIC_RUNNING:
    load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30) 

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587 
    MAIL_USE_TLS = True 
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')

    HF_SPACE_URL = os.environ.get('HF_SPACE_URL')
    AMICA_API_KEY = os.environ.get('AMICA_API_KEY')