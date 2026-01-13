import os
import fcntl
from flask import Flask, request
from flask_apscheduler import APScheduler
from .config import Config
from .routes.auth_routes import auth_bp, bcrypt
from .routes.post_routes import post_bp
from .routes.sdq_routes import sdq_bp
from .routes.test_routes import test_bp
from .routes.comment_routes import comment_bp 
from .routes.user_routes import user_bp
from .routes.feedback_routes import feedback_bp
from .routes.admin_routes import admin_bp 
from .routes.article_routes import article_bp
from .routes.admin_ai_routes import ai_bp
from .routes.api_routes import api_bp
from .routes.report_routes import report_bp 
from .routes.chat_routes import chat_bp
from flask_jwt_extended import JWTManager 
from .routes.password_routes import password_bp
from flask_mail import Mail
from app.routes.bot_routes import bot_bp
from .routes.notification_routes import notif_bp
from .routes.web_routes import web_bp 
from .routes.professional_routes import pro_bp
from .routes.admin_pro_routes import admin_pro_bp
from .routes.discover_routes import discover_bp
from flask import jsonify
from .extensions import db, bcrypt, mail, socketio, limiter
mail = Mail()
scheduler = APScheduler()

def create_app():
    flask_instance = Flask(__name__)
    flask_instance.config.from_object(Config)
    
    from .models import User, Chat, ChatParticipant, Message 

    JWTManager(flask_instance) 
    db.init_app(flask_instance)
    bcrypt.init_app(flask_instance)
    socketio.init_app(flask_instance)
    mail.init_app(flask_instance)
    limiter.init_app(flask_instance) 

    
    flask_instance.register_blueprint(auth_bp, url_prefix='/api/auth')
    flask_instance.register_blueprint(post_bp, url_prefix='/api/posts')
    flask_instance.register_blueprint(sdq_bp, url_prefix='/api/sdq')
    flask_instance.register_blueprint(test_bp, url_prefix='/api/test')
    flask_instance.register_blueprint(comment_bp, url_prefix='/api/comments') 
    flask_instance.register_blueprint(user_bp, url_prefix='/api/users')
    flask_instance.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    flask_instance.register_blueprint(article_bp)
    flask_instance.register_blueprint(ai_bp)
    flask_instance.register_blueprint(api_bp)
    flask_instance.register_blueprint(report_bp, url_prefix='/api/report')
    flask_instance.register_blueprint(admin_bp, url_prefix='/admin')
    flask_instance.register_blueprint(chat_bp, url_prefix='/api/chats')
    flask_instance.register_blueprint(password_bp, url_prefix='/api/password')
    flask_instance.register_blueprint(bot_bp, url_prefix='/api/bot')
    flask_instance.register_blueprint(notif_bp, url_prefix='/api/notifications')
    flask_instance.register_blueprint(web_bp) 
    flask_instance.register_blueprint(pro_bp, url_prefix='/api/pro')
    flask_instance.register_blueprint(admin_pro_bp)
    flask_instance.register_blueprint(discover_bp, url_prefix='/api/discover')

    flask_instance.config['MAIL_DEBUG'] = False

    @flask_instance.after_request
    def add_header(response):
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000'
        return response

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

    if not flask_instance.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        f = open("scheduler.lock", "wb")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            scheduler.init_app(flask_instance)
            scheduler.start()
            
            from app.tasks import cleanup_moderation_task
            scheduler.add_job(
                id='cleanup_rejected_posts',
                func=cleanup_moderation_task,
                args=[flask_instance],
                trigger='interval',
                hours=1
            )
        except BlockingIOError:
            pass

    @flask_instance.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
           "error": "Terlalu banyak permintaan",
            "message": "Tenang ya, server butuh istirahat sejenak. Coba lagi nanti.",
            "retry_after": e.description
        }), 429


    return flask_instance
