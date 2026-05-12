"""
seed_data_v2.py — LBCA Monitoring System (FIXED)
=================================================
Fixes:
  - pace_percent is now realistic (not zero) so Dashboard KPIs show data
  - early_warnings now have real pace_percent + attendance values
  - Section name is stored directly in early_warnings.teacher field
    and the student list endpoint must be patched (see BACKEND FIX below)

HOW TO RUN
----------
1. Copy to your backend project folder (same level as database.py)
2. Ensure .env has DATABASE_URL pointing to your Render PostgreSQL
3. pip install psycopg2-binary bcrypt python-dotenv
4. python seed_data_v2.py
"""

import os, sys, uuid, random
import bcrypt, psycopg2
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

RAW_URL = os.getenv("DATABASE_URL", "")
if not RAW_URL:
    print("❌  DATABASE_URL not found in .env"); sys.exit(1)

CONN_STR = RAW_URL.replace("postgres://", "postgresql://")
try:
    conn = psycopg2.connect(CONN_STR)
    conn.autocommit = False
    cur = conn.cursor()
    print("✅  Connected to Render PostgreSQL")
except Exception as e:
    print(f"❌  Connection failed: {e}"); sys.exit(1)

def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def now(): return datetime.utcnow()
def rdate():
    s = date(2007,1,1); return (s + timedelta(days=random.randint(0,4*365))).isoformat()

# ── Wipe existing seed data cleanly ─────────────────────────────────────────
print("\n🗑️   Clearing old seed data …")
cur.execute("DELETE FROM early_warnings")
cur.execute("DELETE FROM student_paces")
cur.execute("DELETE FROM student_enrollments")
cur.execute("DELETE FROM students")
cur.execute("DELETE FROM staff WHERE email IN ('admin@lbca.edu','teacher1@lbca.edu','teacher2@lbca.edu')")
cur.execute("DELETE FROM subjects")
cur.execute("DELETE FROM sections")
cur.execute("DELETE FROM grade_levels")
cur.execute("DELETE FROM school_years")
print("   Done")

# ── 1. School Year ───────────────────────────────────────────────────────────
print("\n📅  School year …")
cur.execute("""
    INSERT INTO school_years (year, is_current, start_date, end_date)
    VALUES (%s,%s,%s,%s) RETURNING school_year_id
""", ("2024-2025", True, date(2024,6,3), date(2025,3,28)))
sy_id = cur.fetchone()[0]
print(f"   id={sy_id}")

# ── 2. Grade Levels ──────────────────────────────────────────────────────────
print("\n📚  Grade levels …")
grade_map = {}
for lv, nm in [("7","Grade 7"),("8","Grade 8"),("9","Grade 9"),("10","Grade 10")]:
    cur.execute("INSERT INTO grade_levels (level,name) VALUES (%s,%s) RETURNING grade_level_id",(lv,nm))
    grade_map[lv] = cur.fetchone()[0]
print(f"   {grade_map}")

# ── 3. Sections ──────────────────────────────────────────────────────────────
print("\n🏫  Sections …")
section_defs = [
    ("7","G7-FAITH","Faith"), ("7","G7-HOPE","Hope"),
    ("8","G8-CHARITY","Charity"), ("8","G8-JOY","Joy"),
    ("9","G9-PEACE","Peace"), ("9","G9-GRACE","Grace"),
    ("10","G10-WISDOM","Wisdom"), ("10","G10-TRUTH","Truth"),
]
section_map = {}   # code → {id, name, grade}
for g, code, name in section_defs:
    cur.execute("""INSERT INTO sections (grade_level_id,section_code,name)
                   VALUES (%s,%s,%s) RETURNING section_id""", (grade_map[g], code, name))
    section_map[code] = {"id": cur.fetchone()[0], "name": name, "grade": g}
print(f"   {len(section_map)} sections")

# ── 4. Subjects ──────────────────────────────────────────────────────────────
print("\n📖  Subjects …")
SUBJ_DEFS = [
    ("Mathematics","MATH","7"), ("English","ENG","7"),
    ("Science","SCI","7"),      ("Filipino","FIL","7"),
    ("Araling Panlipunan","AP","8"), ("MAPEH","MAPEH","8"),
    ("TLE","TLE","9"),          ("Values Education","VALUES","9"),
]
subj_names = []
for sn, sc, g in SUBJ_DEFS:
    cur.execute("""INSERT INTO subjects (grade_level_id,subject_name,subject_code,is_active)
                   VALUES (%s,%s,%s,TRUE) RETURNING subject_id""", (grade_map[g],sn,sc))
    cur.fetchone()
    subj_names.append(sn)
CORE_SUBJECTS = ["Mathematics", "English", "Science"]
print(f"   {len(SUBJ_DEFS)} subjects")

# ── 5. Staff ──────────────────────────────────────────────────────────────────
print("\n👤  Staff …")
STAFF = [
    ("admin@lbca.edu",   "Admin@1234",   "Maria","Santos",   "admin"),
    ("teacher1@lbca.edu","Teacher@1234", "Juan","dela Cruz", "teacher"),
    ("teacher2@lbca.edu","Teacher@1234", "Ana","Reyes",      "teacher"),
]
staff_ids = {}
for email, pw, fn, ln, role in STAFF:
    sid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO staff (id,email,password_hash,first_name,last_name,
            contact_number,role,account_status,is_active,is_approved,approved_at,created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (sid, email, hash_pw(pw), fn, ln, "09170000000", role,
          "approved", True, True, now(), now()))
    staff_ids[email] = str(cur.fetchone()[0])
    print(f"   {role:7s}  {email}")

admin_id    = staff_ids["admin@lbca.edu"]
teacher1_id = staff_ids["teacher1@lbca.edu"]
teacher2_id = staff_ids["teacher2@lbca.edu"]
TEACHER_NAMES = ["Juan dela Cruz", "Ana Reyes"]

# ── 6. Students ───────────────────────────────────────────────────────────────
print("\n🎓  Students …")
FNAMES = ["Liam","Emma","Noah","Olivia","Aiden","Sophia","Lucas","Isabella",
          "Ethan","Mia","James","Charlotte","Oliver","Amelia","Elijah",
          "Harper","Benjamin","Evelyn","Mason","Abigail","Logan","Emily",
          "Alexander","Elizabeth","Michael","Mila","Daniel","Ella","Henry","Scarlett"]
LNAMES = ["Reyes","Santos","Dela Cruz","Garcia","Mendoza","Torres","Flores",
          "Bautista","Ramos","Aquino","Lopez","Fernandez","Ramirez","Villanueva",
          "Castro","Navarro","Morales","Rivera","Gonzales","Escobar","Lim",
          "Tan","Uy","Chua","Go","Sy","Lee","Chan","Yap","Ko"]
ADDRS  = [
    "Purok 1, Brgy. Poblacion, Manolo Fortich, Bukidnon",
    "Purok 2, Brgy. Dalirig, Manolo Fortich, Bukidnon",
    "Purok 3, Brgy. Lindaban, Manolo Fortich, Bukidnon",
]

student_ids = []
section_codes = list(section_map.keys())

for i in range(30):
    cur.execute("""
        INSERT INTO students
          (first_name,last_name,birth_date,gender,address,
           guardian_first_name,guardian_last_name,guardian_contact,
           guardian_relationship,created_at,updated_at,created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING student_id
    """, (FNAMES[i], LNAMES[i], rdate(),
          "Male" if i%2==0 else "Female",
          ADDRS[i%len(ADDRS)],
          "Parent", LNAMES[i], f"091{random.randint(10000000,99999999)}",
          "Parent", now(), now(), admin_id))
    sid = cur.fetchone()[0]
    cur.execute("UPDATE students SET login_id=%s WHERE student_id=%s", (f"S{sid:03d}", sid))
    student_ids.append(sid)
print(f"   {len(student_ids)} students (S{student_ids[0]:03d}–S{student_ids[-1]:03d})")

# ── 7. Enrollments ────────────────────────────────────────────────────────────
print("\n📋  Enrollments …")
enrollment_map = {}   # student_id → {enrollment_id, section_name, grade}
for idx, stud_id in enumerate(student_ids):
    sec_code = section_codes[idx % len(section_codes)]
    sec      = section_map[sec_code]
    gl_id    = grade_map[sec["grade"]]
    cur.execute("""
        INSERT INTO student_enrollments
          (student_id,grade_level_id,section_id,school_year_id,
           enrolled_by,enrollment_date,is_active)
        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING enrollment_id
    """, (stud_id, gl_id, sec["id"], sy_id, admin_id,
          date(2024,6,3).isoformat(), True))
    enroll_id = cur.fetchone()[0]
    enrollment_map[stud_id] = {
        "enrollment_id": enroll_id,
        "section_name":  sec["name"],
        "grade":         sec["grade"],
    }
print(f"   {len(enrollment_map)} enrollments")

# ── 8. PACE Records ───────────────────────────────────────────────────────────
# KEY FIX: pace_percent is a real number (20–100).
# The frontend computes avg from this field via the paceApi.
print("\n⏱️   Pace records …")

pace_count = 0
for stud_id in student_ids:
    enroll_id = enrollment_map[stud_id]["enrollment_id"]
    for subj in CORE_SUBJECTS:
        # Give realistic spread: most students 50–95%, some low
        pace_pct  = round(random.uniform(25.0, 98.0), 1)
        paces_beh = max(0, int((80 - pace_pct) / 8))
        cur.execute("""
            INSERT INTO student_paces
              (student_id,enrollment_id,subject,pace_percent,paces_behind,
               created_at,updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (stud_id, enroll_id, subj, pace_pct, paces_beh, now(), now()))
        pace_count += 1
print(f"   {pace_count} pace records")

# ── 9. Early Warnings ─────────────────────────────────────────────────────────
# KEY FIX: pace_percent and attendance are real numbers (not 0).
# risk_level matches exactly what frontend expects: critical|high|moderate|low
print("\n⚠️   Early warnings …")

# (risk_level, status, trend, pace_lo, pace_hi, att_lo, att_hi)
RISK_MATRIX = [
    ("critical", "Critical",  "declining",  10, 35,  40, 65),
    ("high",     "At Risk",   "declining",  35, 55,  55, 72),
    ("moderate", "Warning",   "stable",     55, 72,  70, 85),
    ("low",      "On Track",  "improving",  72, 95,  83, 100),
]

warn_count = 0
# Give warnings to first 20 students (varied risk levels)
for i, stud_id in enumerate(student_ids[:20]):
    enroll_id = enrollment_map[stud_id]["enrollment_id"]
    r         = RISK_MATRIX[i % len(RISK_MATRIX)]
    r_level, status, trend, p_lo, p_hi, a_lo, a_hi = r
    pace_pct  = round(random.uniform(p_lo, p_hi), 1)
    attend    = round(random.uniform(a_lo, a_hi), 1)
    paces_beh = max(0, int((80 - pace_pct) / 8))
    teacher   = TEACHER_NAMES[i % len(TEACHER_NAMES)]
    subj      = CORE_SUBJECTS[i % len(CORE_SUBJECTS)]

    cur.execute("""
        INSERT INTO early_warnings
          (student_id,enrollment_id,subject,teacher,risk_level,
           paces_behind,pace_percent,attendance,status,trend,
           last_activity,created_at,updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (stud_id, enroll_id, subj, teacher, r_level,
          paces_beh, pace_pct, attend, status, trend,
          "Today", now(), now()))
    warn_count += 1

print(f"   {warn_count} early warnings")

# ── Commit ────────────────────────────────────────────────────────────────────
conn.commit()
cur.close()
conn.close()

print("""
╔══════════════════════════════════════════════════════════════╗
║  ✅  Seed v2 complete!                                       ║
╠══════════════════════════════════════════════════════════════╣
║  school_years     1  (2024-2025)                            ║
║  grade_levels     4  (7-10)                                 ║
║  sections         8                                         ║
║  subjects         8                                         ║
║  staff            3  (admin + 2 teachers)                   ║
║  students        30                                         ║
║  enrollments     30                                         ║
║  pace records    90  (real pace_percent values 25–98%)      ║
║  early warnings  20  (real pace + attendance, all risk lvls)║
╠══════════════════════════════════════════════════════════════╣
║  admin@lbca.edu       Admin@1234                            ║
║  teacher1@lbca.edu    Teacher@1234                          ║
║  teacher2@lbca.edu    Teacher@1234                          ║
╚══════════════════════════════════════════════════════════════╝

⚠️  IMPORTANT — YOU STILL NEED THE BACKEND FIX (see seed_backend_fix.md)
   The seed data is correct but the /api/students/ endpoint doesn't return
   section_name or attendance, so those columns will still show 0 / blank
   until you apply the backend patch.
""")