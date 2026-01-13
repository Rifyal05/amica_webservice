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

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()

def get_enterprise_key():
    user_id = get_jwt_identity()
    if user_id:
        return str(user_id)
    return get_remote_address()

limiter = Limiter(
    key_func=get_enterprise_key,
    storage_uri=os.environ.get("REDIS_URL", "redis://localhost:6379"),
    default_limits=["2000 per day", "500 per hour"],
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
