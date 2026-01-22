import random
import os
from locust import HttpUser, task, between
from dotenv import load_dotenv

load_dotenv()

BYPASS_TOKEN = os.environ.get("BYPASS_LIMITER_TOKEN", "AKUCAPEKBANGET")

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

    @task(10)
    def view_feed(self):
        self.client.get("/api/posts/?page=1&per_page=10", headers=self.auth_header)

    @task(5)
    def get_articles(self):
        self.client.get("/api/articles", headers={"X-Load-Test-Token": BYPASS_TOKEN})

    @task(2)
    def create_post_with_ai(self):
        file_content = b"fake-image-binary-data" 
        files = {'image': ('test.jpg', file_content, 'image/jpeg')}
        data = {
            'caption': f"Load test Amica. Tangguhlah serverku! #AmicaLoadTest #{random.randint(1000,9999)}",
            'tags': ['Testing', 'AI']
        }
        self.client.post("/api/posts/", data=data, files=files, headers=self.auth_header)

    @task(3)
    def chat_with_bot(self):
        self.client.post("/api/bot/send", json={
            "message": "Apa itu bullying berbasis sara?"
        }, headers=self.auth_header)

    @task(2)
    def check_notifications(self):
        self.client.get("/api/notifications/", headers=self.auth_header)