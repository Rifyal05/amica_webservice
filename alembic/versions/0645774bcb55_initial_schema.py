"""initial_schema

Revision ID: 0645774bcb55
Revises: 
Create Date: 2026-01-12 19:09:50.382638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0645774bcb55'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extension Wajib
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # 2. Eksekusi Schema Lengkap (Sesuai models.py)
    op.execute("""
    -- TABLE USERS
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255),
        username VARCHAR(25) UNIQUE NOT NULL,
        display_name VARCHAR(50) NOT NULL,
        google_uid VARCHAR(128) UNIQUE,
        auth_provider VARCHAR(20) DEFAULT 'email',
        avatar_url VARCHAR(1024),
        banner_url VARCHAR(1024),
        bio TEXT,
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        onesignal_player_id VARCHAR(50),
        is_suspended BOOLEAN DEFAULT FALSE,
        suspended_until TIMESTAMPTZ,
        security_pin_hash VARCHAR(128),
        is_saved_posts_public BOOLEAN DEFAULT FALSE,
        reset_otp VARCHAR(6),
        reset_otp_expires TIMESTAMPTZ,
        is_verified BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- TABLE POSTS
    CREATE TABLE IF NOT EXISTS posts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        caption TEXT,
        image_url VARCHAR(1024),
        tags TEXT[],
        moderation_status VARCHAR(20) DEFAULT 'approved',
        moderation_details JSONB,
        likes_count INT DEFAULT 0,
        comments_count INT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- TABLE COMMENTS
    CREATE TABLE IF NOT EXISTS comments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        moderation_status VARCHAR(20) DEFAULT 'approved',
        moderation_details JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- RELATIONS (Many-to-Many & Actions)
    CREATE TABLE IF NOT EXISTS connections (
        follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (follower_id, following_id)
    );

    CREATE TABLE IF NOT EXISTS saved_posts (
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        saved_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (user_id, post_id)
    );

    CREATE TABLE IF NOT EXISTS seen_posts (
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        seen_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (user_id, post_id)
    );

    CREATE TABLE IF NOT EXISTS post_likes (
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (user_id, post_id)
    );

    -- TABLE ARTICLES
    CREATE TABLE IF NOT EXISTS articles (
        id SERIAL PRIMARY KEY,
        category VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        image_url VARCHAR(1024),
        read_time INT,
        tags TEXT[],
        source_name VARCHAR(100),
        source_url VARCHAR(1024),
        is_featured BOOLEAN DEFAULT FALSE,
        author_id UUID REFERENCES users(id),
        views INT DEFAULT 0,
        is_ingested BOOLEAN DEFAULT FALSE,
        ingested_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_source_url ON articles(source_url) WHERE source_url IS NOT NULL;

    -- TABLE FEEDBACK
    CREATE TABLE IF NOT EXISTS feedback (
        id SERIAL PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        feedback_text TEXT NOT NULL,
        sentiment VARCHAR(20),
        status VARCHAR(20) DEFAULT 'new',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- TABLE SDQ RESULTS
    CREATE TABLE IF NOT EXISTS sdq_results (
        id SERIAL PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        answers INT[],
        total_difficulties_score INT,
        emotional_score INT,
        conduct_score INT,
        hyperactivity_score INT,
        peer_score INT,
        prosocial_score INT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- TABLE REPORTS
    CREATE TABLE IF NOT EXISTS reports (
        id SERIAL PRIMARY KEY,
        reporter_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        reported_user_id UUID REFERENCES users(id),
        reported_post_id UUID REFERENCES posts(id),
        reported_comment_id UUID REFERENCES comments(id),
        reason TEXT NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- TABLE APPEALS
    CREATE TABLE IF NOT EXISTS appeals (
        id SERIAL PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content_type VARCHAR(20) NOT NULL,
        content_id UUID NOT NULL,
        justification TEXT,
        admin_note TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        reviewed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- CHAT SYSTEM (UPDATED)
    CREATE TABLE IF NOT EXISTS chats (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        is_group BOOLEAN DEFAULT FALSE,
        name VARCHAR(100),
        image_url VARCHAR(1024),
        created_by UUID REFERENCES users(id),
        last_message_text TEXT,
        last_message_time TIMESTAMPTZ DEFAULT NOW(),
        allow_member_invites BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS chat_participants (
        chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        is_hidden BOOLEAN DEFAULT FALSE,
        is_admin BOOLEAN DEFAULT FALSE,
        unread_count INT DEFAULT 0,
        joined_at TIMESTAMPTZ DEFAULT NOW(),
        last_cleared_at TIMESTAMPTZ,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
        sender_id UUID REFERENCES users(id) ON DELETE CASCADE,
        text TEXT,
        type VARCHAR(20) DEFAULT 'text',
        attachment_url VARCHAR(1024),
        is_read_by_all BOOLEAN DEFAULT FALSE,
        is_deleted BOOLEAN DEFAULT FALSE,
        reply_to_id UUID REFERENCES messages(id),
        sent_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    CREATE TABLE IF NOT EXISTS group_banned_users (
        group_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        banned_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (group_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS group_invites (
        token VARCHAR(64) PRIMARY KEY,
        group_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
        created_by UUID NOT NULL REFERENCES users(id),
        expires_at TIMESTAMPTZ,
        max_uses INT,
        current_uses INT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- BLOCKED USERS
    CREATE TABLE IF NOT EXISTS blocked_users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        blocked_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (blocker_id, blocked_id)
    );

    -- AUDIT LOGS
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        actor_id UUID NOT NULL REFERENCES users(id), 
        target_id VARCHAR(100), 
        target_type VARCHAR(50), 
        action VARCHAR(50), 
        old_value JSONB,
        new_value JSONB,
        description VARCHAR(255),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- BOT CHAT SYSTEM
    CREATE TABLE IF NOT EXISTS bot_chats (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS bot_messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        bot_chat_id UUID NOT NULL REFERENCES bot_chats(id) ON DELETE CASCADE,
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        sources JSONB,
        sent_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- NOTIFICATIONS
    CREATE TABLE IF NOT EXISTS notifications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        type VARCHAR(20) NOT NULL,
        reference_id VARCHAR(36),
        text VARCHAR(255),
        is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- PROFESSIONAL PROFILES
    CREATE TABLE IF NOT EXISTS professional_profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        pro_type VARCHAR(50) DEFAULT 'psychologist',
        full_name_with_title VARCHAR(255),
        str_number VARCHAR(50) UNIQUE,
        province VARCHAR(100),
        practice_address TEXT,
        practice_schedule TEXT,
        str_image_path VARCHAR(1024),
        ktp_image_path VARCHAR(1024),
        selfie_image_path VARCHAR(1024),
        status VARCHAR(20) DEFAULT 'pending',
        verified_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- QUARANTINED ITEMS
    CREATE TABLE IF NOT EXISTS quarantined_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        original_target_id UUID NOT NULL,
        target_type VARCHAR(50) NOT NULL,
        file_path VARCHAR(1024),
        text_content TEXT,
        quarantined_by UUID REFERENCES users(id),
        reason TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)


def downgrade() -> None:
    # Hapus semua tabel jika perlu rollback
    op.execute("""
    DROP TABLE IF EXISTS 
    quarantined_items, professional_profiles, notifications, 
    bot_messages, bot_chats, audit_logs, blocked_users, group_invites, group_banned_users,
    messages, chat_participants, chats, appeals, reports, sdq_results, feedback, 
    articles, post_likes, seen_posts, saved_posts, connections, comments, posts, users 
    CASCADE;
    """)