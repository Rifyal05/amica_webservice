import os
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()

def get_enterprise_key():
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}"
    except Exception:
        pass
    
    return f"ip:{get_remote_address()}"

limiter = Limiter(
    key_func=get_enterprise_key,
    storage_uri=os.environ.get("REDIS_URL", "redis://localhost:6379"),
    default_limits=["200 per day", "50 per hour"],
    strategy="fixed-window"
)

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="gevent",
    message_queue=os.environ.get("REDIS_URL", "redis://localhost:6379"),
    logger=False,
    engineio_logger=False
)

redis_client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
