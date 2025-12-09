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

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    bcrypt.init_app(app)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(post_bp, url_prefix='/api/posts')
    app.register_blueprint(sdq_bp, url_prefix='/api/sdq')
    app.register_blueprint(test_bp, url_prefix='/api/test')
    app.register_blueprint(comment_bp, url_prefix='/api/comments') 
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    app.register_blueprint(article_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.context_processor
    def inject_firebase_config():
        return dict(firebase_config={
            "apiKey": os.environ.get('FIREBASE_API_KEY'),
            "authDomain": os.environ.get('FIREBASE_AUTH_DOMAIN'),
            "projectId": os.environ.get('FIREBASE_PROJECT_ID'),
            "storageBucket": os.environ.get('FIREBASE_STORAGE_BUCKET'),
            "messagingSenderId": os.environ.get('FIREBASE_MESSAGING_SENDER_ID'),
            "appId": os.environ.get('FIREBASE_APP_ID')
        })
        
    return app