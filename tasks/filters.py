from datetime import datetime, timezone

from sqlalchemy import case, or_

from .models import Task


PRIORITY_RANK = case(
    {Task.HIGH: 3, Task.MEDIUM: 2, Task.LOW: 1},
    value=Task.priority,
)

ORDERING_FIELDS = {
    "created_at": Task.created_at,
    "deadline": Task.deadline,
    "priority": PRIORITY_RANK,
}


def filter_tasks(query, search, status, priority, assignee_id, deadline_from, deadline_to):
    if search:
        title_matches = Task.title.icontains(search, autoescape=True)
        description_matches = Task.description.icontains(search, autoescape=True)
        query = query.where(or_(title_matches, description_matches))

    if status:
        query = query.where(Task.status == status)

    if priority:
        query = query.where(Task.priority == priority)

    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)

    if deadline_from is not None:
        query = query.where(Task.deadline >= deadline_from)

    if deadline_to is not None:
        query = query.where(Task.deadline <= deadline_to)

    return query


def filter_overdue(query):
    now = datetime.now(timezone.utc)
    query = query.where(Task.deadline < now)
    query = query.where(Task.status.not_in(Task.CLOSED_STATUSES))
    return query


def order_tasks(query, ordering):
    field_name = ordering.removeprefix("-")
    field = ORDERING_FIELDS.get(field_name)
    if field is None:
        return query.order_by(
            PRIORITY_RANK.desc(),
            Task.deadline.asc().nulls_last(),
            Task.id.desc(),
        )

    if ordering.startswith("-"):
        field = field.desc()
    else:
        field = field.asc()

    return query.order_by(field.nulls_last(), Task.id.desc())
