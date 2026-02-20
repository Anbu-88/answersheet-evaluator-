from db.session import SessionLocal
from db.models import User, Test, Submission, Dispute, ClassSubjectTeacher, TestStatus, GradingStatus, DisputeStatus
from schemas.schemas import TeacherStats

db = SessionLocal()
try:
    current_user = db.query(User).filter(User.id == 2).first()
    print(f"Teacher: {current_user.full_name}")

    tests = db.query(Test).filter(Test.teacher_id == current_user.id).all()
    test_ids = [t.id for t in tests]
    print(f"Tests: {len(tests)}")

    active = sum(1 for t in tests if t.status == TestStatus.active)
    
    total_subs = 0
    if test_ids:
        total_subs = db.query(Submission).filter(Submission.test_id.in_(test_ids)).count()
    print(f"Submissions: {total_subs}")

    pending_disputes = 0
    if test_ids:
        pending_disputes = db.query(Dispute).join(Submission).filter(
            Submission.test_id.in_(test_ids),
            Dispute.status == DisputeStatus.open,
        ).count()
    print(f"Pending Disputes: {pending_disputes}")

    assigned = db.query(ClassSubjectTeacher).filter(
        ClassSubjectTeacher.teacher_id == current_user.id
    ).count()
    print(f"Assigned Classes: {assigned}")

    stats = TeacherStats(
        total_tests=len(tests),
        active_tests=active,
        pending_disputes=pending_disputes,
        total_submissions=total_subs,
        assigned_classes=assigned,
    )
    print("Stats created successfully")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
