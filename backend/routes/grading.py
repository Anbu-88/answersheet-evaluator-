"""
ExamAI - Grading API Route
Handles exam sheet upload, grading, and report generation.
"""

import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from services.gemini_service import analyze_answer_key, grade_exam_sheet
from services.pdf_service import pdf_to_images, generate_report_pdf

router = APIRouter(prefix="/api", tags=["grading"])


@router.post("/grade")
async def grade_exam(
    exam_sheet: UploadFile = File(..., description="Handwritten exam sheet PDF"),
    answer_key: UploadFile = File(..., description="Answer key PDF"),
):
    """
    Grade a handwritten exam sheet against an answer key.
    
    Pipeline:
    1. Convert both PDFs to page images
    2. Analyze the answer key with Gemini (extract questions, answers, marks)
    3. Grade the exam sheet against the answer key with Gemini
    4. Generate a PDF report with per-question marks and reasoning
    5. Return the report PDF for download
    """
    # Validate file types
    if not exam_sheet.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Exam sheet must be a PDF file")
    if not answer_key.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Answer key must be a PDF file")
    
    try:
        # Read uploaded files
        exam_bytes = await exam_sheet.read()
        answer_bytes = await answer_key.read()
        
        # Step 1: Convert PDFs to images
        print("📄 Converting answer key PDF to images...")
        answer_images = pdf_to_images(answer_bytes)
        print(f"   → {len(answer_images)} pages extracted from answer key")
        
        print("📄 Converting exam sheet PDF to images...")
        exam_images = pdf_to_images(exam_bytes)
        print(f"   → {len(exam_images)} pages extracted from exam sheet")
        
        # Step 2: Analyze answer key with Gemini
        print("🔍 Analyzing answer key with Gemini 3...")
        answer_key_data = analyze_answer_key(answer_images)
        total_questions = answer_key_data.get("total_questions", 0)
        print(f"   → Found {total_questions} questions")
        
        # Step 3: Grade exam sheet against answer key
        print("📝 Grading exam sheet with Gemini 3...")
        grading_results = grade_exam_sheet(exam_images, answer_key_data)
        total_obtained = grading_results.get("total_marks_obtained", 0)
        total_possible = grading_results.get("total_marks_possible", 0)
        print(f"   → Score: {total_obtained}/{total_possible}")
        
        # Step 4: Generate PDF report
        print("📊 Generating grading report PDF...")
        report_pdf = generate_report_pdf(grading_results)
        print(f"   → Report generated ({len(report_pdf)} bytes)")
        
        # Return PDF
        return Response(
            content=report_pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=examai_grading_report.pdf"
            }
        )
    
    except Exception as e:
        print(f"❌ Error during grading: {str(e)}")
        traceback.print_exc()
        raise HTTPException(500, f"Grading failed: {str(e)}")


@router.post("/analyze-answer-key")
async def analyze_key_only(
    answer_key: UploadFile = File(..., description="Answer key PDF"),
):
    """
    Analyze only the answer key and return structured data.
    Useful for previewing the extracted questions before grading.
    """
    if not answer_key.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Answer key must be a PDF file")
    
    try:
        answer_bytes = await answer_key.read()
        answer_images = pdf_to_images(answer_bytes)
        answer_key_data = analyze_answer_key(answer_images)
        return answer_key_data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Analysis failed: {str(e)}")
