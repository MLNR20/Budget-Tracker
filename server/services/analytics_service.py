from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from entities.transaction import Transaction, TransactionType
from repositories import TransactionRepository
from schemas.analytics import AnalyticsResponse, CategoryTotal, GroupBy, TimePoint
from services.exceptions import BusinessRuleError

ZERO = Decimal("0.00")
MAX_POINTS = 1000  # guards against a huge date range producing an enormous gap-filled series


class AnalyticsService:
    """Aggregates a user's transactions for the dashboard charts."""

    def __init__(self, transactions: TransactionRepository):
        self.transactions = transactions

    def summary(
        self,
        user_id: int,
        type: TransactionType | None = TransactionType.expense,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        group_by: GroupBy = GroupBy.day,
        tz_offset_minutes: int = 0,
    ) -> AnalyticsResponse:
        """Totals per category and per period.

        Dates are calendar dates in the caller's timezone (`tz_offset_minutes` is minutes east of
        UTC), because transactions are stored in UTC but the user thinks in local days.
        """
        if date_from and date_to and date_from > date_to:
            raise BusinessRuleError("Start date must be on or before the end date")

        tz = timezone(timedelta(minutes=tz_offset_minutes))
        rows = [
            (t, self._local_date(t, tz))
            for t in self.transactions.list_for_analytics(user_id, type=type, category=category)
        ]
        rows = [
            (t, d)
            for t, d in rows
            if (date_from is None or d >= date_from) and (date_to is None or d <= date_to)
        ]

        return AnalyticsResponse(
            total=sum((t.amount for t, _ in rows), ZERO),
            count=len(rows),
            by_category=self._by_category(rows),
            over_time=self._over_time(rows, group_by, date_from, date_to),
            categories=self.transactions.categories_for_user(user_id),
        )

    @staticmethod
    def _local_date(transaction: Transaction, tz: timezone) -> date:
        created = transaction.date_created
        if created.tzinfo is None:  # SQLite returns naive datetimes; they were stored as UTC
            created = created.replace(tzinfo=timezone.utc)
        return created.astimezone(tz).date()

    @staticmethod
    def _by_category(rows: list[tuple[Transaction, date]]) -> list[CategoryTotal]:
        totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
        counts: dict[str, int] = defaultdict(int)
        for t, _ in rows:
            totals[t.category] += t.amount
            counts[t.category] += 1

        grand_total = sum(totals.values(), ZERO)
        return [
            CategoryTotal(
                category=name,
                total=total,
                count=counts[name],
                percent=round(float(total / grand_total) * 100, 1) if grand_total else 0.0,
            )
            for name, total in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

    @staticmethod
    def _over_time(
        rows: list[tuple[Transaction, date]],
        group_by: GroupBy,
        date_from: date | None,
        date_to: date | None,
    ) -> list[TimePoint]:
        if not rows:
            return []

        def bucket(d: date) -> date:
            return d.replace(day=1) if group_by is GroupBy.month else d

        totals: dict[date, Decimal] = defaultdict(lambda: ZERO)
        counts: dict[date, int] = defaultdict(int)
        for t, d in rows:
            totals[bucket(d)] += t.amount
            counts[bucket(d)] += 1

        # Fill empty days/months so the line shows real gaps instead of joining distant points.
        first = bucket(date_from or min(totals))
        last = bucket(date_to or max(totals))
        fmt = "%Y-%m" if group_by is GroupBy.month else "%Y-%m-%d"

        points: list[TimePoint] = []
        current = first
        while current <= last:
            if len(points) >= MAX_POINTS:
                raise BusinessRuleError("Date range is too large; pick a shorter range or group by month")
            points.append(
                TimePoint(
                    period=current.strftime(fmt),
                    total=totals.get(current, ZERO),
                    count=counts.get(current, 0),
                )
            )
            if group_by is GroupBy.month:
                current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            else:
                current += timedelta(days=1)
        return points
