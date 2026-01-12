from flask import Flask
from app.extensions import db  
from app.models import User, Post, Article, Chat, Message 


from app import create_app 
app = create_app()

def clean_url(url):
    """
    Menghapus 'static/' atau '/static/' di awal string.
    Mengubah 'static/uploads/foto.jpg' -> 'uploads/foto.jpg'
    """
    if not url:
        return None
    
    url = url.strip()
    
    if url.startswith('/static/'):
        return url.replace('/static/', '', 1)
    if url.startswith('static/'):
        return url.replace('static/', '', 1)
    
    return url

def run_cleanup():
    with app.app_context():
        print("--- MEMULAI PEMBERSIHAN URL DATABASE ---")
        
        users = User.query.all()
        count_user = 0
        for u in users:
            changed = False
            if u.avatar_url and 'static/' in u.avatar_url:
                u.avatar_url = clean_url(u.avatar_url)
                changed = True
            if u.banner_url and 'static/' in u.banner_url:
                u.banner_url = clean_url(u.banner_url)
                changed = True
            if changed:
                count_user += 1
        
        posts = Post.query.all()
        count_post = 0
        for p in posts:
            if p.image_url and 'static/' in p.image_url:
                p.image_url = clean_url(p.image_url)
                count_post += 1

        articles = Article.query.all()
        count_article = 0
        for a in articles:
            if a.image_url and 'static/' in a.image_url:
                a.image_url = clean_url(a.image_url)
                count_article += 1

        chats = Chat.query.all()
        count_chat = 0
        for c in chats:
            if c.image_url and 'static/' in c.image_url:
                c.image_url = clean_url(c.image_url)
                count_chat += 1
        
        messages = Message.query.all()
        count_msg = 0
        for m in messages:
            if m.attachment_url and 'static/' in m.attachment_url:
                m.attachment_url = clean_url(m.attachment_url)
                count_msg += 1

        try:
            db.session.commit()
            print(f"✅ Users updated: {count_user}")
            print(f"✅ Posts updated: {count_post}")
            print(f"✅ Articles updated: {count_article}")
            print(f"✅ Chats updated: {count_chat}")
            print(f"✅ Messages updated: {count_msg}")
            print("\n--- PEMBERSIHAN SELESAI ---")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saat commit database: {e}")

if __name__ == '__main__':
    run_cleanup()