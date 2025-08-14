# tests/test_integration.py
import pytest
import asyncio
import json
import os
from storage.redis_client import get_redis_client, TaskManager
from storage.s3_client import AsyncS3Client

# 优先从.env文件加载环境变量
from dotenv import load_dotenv
load_dotenv() 

pytestmark = pytest.mark.asyncio

class TestRedisIntegration:
    """Redis集成测试 - 需要真实的Redis服务"""
    
    @pytest.fixture
    async def redis_client(self):
        """获取真实的Redis客户端"""
        try:
            client = await get_redis_client(os.getenv("REDIS_URL"))
            # 清理测试数据
            await client.flushdb()
            yield client
            # 测试后清理
            await client.flushdb()
            await client.close()
        except Exception as e:
            pytest.skip(f"Redis服务不可用: {e}")
    
    @pytest.fixture
    async def task_manager(self, redis_client):
        """创建任务管理器"""
        return TaskManager(redis_client, "test_queue", "test_status")
    
    async def test_real_redis_connection(self, redis_client):
        """测试真实Redis连接"""
        # 基本连接测试
        pong = await redis_client.ping()
        assert pong is True
        
        # 基本操作测试
        await redis_client.set("test_key", "test_value")
        value = await redis_client.get("test_key")
        assert value == "test_value"
        
        # 清理
        await redis_client.delete("test_key")
    
    async def test_real_task_lifecycle(self, task_manager):
        """测试真实任务生命周期"""
        # 1. 推送任务
        task_data = {
            "task_id": "integration-test-123",
            "type": "document_analysis",
            "template_type": "化学",
            "created_at": asyncio.get_event_loop().time()
        }
        
        success = await task_manager.push_task(task_data)
        assert success is True
        
        # 2. 设置任务状态
        status_success = await task_manager.set_task_status("integration-test-123", "processing")
        assert status_success is True
        
        # 3. 获取任务状态
        status = await task_manager.get_task_status("integration-test-123")
        assert status == "processing"
        
        # 4. 获取任务
        task = await task_manager.get_task()
        assert task is not None
        assert task["task_id"] == "integration-test-123"
        
        # 5. 更新状态和结果
        result = {"text": "从化学文档提取的文本", "confidence": 0.95}
        update_success = await task_manager.update_task_status("integration-test-123", "completed", result)
        assert update_success is True
        
        # 6. 获取结果
        stored_result = await task_manager.get_task_result("integration-test-123")
        assert stored_result == result
        
        # 7. 验证最终状态
        final_status = await task_manager.get_task_status("integration-test-123")
        assert final_status == "completed"
    
    async def test_real_batch_operations(self, task_manager):
        """测试真实批量操作"""
        # 批量推送任务
        tasks = [
            {"task_id": f"batch-test-{i}", "type": "test", "index": i}
            for i in range(5)
        ]
        
        for task in tasks:
            success = await task_manager.push_task(task)
            assert success is True
        
        # 批量设置状态
        for i in range(5):
            success = await task_manager.set_task_status(f"batch-test-{i}", "processing")
            assert success is True
        
        # 批量获取状态
        for i in range(5):
            status = await task_manager.get_task_status(f"batch-test-{i}")
            assert status == "processing"
        
        # 批量获取任务
        retrieved_tasks = []
        for _ in range(5):
            task = await task_manager.get_task()
            if task:
                retrieved_tasks.append(task)
        
        assert len(retrieved_tasks) == 5
        
        # 批量更新为完成状态
        for i in range(5):
            result = {"result": f"batch result {i}"}
            success = await task_manager.update_task_status(f"batch-test-{i}", "completed", result)
            assert success is True

class TestS3Integration:
    """S3集成测试 - 需要真实的S3服务"""
    
    @pytest.fixture
    async def s3_client(self):
        """获取真实的S3客户端"""
        try:
            # 从环境变量获取配置
            endpoint_url = os.getenv("S3_ENDPOINT", "http://localhost:9000")
            access_key = os.getenv("S3_ACCESS_KEY", "minioadmin")
            secret_key = os.getenv("S3_SECRET_KEY", "minioadmin")
            bucket = os.getenv("S3_BUCKET", "test-bucket")
            region = os.getenv("S3_REGION", "us-east-1")
            
            async with AsyncS3Client(endpoint_url, access_key, secret_key, bucket, region) as client:
                yield client
        except Exception as e:
            pytest.skip(f"S3服务不可用: {e}")
    
    async def test_real_s3_connection(self, s3_client):
        """测试真实S3连接"""
        # 测试基本连接 - 尝试生成一个预签名URL来验证连接
        try:
            test_url = await s3_client.generate_presigned_url("test_connection.txt")
            assert test_url is not None
            assert isinstance(test_url, str)
        except Exception as e:
            pytest.fail(f"S3连接测试失败: {e}")
    
    async def test_real_file_upload_download(self, s3_client):
        """测试真实文件上传和下载"""
        # 测试文件内容
        test_content = b"This is a test document content for S3 integration testing."
        filename = "test_integration.txt"
        
        # 上传文件
        presigned_url = await s3_client.upload_file(filename, test_content)
        assert presigned_url is not None
        assert isinstance(presigned_url, str)
        
        # 通过文件名下载文件（使用新的download_file_by_filename方法）
        downloaded_content = await s3_client.download_file_by_filename(filename)
        assert downloaded_content == test_content
        
        # 验证文件大小
        assert len(downloaded_content) == len(test_content)
        
        # 也可以通过编码后的key直接下载
        encoded_key = s3_client._encode_filename(filename)
        downloaded_content2 = await s3_client.download_file(encoded_key)
        assert downloaded_content2 == test_content
    
    async def test_real_batch_upload(self, s3_client):
        """测试真实批量上传"""
        # 准备多个测试文件
        test_files = [
            ("doc1.txt", b"Document 1 content"),
            ("doc2.txt", b"Document 2 content"),
            ("doc3.txt", b"Document 3 content")
        ]
        
        # 批量上传（逐个上传，因为新版本没有upload_files方法）
        presigned_urls = []
        for filename, content in test_files:
            presigned_url = await s3_client.upload_file(filename, content)
            presigned_urls.append(presigned_url)
        
        # 验证结果
        assert len(presigned_urls) == 3
        assert all(isinstance(url, str) for url in presigned_urls)
        
        # 验证所有文件都可以下载
        for filename, original_content in test_files:
            downloaded_content = await s3_client.download_file_by_filename(filename)
            assert downloaded_content == original_content
    
    async def test_real_large_file(self, s3_client):
        """测试真实大文件上传下载"""
        # 创建1MB的测试数据
        large_content = b"x" * (1024 * 1024)  # 1MB
        filename = "large_test_file.bin"
        
        # 上传大文件
        presigned_url = await s3_client.upload_file(filename, large_content)
        assert presigned_url is not None
        
        # 下载大文件（使用文件名）
        downloaded_content = await s3_client.download_file_by_filename(filename)
        assert downloaded_content == large_content
        assert len(downloaded_content) == 1024 * 1024

class TestFullSystemIntegration:
    """完整系统集成测试"""
    
    @pytest.fixture
    async def system_components(self):
        """获取所有系统组件"""
        try:
            # Redis客户端
            redis_client = await get_redis_client(os.getenv("REDIS_URL"))
            await redis_client.flushdb()
            
            # 任务管理器
            task_manager = TaskManager(redis_client, "system_test_queue", "system_test_status")
            
            # S3客户端
            endpoint_url = os.getenv("S3_ENDPOINT", "http://localhost:9000")
            access_key = os.getenv("S3_ACCESS_KEY", "minioadmin")
            secret_key = os.getenv("S3_SECRET_KEY", "minioadmin")
            bucket = os.getenv("S3_BUCKET", "test-bucket")
            region = os.getenv("S3_REGION", "us-east-1")
            
            s3_client = AsyncS3Client(endpoint_url, access_key, secret_key, bucket, region)
            await s3_client.__aenter__()
            
            yield {
                "redis": redis_client,
                "task_manager": task_manager,
                "s3_client": s3_client
            }
            
            # 清理
            await redis_client.flushdb()
            await redis_client.close()
            await s3_client.__aexit__(None, None, None)
            
        except Exception as e:
            pytest.skip(f"系统组件不可用: {e}")
    
    async def test_document_processing_workflow(self, system_components):
        """测试完整文档处理工作流"""
        redis_client = system_components["redis"]
        task_manager = system_components["task_manager"]
        s3_client = system_components["s3_client"]
        
        # 1. 创建文档处理任务
        task_data = {
            "task_id": "workflow-test-123",
            "type": "document_analysis",
            "template_type": "化学",
            "files": ["chemical_doc.pdf"],
            "created_at": asyncio.get_event_loop().time()
        }
        
        # 2. 推送任务到队列
        success = await task_manager.push_task(task_data)
        assert success is True
        
        # 3. 模拟文档上传到S3
        test_content = b"Chemical document content with formulas and structures."
        presigned_url = await s3_client.upload_file("chemical_doc.pdf", test_content)
        assert presigned_url is not None
        
        # 4. 设置任务状态为处理中
        await task_manager.set_task_status("workflow-test-123", "processing")
        
        # 5. 从队列获取任务
        retrieved_task = await task_manager.get_task()
        assert retrieved_task is not None
        assert retrieved_task["task_id"] == "workflow-test-123"
        
        # 6. 模拟文档解析结果
        parsing_result = [{
            "text": "Chemical document content with formulas and structures.",
            "formulas": ["H2O", "CO2", "CH4"],
            "structures": ["molecular_structure_1.png"],
            "confidence": 0.92
        }]
        
        # 7. 更新任务状态和结果
        update_success = await task_manager.update_task_status(
            "workflow-test-123", "completed", parsing_result
        )
        assert update_success is True
        
        # 8. 验证最终状态
        final_status = await task_manager.get_task_status("workflow-test-123")
        assert final_status == "completed"
        
        # 9. 获取解析结果
        final_result = await task_manager.get_task_result("workflow-test-123")
        assert final_result == parsing_result
        
        # 10. 验证S3中的文件仍然可访问
        downloaded_content = await s3_client.download_file_by_filename("chemical_doc.pdf")
        assert downloaded_content == test_content

# 环境检查装饰器
def requires_redis(func):
    """需要Redis服务的装饰器"""
    print(os.getenv("REDIS_URL"))
    return pytest.mark.skipif(
        not os.getenv("REDIS_URL") and not os.getenv("REDIS_ENABLED", "false").lower() == "true",
        reason="需要Redis服务"
    )(func)

def requires_s3(func):
    """需要S3服务的装饰器"""
    return pytest.mark.skipif(
        not os.getenv("S3_ENDPOINT") and not os.getenv("S3_ENABLED", "false").lower() == "true",
        reason="需要S3服务"
    )(func)

# 应用装饰器
TestRedisIntegration.test_real_redis_connection = requires_redis(TestRedisIntegration.test_real_redis_connection)
TestRedisIntegration.test_real_task_lifecycle = requires_redis(TestRedisIntegration.test_real_task_lifecycle)
TestRedisIntegration.test_real_batch_operations = requires_redis(TestRedisIntegration.test_real_batch_operations)

TestS3Integration.test_real_s3_connection = requires_s3(TestS3Integration.test_real_s3_connection)
TestS3Integration.test_real_file_upload_download = requires_s3(TestS3Integration.test_real_file_upload_download)
TestS3Integration.test_real_batch_upload = requires_s3(TestS3Integration.test_real_batch_upload)
TestS3Integration.test_real_large_file = requires_s3(TestS3Integration.test_real_large_file)

TestFullSystemIntegration.test_document_processing_workflow = requires_redis(TestFullSystemIntegration.test_document_processing_workflow)