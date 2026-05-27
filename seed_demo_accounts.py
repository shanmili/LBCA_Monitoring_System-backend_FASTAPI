import hashlib
from datetime import datetime, timezone

from database import sync_engine
from sqlalchemy.orm import sessionmaker
from models import Staff, StaffDevice
from auth import get_password_hash

# ── fixed demo device ──────────────────────────────────────────────────────────
# The front-end must send this exact string as device_id when logging in with
# the demo accounts.  Because it is pre-registered as trusted AND last_2fa_verified
# is set to now, the 90-day re-verification window won't trigger either.
DEMO_DEVICE_ID   = "DEMO-DEVICE-NO-OTP-2024"
DEMO_DEVICE_NAME = "Demo Browser (OTP-exempt)"

DEMO_ACCOUNTS = [
    {
        "email":          "demo.admin@lbca.edu.ph",
        "password":       "DemoAdmin1!",
        "first_name":     "Demo",
        "last_name":      "Admin",
        "contact_number": "+639111111111",
        "role":           "admin",
    },
    {
        "email":          "demo.teacher@lbca.edu.ph",
        "password":       "DemoTeach1!",
        "first_name":     "Demo",
        "last_name":      "Teacher",
        "contact_number": "+639222222222",
        "role":           "teacher",
    },
]

SessionLocal = sessionmaker(bind=sync_engine)
db = SessionLocal()

try:
    for acc in DEMO_ACCOUNTS:
        staff = db.query(Staff).filter(Staff.email == acc["email"]).first()

        if staff:
            # Refresh password in case it was changed
            staff.password_hash = get_password_hash(acc["password"])
            print(f"[UPDATE] {acc['email']} — password refreshed.")
        else:
            staff = Staff(
                email=acc["email"],
                password_hash=get_password_hash(acc["password"]),
                first_name=acc["first_name"],
                last_name=acc["last_name"],
                contact_number=acc["contact_number"],
                role=acc["role"],
                account_status="approved",
                is_approved=True,
                requires_password_change=False,
            )
            db.add(staff)
            db.flush()  # get staff.id before adding the device
            print(f"[CREATE] {acc['email']} ({acc['role']}) created.")

        # ── ensure the trusted device exists ──────────────────────────────────
        existing_device = (
            db.query(StaffDevice)
            .filter(
                StaffDevice.staff_id == staff.id,
                StaffDevice.device_id == DEMO_DEVICE_ID,
            )
            .first()
        )

        if existing_device:
            # Keep last_2fa_verified fresh so the 90-day re-check never fires
            existing_device.last_2fa_verified = datetime.now(timezone.utc)
            existing_device.is_trusted = True
            print(f"         └─ trusted device refreshed.")
        else:
            device = StaffDevice(
                staff_id=staff.id,
                device_id=DEMO_DEVICE_ID,
                device_name=DEMO_DEVICE_NAME,
                ip_address="127.0.0.1",
                is_trusted=True,
                last_2fa_verified=datetime.now(timezone.utc),
            )
            db.add(device)
            print(f"         └─ trusted device registered (no OTP will be asked).")

    db.commit()

    print("\n✅  Done!  Credentials for your instructor:")
    print("─" * 50)
    for acc in DEMO_ACCOUNTS:
        print(f"  Role    : {acc['role'].upper()}")
        print(f"  Email   : {acc['email']}")
        print(f"  Password: {acc['password']}")
        print(f"  Device  : {DEMO_DEVICE_ID}  ← front-end must send this")
        print()

    print("⚠️  IMPORTANT — tell your front-end:")
    print(f'   When logging in with demo accounts, send device_id = "{DEMO_DEVICE_ID}"')
    print("   That device is already trusted, so the OTP screen will be skipped.")

finally:
    db.close()