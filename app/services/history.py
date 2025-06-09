import json
from typing import Any, Optional, Dict, List
from uuid import UUID
from redis.asyncio.client import Redis

from app.models.tool_memory import ToolCallRecord


class MessageHistory:
    def __init__(self, redis: Redis, session_id: str, ttl: int = 3600) -> None:
        self.redis = redis
        self.session_key = f'message_history:{session_id}'
        self.ttl = ttl

    async def append(self, message: Dict[str, Any]) -> None:
        await self.redis.rpush(self.session_key, json.dumps(message))
        await self.redis.expire(self.session_key, self.ttl)

    async def get(self) -> List[Dict[str, Any]]:
        raw = await self.redis.lrange(self.session_key, 0, -1)
        return [json.loads(m) for m in raw]

    async def clear(self) -> None:
        await self.redis.delete(self.session_key)

    async def length(self) -> int:
        return await self.redis.llen(self.session_key)


class ToolMemory:
    def __init__(self, redis: Redis, session_id: UUID, ttl: int = 3600) -> None:
        self.redis = redis
        self.session_key = f'tool_memory:{str(session_id)}'
        self.ttl = ttl

    async def set(self, records: list[ToolCallRecord]) -> None:
        for record in records:
            await self.redis.rpush(self.session_key, record.model_dump_json())
        await self.redis.expire(self.session_key, self.ttl)

    async def get_last(self, tool_name: Optional[str] = None) -> Optional[ToolCallRecord]:
        raw = await self.redis.lrange(self.session_key, 0, -1)
        records = [ToolCallRecord.model_validate(json.loads(item)) for item in raw]

        if tool_name:
            for record in reversed(records):
                if record.name == tool_name:
                    return record
            return None  # No match found
        return records[-1] if records else None

    async def get_all(self) -> List[ToolCallRecord]:
        raw = await self.redis.lrange(self.session_key, 0, -1)
        return [ToolCallRecord.model_validate(r.decode('utf-8')) for r in raw]

    async def clear(self) -> None:
        await self.redis.delete(self.session_key)

    async def length(self) -> int:
        return await self.redis.llen(self.session_key)