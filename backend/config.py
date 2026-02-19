"""
ExamAI v2 - Configuration
Environment variables and app settings for production deployment.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini API ──
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# ── JWT Auth ──
JWT_SECRET = os.getenv("JWT_SECRET", "examai-super-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# ── Database ──
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./examai.db")

# ── App ──
APP_TITLE = "ExamAI - AI Exam Grader"
APP_VERSION = "2.0.0"
MAX_UPLOAD_SIZE_MB = 50
ALLOWED_EXTENSIONS = [".pdf"]

# ── File Storage ──
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
ANSWER_KEYS_DIR = os.path.join(UPLOAD_DIR, "answer_keys")
SUBMISSIONS_DIR = os.path.join(UPLOAD_DIR, "submissions")
REPORTS_DIR = os.path.join(UPLOAD_DIR, "reports")

# Create directories
for d in [UPLOAD_DIR, ANSWER_KEYS_DIR, SUBMISSIONS_DIR, REPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── PDF Processing ──
DPI = 200

# ── Default Admin ──
DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@examai.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_NAME = "System Admin"
