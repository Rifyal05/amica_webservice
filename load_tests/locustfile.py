import random
import os
from locust import HttpUser, task, between
from dotenv import load_dotenv

load_dotenv()

BYPASS_TOKEN = os.environ.get("BYPASS_LIMITER_TOKEN", "AKUCAPEKBANGET")

def load_image(filename):
    try:
        with open(filename, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return b""

SAFE_IMAGE = load_image("jeruk.jpeg")
UNSAFE_IMAGE = load_image("senjata.jpeg")

class AmicaLoadTester(HttpUser):
    wait_time = between(1, 5) 
    
    def on_start(self):
        self.user_idx = random.randint(0, 499)
        self.email = f"test_load_{self.user_idx}@amica.test"
        self.jwt_token = ""
        self.login()

    def login(self):
        response = self.client.post("/api/auth/login", json={
            "email": self.email,
            "password": "password123test"
        }, headers={"X-Load-Test-Token": BYPASS_TOKEN})
        
        if response.status_code == 200:
            self.jwt_token = response.json().get("access_token")

    @property
    def auth_header(self):
        return {
            "Authorization": f"Bearer {self.jwt_token}",
            "X-Load-Test-Token": BYPASS_TOKEN
        }

    @task(2)
    def create_post_with_ai(self):
        is_safe_test = random.choice([True, False])
        img_bytes = SAFE_IMAGE if is_safe_test else UNSAFE_IMAGE
        filename = "jeruk.jpeg" if is_safe_test else "senjata.jpeg"

        if not img_bytes:
            return

        files = {'image': (filename, img_bytes, 'image/jpeg')}
        data = {
            'caption': f"Uji Pipeline {'Safe' if is_safe_test else 'Unsafe'}. #AmicaLoadTest #{random.randint(1000,9999)}",
            'tags': ['Testing', 'AI']
        }
        
        self.client.post("/api/posts/", data=data, files=files, headers=self.auth_header)

    @task(10)
    def view_feed(self):
        self.client.get("/api/posts/?page=1&per_page=10", headers=self.auth_header)

    @task(5)
    def get_articles(self):
        self.client.get("/api/articles", headers={"X-Load-Test-Token": BYPASS_TOKEN})

    @task(3)
    def chat_with_bot(self):
        self.client.post("/api/bot/send", json={
            "message": "Halo Ai, apa pendapatmu tentang perdamaian dunia?"
        }, headers=self.auth_header)

    @task(2)
    def check_notifications(self):
        self.client.get("/api/notifications/", headers=self.auth_header)