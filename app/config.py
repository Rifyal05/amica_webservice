import os
from dotenv import load_dotenv
from datetime import timedelta

IS_ALEMBIC_RUNNING = os.environ.get('ALEMBIC_RUNNING') == 'true'

if not IS_ALEMBIC_RUNNING:
    load_dotenv()
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30) 

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False