from fastapi import APIRouter, Depends

from accounts.security import get_current_user

from .schemas import CommentList, CommentRead, TaskList, TaskRead
from .views import (
    change_task_status,
    create_comment,
    create_task,
    delete_task,
    overdue_tasks,
    task_comments,
    task_detail,
    task_list,
    task_stats,
    update_task,
)


router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)

router.add_api_route("/", task_list, methods=["GET"], response_model=TaskList)
router.add_api_route("/", create_task, methods=["POST"], status_code=201, response_model=TaskRead)
router.add_api_route("/overdue/", overdue_tasks, methods=["GET"], response_model=TaskList)
router.add_api_route("/stats/", task_stats, methods=["GET"])
router.add_api_route("/{task_id}/", task_detail, methods=["GET"], response_model=TaskRead)
router.add_api_route("/{task_id}/", update_task, methods=["PATCH"], response_model=TaskRead)
router.add_api_route("/{task_id}/", delete_task, methods=["DELETE"], status_code=204)
router.add_api_route(
    "/{task_id}/status/",
    change_task_status,
    methods=["PATCH"],
    response_model=TaskRead,
)
router.add_api_route(
    "/{task_id}/comments/",
    task_comments,
    methods=["GET"],
    response_model=CommentList,
)
router.add_api_route(
    "/{task_id}/comments/",
    create_comment,
    methods=["POST"],
    status_code=201,
    response_model=CommentRead,
)
