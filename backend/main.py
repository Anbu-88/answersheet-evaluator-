"""
ExamAI v2 - Main Application
FastAPI entry point with CORS, routers, and startup DB initialization.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.teacher import router as teacher_router
from routes.student import router as student_router
from config import APP_TITLE, APP_VERSION

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="AI-Powered Handwritten Exam Grading Platform for Schools & Colleges",
)

# CORS — allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(teacher_router)
app.include_router(student_router)


@app.on_event("startup")
def on_startup():
    """Initialize database and seed data on startup."""
    from init_db import init_database
    init_database()


@app.get("/")
async def root():
    return {
        "app": APP_TITLE,
        "version": APP_VERSION,
        "docs": "/docs",
        "login": "POST /api/auth/login",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": APP_VERSION}
