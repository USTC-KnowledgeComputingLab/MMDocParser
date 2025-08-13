# storage/redis_client.py
import json
import logging
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)

async def get_redis_client(redis_url: str) -> Any:
    """获取Redis客户端连接"""
    try:
        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        # 测试连接
        await redis_client.ping()
        logger.info("Redis连接成功")
        return redis_client
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
        raise

class TaskManager:
    """任务管理器"""

    def __init__(self, redis_client: redis.Redis, queue_name: str, status_prefix: str):
        self.redis = redis_client
        self.queue_name = queue_name
        self.status_prefix = status_prefix

    async def push_task(self, task_data: dict[str, Any]) -> bool:
        """推送任务到队列"""
        try:
            await self.redis.rpush(self.queue_name, json.dumps(task_data)) # type: ignore
            logger.info(f"任务已推送到队列: {task_data.get('task_id')}")
            return True
        except Exception as e:
            logger.error(f"推送任务失败: {e}")
            return False

    async def get_task(self) -> Any:
        """从队列获取任务"""
        try:
            task_data = await self.redis.blpop([self.queue_name], timeout=1) # type: ignore
            if task_data:
                return json.loads(task_data[1])
            return None
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return None

    async def set_task_status(self, task_id: str, status: str, timeout: int = 3600) -> bool:
        """设置任务状态"""
        try:
            key = f"{self.status_prefix}:{task_id}"
            await self.redis.setex(key, timeout, status)
            return True
        except Exception as e:
            logger.error(f"设置任务状态失败: {e}")
            return False

    async def get_task_status(self, task_id: str) -> Any:
        """获取任务状态"""
        try:
            key = f"{self.status_prefix}:{task_id}"
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None

    async def update_task_status(self, task_id: str, status: str, result: dict | None = None) -> bool:
        """更新任务状态和结果"""
        try:
            # 更新状态
            await self.set_task_status(task_id, status)

            # 如果有结果，存储结果
            if result:
                result_key = f"task_result:{task_id}"
                await self.redis.setex(result_key, 86400, json.dumps(result))  # 24小时过期

            return True
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False

    async def get_task_result(self, task_id: str) -> Any:
        """获取任务结果"""
        try:
            result_key = f"task_result:{task_id}"
            result_data = await self.redis.get(result_key)
            if result_data:
                return json.loads(result_data)
            return None
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return None
