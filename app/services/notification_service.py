import requests
import json
import os
from flask import url_for
from ..utils.image_utils import generate_thumbnail

class NotificationService:
    def send_push_notification(self, player_ids, title, content, data=None, group_key=None, large_icon=None):
        header = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Basic {os.environ.get('ONESIGNAL_REST_API_KEY')}"
        }

        android_group = str(group_key) if group_key else None

        payload = {
            "app_id": os.environ.get('ONESIGNAL_APP_ID'),
            "include_player_ids": player_ids,
            "headings": {"en": title},
            "contents": {"en": content},
            "data": data if data else {},
            
            "android_group": android_group, 
            "android_group_message": {
                "en": "$[notif_count] pesan baru" 
            },

            "large_icon": large_icon if large_icon else None,
            "small_icon": "ic_stat_onesignal_default",
            "android_accent_color": "FF6B4EFF"
        }

        try:
            req = requests.post(
                "https://onesignal.com/api/v1/notifications", 
                headers=header, 
                data=json.dumps(payload)
            )
            return req.status_code == 200
        except Exception as e:
            print(f"Notification Error: {e}")
            return False

    def send_post_notification(self, recipient_ids, sender_name, text, post_id, post_image_path=None):
        image_url = None
        if post_image_path:
            thumb_path = generate_thumbnail(post_image_path, size=(256, 256))
            if thumb_path:
                image_url = url_for('static', filename=thumb_path, _external=True)
            else:
                image_url = url_for('static', filename=post_image_path, _external=True)

        click_data = {
            "type": "post",
            "reference_id": str(post_id)
        }

        self.send_push_notification(
            player_ids=recipient_ids,
            title=f"{sender_name}",
            content=text,
            data=click_data,
            large_icon=image_url
        )

    def send_chat_notification(self, recipient_ids, title, content, chat_id, is_group, sender_avatar_path=None):
        icon_url = None
        if sender_avatar_path:
            thumb_path = generate_thumbnail(sender_avatar_path, size=(128, 128))
            if thumb_path:
                icon_url = url_for('static', filename=thumb_path, _external=True)
            else:
                icon_url = url_for('static', filename=sender_avatar_path, _external=True)

        click_data = {
            "type": "chat",
            "chat_id": str(chat_id),
            "is_group": is_group
        }

        self.send_push_notification(
            player_ids=recipient_ids,
            title=title,
            content=content,
            data=click_data,
            group_key=str(chat_id),
            large_icon=icon_url
        )