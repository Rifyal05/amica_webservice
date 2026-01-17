from .extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime, timezone

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
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
    is_saved_posts_public = db.Column(db.Boolean, default=False)
    reset_otp = db.Column(db.String(6), nullable=True)
    reset_otp_expires = db.Column(db.DateTime(timezone=True), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)

    # Relationships with cascade delete to prevent NotNullViolation
    posts = db.relationship('Post', backref=db.backref('author', lazy=True), cascade="all, delete-orphan", passive_deletes=True)
    comments = db.relationship('Comment', backref=db.backref('author', lazy=True), cascade="all, delete-orphan", passive_deletes=True)
    articles = db.relationship('Article', backref=db.backref('author', lazy=True), cascade="all, delete-orphan", passive_deletes=True)
    feedback = db.relationship('Feedback', backref=db.backref('author', lazy=True), cascade="all, delete-orphan", passive_deletes=True)
    sdq_results = db.relationship('SdqResult', backref=db.backref('author', lazy=True), cascade="all, delete-orphan", passive_deletes=True)
    reports_made = db.relationship('Report', foreign_keys='Report.reporter_user_id', backref='reporter', cascade="all, delete-orphan", passive_deletes=True)
    reports_received = db.relationship('Report', foreign_keys='Report.reported_user_id', backref='reported_user', cascade="all, delete-orphan", passive_deletes=True)
    appeals = db.relationship('Appeal', backref=db.backref('author', lazy=True), cascade="all, delete-orphan", passive_deletes=True)
 


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
    
    replies = db.relationship(
        'Comment',
        backref=db.backref('parent', remote_side=[id]),
        lazy=True, 
        cascade="all, delete-orphan"
    )

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
    source_url = db.Column(db.String(1024), nullable=True, unique=True, index=True)
    is_featured = db.Column(db.Boolean, default=False)
    author_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'))
    views = db.Column(db.Integer, default=0)
 
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_ingested = db.Column(db.Boolean, default=False)
    ingested_at = db.Column(db.DateTime(timezone=True), nullable=True)

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
    reported_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'))
    reported_post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('posts.id', ondelete='CASCADE'))
    reported_comment_id = db.Column(UUID(as_uuid=True), db.ForeignKey('comments.id', ondelete='CASCADE'))
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Appeal(db.Model):
    __tablename__ = 'appeals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)
    content_id = db.Column(UUID(as_uuid=True), nullable=False)
    justification = db.Column(db.Text)
    admin_note = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime(timezone=True))

class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    is_group = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=True)
    image_url = db.Column(db.String(1024), nullable=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    last_message_text = db.Column(db.Text, nullable=True)
    last_message_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    participants = db.relationship('ChatParticipant', backref='chat', cascade="all, delete-orphan", lazy=True)
    messages = db.relationship('Message', backref='chat', cascade="all, delete-orphan", lazy='dynamic')
    allow_member_invites = db.Column(db.Boolean, default=False)


class ChatParticipant(db.Model):
    __tablename__ = 'chat_participants'
    chat_id = db.Column(UUID(as_uuid=True), db.ForeignKey('chats.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    is_hidden = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    unread_count = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_cleared_at = db.Column(db.DateTime(timezone=True), nullable=True)
    user = db.relationship(
        'User', 
        backref=db.backref('chat_participations', cascade="all, delete-orphan", passive_deletes=True)
    )

class GroupBannedUser(db.Model):
    __tablename__ = 'group_banned_users'
    group_id = db.Column(UUID(as_uuid=True), db.ForeignKey('chats.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    banned_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = db.Column(UUID(as_uuid=True), db.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    sender_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    text = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(20), default='text') # 'text', 'image', 'system'
    attachment_url = db.Column(db.String(1024), nullable=True)
    is_read_by_all = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted = db.Column(db.Boolean, default=False)
    reply_to_id = db.Column(UUID(as_uuid=True), db.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    reply_to = db.relationship('Message', remote_side=[id], backref='replies')
    
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_id = db.Column(db.String(100), nullable=True) 
    target_type = db.Column(db.String(50)) 
    action = db.Column(db.String(50)) 
    old_value = db.Column(JSONB, nullable=True) 
    new_value = db.Column(JSONB, nullable=True)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    actor = db.relationship('User', foreign_keys=[actor_id])


class BotChat(db.Model):
    __tablename__ = 'bot_chats'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user = db.relationship('User', backref=backref('bot_chats', cascade="all, delete-orphan"))
    messages = db.relationship('BotMessage', backref='bot_chat', cascade="all, delete-orphan", lazy='dynamic')

class BotMessage(db.Model):
    __tablename__ = 'bot_messages'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_chat_id = db.Column(UUID(as_uuid=True), db.ForeignKey('bot_chats.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'user' atau 'model'
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sources = db.Column(JSONB, nullable=True)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    recipient_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    sender_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    type = db.Column(db.String(20), nullable=False) 
    
    reference_id = db.Column(db.String(36), nullable=True) 
    
    text = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    recipient = db.relationship(
        'User', 
        foreign_keys=[recipient_id], 
        backref=db.backref('notifications_received', cascade="all, delete-orphan", passive_deletes=True)
    )
    sender = db.relationship(
        'User', 
        foreign_keys=[sender_id], 
        backref=db.backref('notifications_sent', cascade="all, delete-orphan", passive_deletes=True)
    )

    def to_dict(self):
        from flask import url_for
        from app.utils.image_utils import generate_thumbnail

        is_moderation = self.type in ['post_rejected', 'appeal_approved', 'appeal_rejected', 'system']
    
        related_image = None
        if self.type in ['like', 'comment'] and self.reference_id:
            from .models import Post
            try:
                post = Post.query.filter_by(id=self.reference_id).first()
                if post and post.image_url:
                    thumb_path = generate_thumbnail(post.image_url, size=(128, 128))
                    if thumb_path:
                        related_image = url_for('static', filename=thumb_path, _external=True)
                    else:
                        related_image = url_for('static', filename=f"uploads/{post.image_url}", _external=True)
            except:
                pass

        return {
            'id': str(self.id),
            'recipient_id': str(self.recipient_id),
            'sender_id': str(self.sender_id),
            'sender_name': "AMICA" if is_moderation else (self.sender.username if self.sender else "Unknown"),
            'sender_avatar': "static/images/logo_light.png" if is_moderation else (self.sender.avatar_url if self.sender else None),
            'sender_is_verified': True if is_moderation else (self.sender.is_verified if self.sender else False),
            'type': self.type,
            'reference_id': self.reference_id,
            'text': self.text,
            'is_read': self.is_read,
            'related_image_url': related_image,
            'created_at': self.created_at.isoformat()
        }
    


class GroupInvite(db.Model):
    __tablename__ = 'group_invites'
    token = db.Column(db.String(64), primary_key=True)
    group_id = db.Column(UUID(as_uuid=True), db.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True) # Null = selamanya
    max_uses = db.Column(db.Integer, nullable=True) # Null = tak terbatas
    current_uses = db.Column(db.Integer, default=0)


class ProfessionalProfile(db.Model):
    __tablename__ = 'professional_profiles'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    
    pro_type = db.Column(db.String(50), default='psychologist') 
    full_name_with_title = db.Column(db.String(255))
    str_number = db.Column(db.String(50), unique=True)
    province = db.Column(db.String(100))
    practice_address = db.Column(db.Text)
    practice_schedule = db.Column(db.Text)
    
    str_image_path = db.Column(db.String(1024)) 
    ktp_image_path = db.Column(db.String(1024), nullable=True) 
    selfie_image_path = db.Column(db.String(1024), nullable=True) 
    
    status = db.Column(db.String(20), default='pending') 
    verified_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("professional_profile", uselist=False))



class QuarantinedItem(db.Model):
    __tablename__ = 'quarantined_items'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ID asli dari Post, User, atau Comment yang ditindak
    original_target_id = db.Column(UUID(as_uuid=True), nullable=False)
    
    # Tipe target: 'post', 'comment', 'user_avatar', 'user_banner', 'user_bio'
    target_type = db.Column(db.String(50), nullable=False)
    
    # Lokasi file di folder 'static/quarantine/' (Jika berupa gambar)
    file_path = db.Column(db.String(1024), nullable=True)
    
    # Isi teks asli (Jika yang dihapus adalah komentar/bio)
    text_content = db.Column(db.Text, nullable=True)
    
    # Siapa admin yang melakukan eksekusi
    quarantined_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Alasan tindakan (diambil dari input admin saat delete)
    reason = db.Column(db.Text, nullable=True)
    
    # Waktu tindakan (untuk cron job penghapusan otomatis 30 hari)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relasi ke Admin (opsional, untuk audit)
    admin = db.relationship('User', foreign_keys=[quarantined_by])



class RAGTestCase(db.Model):
    __tablename__ = 'rag_test_cases'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    expected_answer = db.Column(db.Text, nullable=False) 
    target_article_id = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class RAGBenchmarkResult(db.Model):
    __tablename__ = 'rag_benchmark_results'
    id = db.Column(db.Integer, primary_key=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('rag_test_cases.id', ondelete='CASCADE'))
    
    ai_answer = db.Column(db.Text)    
    llama_score = db.Column(db.Float) 
    llama_reason = db.Column(db.Text)
    
    mrr_score = db.Column(db.Float)
    retrieved_ids = db.Column(db.JSON)
    
    latency = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    test_case = db.relationship('RAGTestCase', backref='results')