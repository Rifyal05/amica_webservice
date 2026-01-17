from ..models import db, Notification, User
from ..services.notification_service import NotificationService 

def create_notification(recipient_id, sender_id, type, reference_id=None, text=None):
    if recipient_id == sender_id and type not in ['post_rejected', 'appeal_approved', 'appeal_rejected']:
        return

    new_notif = Notification(
        recipient_id=recipient_id, # type: ignore
        sender_id=sender_id, # type: ignore
        type=type, # type: ignore
        reference_id=reference_id, # type: ignore
        text=text  # type: ignore
    )
    db.session.add(new_notif)
    db.session.commit()

    recipient = User.query.get(recipient_id)
    sender = User.query.get(sender_id)

    if recipient and recipient.onesignal_player_id:
        if type in ['like', 'comment'] and reference_id:
            from ..models import Post 
            post = Post.query.get(reference_id)
            content = f"menyukai postingan Anda." if type == 'like' else f"mengomentari: {(text[:40] + '..') if text and len(text) > 40 else text}"
            NotificationService().send_post_notification(
                recipient_ids=[recipient.onesignal_player_id],
                sender_name=sender.display_name, # type: ignore
                text=content,
                post_id=reference_id,
                post_image_path=post.image_url if post else None 
            )
            return

        elif type == 'follow':
            NotificationService().send_push_notification(
                player_ids=[recipient.onesignal_player_id],
                title="Pengikut Baru",
                content=f"{sender.display_name} mulai mengikuti Anda.", # type: ignore
                data={"type": "follow", "user_id": str(sender.id)}, # type: ignore
                large_icon=sender.avatar_url # type: ignore
            )
            return

        is_mod = type in ['post_rejected', 'appeal_approved', 'appeal_rejected']
        title = "Pemberitahuan Amica"
        content = "Seseorang berinteraksi dengan Anda."

        if type == 'post_rejected':
            title = "AMICA Moderasi"
            content = "Postingan Anda ditahan karena melanggar pedoman komunitas."
        elif type == 'appeal_approved':
            title = "AMICA Update"
            content = "Banding diterima! Postingan Anda kini telah tayang."
        elif type == 'appeal_rejected':
            title = "AMICA Update"
            content = "Banding ditolak. Postingan Anda dihapus permanen."

        NotificationService().send_push_notification(
            player_ids=[recipient.onesignal_player_id],
            title=title,
            content=content,
            data={"type": type, "reference_id": reference_id},
            large_icon="static/assets/logo_amica.png" if is_mod else sender.avatar_url # type: ignore
        )