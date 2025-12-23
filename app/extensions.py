from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_mail import Mail

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()
socketio = SocketIO(cors_allowed_origins="*", logger=False, engineio_logger=False)
