import asyncio
import logging

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from config.database import SessionLocal

from .filters import filter_overdue
from .models import Task


logger = logging.getLogger(__name__)


async def cancel_overdue_tasks():
    query = update(Task)
    query = filter_overdue(query)
    query = query.values(status=Task.CANCELLED)

    async with SessionLocal() as session:
        result = await session.execute(query)
        await session.commit()

    return result.rowcount


async def run_auto_cancel():
    while True:
        try:
            await cancel_overdue_tasks()
        except (SQLAlchemyError, OSError):
            logger.exception("Could not cancel overdue tasks.")

        await asyncio.sleep(settings.AUTO_CANCEL_INTERVAL)
