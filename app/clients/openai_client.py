from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt

from app.settings import get_settings

client = AsyncOpenAI(api_key=get_settings().OPENAI_API_KEY)


@retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(5))
async def safe_chat_completion(*args, **kwargs):
    return await client.chat.completions.create(*args, **kwargs)
