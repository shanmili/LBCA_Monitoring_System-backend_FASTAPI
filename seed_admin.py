from database import sync_engine
from sqlalchemy.orm import sessionmaker
from models import Staff
from auth import get_password_hash

SessionLocal = sessionmaker(bind=sync_engine)
db = SessionLocal()

try:
    existing = db.query(Staff).filter(Staff.email == "admin@lbca.edu.ph").first()

    if existing:
        # Force-update the hash instead of verifying the old one
        existing.password_hash = get_password_hash("Admin123!")
        db.commit()
        print("Admin already existed — password hash refreshed.")
    else:
        admin = Staff(
            email="admin@lbca.edu.ph",
            password_hash=get_password_hash("Admin123!"),
            first_name="System",
            last_name="Administrator",
            contact_number="+639123456789",
            role="admin",
            account_status="approved",
            is_approved=True,
            requires_password_change=False,
        )
        db.add(admin)
        db.commit()
        print("Admin created: admin@lbca.edu.ph / Admin123!")
finally:
    db.close()