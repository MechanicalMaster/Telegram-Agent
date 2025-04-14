from fastapi import FastAPI

from ai_companion.interfaces.telegram.telegram_response import telegram_router
from ai_companion.interfaces.admin_dashboard import admin_router

app = FastAPI()
app.include_router(telegram_router)
app.include_router(admin_router)
