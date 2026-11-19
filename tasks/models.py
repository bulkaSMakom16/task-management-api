from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text

from config.database import Base, utc_now


class Task(Base):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [BACKLOG, IN_PROGRESS, REVIEW, DONE, CANCELLED]
    ACTIVE_STATUSES = [BACKLOG, IN_PROGRESS, REVIEW]
    CLOSED_STATUSES = [DONE, CANCELLED]

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PRIORITY_CHOICES = [LOW, MEDIUM, HIGH]

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('backlog', 'in_progress', 'review', 'done', 'cancelled')",
            name="task_status_is_valid",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="task_priority_is_valid",
        ),
        Index("task_assignee_status_idx", "assignee_id", "status"),
        Index("task_status_deadline_idx", "status", "deadline"),
    )

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default=BACKLOG)
    priority = Column(String(10), nullable=False, default=MEDIUM)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("comment_task_created_idx", "task_id", "created_at"),)

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
