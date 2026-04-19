from fastapi import FastAPI

from app.api.routers import grade_levels, school_years, sections
from app.models import academic  # noqa: F401


app = FastAPI(title="LBCA Academic API", version="1.0.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(school_years.router)
app.include_router(grade_levels.router)
app.include_router(sections.router)
