Run this module:

uvicorn app.main:app --reload

Notes:
- This uses REST-style routes for school_years, grade_levels, and sections.
- It reuses your existing auth dependencies from dependencies.py.
- Admin check requires role == "admin".
- Create DB tables for the new models with your migration flow or Base.metadata.create_all in a setup script.

Examples:
- GET /api/school-years/
- POST /api/school-years
- GET /api/school-years/{school_year_id}
- PUT/PATCH /api/school-years/{school_year_id}
- DELETE /api/school-years/{school_year_id}
- GET /api/grade-levels/
- POST /api/grade-levels
- GET /api/grade-levels/{grade_level_id}/sections
