from db.session import SessionLocal
from db.models import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f"ID: {u.id}, Email: {u.email}, Role: {u.role}")
db.close()
