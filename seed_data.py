"""
seed_data.py — LBCA Monitoring System
======================================
Populates your Render PostgreSQL database with realistic sample data
so the Dashboard and Early Warning pages have something to display.

HOW TO RUN
----------
1. Copy this file into your backend project folder (same level as database.py).
2. Make sure your .env has DATABASE_URL set to your Render PostgreSQL URL.
3. Install deps (if not already):
       pip install psycopg2-binary python-dotenv bcrypt
4. Run:
       python seed_data.py

What it inserts
---------------
  • 1 school year  (2024-2025, current)
  • 4 grade levels (7, 8, 9, 10)
  • 8 sections     (2 per grade level)
  • 8 subjects     (core subjects for junior high)
  • 1 admin staff  (admin@lbca.edu / Admin@1234)
  • 2 teacher staff accounts
  • 30 students    spread across sections
  • 30 enrollments (one per student)
  • ~90 pace records (3 subjects per student)
  • 15 early warnings (mix of risk levels)
"""

import os
import sys
import uuid
import bcrypt
import psycopg2
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import random

load_dotenv()

# ── Database connection ──────────────────────────────────────────────────────

RAW_URL = os.getenv("DATABASE_URL", "")
if not RAW_URL:
    print("❌  DATABASE_URL not found in .env")
    sys.exit(1)

# psycopg2 needs postgresql:// not postgres://
CONN_STR = RAW_URL.replace("postgres://", "postgresql://")

try:
    conn = psycopg2.connect(CONN_STR)
    conn.autocommit = False
    cur = conn.cursor()
    print("✅  Connected to Render PostgreSQL")
except Exception as e:
    print(f"❌  Connection failed: {e}")
    sys.exit(1)


# ── Helpers ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def now():
    return datetime.utcnow()

def rand_date_of_birth() -> str:
    """Return a random birth date for a junior high student (age 12-16)."""
    start = date(2007, 1, 1)
    end   = date(2011, 12, 31)
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


# ── 1. School Years ──────────────────────────────────────────────────────────

print("\n📅  Inserting school year …")
cur.execute("""
    INSERT INTO school_years (year, is_current, start_date, end_date)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (year) DO NOTHING
    RETURNING school_year_id
""", ("2024-2025", True, date(2024, 6, 3), date(2025, 3, 28)))
row = cur.fetchone()
if row:
    school_year_id = row[0]
else:
    cur.execute("SELECT school_year_id FROM school_years WHERE year = '2024-2025'")
    school_year_id = cur.fetchone()[0]
print(f"   school_year_id = {school_year_id}")


# ── 2. Grade Levels ──────────────────────────────────────────────────────────

print("\n📚  Inserting grade levels …")
grade_map = {}  # level_str → grade_level_id
for level, name in [("7","Grade 7"), ("8","Grade 8"), ("9","Grade 9"), ("10","Grade 10")]:
    cur.execute("""
        INSERT INTO grade_levels (level, name)
        VALUES (%s, %s)
        ON CONFLICT (level) DO NOTHING
        RETURNING grade_level_id
    """, (level, name))
    row = cur.fetchone()
    if row:
        grade_map[level] = row[0]
    else:
        cur.execute("SELECT grade_level_id FROM grade_levels WHERE level = %s", (level,))
        grade_map[level] = cur.fetchone()[0]
print(f"   Grade map: {grade_map}")


# ── 3. Sections ──────────────────────────────────────────────────────────────

print("\n🏫  Inserting sections …")
section_defs = [
    ("7",  "G7-FAITH",    "Faith"),
    ("7",  "G7-HOPE",     "Hope"),
    ("8",  "G8-CHARITY",  "Charity"),
    ("8",  "G8-JOY",      "Joy"),
    ("9",  "G9-PEACE",    "Peace"),
    ("9",  "G9-GRACE",    "Grace"),
    ("10", "G10-WISDOM",  "Wisdom"),
    ("10", "G10-TRUTH",   "Truth"),
]
section_map = {}  # section_code → section_id
for grade_str, code, name in section_defs:
    gl_id = grade_map[grade_str]
    cur.execute("""
        INSERT INTO sections (grade_level_id, section_code, name)
        VALUES (%s, %s, %s)
        ON CONFLICT (section_code) DO NOTHING
        RETURNING section_id
    """, (gl_id, code, name))
    row = cur.fetchone()
    if row:
        section_map[code] = row[0]
    else:
        cur.execute("SELECT section_id FROM sections WHERE section_code = %s", (code,))
        section_map[code] = cur.fetchone()[0]
print(f"   Sections: {section_map}")


# ── 4. Subjects ──────────────────────────────────────────────────────────────

print("\n📖  Inserting subjects …")
# Core subjects — grade_level_id=None means shared; we'll attach to Grade 7 as default
subject_defs = [
    ("Mathematics",         "MATH",    "7"),
    ("English",             "ENG",     "7"),
    ("Science",             "SCI",     "7"),
    ("Filipino",            "FIL",     "7"),
    ("Araling Panlipunan",  "AP",      "8"),
    ("MAPEH",               "MAPEH",   "8"),
    ("TLE",                 "TLE",     "9"),
    ("Values Education",    "VALUES",  "9"),
]
subject_ids = []
subject_names = []
for s_name, s_code, grade_str in subject_defs:
    gl_id = grade_map[grade_str]
    cur.execute("""
        INSERT INTO subjects (grade_level_id, subject_name, subject_code, is_active)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (subject_code) DO NOTHING
        RETURNING subject_id
    """, (gl_id, s_name, s_code))
    row = cur.fetchone()
    if row:
        sid = row[0]
    else:
        cur.execute("SELECT subject_id FROM subjects WHERE subject_code = %s", (s_code,))
        sid = cur.fetchone()[0]
    subject_ids.append(sid)
    subject_names.append(s_name)
print(f"   {len(subject_ids)} subjects ready")


# ── 5. Staff (admin + 2 teachers) ────────────────────────────────────────────

print("\n👤  Inserting staff accounts …")

staff_records = [
    {
        "email":      "admin@lbca.edu",
        "password":   "Admin@1234",
        "first_name": "Maria",
        "last_name":  "Santos",
        "role":       "admin",
        "contact":    "09171234567",
        "approved":   True,
        "status":     "approved",
    },
    {
        "email":      "teacher1@lbca.edu",
        "password":   "Teacher@1234",
        "first_name": "Juan",
        "last_name":  "dela Cruz",
        "role":       "teacher",
        "contact":    "09181234567",
        "approved":   True,
        "status":     "approved",
    },
    {
        "email":      "teacher2@lbca.edu",
        "password":   "Teacher@1234",
        "first_name": "Ana",
        "last_name":  "Reyes",
        "role":       "teacher",
        "contact":    "09191234567",
        "approved":   True,
        "status":     "approved",
    },
]

staff_ids = {}
for s in staff_records:
    pw_hash = hash_password(s["password"])
    sid = uuid.uuid4()
    cur.execute("""
        INSERT INTO staff
          (id, email, password_hash, first_name, last_name, contact_number,
           role, account_status, is_active, is_approved, approved_at, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (email) DO NOTHING
        RETURNING id
    """, (
        str(sid), s["email"], pw_hash,
        s["first_name"], s["last_name"], s["contact"],
        s["role"], s["status"], True, s["approved"],
        now(), now()
    ))
    row = cur.fetchone()
    if row:
        staff_ids[s["email"]] = str(row[0])
    else:
        cur.execute("SELECT id FROM staff WHERE email = %s", (s["email"],))
        staff_ids[s["email"]] = str(cur.fetchone()[0])
    print(f"   {s['role']:7s}  {s['email']}")

admin_id    = staff_ids["admin@lbca.edu"]
teacher1_id = staff_ids["teacher1@lbca.edu"]
teacher2_id = staff_ids["teacher2@lbca.edu"]


# ── 6. Students ──────────────────────────────────────────────────────────────

print("\n🎓  Inserting students …")

FIRST_NAMES = [
    "Liam","Emma","Noah","Olivia","Aiden","Sophia","Lucas","Isabella",
    "Ethan","Mia","James","Charlotte","Oliver","Amelia","Elijah",
    "Harper","Benjamin","Evelyn","Mason","Abigail","Logan","Emily",
    "Alexander","Elizabeth","Michael","Mila","Daniel","Ella","Henry","Scarlett"
]
LAST_NAMES = [
    "Reyes","Santos","Dela Cruz","Garcia","Mendoza","Torres","Flores",
    "Bautista","Ramos","Aquino","Lopez","Fernandez","Ramirez","Villanueva",
    "Castro","Navarro","Morales","Rivera","Gonzales","Escobar","Lim",
    "Tan","Uy","Chua","Go","Sy","Lee","Chan","Yap","Ko"
]
ADDRESSES = [
    "Purok 1, Brgy. Poblacion, Manolo Fortich, Bukidnon",
    "Purok 2, Brgy. Dalirig, Manolo Fortich, Bukidnon",
    "Purok 3, Brgy. Lindaban, Manolo Fortich, Bukidnon",
    "Purok 4, Brgy. Manalog, Manolo Fortich, Bukidnon",
    "Purok 5, Brgy. Sankanan, Manolo Fortich, Bukidnon",
]

# Sections to distribute students across (10 sections × 3 students each = 30)
section_codes = list(section_map.keys())
student_ids = []

for i in range(30):
    fname  = FIRST_NAMES[i]
    lname  = LAST_NAMES[i]
    gender = "Male" if i % 2 == 0 else "Female"
    bdate  = rand_date_of_birth()
    addr   = ADDRESSES[i % len(ADDRESSES)]

    cur.execute("""
        INSERT INTO students
          (first_name, last_name, birth_date, gender, address,
           guardian_first_name, guardian_last_name, guardian_contact,
           guardian_relationship, created_at, updated_at, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING student_id
    """, (
        fname, lname, bdate, gender, addr,
        "Parent of " + fname, lname, f"091{random.randint(10000000,99999999)}",
        "Parent", now(), now(), admin_id
    ))
    row = cur.fetchone()
    student_id = row[0]

    # Assign login_id like S001, S002 …
    login_id = f"S{student_id:03d}"
    cur.execute("UPDATE students SET login_id = %s WHERE student_id = %s", (login_id, student_id))

    student_ids.append(student_id)

print(f"   {len(student_ids)} students inserted (IDs {student_ids[0]}–{student_ids[-1]})")


# ── 7. Enrollments ───────────────────────────────────────────────────────────

print("\n📋  Inserting enrollments …")

enrollment_ids = []
# Distribute 30 students evenly across 8 sections (≈4 per section)
for idx, student_id in enumerate(student_ids):
    sec_code   = section_codes[idx % len(section_codes)]
    sec_id     = section_map[sec_code]

    # Find the grade level for this section
    cur.execute("SELECT grade_level_id FROM sections WHERE section_id = %s", (sec_id,))
    gl_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO student_enrollments
          (student_id, grade_level_id, section_id, school_year_id,
           enrolled_by, enrollment_date, is_active)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING enrollment_id
    """, (
        student_id, gl_id, sec_id, school_year_id,
        admin_id, date(2024, 6, 3).isoformat(), True
    ))
    enrollment_ids.append(cur.fetchone()[0])

print(f"   {len(enrollment_ids)} enrollments inserted")


# ── 8. Student Pace Records ──────────────────────────────────────────────────

print("\n⏱️   Inserting pace records …")

CORE_SUBJECTS = ["Mathematics", "English", "Science"]

pace_count = 0
for student_id, enrollment_id in zip(student_ids, enrollment_ids):
    for subj in CORE_SUBJECTS:
        # Create varied pace percentages: some on track, some behind
        pace_pct   = round(random.uniform(20.0, 100.0), 1)
        paces_beh  = max(0, int((80 - pace_pct) / 10))   # rough estimate

        cur.execute("""
            INSERT INTO student_paces
              (student_id, enrollment_id, subject, pace_percent, paces_behind,
               created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            student_id, enrollment_id, subj,
            pace_pct, paces_beh, now(), now()
        ))
        pace_count += 1

print(f"   {pace_count} pace records inserted")


# ── 9. Early Warnings ────────────────────────────────────────────────────────

print("\n⚠️   Inserting early warnings …")

RISK_MATRIX = [
    # (risk_level, status, trend, pace_min, pace_max, att_min, att_max)
    ("critical", "Critical",  "declining",  10, 30,  40, 60),
    ("high",     "At Risk",   "declining",  30, 50,  55, 75),
    ("moderate", "Warning",   "stable",     50, 70,  70, 85),
    ("low",      "On Track",  "improving",  70, 95,  85, 100),
]

TEACHERS = ["Juan dela Cruz", "Ana Reyes"]

warning_count = 0
# Pick 15 students to have warnings (every other student, first 15)
for i, (student_id, enrollment_id) in enumerate(zip(student_ids[:15], enrollment_ids[:15])):
    risk_row  = RISK_MATRIX[i % len(RISK_MATRIX)]
    r_level, status, trend, p_min, p_max, a_min, a_max = risk_row
    pace_pct  = round(random.uniform(p_min, p_max), 1)
    attend    = round(random.uniform(a_min, a_max), 1)
    paces_beh = max(0, int((80 - pace_pct) / 10))

    cur.execute("""
        INSERT INTO early_warnings
          (student_id, enrollment_id, subject, teacher, risk_level,
           paces_behind, pace_percent, attendance, status, trend,
           last_activity, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        student_id, enrollment_id,
        CORE_SUBJECTS[i % len(CORE_SUBJECTS)],
        TEACHERS[i % len(TEACHERS)],
        r_level, paces_beh, pace_pct, attend,
        status, trend, "Today", now(), now()
    ))
    warning_count += 1

print(f"   {warning_count} early warnings inserted")


# ── Commit & close ───────────────────────────────────────────────────────────

conn.commit()
cur.close()
conn.close()

print("""
╔══════════════════════════════════════════════════════════╗
║  ✅  Seed complete!  Your Render DB is now populated.    ║
╠══════════════════════════════════════════════════════════╣
║  School years :  1  (2024-2025, current)                ║
║  Grade levels :  4  (7, 8, 9, 10)                       ║
║  Sections     :  8                                       ║
║  Subjects     :  8                                       ║
║  Staff        :  3  (1 admin, 2 teachers)                ║
║  Students     :  30                                      ║
║  Enrollments  :  30                                      ║
║  Pace records :  90                                      ║
║  Early warns  :  15  (mix of risk levels)                ║
╠══════════════════════════════════════════════════════════╣
║  Login credentials                                       ║
║  admin@lbca.edu    / Admin@1234                          ║
║  teacher1@lbca.edu / Teacher@1234                        ║
║  teacher2@lbca.edu / Teacher@1234                        ║
╚══════════════════════════════════════════════════════════╝
""")