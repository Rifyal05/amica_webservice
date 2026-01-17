from flask import Blueprint, jsonify, request
from ..models import Article, User, db
from ..extensions import limiter 
api_bp = Blueprint('public_api', __name__, url_prefix='/api')

@api_bp.route('/articles', methods=['GET'])
@limiter.limit("30 per minute")
def get_public_articles():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 50, type=int) 
        search = request.args.get('q', '', type=str)
        category = request.args.get('category', '', type=str)

        query = Article.query

        if search:
            query = query.filter(Article.title.ilike(f"%{search}%"))
        
        if category and category.lower() != 'semua':
            query = query.filter(Article.category.ilike(category))

        pagination = query.order_by(Article.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        data = []
        for a in pagination.items:
            author = User.query.get(a.author_id)
            data.append({
                'id': a.id,
                'title': a.title,
                'category': a.category,
                'author': author.display_name if author else "Lensa Team",
                'created_at': a.created_at.strftime('%d %B %Y'),
                'is_featured': a.is_featured,
                'image_url': a.image_url,
                'content': a.content,
                'tags': a.tags if a.tags else [],
                'read_time': a.read_time,
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
    


@api_bp.route('/articles/categories', methods=['GET'])
def get_article_categories():
    try:
        categories = db.session.query(Article.category).distinct().all()
        

        category_list = [c[0] for c in categories if c[0]]
        category_list.sort()
        
        final_categories = ['Semua'] + category_list
        
        return jsonify(final_categories), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500