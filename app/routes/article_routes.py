import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from ..models import db, Article, User
from ..utils.decorators import admin_required
from ..utils.logger import record_log # Pastikan import logger

article_bp = Blueprint('article_admin', __name__, url_prefix='/admin/articles')

# Helper: Save Image
def save_article_image(file):
    if not file: return None
    filename = secure_filename(file.filename)
    upload_path = os.path.join(current_app.root_path, 'static/uploads/articles')
    if not os.path.exists(upload_path): os.makedirs(upload_path)
    
    unique_filename = f"art_{uuid.uuid4().hex}_{filename}"
    file.save(os.path.join(upload_path, unique_filename))
    return unique_filename

@article_bp.route('/', methods=['GET'])
@admin_required
def get_articles(current_user):
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        search = request.args.get('q', '', type=str)

        query = Article.query
        if search:
            query = query.filter(Article.title.ilike(f"%{search}%"))

        pagination = query.order_by(Article.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        data = []
        for a in pagination.items:
            author = User.query.get(a.author_id)
            data.append({
                'id': a.id,
                'title': a.title,
                'category': a.category,
                'author': author.display_name if author else "Unknown",
                'created_at': a.created_at.strftime('%d/%m/%Y'),
                'is_featured': a.is_featured,
                'image_url': a.image_url,
                'content': a.content,
                'tags': a.tags,
                'source_name': a.source_name,
                'source_url': a.source_url
            })

        return jsonify({
            'articles': data,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@article_bp.route('/', methods=['POST'])
@admin_required
def create_article(current_user):
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            return jsonify({'message': 'Judul dan Konten wajib diisi'}), 400

        final_image = None
        if 'image' in request.files:
            final_image = save_article_image(request.files['image'])
        elif request.form.get('image_url_manual'):
            final_image = request.form.get('image_url_manual')

        tags_list = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]

        new_article = Article(
            title=title, # type: ignore
            content=content,# type: ignore
            category=request.form.get('category'),# type: ignore
            tags=tags_list,# type: ignore
            image_url=final_image,# type: ignore
            author_id=current_user.id,# type: ignore
            read_time=len(content.split()) // 200 + 1,# type: ignore
            source_name=request.form.get('source_name'),# type: ignore
            source_url=request.form.get('source_url'),# type: ignore
            is_featured=request.form.get('is_featured') == 'true'# type: ignore
        )

        db.session.add(new_article)
        db.session.commit()

        # --- LOG CREATE ---
        record_log(
            actor_id=current_user.id,
            target_id=str(new_article.id), # Simpan ID Artikel
            target_type='Article',
            action='CREATE_ARTICLE',
            old_val=None,
            new_val={'title': title, 'category': new_article.category},
            description=f"Menerbitkan artikel baru: {title[:50]}..."
        )

        return jsonify({'message': 'Artikel berhasil diterbitkan!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# UPDATE ARTICLE (PUT)
@article_bp.route('/<int:id>', methods=['POST']) 
@admin_required
def update_article(current_user, id):
    try:
        article = Article.query.get(id)
        if not article: return jsonify({'message': 'Artikel tidak ditemukan'}), 404

        # Snapshot data lama
        old_data = {
            'title': article.title,
            'category': article.category,
            'is_featured': article.is_featured
        }

        article.title = request.form.get('title')
        article.content = request.form.get('content')
        article.category = request.form.get('category')
        article.source_name = request.form.get('source_name')
        article.source_url = request.form.get('source_url')
        article.is_featured = request.form.get('is_featured') == 'true'
        
        tags_raw = request.form.get('tags', '')
        article.tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

        if 'image' in request.files:
            article.image_url = save_article_image(request.files['image'])
        elif request.form.get('image_url_manual'):
            article.image_url = request.form.get('image_url_manual')

        article.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        # --- LOG UPDATE ---
        record_log(
            actor_id=current_user.id,
            target_id=str(article.id),
            target_type='Article',
            action='UPDATE_ARTICLE',
            old_val=old_data,
            new_val={'title': article.title, 'category': article.category},
            description=f"Mengedit artikel: {article.title[:50]}..."# type: ignore
        )

        return jsonify({'message': 'Artikel berhasil diperbarui!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@article_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def delete_article(current_user, id):
    try:
        article = Article.query.get(id)
        if not article: return jsonify({'message': 'Artikel tidak ditemukan'}), 404
        
        title_backup = article.title
        
        db.session.delete(article)
        db.session.commit()

        # --- LOG DELETE ---
        record_log(
            actor_id=current_user.id,
            target_id=None, # Target ID null karena artikel dihapus
            target_type='Article',
            action='DELETE_ARTICLE',
            old_val={'title': title_backup}, # Simpan judul buat kenang-kenangan
            new_val=None,
            description=f"Menghapus artikel: {title_backup[:50]}..."
        )

        return jsonify({'message': 'Artikel dihapus.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500