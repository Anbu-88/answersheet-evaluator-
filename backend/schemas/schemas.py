"""
ExamAI - Pydantic Schemas
Request/Response models for all API endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


# ── Auth ──

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ── Users ──

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str  # "admin", "teacher", "student"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Classes ──

class ClassCreate(BaseModel):
    name: str
    section: str = ""
    academic_year: str = "2025-26"

class ClassUpdate(BaseModel):
    name: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None

class ClassResponse(BaseModel):
    id: int
    name: str
    section: str
    academic_year: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Subjects ──

class SubjectCreate(BaseModel):
    name: str
    code: str

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class SubjectResponse(BaseModel):
    id: int
    name: str
    code: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Mappings ──

class ClassSubjectTeacherCreate(BaseModel):
    class_id: int
    subject_id: int
    teacher_id: int

class ClassSubjectTeacherResponse(BaseModel):
    id: int
    class_id: int
    subject_id: int
    teacher_id: int
    class_name: Optional[str] = None
    subject_name: Optional[str] = None
    teacher_name: Optional[str] = None

class StudentClassCreate(BaseModel):
    student_id: int
    class_id: int

class StudentClassResponse(BaseModel):
    id: int
    student_id: int
    class_id: int
    student_name: Optional[str] = None
    class_name: Optional[str] = None


# ── Tests ──

class TestCreate(BaseModel):
    title: str
    description: str = ""
    subject_id: int
    class_id: int
    start_time: datetime
    end_time: datetime
    total_marks: int = 0
    test_type: str = "subjective" # "subjective" or "mcq"

class TestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_marks: Optional[int] = None
    status: Optional[str] = None

class TestResponse(BaseModel):
    id: int
    title: str
    description: str
    subject_id: int
    class_id: int
    teacher_id: int
    start_time: datetime
    end_time: datetime
    total_marks: int
    status: str
    test_type: str
    answer_key_path: Optional[str] = None
    answer_key_uploaded: bool = False
    created_at: datetime
    subject_name: Optional[str] = None
    class_name: Optional[str] = None
    teacher_name: Optional[str] = None
    submission_count: Optional[int] = 0
    graded_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ── Submissions ──

class SubmissionResponse(BaseModel):
    id: int
    test_id: int
    student_id: int
    submitted_at: datetime
    grading_status: str
    marks_obtained: Optional[float] = None
    total_marks: Optional[float] = None
    graded_at: Optional[datetime] = None
    student_name: Optional[str] = None
    test_title: Optional[str] = None
    percentage: Optional[float] = None
    has_report: bool = False

    class Config:
        from_attributes = True


# ── Disputes ──

class DisputeCreate(BaseModel):
    submission_id: int
    question_number: str
    description: str

class DisputeResolve(BaseModel):
    teacher_response: str
    marks_after: Optional[float] = None  # None = reject (no change)
    status: str = "resolved"  # "resolved" or "rejected"

class DisputeResponse(BaseModel):
    id: int
    submission_id: int
    student_id: int
    question_number: str
    description: str
    status: str
    teacher_response: Optional[str] = None
    marks_before: Optional[float] = None
    marks_after: Optional[float] = None
    resolved_by: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    student_name: Optional[str] = None
    test_title: Optional[str] = None
    report_pdf_path: Optional[str] = None
    question_total_marks: Optional[float] = None

    class Config:
        from_attributes = True


# ── Dashboard Stats ──

class AdminStats(BaseModel):
    total_teachers: int
    total_students: int
    total_classes: int
    total_subjects: int
    total_tests: int

class TeacherStats(BaseModel):
    total_tests: int
    active_tests: int
    pending_disputes: int
    total_submissions: int
    assigned_classes: int

class StudentStats(BaseModel):
    total_tests: int
    pending_tests: int
    completed_tests: int
    average_score: Optional[float] = None
    open_disputes: int
