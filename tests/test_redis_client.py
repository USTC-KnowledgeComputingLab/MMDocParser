# tests/test_redis_client.py
import pytest
import json
from unittest.mock import patch, AsyncMock
from storage.redis_client import get_redis_client, TaskManager

pytestmark = pytest.mark.asyncio

class TestRedisConnection:
    """Redis连接测试"""
    
    async def test_redis_connection_success(self):
        """测试Redis连接成功"""
        with patch("storage.redis_client.redis.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_from_url.return_value = mock_redis
            
            client = await get_redis_client("redis://localhost:6379")
            
            assert client is not None
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379", 
                encoding="utf-8", 
                decode_responses=True
            )
    
    async def test_redis_connection_failure(self):
        """测试Redis连接失败"""
        with patch("storage.redis_client.redis.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception, match="Connection failed"):
                await get_redis_client("redis://localhost:6379")

class TestTaskManager:
    """任务管理器核心功能测试"""
    
    @pytest.fixture
    async def task_manager(self):
        """创建任务管理器实例"""
        mock_redis = AsyncMock()
        return TaskManager(mock_redis, "test_queue", "test_status")
    
    async def test_push_task_success(self, task_manager):
        """测试推送任务成功"""
        task_data = {"task_id": "123", "type": "test"}
        task_manager.redis.rpush = AsyncMock(return_value=1)
        
        result = await task_manager.push_task(task_data)
        
        assert result is True
        task_manager.redis.rpush.assert_called_once_with(
            "test_queue", 
            json.dumps(task_data)
        )
    
    async def test_push_task_failure(self, task_manager):
        """测试推送任务失败"""
        task_data = {"task_id": "123", "type": "test"}
        task_manager.redis.rpush = AsyncMock(side_effect=Exception("Redis error"))
        
        result = await task_manager.push_task(task_data)
        
        assert result is False
    
    async def test_get_task_success(self, task_manager):
        """测试获取任务成功"""
        expected_task = {"task_id": "123", "type": "test"}
        mock_data = ("test_queue", json.dumps(expected_task))
        task_manager.redis.blpop = AsyncMock(return_value=mock_data)
        
        result = await task_manager.get_task()
        
        assert result == expected_task
        task_manager.redis.blpop.assert_called_once_with(["test_queue"], timeout=1)
    
    async def test_get_task_no_data(self, task_manager):
        """测试获取任务无数据"""
        task_manager.redis.blpop = AsyncMock(return_value=None)
        
        result = await task_manager.get_task()
        
        assert result is None
    
    async def test_set_task_status(self, task_manager):
        """测试设置任务状态"""
        task_id = "123"
        status = "processing"
        task_manager.redis.setex = AsyncMock(return_value=True)
        
        result = await task_manager.set_task_status(task_id, status)
        
        assert result is True
        task_manager.redis.setex.assert_called_once_with(
            f"test_status:123", 
            3600, 
            status
        )
    
    async def test_get_task_status(self, task_manager):
        """测试获取任务状态"""
        task_id = "123"
        expected_status = "processing"
        task_manager.redis.get = AsyncMock(return_value=expected_status)
        
        result = await task_manager.get_task_status(task_id)
        
        assert result == expected_status
        task_manager.redis.get.assert_called_once_with(f"test_status:123")
    
    async def test_update_task_status_with_result(self, task_manager):
        """测试更新任务状态和结果"""
        task_id = "123"
        status = "completed"
        result_data = {"text": "extracted text"}
        task_manager.redis.setex = AsyncMock(return_value=True)
        
        result = await task_manager.update_task_status(task_id, status, result_data)
        
        assert result is True
        # 验证调用了两次：状态更新 + 结果存储
        assert task_manager.redis.setex.call_count == 2
    
    async def test_get_task_result(self, task_manager):
        """测试获取任务结果"""
        task_id = "123"
        expected_result = {"text": "extracted text"}
        task_manager.redis.get = AsyncMock(return_value=json.dumps(expected_result))
        
        result = await task_manager.get_task_result(task_id)
        
        assert result == expected_result
        task_manager.redis.get.assert_called_once_with(f"task_result:123")

class TestErrorHandling:
    """核心异常处理测试"""
    
    @pytest.fixture
    async def task_manager(self):
        """创建任务管理器实例"""
        mock_redis = AsyncMock()
        return TaskManager(mock_redis, "test_queue", "test_status")
    
    async def test_json_serialization_error(self, task_manager):
        """测试JSON序列化错误"""
        class UnserializableObject:
            pass
        
        task_data = {"data": UnserializableObject()}
        
        result = await task_manager.push_task(task_data)
        
        assert result is False
    
    async def test_redis_operation_failure(self, task_manager):
        """测试Redis操作失败"""
        task_manager.redis.rpush = AsyncMock(side_effect=Exception("Redis error"))
        
        result = await task_manager.push_task({"task_id": "123"})
        
        assert result is False