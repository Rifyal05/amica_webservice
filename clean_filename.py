from app.extensions import db
from app.models import User, Post, Article, Chat, Message
from app import create_app 

app = create_app()

def clean_to_filename(url):
    """
    Mengubah path panjang menjadi hanya nama file.
    Contoh: 
    - 'static/uploads/foto.jpg' -> 'foto.jpg'
    - '/uploads/foto.jpg' -> 'foto.jpg'
    - 'uploads/foto.jpg' -> 'foto.jpg'
    """
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
        print("--- MEMULAI PEMBERSIHAN KE NAMA FILE SAJA ---")
        
        users = User.query.all()
        count_user = 0
        for u in users:
            changed = False
            if u.avatar_url and ('/' in u.avatar_url):
                u.avatar_url = clean_to_filename(u.avatar_url)
                changed = True
            if u.banner_url and ('/' in u.banner_url):
                u.banner_url = clean_to_filename(u.banner_url)
                changed = True
            if changed: count_user += 1
        
        posts = Post.query.all()
        count_post = 0
        for p in posts:
            if p.image_url and ('/' in p.image_url):
                p.image_url = clean_to_filename(p.image_url)
                count_post += 1

        chats = Chat.query.all()
        count_chat = 0
        for c in chats:
            if c.image_url and ('/' in c.image_url):
                c.image_url = clean_to_filename(c.image_url)
                count_chat += 1

        
        try:
            db.session.commit()
            print(f"✅ Users fixed: {count_user}")
            print(f"✅ Posts fixed: {count_post}")
            print(f"✅ Chats fixed: {count_chat}")
            print("--- DATABASE BERSIH (HANYA NAMA FILE) ---")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    run_cleanup()