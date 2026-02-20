from db.session import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("ALTER TABLE tests ADD COLUMN test_type VARCHAR(20) DEFAULT 'subjective'"))
    print("✅ test_type column added to tests table")
