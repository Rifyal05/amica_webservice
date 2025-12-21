import requests
import json
import os

def send_push_notification(player_ids, title, content, data=None):
    header = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {os.environ.get('ONESIGNAL_REST_API_KEY')}"
    }

    payload = {
        "app_id": os.environ.get('ONESIGNAL_APP_ID'),
        "include_player_ids": player_ids,
        "headings": {"en": title},
        "contents": {"en": content},
        "data": data if data else {} 
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