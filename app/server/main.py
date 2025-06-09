import logging

from fastapi import FastAPI

from app.server.routes.chat import router as chat_router
from app.settings import get_settings

logging.basicConfig(
    level=get_settings().LOGGING_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI()
app.include_router(chat_router)
