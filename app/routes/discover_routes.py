from flask import Blueprint, jsonify, request
import json 
from sqlalchemy import func, desc, or_, cast, String, case
from datetime import datetime, timedelta, timezone
from ..models import Post, User, Connection, db, Article
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..routes.user_routes import user_to_dict, serialize_post
import random
from ..extensions import limiter 
from ..extensions import redis_client, db, limiter

discover_bp = Blueprint('discover', __name__)

def get_smart_trending_tags():
    cached_tags = redis_client.get("trending_tags")
    if cached_tags is not None:
        try:
            return json.loads(cached_tags) # type: ignore
        except (json.JSONDecodeError, TypeError):
            pass

    now = datetime.now(timezone.utc)
    posts = Post.query.filter(
        Post.moderation_status == 'approved', 
        Post.created_at >= (now - timedelta(days=30))
    ).all()

    tag_counts = {}
    for post in posts:
        if post.tags:
            for tag in post.tags:
                clean = tag.lower().strip()
                if len(clean) > 1:
                    tag_counts[clean] = tag_counts.get(clean, 0) + 1
    
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    final_tags = [t[0] for t in sorted_tags[:10]]
    redis_client.set("trending_tags", json.dumps(final_tags), ex=3600)

    return final_tags
def serialize_article(article):
    img = article.image_url
    if img and not img.startswith('http') and not img.startswith('/static'):
        img = f"/static/uploads/{img}"
        
    return {
        'id': article.id,
        'title': article.title,
        'category': article.category,
        'image_url': img,
        
        'content': article.content, 
        
        'views': getattr(article, 'views', 0),
        'read_time': getattr(article, 'read_time', 5),
        'created_at': article.created_at.isoformat(),
        'author': {
            'username': article.author.username if article.author else 'Admin',
            'avatar_url': article.author.avatar_url if article.author else None
        }
    }

@discover_bp.route('/', methods=['GET'])
@limiter.limit("20 per minute")
@jwt_required(optional=True)
def get_discover_dashboard():
    current_id = get_jwt_identity()
    tags = get_smart_trending_tags()
    q_ver = User.query.filter_by(is_verified=True)
    if current_id:
        q_ver = q_ver.filter(User.id != current_id)
    verified = q_ver.order_by(func.random()).limit(10).all()
    articles = Article.query.order_by(Article.created_at.desc()).limit(5).all()
    return jsonify({
        'tags': tags,
        'users': [user_to_dict(u) for u in verified],
        'articles': [serialize_article(a) for a in articles]
    }), 200

@discover_bp.route('/users/list', methods=['GET'])
@jwt_required(optional=True)
def get_user_list():
    page = request.args.get('page', 1, type=int)
    current_id = get_jwt_identity()
    query = User.query.filter_by(is_verified=True)
    if current_id:
        query = query.filter(User.id != current_id)
    p = query.paginate(page=page, per_page=20, error_out=False)
    return jsonify({'users': [user_to_dict(u) for u in p.items], 'has_next': p.has_next}), 200

@discover_bp.route('/posts/list', methods=['GET'])
@jwt_required(optional=True)
def get_post_list():
    t = request.args.get('type', 'all')
    page = request.args.get('page', 1, type=int)
    current_id = get_jwt_identity()
    query = Post.query.filter_by(moderation_status='approved')
    if current_id:
        query = query.filter(Post.user_id != current_id)
    if t == 'image':
        query = query.filter(Post.image_url != None)
    elif t == 'text':
        query = query.filter(or_(Post.image_url == None, Post.image_url == ''))
    p = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=20)
    return jsonify({'posts': [serialize_post(post, current_id) for post in p.items], 'has_next': p.has_next}), 200

@discover_bp.route('/articles/list', methods=['GET'])
def get_article_list():
    page = request.args.get('page', 1, type=int)
    p = Article.query.order_by(Article.created_at.desc()).paginate(page=page, per_page=15)
    return jsonify({'articles': [serialize_article(a) for a in p.items], 'has_next': p.has_next}), 200


@discover_bp.route('/articles/<int:article_id>', methods=['GET'])
def get_article_detail(article_id):
    article = Article.query.get(article_id)
    if not article:
        return jsonify({"error": "Artikel tidak ditemukan"}), 404
    
    article.views = (article.views or 0) + 1
    db.session.commit()
    
    return jsonify(serialize_article(article)), 200

@discover_bp.route('/search', methods=['GET'])
@limiter.limit("10 per minute")
@jwt_required(optional=True)
def search_content():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'users':[], 'posts':[], 'articles':[]}), 200
    current_id = get_jwt_identity()
    users = User.query.filter(or_(User.username.ilike(f'%{q}%'), User.display_name.ilike(f'%{q}%'))).limit(10).all()
    posts = Post.query.filter(Post.moderation_status == 'approved', or_(Post.caption.ilike(f'%{q}%'), cast(Post.tags, String).ilike(f'%{q}%'))).limit(20).all()
    articles = Article.query.filter(or_(Article.title.ilike(f'%{q}%'), Article.category.ilike(f'%{q}%'), cast(Article.tags, String).ilike(f'%{q}%'), Article.content.ilike(f'%{q}%'))).order_by(case((Article.title.ilike(f'%{q}%'), 1), (cast(Article.tags, String).ilike(f'%{q}%'), 2), else_=3)).limit(10).all()
    return jsonify({
        'users': [user_to_dict(u) for u in users if str(u.id) != str(current_id)],
        'posts': [serialize_post(p, current_id) for p in posts if str(p.user_id) != str(current_id)],
        'articles': [serialize_article(a) for a in articles]
    }), 200

@discover_bp.route('/articles/lookup', methods=['POST'])
def lookup_article_by_url():
    data = request.get_json()
    target_url = data.get('url', '').strip()
    
    if not target_url:
        return jsonify({"error": "URL required"}), 400

    article = Article.query.filter(Article.source_url == target_url).first()
    
    if not article:
        clean_target = target_url.replace("https://", "").replace("http://", "").rstrip("/")
        article = Article.query.filter(Article.source_url.ilike(f"%{clean_target}%")).first()

    if article:
        return jsonify({
            "found": True,
            "article": serialize_article(article)
        }), 200
    
    return jsonify({"found": False}), 200