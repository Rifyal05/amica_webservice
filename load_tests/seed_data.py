import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db, bcrypt
from app.models import User

def seed_test_users(count=500):
    app = create_app()
    with app.app_context():
        print(f"Memulai pembuatan {count} user dummy untuk testing...")
        
        hashed_password = bcrypt.generate_password_hash("password123test").decode('utf-8')
        
        for i in range(count):
            email = f"test_load_{i}@amica.test"
            username = f"tester_{i}"
            
            existing = User.query.filter_by(email=email).first()
            if existing:
                continue
                
            new_user = User(
                id=uuid.uuid4(), # type: ignore
                email=email, # type: ignore
                username=username, # type: ignore
                display_name=f"Load Tester {i}", # type: ignore
                password_hash=hashed_password, # type: ignore
                role='user', # type: ignore
                is_verified=True  # type: ignore
            )
            db.session.add(new_user)
        
        db.session.commit()
        print("Selesai! User dummy siap digunakan.")

if __name__ == "__main__":
    seed_test_users(500)