from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from sqlalchemy import func, select

from accounts.models import User
from accounts.security import get_current_user
from config import settings
from config.database import get_session

from .filters import filter_overdue, filter_tasks, order_tasks
from .models import Comment, Task
from .permissions import can_change_task, can_delete_task
from .schemas import CommentCreate, TaskCreate, TaskStatusUpdate, TaskUpdate


ALLOWED_TRANSITIONS = {
    Task.BACKLOG: [Task.IN_PROGRESS, Task.CANCELLED],
    Task.IN_PROGRESS: [Task.REVIEW, Task.CANCELLED],
    Task.REVIEW: [Task.DONE],
}


async def get_task_or_404(session, task_id, with_for_update=False):
    task = await session.get(Task, task_id, with_for_update=with_for_update)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    return task


async def check_assignee(session, assignee_id):
    query = select(User).where(User.id == assignee_id)
    # Lock the assignee so two requests at once cannot both pass the active task limit.
    query = query.with_for_update()
    result = await session.execute(query)
    assignee = result.scalar_one_or_none()
    if assignee is None:
        raise HTTPException(status_code=400, detail="Assignee does not exist.")

    query = select(func.count(Task.id))
    query = query.where(Task.assignee_id == assignee_id)
    query = query.where(Task.status.in_(Task.ACTIVE_STATUSES))
    active_count = await session.scalar(query)
    if active_count >= settings.MAX_ACTIVE_TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"This user already has {settings.MAX_ACTIVE_TASKS} active tasks.",
        )


async def paginate(session, query, page, page_size):
    count_query = select(func.count()).select_from(query.subquery())
    count = await session.scalar(count_query)

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    items = result.scalars().all()
    return {"count": count, "results": items}


async def task_list(
    search: str = "",
    status: str = "",
    priority: str = "",
    assignee_id: int | None = None,
    deadline_from: AwareDatetime | None = None,
    deadline_to: AwareDatetime | None = None,
    ordering: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.PAGE_SIZE, ge=1, le=100),
    session=Depends(get_session),
):
    query = select(Task)
    query = filter_tasks(query, search, status, priority, assignee_id, deadline_from, deadline_to)
    query = order_tasks(query, ordering)
    return await paginate(session, query, page, page_size)


async def create_task(
    data: TaskCreate,
    user=Depends(get_current_user),
    session=Depends(get_session),
):
    if data.assignee_id is not None:
        await check_assignee(session, data.assignee_id)

    task = Task(**data.model_dump(), author_id=user.id)
    session.add(task)
    await session.commit()
    return task


async def task_detail(task_id: int, session=Depends(get_session)):
    return await get_task_or_404(session, task_id)


async def update_task(
    task_id: int,
    data: TaskUpdate,
    user=Depends(get_current_user),
    session=Depends(get_session),
):
    task = await get_task_or_404(session, task_id, with_for_update=True)
    if not can_change_task(task, user):
        raise HTTPException(
            status_code=403,
            detail="Only the author or assignee can edit this task.",
        )

    if task.status in Task.CLOSED_STATUSES:
        raise HTTPException(status_code=409, detail="Done and cancelled tasks cannot be edited.")

    changes = data.model_dump(exclude_unset=True)
    new_assignee_id = changes.get("assignee_id", task.assignee_id)
    assignee_changed = new_assignee_id != task.assignee_id
    if assignee_changed and task.status in (Task.REVIEW, Task.DONE):
        raise HTTPException(
            status_code=409,
            detail="The assignee cannot be changed after the task is in review.",
        )

    if assignee_changed and new_assignee_id is not None:
        await check_assignee(session, new_assignee_id)

    for field, value in changes.items():
        setattr(task, field, value)

    await session.commit()
    return task


async def delete_task(task_id: int, user=Depends(get_current_user), session=Depends(get_session)):
    task = await get_task_or_404(session, task_id, with_for_update=True)
    if not can_delete_task(task, user):
        raise HTTPException(status_code=403, detail="Only the author can delete this task.")

    if task.status in (Task.IN_PROGRESS, Task.REVIEW):
        raise HTTPException(
            status_code=409,
            detail="Tasks in progress or in review cannot be deleted.",
        )

    await session.delete(task)
    await session.commit()
    return Response(status_code=204)


async def change_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    user=Depends(get_current_user),
    session=Depends(get_session),
):
    task = await get_task_or_404(session, task_id, with_for_update=True)
    if not can_change_task(task, user):
        raise HTTPException(
            status_code=403,
            detail="Only the author or assignee can change the status.",
        )

    allowed_statuses = ALLOWED_TRANSITIONS.get(task.status, [])
    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status from {task.status} to {data.status}.",
        )

    if data.status == Task.DONE:
        if task.assignee_id is None:
            raise HTTPException(
                status_code=400,
                detail="A task without an assignee cannot be done.",
            )

        now = datetime.now(timezone.utc)
        deadline_passed = task.deadline is not None and task.deadline < now
        if deadline_passed:
            raise HTTPException(
                status_code=400,
                detail="A task with a passed deadline cannot be done.",
            )

    task.status = data.status
    await session.commit()
    return task


async def task_comments(
    task_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.PAGE_SIZE, ge=1, le=100),
    session=Depends(get_session),
):
    task = await get_task_or_404(session, task_id)

    query = select(Comment).where(Comment.task_id == task.id)
    query = query.order_by(Comment.created_at, Comment.id)
    return await paginate(session, query, page, page_size)


async def create_comment(
    task_id: int,
    data: CommentCreate,
    user=Depends(get_current_user),
    session=Depends(get_session),
):
    task = await get_task_or_404(session, task_id)

    comment = Comment(task_id=task.id, author_id=user.id, text=data.text)
    session.add(comment)
    await session.commit()
    return comment


async def overdue_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.PAGE_SIZE, ge=1, le=100),
    session=Depends(get_session),
):
    query = filter_overdue(select(Task))
    query = query.order_by(Task.deadline, Task.id)
    return await paginate(session, query, page, page_size)


async def task_stats(session=Depends(get_session)):
    total = await session.scalar(select(func.count(Task.id)))

    by_status = {status: 0 for status in Task.STATUS_CHOICES}
    query = select(Task.status, func.count(Task.id)).group_by(Task.status)
    result = await session.execute(query)
    for status, count in result.all():
        by_status[status] = count

    by_priority = {priority: 0 for priority in Task.PRIORITY_CHOICES}
    query = select(Task.priority, func.count(Task.id)).group_by(Task.priority)
    result = await session.execute(query)
    for priority, count in result.all():
        by_priority[priority] = count

    query = filter_overdue(select(func.count(Task.id)))
    overdue = await session.scalar(query)

    active = 0
    for status in Task.ACTIVE_STATUSES:
        active += by_status[status]

    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue": overdue,
        "active": active,
    }
