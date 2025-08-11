import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from storage.redis_client import get_redis_client, TaskManager

pytestmark = pytest.mark.asyncio

class TestRedisConnection:
    async def test_redis_connection_success(self):
        with patch("storage.redis_client.redis.from_url") as mock_from_url:
            mock_redis_client = AsyncMock()
            mock_redis_client.ping.return_value = AsyncMock(return_value=True)
            mock_from_url.return_value = mock_redis_client
            redis_url = "redis://localhost:6379"
            redis_client = await get_redis_client(redis_url)
            assert redis_client is not None
            assert await redis_client.ping()
            mock_from_url.assert_called_once_with(redis_url, encoding="utf-8", decode_responses=True)

    async def test_redis_connection_failure(self):
        with patch("storage.redis_client.redis.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Connection failed")
            redis_url = "redis://localhost:6379"
            with pytest.raises(Exception):
                await get_redis_client(redis_url)
            mock_from_url.assert_called_once_with(redis_url, encoding="utf-8", decode_responses=True)

class TestTaskManager:
    pass