import os
from flask import Flask 
from .config import Config
from .database import db
from .routes.auth_routes import auth_bp, bcrypt
from .routes.post_routes import post_bp
from .routes.sdq_routes import sdq_bp
from .routes.test_routes import test_bp
from .routes.comment_routes import comment_bp 
from .routes.user_routes import user_bp
from .routes.feedback_routes import feedback_bp
from .routes.admin_routes import admin_bp 
from .routes.article_routes import article_bp
from .routes.api_routes import api_bp
from .routes.report_routes import report_bp 
from .routes.chat_routes import chat_bp
from flask_jwt_extended import JWTManager 
from .socket_instance import socketio 

def create_app():
    flask_instance = Flask(__name__)
    flask_instance.config.from_object(Config)
    from .models import User, Chat, ChatParticipant, Message 

    JWTManager(flask_instance) 
    db.init_app(flask_instance)
    bcrypt.init_app(flask_instance)
    socketio.init_app(flask_instance)

    # Register Blueprint 
    flask_instance.register_blueprint(auth_bp, url_prefix='/api/auth')
    flask_instance.register_blueprint(post_bp, url_prefix='/api/posts')
    flask_instance.register_blueprint(sdq_bp, url_prefix='/api/sdq')
    flask_instance.register_blueprint(test_bp, url_prefix='/api/test')
    flask_instance.register_blueprint(comment_bp, url_prefix='/api/comments') 
    flask_instance.register_blueprint(user_bp, url_prefix='/api/users')
    flask_instance.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    flask_instance.register_blueprint(article_bp)
    flask_instance.register_blueprint(api_bp)
    flask_instance.register_blueprint(report_bp, url_prefix='/api/report')
    flask_instance.register_blueprint(admin_bp, url_prefix='/admin')
    flask_instance.register_blueprint(chat_bp, url_prefix='/api/chats')

    @flask_instance.context_processor
    def inject_firebase_config():
        return dict(firebase_config={
            "apiKey": os.environ.get('FIREBASE_API_KEY'),
            "authDomain": os.environ.get('FIREBASE_AUTH_DOMAIN'),
            "projectId": os.environ.get('FIREBASE_PROJECT_ID'),
            "storageBucket": os.environ.get('FIREBASE_STORAGE_BUCKET'),
            "messagingSenderId": os.environ.get('FIREBASE_MESSAGING_SENDER_ID'),
            "appId": os.environ.get('FIREBASE_APP_ID')
        })
    
    from . import socket_events 
        
    return flask_instance