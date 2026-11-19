import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from accounts.urls import router as accounts_router
from config import settings
from tasks.jobs import run_auto_cancel
from tasks.urls import router as tasks_router


@asynccontextmanager
async def lifespan(app):
    job = None
    if settings.AUTO_CANCEL_ENABLED:
        job = asyncio.create_task(run_auto_cancel())

    yield

    if job is not None:
        job.cancel()
        with suppress(asyncio.CancelledError):
            await job


app = FastAPI(title="Task Management API", lifespan=lifespan)
app.include_router(accounts_router)
app.include_router(tasks_router)
