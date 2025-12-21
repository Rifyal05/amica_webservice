from ..models import Report
from ..database import db

def create_report(reporter_id, target_type, target_id, reason):
    """Logika dasar untuk menyimpan laporan ke database."""
    
    reported_post_id = None
    reported_comment_id = None
    reported_user_id = None

    if target_type == 'post':
        reported_post_id = target_id
    elif target_type == 'comment':
        reported_comment_id = target_id
    elif target_type == 'user':
        reported_user_id = target_id
    else:
        return False, "Tipe laporan tidak valid."

    new_report = Report(
        reporter_user_id=reporter_id, # type: ignore
        reported_user_id=reported_user_id, # type: ignore
        reported_post_id=reported_post_id, # type: ignore
        reported_comment_id=reported_comment_id, # type: ignore
        reason=reason, # type: ignore
        status='pending' # type: ignore
    )
    
    try:
        db.session.add(new_report)
        db.session.commit()
        return True, "Laporan berhasil dikirim."
    except Exception as e:
        db.session.rollback()
        return False, f"Gagal menyimpan laporan: {str(e)}"