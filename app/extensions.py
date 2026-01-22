import os
import redis
from flask import request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
from flask_socketio import SocketIO
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

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
    default_limits=["600 per day", "200 per hour"],
    strategy="fixed-window"
)

@limiter.request_filter
def global_bypass_filter():
    secret_token = os.environ.get("BYPASS_LIMITER_TOKEN")
    if secret_token and request.headers.get("X-Load-Test-Token") == secret_token:
        return True
    return False

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="gevent",
    message_queue=os.environ.get("REDIS_URL", "redis://localhost:6379"),
    logger=False,
    engineio_logger=False
)

redis_client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))