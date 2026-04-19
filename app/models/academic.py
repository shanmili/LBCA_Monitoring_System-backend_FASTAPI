from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class SchoolYear(Base):
    __tablename__ = "school_years"

    school_year_id = Column(Integer, primary_key=True, index=True)
    year = Column(String(20), unique=True, nullable=False, index=True)
    is_current = Column(Boolean, default=False, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)


class GradeLevel(Base):
    __tablename__ = "grade_levels"

    grade_level_id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(20), nullable=False)

    sections = relationship("Section", back_populates="grade_level")


class Section(Base):
    __tablename__ = "sections"

    section_id = Column(Integer, primary_key=True, index=True)
    grade_level_id = Column(Integer, ForeignKey("grade_levels.grade_level_id", ondelete="CASCADE"), nullable=False, index=True)
    section_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(30), nullable=False)

    grade_level = relationship("GradeLevel", back_populates="sections")
