from fastapi import FastAPI

from accounts.urls import router as accounts_router


app = FastAPI(title="Task Management API")
app.include_router(accounts_router)
