"""
ExamAI - Student Routes
View tests, submit answer sheets, view results, and raise disputes.
"""

import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.session import get_db
from db.models import (
    User, UserRole, Test, TestStatus, Submission, GradingStatus,
    Dispute, DisputeStatus, StudentClass,
)
from auth.dependencies import require_role
from schemas.schemas import (
    TestResponse, SubmissionResponse, DisputeCreate, DisputeResponse, StudentStats,
)
from config import SUBMISSIONS_DIR

router = APIRouter(prefix="/api/student", tags=["student"])
student_dep = require_role(UserRole.student)


# ── Dashboard ──

@router.get("/stats", response_model=StudentStats)
async def get_student_stats(
    current_user: User = Depends(student_dep),
    db: Session = Depends(get_db),
):
    """Get student dashboard statistics."""
    class_ids = [sc.class_id for sc in db.query(StudentClass).filter(
        StudentClass.student_id == current_user.id
    ).all()]

    if not class_ids:
        return StudentStats(
            total_tests=0, pending_tests=0, completed_tests=0,
            average_score=None, open_disputes=0,
        )

    now = datetime.utcnow()
    tests = db.query(Test).filter(
        Test.class_id.in_(class_ids),
        Test.status != TestStatus.draft,
    ).all()

    # Tests where student has submitted
    submitted_test_ids = [s.test_id for s in db.query(Submission).filter(
        Submission.student_id == current_user.id
    ).all()]

    pending = sum(1 for t in tests if t.id not in submitted_test_ids and t.end_time > now)
    completed = len(submitted_test_ids)

    # Average score
    graded = db.query(Submission).filter(
        Submission.student_id == current_user.id,
        Submission.grading_status == GradingStatus.graded,
        Submission.marks_obtained.isnot(None),
        Submission.total_marks.isnot(None),
    ).all()

    avg = None
    if graded:
        percentages = [(s.marks_obtained / s.total_marks) * 100 for s in graded if s.total_marks > 0]
        if percentages:
            avg = round(sum(percentages) / len(percentages), 1)

    open_disputes = db.query(Dispute).filter(
        Dispute.student_id == current_user.id,
        Dispute.status == DisputeStatus.open,
    ).count()

    return StudentStats(
        total_tests=len(tests),
        pending_tests=pending,
        completed_tests=completed,
        average_score=avg,
        open_disputes=open_disputes,
    )


# ── Tests ──

@router.get("/tests")
async def list_my_tests(
    current_user: User = Depends(student_dep),
    db: Session = Depends(get_db),
):
    """List all tests assigned to the student's class(es)."""
    class_ids = [sc.class_id for sc in db.query(StudentClass).filter(
        StudentClass.student_id == current_user.id
    ).all()]

    if not class_ids:
        return []

    now = datetime.utcnow()
    tests = db.query(Test).filter(
        Test.class_id.in_(class_ids),
        Test.status != TestStatus.draft,
    ).order_by(Test.end_time.desc()).all()

    result = []
    for t in tests:
        # Check if student has already submitted
        submission = db.query(Submission).filter(
            Submission.test_id == t.id,
            Submission.student_id == current_user.id,
        ).first()

        can_submit = (
            t.status == TestStatus.active
            and t.start_time <= now <= t.end_time
            and submission is None
        )

        result.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "subject_name": t.subject.name if t.subject else "",
            "class_name": t.class_.name if t.class_ else "",
            "start_time": t.start_time.isoformat(),
            "end_time": t.end_time.isoformat(),
            "total_marks": t.total_marks,
            "status": t.status.value,
            "can_submit": can_submit,
            "has_submitted": submission is not None,
            "submission_id": submission.id if submission else None,
            "grading_status": submission.grading_status.value if submission else None,
            "marks_obtained": submission.marks_obtained if submission else None,
        })

    return result


# ── Submit Answer Sheet ──

@router.post("/tests/{test_id}/submit")
async def submit_answer_sheet(
    test_id: int,
    answer_sheet: UploadFile = File(..., description="Answer sheet PDF"),
    current_user: User = Depends(student_dep),
    db: Session = Depends(get_db),
):
    """Submit an answer sheet PDF for a test."""
    now = datetime.utcnow()

    # Validate test
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(404, "Test not found")

    # Check student is in the class
    in_class = db.query(StudentClass).filter(
        StudentClass.student_id == current_user.id,
        StudentClass.class_id == test.class_id,
    ).first()
    if not in_class:
        raise HTTPException(403, "You are not enrolled in this class")

    # Check time restrictions
    if now < test.start_time:
        raise HTTPException(400, "Test has not started yet")
    if now > test.end_time:
        raise HTTPException(400, "Submission deadline has passed")
    if test.status != TestStatus.active:
        raise HTTPException(400, "Test is not currently active")

    # Check for duplicate submission
    existing = db.query(Submission).filter(
        Submission.test_id == test_id,
        Submission.student_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(400, "You have already submitted for this test")

    if not answer_sheet.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Answer sheet must be a PDF file")

    # Save file
    filename = f"test{test_id}_student{current_user.id}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(SUBMISSIONS_DIR, filename)
    content = await answer_sheet.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Create submission record
    submission = Submission(
        test_id=test_id,
        student_id=current_user.id,
        answer_pdf_path=filepath,
        grading_status=GradingStatus.pending,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "message": "Answer sheet submitted successfully",
        "submission_id": submission.id,
        "submitted_at": submission.submitted_at.isoformat(),
    }


# ── Results ──

@router.get("/results")
async def list_my_results(
    current_user: User = Depends(student_dep),
    db: Session = Depends(get_db),
):
    """List all graded results for the student."""
    submissions = db.query(Submission).filter(
        Submission.student_id == current_user.id,
    ).order_by(Submission.submitted_at.desc()).all()

    results = []
    for s in submissions:
        pct = None
        if s.marks_obtained is not None and s.total_marks and s.total_marks > 0:
            pct = round((s.marks_obtained / s.total_marks) * 100, 1)

        results.append({
            "id": s.id,
            "test_id": s.test_id,
            "test_title": s.test.title if s.test else "",
            "subject_name": s.test.subject.name if s.test and s.test.subject else "",
            "submitted_at": s.submitted_at.isoformat(),
            "grading_status": s.grading_status.value,
            "marks_obtained": s.marks_obtained,
            "total_marks": s.total_marks,
            "percentage": pct,
            "has_report": s.report_pdf_path is not None,
            "graded_at": s.graded_at.isoformat() if s.graded_at else None,
            "grading_result": s.grading_result,
        })

    return results


@router.get("/results/{submission_id}/report")
async def download_report(
    submission_id: int,
    current_user: User = Depends(student_dep),
    db: Session = Depends(get_db),
):
    """Download the grading report PDF for a submission."""
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.student_id == current_user.id,
    ).first()

    if not submission:
        raise HTTPException(404, "Submission not found")
    if not submission.report_pdf_path or not os.path.exists(submission.report_pdf_path):
        raise HTTPException(404, "Report not available yet")

    return FileResponse(
        submission.report_pdf_path,
        media_type="application/pdf",
        filename="examai_grading_report.pdf",
    )


# ── Disputes ──

@router.get("/disputes", response_model=list[DisputeResponse])
async def list_my_disputes(
    current_user: User = Depends(student_dep),
    db: Session = Depends(get_db),
):
    """List all disputes raised by this student."""
    disputes = db.query(Dispute).filter(
        Dispute.student_id == current_user.id,
    ).order_by(Dispute.created_at.desc()).all()

    result = []
    for d in disputes:
        test_title = None
        if d.submission and d.submission.test:
            test_title = d.submission.test.title

        result.append(DisputeResponse(
            id=d.id,
            submission_id=d.submission_id,
            student_id=d.student_id,
            question_number=d.question_number,
            description=d.description,
            status=d.status.value,
            teacher_response=d.teacher_response,
            marks_before=d.marks_before,
            marks_after=d.marks_after,
            resolved_by=d.resolved_by,
            created_at=d.created_at,
            resolved_at=d.resolved_at,
            student_name=current_user.full_name,
            test_title=test_title,
        ))

    return result


@router.post("/disputes", response_model=DisputeResponse, status_code=201)
async def raise_dispute(
    data: DisputeCreate,
    current_user: User = Depends(student_dep),
    db: Session = Depends(get_db),
):
    """Raise a dispute on a specific question's marks."""
    submission = db.query(Submission).filter(
        Submission.id == data.submission_id,
        Submission.student_id == current_user.id,
    ).first()

    if not submission:
        raise HTTPException(404, "Submission not found")

    if submission.grading_status != GradingStatus.graded:
        raise HTTPException(400, "Can only dispute graded submissions")

    # Get original marks for the disputed question
    marks_before = None
    if submission.grading_result and "results" in submission.grading_result:
        for r in submission.grading_result["results"]:
            if str(r.get("question_number")) == str(data.question_number):
                marks_before = r.get("marks_obtained")
                break

    # Check for existing open dispute on same question
    existing = db.query(Dispute).filter(
        Dispute.submission_id == data.submission_id,
        Dispute.question_number == data.question_number,
        Dispute.status.in_([DisputeStatus.open, DisputeStatus.under_review]),
    ).first()
    if existing:
        raise HTTPException(400, "An open dispute already exists for this question")

    dispute = Dispute(
        submission_id=data.submission_id,
        student_id=current_user.id,
        question_number=data.question_number,
        description=data.description,
        marks_before=marks_before,
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)

    test_title = None
    if submission.test:
        test_title = submission.test.title

    return DisputeResponse(
        id=dispute.id,
        submission_id=dispute.submission_id,
        student_id=dispute.student_id,
        question_number=dispute.question_number,
        description=dispute.description,
        status=dispute.status.value,
        teacher_response=None,
        marks_before=marks_before,
        marks_after=None,
        resolved_by=None,
        created_at=dispute.created_at,
        resolved_at=None,
        student_name=current_user.full_name,
        test_title=test_title,
    )
