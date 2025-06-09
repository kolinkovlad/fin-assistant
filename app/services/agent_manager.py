from uuid import UUID
from redis.asyncio import Redis

from app.data.latest_prices import latest_prices
from app.data.load import load_portfolio_data
from app.enums import ModelName
from app.services.history import MessageHistory, ToolMemory
from app.services.llm_agent import LLMPortfolioAgent


class AgentManager:
    def __init__(self, redis: Redis):
        self.redis = redis

    def get_agent(self, session_id: UUID, model: ModelName = ModelName.GPT_4) -> LLMPortfolioAgent:
        portfolio = load_portfolio_data()

        return LLMPortfolioAgent(
            model=model.value,
            history=MessageHistory(self.redis, str(session_id)),
            memory=ToolMemory(self.redis, session_id),
            holdings=portfolio['holdings'],
            cash_balances=portfolio['cash_balances'],
            accounts=portfolio['accounts'],
            fund_metadata=portfolio['fund_metadata'],
            transactions=portfolio['transactions'],
            latest_prices=latest_prices,
        )