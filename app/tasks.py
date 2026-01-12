import os
from datetime import datetime, timezone, timedelta
from .extensions import db
from .models import Post, Appeal

def cleanup_moderation_task(app):
    with app.app_context():
        limit_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        expired_posts = Post.query.filter(
            Post.moderation_status == 'rejected',
            Post.created_at <= limit_time
        ).all()

        reject_folder = os.path.join(app.root_path, 'static', 'reject')
        
        count = 0
        for post in expired_posts:
            if post.image_url:
                path = os.path.join(reject_folder, post.image_url)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            
            Appeal.query.filter_by(content_id=post.id).delete()
            db.session.delete(post)
            count += 1
        
        if count > 0:
            db.session.commit()
            print(f"[Scheduler] Cleanup finished: {count} posts removed.")