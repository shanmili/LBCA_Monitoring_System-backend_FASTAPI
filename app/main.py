from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import grade_levels, school_years, sections, subjects
from app.api.routers import students, student_enrollments, student_pace
from app.api.routers import schedules, teacher_availabilities, data_quality_logs
from app.models import academic   # noqa: F401
from app.models import students as _students_models  # noqa: F401
from app.models import operational  # noqa: F401

app = FastAPI(title="LBCA Academic API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5177",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}



app.include_router(school_years.router)
app.include_router(grade_levels.router)
app.include_router(sections.router)
app.include_router(subjects.router)


app.include_router(students.router)
app.include_router(student_enrollments.router)
app.include_router(student_pace.router)

app.include_router(schedules.router)
app.include_router(teacher_availabilities.router)
app.include_router(data_quality_logs.router)