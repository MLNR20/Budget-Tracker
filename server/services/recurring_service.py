from datetime import date, datetime, timedelta
from typing import Sequence
from zoneinfo import ZoneInfo

from config import APP_TIMEZONE
from entities.recurring_transaction import RecurringTransaction
from entities.transaction import Transaction
from repositories import RecurringTransactionRepository
from schemas.recurring import RecurringCreate, RecurringUpdate
from services.exceptions import BusinessRuleError, NotFoundError
from services.recurrence import nth_occurrence, occurrence_datetime

# A rule may start at most this far in the past, because creating it backfills every missed date.
MAX_BACKFILL_DAYS = 366
# Safety cap per rule per catch-up run (the backfill limit above already keeps real use far below).
MAX_PER_RULE_RUN = 400


def local_today() -> date:
    return datetime.now(ZoneInfo(APP_TIMEZONE)).date()


class RecurringTransactionService:
    """Rules that turn into real transactions.

    There is no background scheduler: `process_due` is called when a user logs in or opens the
    dashboard, and creates every transaction that has come due since the last time. A missed day
    (server off, nobody logged in) is simply caught up next time.
    """

    def __init__(self, recurring: RecurringTransactionRepository):
        self.recurring = recurring

    def get(self, rule_id: int, user_id: int) -> RecurringTransaction:
        rule = self.recurring.get_for_user(rule_id, user_id)
        if rule is None:
            raise NotFoundError("Recurring transaction not found")
        return rule

    def list(self, user_id: int) -> Sequence[RecurringTransaction]:
        return self.recurring.list_for_user(user_id)

    def create(self, user_id: int, data: RecurringCreate) -> RecurringTransaction:
        if data.start_date < local_today() - timedelta(days=MAX_BACKFILL_DAYS):
            raise BusinessRuleError("The start date can't be more than a year in the past.")
        rule = self.recurring.add(
            RecurringTransaction(
                user_id=user_id,
                description=data.description,
                amount=data.amount,
                type=data.type,
                category=data.category,
                frequency=data.frequency,
                start_date=data.start_date,
                end_date=data.end_date,
                next_run_date=data.start_date,
                occurrences_generated=0,
            )
        )
        self.process_due(user_id)  # a start date in the past is backfilled straight away
        self.recurring.session.refresh(rule)
        return rule

    def update(self, rule_id: int, user_id: int, data: RecurringUpdate) -> RecurringTransaction:
        rule = self.get(rule_id, user_id)
        # end_date may be sent as null to remove it; every other field must not be null.
        values = {
            k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k == "end_date"
        }
        if values.get("end_date") is not None and values["end_date"] < rule.start_date:
            raise BusinessRuleError("The end date can't be before the start date.")

        resuming = values.get("is_active") is True and not rule.is_active
        rule = self.recurring.update(rule, values)
        if resuming:
            self._skip_missed(rule)
        return rule

    def delete(self, rule_id: int, user_id: int) -> None:
        """Removes the rule only. Transactions it already created stay."""
        self.recurring.delete(self.get(rule_id, user_id))

    def process_due(self, user_id: int) -> int:
        """Create every transaction that is due (up to today) for this user's rules.

        Returns how many were created. Safe to call as often as you like: each rule's
        next_run_date moves forward in the same database transaction that inserts the rows.
        """
        today = local_today()
        created: list[Transaction] = []

        for rule in self.recurring.lock_due(user_id, today):
            made = 0
            while rule.next_run_date <= today and made < MAX_PER_RULE_RUN:
                if rule.end_date is not None and rule.next_run_date > rule.end_date:
                    break
                created.append(
                    Transaction(
                        user_id=rule.user_id,
                        description=rule.description,
                        amount=rule.amount,
                        type=rule.type,
                        category=rule.category,
                        date_created=occurrence_datetime(rule.next_run_date),
                    )
                )
                self._advance(rule)
                made += 1
            if rule.end_date is not None and rule.next_run_date > rule.end_date:
                rule.is_active = False  # finished

        self.recurring.save_generated(created)  # also commits the modified rules
        return len(created)

    # ---- helpers ----

    @staticmethod
    def _advance(rule: RecurringTransaction) -> None:
        rule.occurrences_generated += 1
        rule.next_run_date = nth_occurrence(rule.start_date, rule.frequency, rule.occurrences_generated)

    def _skip_missed(self, rule: RecurringTransaction) -> None:
        """After un-pausing, don't back-create everything missed while it was paused."""
        today = local_today()
        skipped = 0
        while rule.next_run_date < today and skipped < 100_000:
            self._advance(rule)
            skipped += 1
        if rule.end_date is not None and rule.next_run_date > rule.end_date:
            rule.is_active = False
        self.recurring.session.commit()
        self.recurring.session.refresh(rule)
