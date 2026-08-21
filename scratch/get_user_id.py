from db import SessionLocal
from db.models import User

db = SessionLocal()
user = db.query(User).filter(User.username == "kikan").first()
if user:
    print(f"user_id: {user.id}")
else:
    print("User 'kikan' not found")
db.close()
