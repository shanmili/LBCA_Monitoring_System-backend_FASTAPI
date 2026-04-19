import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


_YEAR_PATTERN = re.compile(r"^\d{4}-\d{4}$")


def _validate_year_format(value: str) -> str:
    if not _YEAR_PATTERN.match(value):
        raise ValueError("Year must follow the format YYYY-YYYY (e.g. 2024-2025).")
    first, second = value.split("-")
    if int(second) != int(first) + 1:
        raise ValueError("The second year must be exactly one year after the first.")
    return value


class SchoolYearCreate(BaseModel):
    year: str
    is_current: bool = False
    start_date: date
    end_date: date

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: str) -> str:
        return _validate_year_format(value)


class SchoolYearUpdate(BaseModel):
    year: Optional[str] = None
    is_current: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_year_format(value)


class SchoolYearOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    school_year_id: int
    year: str
    is_current: bool
    start_date: date
    end_date: date
