from fastapi import FastAPI

from accounts.urls import router as accounts_router
from tasks.urls import router as tasks_router


app = FastAPI(title="Task Management API")
app.include_router(accounts_router)
app.include_router(tasks_router)
