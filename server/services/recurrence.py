"""Pure date maths for recurring transactions (no database)."""
import calendar
from datetime import date, datetime, timedelta, timezone

from entities.recurring_transaction import Frequency


def add_months(d: date, months: int) -> date:
    """Move `d` by whole months, clamping the day (Jan 31 + 1 month = Feb 28/29)."""
    year, month0 = divmod(d.year * 12 + (d.month - 1) + months, 12)
    month = month0 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def nth_occurrence(start: date, frequency: Frequency, n: int) -> date:
    """The date of the n-th occurrence (0 = the start date itself)."""
    if frequency is Frequency.daily:
        return start + timedelta(days=n)
    if frequency is Frequency.weekly:
        return start + timedelta(weeks=n)
    if frequency is Frequency.monthly:
        return add_months(start, n)
    return add_months(start, 12 * n)  # yearly


def occurrence_datetime(d: date) -> datetime:
    """Noon UTC on that date: the same calendar day in nearly every timezone."""
    return datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc)
