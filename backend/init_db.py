"""
ExamAI - Database Initializer
Creates all tables and seeds the default admin user.
"""

from db.session import engine, SessionLocal
from db.models import Base, User, UserRole
from auth.password import hash_password
from config import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_NAME


def init_database():
    """Create all tables and seed the default admin user."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

    # Seed admin user
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEFAULT_ADMIN_EMAIL).first()
        if not existing:
            admin = User(
                email=DEFAULT_ADMIN_EMAIL,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                full_name=DEFAULT_ADMIN_NAME,
                role=UserRole.admin,
            )
            db.add(admin)
            db.commit()
            print(f"✅ Default admin created: {DEFAULT_ADMIN_EMAIL} / {DEFAULT_ADMIN_PASSWORD}")
        else:
            print(f"ℹ️  Admin user already exists: {DEFAULT_ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
