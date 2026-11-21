from datetime import date
from typing import Literal

from fastapi import APIRouter, Query

from dependencies import AnalyticsSvc, CurrentUser
from entities.transaction import TransactionType
from schemas.analytics import AnalyticsResponse, GroupBy

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
def get_analytics(
    current_user: CurrentUser,
    service: AnalyticsSvc,
    type: Literal["expense", "income", "all"] = "expense",
    category: str | None = Query(None, min_length=1, max_length=50),
    date_from: date | None = None,
    date_to: date | None = None,
    group_by: GroupBy = GroupBy.day,
    tz_offset_minutes: int = Query(0, ge=-840, le=840, description="Minutes east of UTC"),
):
    """Aggregated data for the pie, bar and line charts, narrowed by the optional filters."""
    return service.summary(
        current_user.id,
        type=None if type == "all" else TransactionType(type),
        category=category,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
        tz_offset_minutes=tz_offset_minutes,
    )
