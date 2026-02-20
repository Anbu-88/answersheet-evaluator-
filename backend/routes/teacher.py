"""
ExamAI - Teacher Routes
Test management, answer key upload, grading trigger, and dispute resolution.
"""

import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.session import get_db
from db.models import (
    User, UserRole, Test, TestStatus, Submission, GradingStatus,
    Dispute, DisputeStatus, ClassSubjectTeacher,
)
from auth.dependencies import require_role
from schemas.schemas import (
    TestCreate, TestUpdate, TestResponse, SubmissionResponse,
    DisputeResponse, DisputeResolve, TeacherStats,
)
from services.grading_pipeline import process_answer_key, grade_all_submissions
from config import ANSWER_KEYS_DIR

router = APIRouter(prefix="/api/teacher", tags=["teacher"])
teacher_dep = require_role(UserRole.teacher)


# ── Dashboard ──

@router.get("/stats", response_model=TeacherStats)
async def get_teacher_stats(
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Get teacher dashboard statistics."""
    tests = db.query(Test).filter(Test.teacher_id == current_user.id).all()
    test_ids = [t.id for t in tests]

    active = sum(1 for t in tests if t.status == TestStatus.active)
    total_subs = db.query(Submission).filter(Submission.test_id.in_(test_ids)).count() if test_ids else 0
    pending_disputes = db.query(Dispute).join(Submission).filter(
        Submission.test_id.in_(test_ids),
        Dispute.status == DisputeStatus.open,
    ).count() if test_ids else 0
    assigned = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == current_user.id
    ).count()

    return TeacherStats(
        total_tests=len(tests),
        active_tests=active,
        pending_disputes=pending_disputes,
        total_submissions=total_subs,
        assigned_classes=assigned,
    )


# ── My Assignments ──

@router.get("/assignments")
async def get_my_assignments(
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Get all class-subject assignments for this teacher."""
    assignments = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == current_user.id
    ).all()

    return [
        {
            "id": a.id,
            "class_id": a.class_id,
            "class_name": a.class_.name if a.class_ else "",
            "class_section": a.class_.section if a.class_ else "",
            "subject_id": a.subject_id,
            "subject_name": a.subject.name if a.subject else "",
            "subject_code": a.subject.code if a.subject else "",
        }
        for a in assignments
    ]


# ── Test Management ──

@router.get("/tests", response_model=list[TestResponse])
async def list_my_tests(
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """List all tests created by this teacher."""
    tests = db.query(Test).filter(Test.teacher_id == current_user.id).order_by(Test.created_at.desc()).all()
    return [_test_to_response(t, db) for t in tests]


@router.post("/tests", response_model=TestResponse, status_code=201)
async def create_test(
    data: TestCreate,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Create a new test."""
    # Verify teacher is assigned to this class-subject
    assignment = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == current_user.id,
        ClassSubjectTeacher.class_id == data.class_id,
        ClassSubjectTeacher.subject_id == data.subject_id,
    ).first()

    if not assignment:
        raise HTTPException(403, "You are not assigned to teach this subject in this class")

    if data.end_time <= data.start_time:
        raise HTTPException(400, "End time must be after start time")

    test = Test(
        title=data.title,
        description=data.description,
        subject_id=data.subject_id,
        class_id=data.class_id,
        teacher_id=current_user.id,
        start_time=data.start_time,
        end_time=data.end_time,
        total_marks=data.total_marks,
        test_type=data.test_type,
        status=TestStatus.active,
    )
    db.commit()
    db.refresh(test)

    return _test_to_response(test, db)


@router.put("/tests/{test_id}", response_model=TestResponse)
async def update_test(
    test_id: int,
    data: TestUpdate,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Update a test."""
    test = db.query(Test).filter(Test.id == test_id, Test.teacher_id == current_user.id).first()
    if not test:
        raise HTTPException(404, "Test not found")

    if data.title is not None:
        test.title = data.title
    if data.description is not None:
        test.description = data.description
    if data.start_time is not None:
        test.start_time = data.start_time
    if data.end_time is not None:
        test.end_time = data.end_time
    if data.total_marks is not None:
        test.total_marks = data.total_marks
    if data.status is not None:
        test.status = TestStatus(data.status)

    db.commit()
    db.refresh(test)
    return _test_to_response(test, db)


@router.get("/tests/{test_id}", response_model=TestResponse)
async def get_test(
    test_id: int,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Get a specific test."""
    test = db.query(Test).filter(Test.id == test_id, Test.teacher_id == current_user.id).first()
    if not test:
        raise HTTPException(404, "Test not found")
    return _test_to_response(test, db)


# ── Answer Key Upload ──

@router.post("/tests/{test_id}/answer-key")
async def upload_answer_key(
    test_id: int,
    background_tasks: BackgroundTasks,
    answer_key: UploadFile = File(..., description="Answer key PDF"),
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Upload an answer key PDF for a test. Triggers AI analysis."""
    test = db.query(Test).filter(Test.id == test_id, Test.teacher_id == current_user.id).first()
    if not test:
        raise HTTPException(404, "Test not found")

    if not answer_key.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Answer key must be a PDF file")

    # Save file
    filename = f"test_{test_id}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(ANSWER_KEYS_DIR, filename)
    content = await answer_key.read()
    with open(filepath, "wb") as f:
        f.write(content)

    test.answer_key_path = filepath

    # Process answer key with Gemini in background
    background_tasks.add_task(process_answer_key, test_id, filepath)

    db.commit()
    return {"message": "Answer key uploaded. AI analysis started in background.", "path": filepath}


# ── Grading ──

@router.post("/tests/{test_id}/grade")
async def trigger_grading(
    test_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Trigger grading for all submissions of a test."""
    test = db.query(Test).filter(Test.id == test_id, Test.teacher_id == current_user.id).first()
    if not test:
        raise HTTPException(404, "Test not found")

    if not test.answer_key_data:
        raise HTTPException(400, "Answer key has not been analyzed yet. Upload the answer key first.")

    # Update test status
    test.status = TestStatus.grading
    db.commit()

    # Grade all pending submissions in background
    background_tasks.add_task(grade_all_submissions, test_id)

    pending = db.query(Submission).filter(
        Submission.test_id == test_id,
        Submission.grading_status == GradingStatus.pending,
    ).count()

    return {"message": f"Grading started for {pending} submissions", "pending_count": pending}


# ── Submissions ──

@router.get("/tests/{test_id}/submissions", response_model=list[SubmissionResponse])
async def list_test_submissions(
    test_id: int,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """List all submissions for a test."""
    test = db.query(Test).filter(Test.id == test_id, Test.teacher_id == current_user.id).first()
    if not test:
        raise HTTPException(404, "Test not found")

    submissions = db.query(Submission).filter(Submission.test_id == test_id).all()
    return [_submission_to_response(s) for s in submissions]


# ── Disputes ──

@router.get("/disputes", response_model=list[DisputeResponse])
async def list_my_disputes(
    status: str = None,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """List all disputes for tests owned by this teacher."""
    test_ids = [t.id for t in db.query(Test).filter(Test.teacher_id == current_user.id).all()]
    if not test_ids:
        return []

    query = db.query(Dispute).join(Submission).filter(Submission.test_id.in_(test_ids))
    if status:
        query = query.filter(Dispute.status == DisputeStatus(status))

    disputes = query.order_by(Dispute.created_at.desc()).all()
    return [_dispute_to_response(d) for d in disputes]


@router.get("/disputes/{dispute_id}/report")
async def download_student_report(
    dispute_id: int,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Download the grading report PDF for a student from a dispute."""
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(404, "Dispute not found")

    # Verify this dispute belongs to one of the teacher's tests
    submission = db.query(Submission).filter(Submission.id == dispute.submission_id).first()
    test = db.query(Test).filter(Test.id == submission.test_id, Test.teacher_id == current_user.id).first()
    if not test:
        raise HTTPException(403, "Access denied")

    if not submission.report_pdf_path or not os.path.exists(submission.report_pdf_path):
        raise HTTPException(404, "Report not available")

    return FileResponse(
        submission.report_pdf_path,
        media_type="application/pdf",
        filename=f"student_report_{submission.student_id}.pdf"
    )


@router.get("/disputes/{dispute_id}/answer")
async def download_student_answer(
    dispute_id: int,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Download the original handwritten answer PDF for a student from a dispute."""
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(404, "Dispute not found")

    submission = db.query(Submission).filter(Submission.id == dispute.submission_id).first()
    test = db.query(Test).filter(Test.id == submission.test_id, Test.teacher_id == current_user.id).first()
    if not test:
        raise HTTPException(403, "Access denied")

    if not submission.answer_pdf_path or not os.path.exists(submission.answer_pdf_path):
        raise HTTPException(404, "Original answer PDF not found")

    return FileResponse(
        submission.answer_pdf_path,
        media_type="application/pdf",
        filename=f"student_answer_{submission.student_id}.pdf"
    )


@router.put("/disputes/{dispute_id}/resolve", response_model=DisputeResponse)
async def resolve_dispute(
    dispute_id: int,
    data: DisputeResolve,
    current_user: User = Depends(teacher_dep),
    db: Session = Depends(get_db),
):
    """Resolve a dispute — accept (update marks) or reject."""
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(404, "Dispute not found")

    # Verify this dispute belongs to one of the teacher's tests
    submission = db.query(Submission).filter(Submission.id == dispute.submission_id).first()
    test = db.query(Test).filter(Test.id == submission.test_id, Test.teacher_id == current_user.id).first()
    if not test:
        raise HTTPException(403, "This dispute is not for your test")

    dispute.teacher_response = data.teacher_response
    dispute.resolved_by = current_user.id
    dispute.resolved_at = datetime.utcnow()

    if data.status == "resolved" and data.marks_after is not None:
        dispute.status = DisputeStatus.resolved
        dispute.marks_after = data.marks_after

        # Update the submission's total marks
        mark_diff = data.marks_after - (dispute.marks_before or 0)
        submission.marks_obtained = (submission.marks_obtained or 0) + mark_diff

        # Update the grading result JSON too
        if submission.grading_result and "results" in submission.grading_result:
            for r in submission.grading_result["results"]:
                if str(r.get("question_number")) == str(dispute.question_number):
                    r["marks_obtained"] = data.marks_after
                    r["manually_updated"] = True
                    r["teacher_note"] = data.teacher_response
                    break
            submission.grading_result["total_marks_obtained"] = submission.marks_obtained
    else:
        dispute.status = DisputeStatus.rejected

    db.commit()
    db.refresh(dispute)
    return _dispute_to_response(dispute)


# ── Helpers ──

def _test_to_response(test: Test, db: Session) -> TestResponse:
    sub_count = db.query(Submission).filter(Submission.test_id == test.id).count()
    graded_count = db.query(Submission).filter(
        Submission.test_id == test.id,
        Submission.grading_status == GradingStatus.graded,
    ).count()

    return TestResponse(
        id=test.id,
        title=test.title,
        description=test.description,
        subject_id=test.subject_id,
        class_id=test.class_id,
        teacher_id=test.teacher_id,
        start_time=test.start_time,
        end_time=test.end_time,
        total_marks=test.total_marks,
        status=test.status.value,
        test_type=test.test_type.value,
        answer_key_path=test.answer_key_path,
        answer_key_uploaded=test.answer_key_path is not None,
        created_at=test.created_at,
        subject_name=test.subject.name if test.subject else None,
        class_name=test.class_.name if test.class_ else None,
        teacher_name=test.teacher.full_name if test.teacher else None,
        submission_count=sub_count,
        graded_count=graded_count,
    )


def _submission_to_response(s: Submission) -> SubmissionResponse:
    pct = None
    if s.marks_obtained is not None and s.total_marks:
        pct = round((s.marks_obtained / s.total_marks) * 100, 1)

    return SubmissionResponse(
        id=s.id,
        test_id=s.test_id,
        student_id=s.student_id,
        submitted_at=s.submitted_at,
        grading_status=s.grading_status.value,
        marks_obtained=s.marks_obtained,
        total_marks=s.total_marks,
        graded_at=s.graded_at,
        student_name=s.student.full_name if s.student else None,
        test_title=s.test.title if s.test else None,
        percentage=pct,
        has_report=s.report_pdf_path is not None,
    )


def _dispute_to_response(d: Dispute) -> DisputeResponse:
    test_title = None
    q_total = None
    if d.submission:
        if d.submission.test:
            test_title = d.submission.test.title
        
        # Extract total marks for this specific question
        if d.submission.grading_result and "results" in d.submission.grading_result:
            for r in d.submission.grading_result["results"]:
                if str(r.get("question_number")) == str(d.question_number):
                    q_total = r.get("max_marks")
                    break

    return DisputeResponse(
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
        student_name=d.student.full_name if d.student else None,
        test_title=test_title,
        report_pdf_path=d.submission.report_pdf_path if d.submission else None,
        question_total_marks=q_total,
    )
