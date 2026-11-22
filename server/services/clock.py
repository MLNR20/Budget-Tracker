from datetime import date, datetime
from zoneinfo import ZoneInfo

from config import APP_TIMEZONE


def local_today() -> date:
    """Today's calendar date in APP_TIMEZONE (not the server's UTC date)."""
    return datetime.now(ZoneInfo(APP_TIMEZONE)).date()
