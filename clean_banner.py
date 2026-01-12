from app.extensions import db
from app.models import User, Post, Article, Chat, Message
from app import create_app

app = create_app()

def clean_to_filename(url):
    if not url:
        return None
    url = url.strip()
    if 'static/' in url:
        url = url.replace('static/', '')
    if 'uploads/' in url:
        url = url.replace('uploads/', '')
    if url.startswith('/'):
        url = url[1:]
    return url

def run_cleanup():
    with app.app_context():
        users = User.query.all()
        for u in users:
            if u.avatar_url:
                u.avatar_url = clean_to_filename(u.avatar_url)
            if u.banner_url:
                u.banner_url = clean_to_filename(u.banner_url)
        
        posts = Post.query.all()
        for p in posts:
            if p.image_url:
                p.image_url = clean_to_filename(p.image_url)

        chats = Chat.query.all()
        for c in chats:
            if c.image_url:
                c.image_url = clean_to_filename(c.image_url)

        try:
            db.session.commit()
            print("Pembersihan database berhasil.")
        except Exception as e:
            db.session.rollback()
            print(f"Gagal: {e}")

if __name__ == '__main__':
    run_cleanup()