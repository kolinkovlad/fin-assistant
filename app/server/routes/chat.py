import logging
from uuid import UUID

from fastapi import APIRouter, Header, Depends
from redis.asyncio.client import Redis
from starlette.responses import Response

from app.clients.redis import get_redis
from app.server.schemes.chat import Prompt, ChatResponse, SelectModelRequest
from app.services.agent_manager import AgentManager
from app.services.llm_agent import LLMPortfolioAgent

logger = logging.getLogger(__name__)
router = APIRouter()


def get_agent(session_id: UUID = Header(...), redis_client: Redis = Depends(get_redis)) -> LLMPortfolioAgent:
    return AgentManager(redis_client).get_agent(session_id=session_id)


@router.post("/model")
async def select_model(req: SelectModelRequest, agent: LLMPortfolioAgent = Depends(get_agent)) -> Response:
    agent.set_model(req.model_name)
    return Response(status_code=200)


@router.post('/chat', response_model=ChatResponse)
async def chat(prompt: Prompt, agent: LLMPortfolioAgent = Depends(get_agent)):
    logger.info(f"prompt: {prompt}")
    return await agent.process_prompt(prompt)
