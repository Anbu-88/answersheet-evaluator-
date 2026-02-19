"""
ExamAI - Admin Routes
User management, class/subject CRUD, and mapping operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.session import get_db
from db.models import (
    User, UserRole, Class, Subject,
    ClassSubjectTeacher, StudentClass, Test, Submission,
)
from auth.dependencies import require_role
from auth.password import hash_password
from schemas.schemas import (
    UserCreate, UserUpdate, UserResponse,
    ClassCreate, ClassUpdate, ClassResponse,
    SubjectCreate, SubjectUpdate, SubjectResponse,
    ClassSubjectTeacherCreate, ClassSubjectTeacherResponse,
    StudentClassCreate, StudentClassResponse,
    AdminStats,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin_dep = require_role(UserRole.admin)


# ── Dashboard ──

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Get admin dashboard statistics."""
    return AdminStats(
        total_teachers=db.query(User).filter(User.role == UserRole.teacher, User.is_active == True).count(),
        total_students=db.query(User).filter(User.role == UserRole.student, User.is_active == True).count(),
        total_classes=db.query(Class).count(),
        total_subjects=db.query(Subject).count(),
        total_tests=db.query(Test).count(),
    )


# ── User Management ──

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    role: str = None,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """List all users, optionally filtered by role."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    users = query.order_by(User.created_at.desc()).all()
    return [
        UserResponse(
            id=u.id, email=u.email, full_name=u.full_name,
            role=u.role.value, is_active=u.is_active, created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Create a new user (teacher or student)."""
    if data.role not in ["teacher", "student", "admin"]:
        raise HTTPException(400, "Role must be 'teacher', 'student', or 'admin'")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(400, f"User with email {data.email} already exists")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole(data.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role.value, is_active=user.is_active, created_at=user.created_at,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Update a user's details."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = data.email
    if data.is_active is not None:
        user.is_active = data.is_active

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role.value, is_active=user.is_active, created_at=user.created_at,
    )


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Deactivate a user (soft delete)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot deactivate your own account")

    user.is_active = False
    db.commit()
    return {"message": f"User {user.full_name} deactivated"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Reset a user's password to a default temporary password."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    temp_password = "changeme123"
    user.password_hash = hash_password(temp_password)
    db.commit()
    return {"message": f"Password reset for {user.full_name}", "temporary_password": temp_password}


# ── Class Management ──

@router.get("/classes", response_model=list[ClassResponse])
async def list_classes(
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """List all classes."""
    return db.query(Class).order_by(Class.name).all()


@router.post("/classes", response_model=ClassResponse, status_code=201)
async def create_class(
    data: ClassCreate,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Create a new class."""
    cls = Class(name=data.name, section=data.section, academic_year=data.academic_year)
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls


@router.put("/classes/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: int,
    data: ClassUpdate,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Update a class."""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(404, "Class not found")

    if data.name is not None:
        cls.name = data.name
    if data.section is not None:
        cls.section = data.section
    if data.academic_year is not None:
        cls.academic_year = data.academic_year

    db.commit()
    db.refresh(cls)
    return cls


@router.delete("/classes/{class_id}")
async def delete_class(
    class_id: int,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Delete a class."""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(404, "Class not found")

    db.delete(cls)
    db.commit()
    return {"message": f"Class {cls.name} deleted"}


# ── Subject Management ──

@router.get("/subjects", response_model=list[SubjectResponse])
async def list_subjects(
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """List all subjects."""
    return db.query(Subject).order_by(Subject.name).all()


@router.post("/subjects", response_model=SubjectResponse, status_code=201)
async def create_subject(
    data: SubjectCreate,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Create a new subject."""
    existing = db.query(Subject).filter(Subject.code == data.code).first()
    if existing:
        raise HTTPException(400, f"Subject with code {data.code} already exists")

    sub = Subject(name=data.name, code=data.code)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: int,
    data: SubjectUpdate,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Update a subject."""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(404, "Subject not found")

    if data.name is not None:
        sub.name = data.name
    if data.code is not None:
        sub.code = data.code

    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: int,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Delete a subject."""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(404, "Subject not found")

    db.delete(sub)
    db.commit()
    return {"message": f"Subject {sub.name} deleted"}


# ── Class-Subject-Teacher Mapping ──

@router.get("/mappings/class-subject", response_model=list[ClassSubjectTeacherResponse])
async def list_class_subject_mappings(
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """List all class-subject-teacher mappings."""
    mappings = db.query(ClassSubjectTeacher).all()
    result = []
    for m in mappings:
        result.append(ClassSubjectTeacherResponse(
            id=m.id,
            class_id=m.class_id,
            subject_id=m.subject_id,
            teacher_id=m.teacher_id,
            class_name=m.class_.name if m.class_ else None,
            subject_name=m.subject.name if m.subject else None,
            teacher_name=m.teacher.full_name if m.teacher else None,
        ))
    return result


@router.post("/mappings/class-subject", response_model=ClassSubjectTeacherResponse, status_code=201)
async def create_class_subject_mapping(
    data: ClassSubjectTeacherCreate,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Assign a teacher to a subject in a class."""
    # Validate references
    teacher = db.query(User).filter(User.id == data.teacher_id, User.role == UserRole.teacher).first()
    if not teacher:
        raise HTTPException(404, "Teacher not found")

    cls = db.query(Class).filter(Class.id == data.class_id).first()
    if not cls:
        raise HTTPException(404, "Class not found")

    sub = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not sub:
        raise HTTPException(404, "Subject not found")

    # Check for duplicate
    existing = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.class_id == data.class_id,
        ClassSubjectTeacher.subject_id == data.subject_id,
    ).first()
    if existing:
        raise HTTPException(400, "This class-subject combination is already assigned to a teacher")

    mapping = ClassSubjectTeacher(
        class_id=data.class_id,
        subject_id=data.subject_id,
        teacher_id=data.teacher_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return ClassSubjectTeacherResponse(
        id=mapping.id,
        class_id=mapping.class_id,
        subject_id=mapping.subject_id,
        teacher_id=mapping.teacher_id,
        class_name=cls.name,
        subject_name=sub.name,
        teacher_name=teacher.full_name,
    )


@router.delete("/mappings/class-subject/{mapping_id}")
async def delete_class_subject_mapping(
    mapping_id: int,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Remove a class-subject-teacher mapping."""
    mapping = db.query(ClassSubjectTeacher).filter(ClassSubjectTeacher.id == mapping_id).first()
    if not mapping:
        raise HTTPException(404, "Mapping not found")

    db.delete(mapping)
    db.commit()
    return {"message": "Mapping removed"}


# ── Student-Class Mapping ──

@router.get("/mappings/student-class", response_model=list[StudentClassResponse])
async def list_student_class_mappings(
    class_id: int = None,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """List all student-class mappings."""
    query = db.query(StudentClass)
    if class_id:
        query = query.filter(StudentClass.class_id == class_id)

    mappings = query.all()
    result = []
    for m in mappings:
        result.append(StudentClassResponse(
            id=m.id,
            student_id=m.student_id,
            class_id=m.class_id,
            student_name=m.student.full_name if m.student else None,
            class_name=m.class_.name if m.class_ else None,
        ))
    return result


@router.post("/mappings/student-class", response_model=StudentClassResponse, status_code=201)
async def add_student_to_class(
    data: StudentClassCreate,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Add a student to a class."""
    student = db.query(User).filter(User.id == data.student_id, User.role == UserRole.student).first()
    if not student:
        raise HTTPException(404, "Student not found")

    cls = db.query(Class).filter(Class.id == data.class_id).first()
    if not cls:
        raise HTTPException(404, "Class not found")

    existing = db.query(StudentClass).filter(
        StudentClass.student_id == data.student_id,
        StudentClass.class_id == data.class_id,
    ).first()
    if existing:
        raise HTTPException(400, "Student is already in this class")

    mapping = StudentClass(student_id=data.student_id, class_id=data.class_id)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return StudentClassResponse(
        id=mapping.id,
        student_id=mapping.student_id,
        class_id=mapping.class_id,
        student_name=student.full_name,
        class_name=cls.name,
    )


@router.delete("/mappings/student-class/{mapping_id}")
async def remove_student_from_class(
    mapping_id: int,
    current_user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """Remove a student from a class."""
    mapping = db.query(StudentClass).filter(StudentClass.id == mapping_id).first()
    if not mapping:
        raise HTTPException(404, "Mapping not found")

    db.delete(mapping)
    db.commit()
    return {"message": "Student removed from class"}
