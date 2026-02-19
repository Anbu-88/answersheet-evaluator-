"""
ExamAI - Grading Pipeline
Orchestrates the full grading workflow:
  1. Process answer key PDF → Gemini analysis
  2. Grade each student submission against the answer key
  3. Generate individual report PDFs
"""

import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import Test, TestStatus, Submission, GradingStatus
from services.gemini_service import analyze_answer_key, grade_exam_sheet
from services.pdf_service import pdf_to_images, generate_report_pdf
from config import REPORTS_DIR

logger = logging.getLogger(__name__)


def process_answer_key(test_id: int, pdf_path: str):
    """
    Background task: Analyze the answer key with Gemini.
    Runs in a background thread, needs its own DB session.
    """
    db = SessionLocal()
    try:
        logger.info(f"Processing answer key for test {test_id}")

        test = db.query(Test).filter(Test.id == test_id).first()
        if not test:
            logger.error(f"Test {test_id} not found")
            return

        # Read PDF and convert to images
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        page_images = pdf_to_images(pdf_bytes)
        logger.info(f"Answer key: {len(page_images)} pages extracted")

        # Analyze with Gemini
        answer_key_data = analyze_answer_key(page_images)
        logger.info(f"Answer key analyzed: {answer_key_data.get('total_questions', 0)} questions found")

        # Update the test record
        test.answer_key_data = answer_key_data
        if answer_key_data.get("total_marks"):
            test.total_marks = answer_key_data["total_marks"]

        db.commit()
        logger.info(f"Answer key for test {test_id} processed successfully")

    except Exception as e:
        logger.error(f"Failed to process answer key for test {test_id}: {e}", exc_info=True)
    finally:
        db.close()


def grade_all_submissions(test_id: int):
    """
    Background task: Grade all pending submissions for a test.
    Each submission is graded individually and a report PDF is generated.
    """
    db = SessionLocal()
    try:
        test = db.query(Test).filter(Test.id == test_id).first()
        if not test:
            logger.error(f"Test {test_id} not found")
            return

        if not test.answer_key_data:
            logger.error(f"Test {test_id} has no answer key data")
            return

        # Get all pending submissions
        submissions = db.query(Submission).filter(
            Submission.test_id == test_id,
            Submission.grading_status == GradingStatus.pending,
        ).all()

        logger.info(f"Grading {len(submissions)} submissions for test '{test.title}'")

        graded_count = 0
        error_count = 0

        for submission in submissions:
            try:
                _grade_single_submission(db, test, submission)
                graded_count += 1
                logger.info(
                    f"Graded submission {submission.id} "
                    f"({submission.student.full_name}): "
                    f"{submission.marks_obtained}/{submission.total_marks}"
                )
            except Exception as e:
                error_count += 1
                submission.grading_status = GradingStatus.error
                db.commit()
                logger.error(
                    f"Failed to grade submission {submission.id}: {e}",
                    exc_info=True,
                )

        # Update test status
        test.status = TestStatus.graded
        db.commit()

        logger.info(
            f"Test '{test.title}' grading complete: "
            f"{graded_count} graded, {error_count} errors"
        )

    except Exception as e:
        logger.error(f"Grading pipeline failed for test {test_id}: {e}", exc_info=True)
    finally:
        db.close()


def _grade_single_submission(db: Session, test: Test, submission: Submission):
    """Grade a single student submission."""
    # Mark as processing
    submission.grading_status = GradingStatus.processing
    db.commit()

    # Read the student's answer sheet PDF
    with open(submission.answer_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Convert to images
    page_images = pdf_to_images(pdf_bytes)

    # Grade with Gemini
    grading_result = grade_exam_sheet(page_images, test.answer_key_data)

    # Generate report PDF
    report_pdf = generate_report_pdf(grading_result)
    report_filename = f"report_test{test.id}_student{submission.student_id}.pdf"
    report_path = os.path.join(REPORTS_DIR, report_filename)
    with open(report_path, "wb") as f:
        f.write(report_pdf)

    # Update submission record
    submission.grading_result = grading_result
    submission.marks_obtained = grading_result.get("total_marks_obtained", 0)
    submission.total_marks = grading_result.get("total_marks_possible", test.total_marks)
    submission.report_pdf_path = report_path
    submission.grading_status = GradingStatus.graded
    submission.graded_at = datetime.utcnow()

    db.commit()
