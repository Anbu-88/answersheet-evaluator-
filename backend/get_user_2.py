from db.session import SessionLocal
from db.models import User

db = SessionLocal()
u = db.query(User).filter(User.id == 2).first()
if u:
    print(f"ID: {u.id}, Email: {u.email}, Role: {u.role}")
else:
    print("User not found")
db.close()
