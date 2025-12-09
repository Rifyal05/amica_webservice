-- DANGER!! JALANKAN DENGAN HATI-HATI. INI AKAN MENGHAPUS SELURUH DATA DI SERVER JIKA DIJALANKAN SECARA LANGSUNG PADA SERVER PRODUKSI YANG SUDAH BERJALAN

DROP TABLE IF EXISTS audit_logs, blocked_users, messages, chat_participants, chats, appeals, reports, sdq_results, feedback, articles, post_likes, seen_posts, saved_posts, connections, comments, posts, users CASCADE;

-- TABLE USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    username VARCHAR(25) UNIQUE NOT NULL,
    display_name VARCHAR(50) NOT NULL,
    avatar_url VARCHAR(1024),
    banner_url VARCHAR(1024),
    bio TEXT,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    onesignal_player_id VARCHAR(50),
    
    -- Status Hukuman
    is_suspended BOOLEAN DEFAULT FALSE,
    suspended_until TIMESTAMPTZ,
    
    -- Fitur Baru: Google Login
    google_uid VARCHAR(128) UNIQUE, 
    auth_provider VARCHAR(20) DEFAULT 'email', -- 'email', 'google'
    
    -- Fitur Baru: PIN Keamanan
    security_pin_hash VARCHAR(255), 

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- TABLE POSTS
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caption TEXT,
    image_url VARCHAR(1024),
    tags TEXT[],
    moderation_status VARCHAR(20) DEFAULT 'approved',
    moderation_details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0
);

-- TABLE COMMENTS
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    text TEXT NOT NULL, 
    moderation_status VARCHAR(20) DEFAULT 'approved',
    moderation_details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RELATIONS
CREATE TABLE connections (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, following_id)
);
CREATE TABLE saved_posts (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    saved_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);
CREATE TABLE seen_posts (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    seen_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);
CREATE TABLE post_likes (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);

-- TABLE ARTICLES
CREATE TABLE articles (
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- TABLE FEEDBACK
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    feedback_text TEXT NOT NULL,
    sentiment VARCHAR(20),
    status VARCHAR(20) DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- TABLE SDQ
CREATE TABLE sdq_results (
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
CREATE TABLE reports (
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
CREATE TABLE appeals (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(20) NOT NULL,
    content_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CHAT SYSTEM
CREATE TABLE chats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE chat_participants (
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- BLOCKED USERS
CREATE TABLE blocked_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (blocker_id, blocked_id)
);

-- TABLE BARU: AUDIT LOGS (Untuk History Admin)
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    actor_id UUID NOT NULL REFERENCES users(id), -- Siapa yang melakukan aksi
    target_id VARCHAR(100), -- ID Korban/Objek (Bisa UUID User atau Int Artikel/Laporan)
    target_type VARCHAR(50), -- 'User', 'Article', 'Report'
    action VARCHAR(50), -- 'SUSPEND', 'DELETE', 'UPDATE'
    
    old_value JSONB,
    new_value JSONB,
    
    description VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);