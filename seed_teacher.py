from database import sync_engine
from sqlalchemy.orm import sessionmaker
from models import Staff
from auth import get_password_hash

SessionLocal = sessionmaker(bind=sync_engine)
db = SessionLocal()

try:
    existing = db.query(Staff).filter(Staff.email == "teacher@lbca.edu.ph").first()

    if existing:
        # Force-update the hash instead of verifying the old one
        existing.password_hash = get_password_hash("Teacher123!")
        db.commit()
        print("Teacher already existed — password hash refreshed.")
    else:
        teacher = Staff(
            email="teacher@lbca.edu.ph",
            password_hash=get_password_hash("Teacher123!"),
            first_name="Juan",
            last_name="Dela Cruz",
            contact_number="+639987654321",
            role="teacher",
            account_status="approved",
            is_approved=True,
            requires_password_change=False,
        )
        db.add(teacher)
        db.commit()
        print("Teacher created: teacher@lbca.edu.ph / Teacher123!")
finally:
    db.close()
