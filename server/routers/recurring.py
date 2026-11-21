from fastapi import APIRouter, status

from dependencies import CurrentUser, RecurringSvc
from schemas.recurring import ProcessResult, RecurringCreate, RecurringResponse, RecurringUpdate

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.post("", response_model=RecurringResponse, status_code=status.HTTP_201_CREATED)
def create_rule(data: RecurringCreate, current_user: CurrentUser, service: RecurringSvc):
    """Create a rule. A start date in the past is backfilled immediately."""
    return service.create(current_user.id, data)


@router.get("", response_model=list[RecurringResponse])
def list_rules(current_user: CurrentUser, service: RecurringSvc):
    return service.list(current_user.id)


@router.post("/process", response_model=ProcessResult)
def process_due(current_user: CurrentUser, service: RecurringSvc):
    """Catch up: create every transaction that has come due. The client calls this on login and
    when the dashboard opens. Idempotent: calling it again creates nothing new."""
    return ProcessResult(created=service.process_due(current_user.id))


@router.patch("/{rule_id}", response_model=RecurringResponse)
def update_rule(rule_id: int, data: RecurringUpdate, current_user: CurrentUser, service: RecurringSvc):
    return service.update(rule_id, current_user.id, data)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, current_user: CurrentUser, service: RecurringSvc):
    """Deletes the rule only; transactions it already created are kept."""
    service.delete(rule_id, current_user.id)
