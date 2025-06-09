from pydantic import BaseModel

from app.enums import ModelName


class SelectModelRequest(BaseModel):
    model_name: ModelName


class Prompt(BaseModel):
    text: str


class ChatResponse(BaseModel):
    response: str
