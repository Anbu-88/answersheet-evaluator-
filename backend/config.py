"""
ExamAI - Configuration
Loads environment variables and defines app settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"  # Latest Gemini Flash with native vision

# App Configuration
APP_TITLE = "ExamAI - AI Exam Grader"
APP_VERSION = "1.0.0"
MAX_UPLOAD_SIZE_MB = 50
ALLOWED_EXTENSIONS = [".pdf"]

# PDF Processing
DPI = 200  # Resolution for PDF to image conversion
