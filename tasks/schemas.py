from datetime import datetime, timezone

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from .models import Task


def check_deadline(deadline):
    if deadline is None:
        return deadline

    if deadline < datetime.now(timezone.utc):
        raise ValueError("Deadline cannot be in the past.")

    return deadline


def check_priority(priority):
    if priority not in Task.PRIORITY_CHOICES:
        raise ValueError(f"Choose one of: {', '.join(Task.PRIORITY_CHOICES)}.")

    return priority


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: str = Task.MEDIUM
    assignee_id: int | None = None
    deadline: AwareDatetime | None = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, priority):
        return check_priority(priority)

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, deadline):
        return check_deadline(deadline)


class TaskUpdate(BaseModel):
    # None defaults are not validated, so an explicit null for these fields still fails.
    title: str = Field(default=None, min_length=1, max_length=200)
    description: str = None
    priority: str = None
    assignee_id: int | None = None
    deadline: AwareDatetime | None = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, priority):
        return check_priority(priority)

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, deadline):
        return check_deadline(deadline)


class TaskStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, status):
        if status not in Task.STATUS_CHOICES:
            raise ValueError(f"Choose one of: {', '.join(Task.STATUS_CHOICES)}.")

        return status


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    priority: str
    author_id: int
    assignee_id: int | None
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    count: int
    results: list[TaskRead]


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    text: str
    created_at: datetime


class CommentList(BaseModel):
    count: int
    results: list[CommentRead]
