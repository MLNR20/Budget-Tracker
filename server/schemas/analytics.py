from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class GroupBy(str, Enum):
    day = "day"
    month = "month"


class CategoryTotal(BaseModel):
    """One slice of the pie / one bar of the bar chart."""

    category: str
    total: Decimal
    count: int
    percent: float


class TimePoint(BaseModel):
    """One point of the line chart. `period` is YYYY-MM-DD (day) or YYYY-MM (month)."""

    period: str
    total: Decimal
    count: int


class AnalyticsResponse(BaseModel):
    total: Decimal
    count: int
    by_category: list[CategoryTotal]  # largest first; feeds the pie and bar charts
    over_time: list[TimePoint]  # oldest first, gaps filled with 0; feeds the line chart
    categories: list[str]  # every category the user has used, for the filter dropdown
