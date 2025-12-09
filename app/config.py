import os
from dotenv import load_dotenv

IS_ALEMBIC_RUNNING = os.environ.get('ALEMBIC_RUNNING') == 'true'

if not IS_ALEMBIC_RUNNING:
    load_dotenv()
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False