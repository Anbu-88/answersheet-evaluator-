"""
ExamAI - Main Application
FastAPI entry point with CORS and route mounting.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.grading import router as grading_router
from config import APP_TITLE, APP_VERSION

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="AI-Powered Handwritten Exam Grading using Gemini 3",
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
app.include_router(grading_router)


@app.get("/")
async def root():
    return {
        "app": APP_TITLE,
        "version": APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "grade_exam": "POST /api/grade",
            "analyze_answer_key": "POST /api/analyze-answer-key",
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
