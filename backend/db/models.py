"""
ExamAI - Database Models
All SQLAlchemy ORM models for the exam grading platform.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, Enum, JSON, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ── Enums ──

class UserRole(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"


class TestStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"
    grading = "grading"
    graded = "graded"


class GradingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    graded = "graded"
    error = "error"


class DisputeStatus(str, enum.Enum):
    open = "open"
    under_review = "under_review"
    resolved = "resolved"
    rejected = "rejected"


def utcnow():
    return datetime.now(timezone.utc)


# ── Models ──

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    teaching_assignments = relationship("ClassSubjectTeacher", back_populates="teacher")
    student_classes = relationship("StudentClass", back_populates="student")
    created_tests = relationship("Test", back_populates="teacher")
    submissions = relationship("Submission", back_populates="student")
    disputes_raised = relationship("Dispute", foreign_keys="Dispute.student_id", back_populates="student")
    disputes_resolved = relationship("Dispute", foreign_keys="Dispute.resolved_by", back_populates="resolver")


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    section = Column(String(20), default="")
    academic_year = Column(String(20), default="2025-26")
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    subject_teachers = relationship("ClassSubjectTeacher", back_populates="class_")
    students = relationship("StudentClass", back_populates="class_")
    tests = relationship("Test", back_populates="class_")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    class_teachers = relationship("ClassSubjectTeacher", back_populates="subject")
    tests = relationship("Test", back_populates="subject")


class ClassSubjectTeacher(Base):
    """Maps which teacher teaches which subject in which class."""
    __tablename__ = "class_subject_teacher"
    __table_args__ = (
        UniqueConstraint("class_id", "subject_id", name="uq_class_subject"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    class_ = relationship("Class", back_populates="subject_teachers")
    subject = relationship("Subject", back_populates="class_teachers")
    teacher = relationship("User", back_populates="teaching_assignments")


class StudentClass(Base):
    """Maps students to their classes."""
    __tablename__ = "student_class"
    __table_args__ = (
        UniqueConstraint("student_id", "class_id", name="uq_student_class"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)

    # Relationships
    student = relationship("User", back_populates="student_classes")
    class_ = relationship("Class", back_populates="students")


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    answer_key_path = Column(String(500), nullable=True)
    answer_key_data = Column(JSON, nullable=True)
    total_marks = Column(Integer, default=0)
    status = Column(Enum(TestStatus), default=TestStatus.draft)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    subject = relationship("Subject", back_populates="tests")
    class_ = relationship("Class", back_populates="tests")
    teacher = relationship("User", back_populates="created_tests")
    submissions = relationship("Submission", back_populates="test")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("test_id", "student_id", name="uq_test_student"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime, default=utcnow)
    answer_pdf_path = Column(String(500), nullable=False)
    grading_status = Column(Enum(GradingStatus), default=GradingStatus.pending)
    grading_result = Column(JSON, nullable=True)
    marks_obtained = Column(Float, nullable=True)
    total_marks = Column(Float, nullable=True)
    report_pdf_path = Column(String(500), nullable=True)
    graded_at = Column(DateTime, nullable=True)

    # Relationships
    test = relationship("Test", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
    disputes = relationship("Dispute", back_populates="submission")


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_number = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(DisputeStatus), default=DisputeStatus.open)
    teacher_response = Column(Text, nullable=True)
    marks_before = Column(Float, nullable=True)
    marks_after = Column(Float, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    submission = relationship("Submission", back_populates="disputes")
    student = relationship("User", foreign_keys=[student_id], back_populates="disputes_raised")
    resolver = relationship("User", foreign_keys=[resolved_by], back_populates="disputes_resolved")
