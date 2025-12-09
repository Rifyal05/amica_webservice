from .database import db
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import uuid
from datetime import datetime, timezone

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(25), unique=True, nullable=False)
    display_name = db.Column(db.String(50), nullable=False)
    google_uid = db.Column(db.String(128), unique=True, nullable=True)
    auth_provider = db.Column(db.String(20), default='email') # 'email' atau 'google'
    avatar_url = db.Column(db.String(1024))
    banner_url = db.Column(db.String(1024))
    bio = db.Column(db.Text)
    role = db.Column(db.String(20), nullable=False, default='user')
    onesignal_player_id = db.Column(db.String(50))
    is_suspended = db.Column(db.Boolean, default=False)
    suspended_until = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    security_pin_hash = db.Column(db.String(128), nullable=True)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    caption = db.Column(db.Text)
    image_url = db.Column(db.String(1024))
    tags = db.Column(ARRAY(db.Text))
    moderation_status = db.Column(db.String(20), default='approved')
    moderation_details = db.Column(JSONB)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    parent_comment_id = db.Column(UUID(as_uuid=True), db.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    text = db.Column(db.Text, nullable=False)
    moderation_status = db.Column(db.String(20), default='approved')
    moderation_details = db.Column(JSONB)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Connection(db.Model):
    __tablename__ = 'connections'
    follower_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    following_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class SavedPost(db.Model):
    __tablename__ = 'saved_posts'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True)
    saved_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class SeenPost(db.Model):
    __tablename__ = 'seen_posts'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True)
    seen_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class PostLike(db.Model):
    __tablename__ = 'post_likes'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(1024))
    read_time = db.Column(db.Integer)
    tags = db.Column(ARRAY(db.Text))
    source_name = db.Column(db.String(100))
    source_url = db.Column(db.String(1024))
    is_featured = db.Column(db.Boolean, default=False)
    author_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    feedback_text = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.String(20))
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BlockedUser(db.Model):
    __tablename__ = 'blocked_users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    blocked_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.UniqueConstraint('blocker_id', 'blocked_id', name='_blocker_blocked_uc'),)

    blocker = db.relationship("User", foreign_keys=[blocker_id], backref="blocking_relationships")
    blocked_user = db.relationship("User", foreign_keys=[blocked_id], backref="blocked_by_relationships")

class SdqResult(db.Model):
    __tablename__ = 'sdq_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    answers = db.Column(ARRAY(db.Integer))
    total_difficulties_score = db.Column(db.Integer)
    emotional_score = db.Column(db.Integer)
    conduct_score = db.Column(db.Integer)
    hyperactivity_score = db.Column(db.Integer)
    peer_score = db.Column(db.Integer)
    prosocial_score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    reporter_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reported_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    reported_post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('posts.id'))
    reported_comment_id = db.Column(UUID(as_uuid=True), db.ForeignKey('comments.id'))
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Appeal(db.Model):
    __tablename__ = 'appeals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)
    content_id = db.Column(UUID(as_uuid=True), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ChatParticipant(db.Model):
    __tablename__ = 'chat_participants'
    chat_id = db.Column(UUID(as_uuid=True), db.ForeignKey('chats.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    joined_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = db.Column(UUID(as_uuid=True), db.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    sender_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    
    actor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    
    target_id = db.Column(db.String(100), nullable=True) 

    
    target_type = db.Column(db.String(50)) 
    action = db.Column(db.String(50)) 
    
    old_value = db.Column(JSONB, nullable=True) 
    new_value = db.Column(JSONB, nullable=True)
    
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    actor = db.relationship('User', foreign_keys=[actor_id])
