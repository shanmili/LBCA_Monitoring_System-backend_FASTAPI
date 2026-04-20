"""
init_db.py  –  Create (or recreate) all database tables.

Run directly:
    python init_db.py

TABLE DESIGN
============

── school_years ────────────────────────────────────────────────────
  school_year_id  INTEGER  PK
  year            VARCHAR(20)  UNIQUE NOT NULL   e.g. "2024-2025"
  is_current      BOOLEAN NOT NULL DEFAULT FALSE
  start_date      DATE NOT NULL
  end_date        DATE NOT NULL

── grade_levels ────────────────────────────────────────────────────
  grade_level_id  INTEGER  PK
  level           VARCHAR(10)  UNIQUE NOT NULL   e.g. "7", "8"
  name            VARCHAR(20)  NOT NULL          e.g. "Grade 7"

── sections ────────────────────────────────────────────────────────
  section_id      INTEGER  PK
  grade_level_id  INTEGER  FK → grade_levels(grade_level_id) ON DELETE CASCADE
  section_code    VARCHAR(20)  UNIQUE NOT NULL
  name            VARCHAR(30)  NOT NULL

── subjects ────────────────────────────────────────────────────────
  subject_id      INTEGER  PK
  grade_level_id  INTEGER  FK → grade_levels(grade_level_id) ON DELETE CASCADE
  subject_name    VARCHAR(255)  NOT NULL
  subject_code    VARCHAR(50)  UNIQUE NOT NULL
  is_active       BOOLEAN NOT NULL DEFAULT TRUE

── students ────────────────────────────────────────────────────────
  student_id          INTEGER  PK
  login_id            VARCHAR(20)  UNIQUE NULLABLE   auto-assigned as S### after insert
  first_name          VARCHAR(50)  NOT NULL
  middle_name         VARCHAR(50)  NULLABLE
  last_name           VARCHAR(50)  NOT NULL
  birth_date          VARCHAR(15)  NOT NULL
  gender              VARCHAR(10)  NOT NULL           Male | Female
  address             VARCHAR(255) NOT NULL
  guardian_first_name VARCHAR(50)  NOT NULL
  guardian_mid_name   VARCHAR(50)  NULLABLE
  guardian_last_name  VARCHAR(50)  NOT NULL
  guardian_contact    VARCHAR(15)  NOT NULL
  relationship        VARCHAR(10)  NOT NULL           Parent | Guardian | Other
  created_at          DATETIME     NOT NULL  DEFAULT utcnow
  updated_at          DATETIME     NOT NULL  DEFAULT utcnow  ON UPDATE utcnow
  created_by          INTEGER  FK → staff(staff_id) ON DELETE SET NULL

── student_enrollments ─────────────────────────────────────────────
  enrollment_id       INTEGER  PK
  student_id          INTEGER  FK → students(student_id) ON DELETE CASCADE
  grade_level_id      INTEGER  FK → grade_levels(grade_level_id) ON DELETE RESTRICT
  section_id          INTEGER  FK → sections(section_id) ON DELETE RESTRICT
  school_year_id      INTEGER  FK → school_years(school_year_id) ON DELETE RESTRICT
  enrolled_by         INTEGER  FK → staff(staff_id) ON DELETE SET NULL
  next_grade_level_id INTEGER  FK → grade_levels(grade_level_id) ON DELETE SET NULL  NULLABLE
  enrollment_date     VARCHAR(20) NULLABLE   ISO date string set on create
  is_active           BOOLEAN  NOT NULL DEFAULT TRUE
  end_of_year_status  VARCHAR(20) NULLABLE   Promoted | Retained | Dropped | Graduated

── student_paces ───────────────────────────────────────────────────
  pace_id       INTEGER  PK
  student_id    INTEGER  FK → students(student_id) ON DELETE CASCADE
  enrollment_id INTEGER  FK → student_enrollments(enrollment_id) ON DELETE CASCADE
  subject       VARCHAR(100) NOT NULL
  pace_percent  FLOAT  NOT NULL DEFAULT 0.0   % of curriculum completed
  paces_behind  INTEGER NOT NULL DEFAULT 0    number of paces behind standard
  created_at    DATETIME NOT NULL DEFAULT utcnow
  updated_at    DATETIME NOT NULL DEFAULT utcnow ON UPDATE utcnow

── early_warnings ──────────────────────────────────────────────────
  warning_id    INTEGER  PK
  student_id    INTEGER  FK → students(student_id) ON DELETE CASCADE
  enrollment_id INTEGER  FK → student_enrollments(enrollment_id) ON DELETE CASCADE  NULLABLE
  subject       VARCHAR(100) NOT NULL
  teacher       VARCHAR(100) NOT NULL
  risk_level    VARCHAR(20)  NOT NULL   critical | high | moderate | low
  paces_behind  INTEGER  NOT NULL DEFAULT 0
  pace_percent  FLOAT    NOT NULL DEFAULT 0.0
  attendance    FLOAT    NOT NULL DEFAULT 0.0   attendance %
  status        VARCHAR(20)  NOT NULL   Critical | At Risk | Warning | On Track
  trend         VARCHAR(20)  NOT NULL   declining | stable | improving
  last_activity VARCHAR(100) NOT NULL DEFAULT "Today"
  created_at    DATETIME NOT NULL DEFAULT utcnow
  updated_at    DATETIME NOT NULL DEFAULT utcnow ON UPDATE utcnow

── schedules ────────────────────────────────────────────────────────
  schedule_id   INTEGER  PK
  section_id    INTEGER  FK → sections(section_id) ON DELETE CASCADE
  day           VARCHAR(20) NOT NULL
  time_start    TIME NOT NULL
  time_end      TIME NOT NULL
  classroom     VARCHAR(50) NOT NULL

── teacher_availabilities ──────────────────────────────────────────
  availability_id INTEGER  PK
  teacher_id      UUID  FK → staff(id) ON DELETE CASCADE
  day             VARCHAR(20) NOT NULL
  start_time      TIME NOT NULL
  end_time        TIME NOT NULL
  location        VARCHAR(100) NOT NULL
  is_active       BOOLEAN NOT NULL DEFAULT TRUE
  created_at      DATETIME NOT NULL DEFAULT utcnow
  updated_at      DATETIME NOT NULL DEFAULT utcnow ON UPDATE utcnow

── data_quality_logs ──────────────────────────────────────────────
  log_id           INTEGER  PK
  student_id       INTEGER  FK → students(student_id) ON DELETE CASCADE
  teacher_id       UUID  FK → staff(id) ON DELETE SET NULL  NULLABLE
  student_pace_id  INTEGER  FK → student_paces(pace_id) ON DELETE SET NULL  NULLABLE
  issue_type       VARCHAR(100) NOT NULL
  resolved         BOOLEAN NOT NULL DEFAULT FALSE
  resolved_date    DATETIME NULLABLE
  created_at       DATETIME NOT NULL DEFAULT utcnow
  updated_at       DATETIME NOT NULL DEFAULT utcnow ON UPDATE utcnow
"""

from database import sync_engine, Base

# Import all model modules so SQLAlchemy registers their metadata before
# calling create_all().  The noqa comments suppress "imported but unused"
# linter warnings – these imports are intentional side-effects.
import models                           # noqa: F401  (staff / auth models)
import app.models.academic              # noqa: F401  (SchoolYear, GradeLevel, Section, Subject)
import app.models.students              # noqa: F401  (Student, StudentEnrollment, StudentPace, EarlyWarning)
import app.models.operational           # noqa: F401  (Schedule, TeacherAvailability, DataQualityLog)


def init_db() -> None:
    print("Creating database tables...")
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    print("Tables created successfully!")


if __name__ == "__main__":
    init_db()