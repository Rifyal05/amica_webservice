from ..models import SavedPost, Post, User
from ..extensions import db

def toggle_save_post(user_id, post_id):
    existing_save = SavedPost.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if existing_save:
        db.session.delete(existing_save)
        db.session.commit()
        return False
    else:
        new_save = SavedPost(user_id=user_id, post_id=post_id) # type: ignore
        db.session.add(new_save)
        db.session.commit()
        return True 

def get_user_saved_posts(target_user_id, current_user_id):
    target_user = User.query.get(target_user_id)
    if not target_user:
        return None, "User tidak ditemukan"

    # Cek Privasi
    if target_user_id != current_user_id and not target_user.is_saved_posts_public:
        return None, "Koleksi ini bersifat pribadi."

    saved_posts = db.session.query(Post).join(
        SavedPost, SavedPost.post_id == Post.id
    ).filter(
        SavedPost.user_id == target_user_id
    ).order_by(SavedPost.saved_at.desc()).all()

    return saved_posts, "Sukses"