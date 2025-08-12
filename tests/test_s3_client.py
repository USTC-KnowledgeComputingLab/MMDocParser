# tests/test_s3_client.py
import pytest
from unittest.mock import patch, AsyncMock
from storage.s3_client import AsyncS3Client, S3Error

pytestmark = pytest.mark.asyncio

class TestAsyncS3Client:
    """S3客户端核心功能测试"""
    
    @pytest.fixture
    async def s3_client(self):
        """创建S3客户端实例"""
        client = AsyncS3Client(
            endpoint_url="http://localhost:9000",
            access_key="test_key",
            secret_key="test_secret",
            bucket="test_bucket",
            region="us-east-1"
        )
        return client
    
    async def test_init_validation(self):
        """测试初始化参数验证"""
        # 测试缺少参数
        with pytest.raises(ValueError, match="所有S3配置参数都是必需的"):
            AsyncS3Client("", "key", "secret", "bucket", "region")
        
        with pytest.raises(ValueError, match="所有S3配置参数都是必需的"):
            AsyncS3Client("endpoint", "", "secret", "bucket", "region")
    
    async def test_context_manager(self, s3_client):
        """测试异步上下文管理器"""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with s3_client as client:
                assert client.session is not None
                assert client.session == mock_session
            
            # 验证会话被关闭
            mock_session.close.assert_called_once()
    
    async def test_upload_file_success(self, s3_client):
        """测试文件上传成功"""
        # 创建模拟会话
        mock_session = AsyncMock()
        s3_client.session = mock_session
        
        # 创建模拟响应
        mock_response = AsyncMock()
        mock_response.status = 200
        
        # 直接模拟 put 方法返回响应对象
        mock_session.put = AsyncMock(return_value=mock_response)
        
        filename = "test.pdf"
        content = b"PDF content"
        
        result = await s3_client.upload_file(filename, content)
        
        # 验证结果
        assert "test_bucket" in result
        assert filename in result
        assert "documents" in result
        
        # 验证调用
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args
        assert "test_bucket" in call_args[0][0]  # URL包含bucket
    
    async def test_upload_file_failure(self, s3_client):
        """测试文件上传失败"""
        # 创建模拟会话
        mock_session = AsyncMock()
        s3_client.session = mock_session
        
        # 创建模拟响应
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        # 直接模拟 put 方法返回响应对象
        mock_session.put = AsyncMock(return_value=mock_response)
        
        filename = "test.pdf"
        content = b"PDF content"
        
        with pytest.raises(S3Error, match="上传失败: 500"):
            await s3_client.upload_file(filename, content)
    
    async def test_upload_files_success(self, s3_client):
        """测试批量文件上传成功"""
        # 创建模拟会话
        mock_session = AsyncMock()
        s3_client.session = mock_session
        
        # 创建模拟响应
        mock_response = AsyncMock()
        mock_response.status = 200
        
        # 直接模拟 put 方法返回响应对象
        mock_session.put = AsyncMock(return_value=mock_response)
        
        files = [
            ("doc1.pdf", b"PDF content 1"),
            ("doc2.docx", b"DOCX content 2")
        ]
        
        results = await s3_client.upload_files(files)
        
        # 验证结果
        assert len(results) == 2
        assert all("test_bucket" in result for result in results)
        assert all("documents" in result for result in results)
        
        # 验证调用次数
        assert mock_session.put.call_count == 2
    
    async def test_upload_files_with_errors(self, s3_client):
        """测试批量上传包含错误"""
        # 创建模拟会话
        mock_session = AsyncMock()
        s3_client.session = mock_session
        
        # 第一个文件成功，第二个文件失败
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        
        mock_response_failure = AsyncMock()
        mock_response_failure.status = 500
        mock_response_failure.text = AsyncMock(return_value="Error")
        
        # 设置 side_effect 来返回不同的响应
        mock_session.put = AsyncMock(side_effect=[
            mock_response_success, 
            mock_response_failure
        ])
        
        files = [
            ("doc1.pdf", b"PDF content 1"),
            ("doc2.docx", b"DOCX content 2")
        ]
        
        results = await s3_client.upload_files(files)
        
        # 验证结果包含异常
        assert len(results) == 2
        assert isinstance(results[0], str)  # 第一个成功
        assert isinstance(results[1], Exception)  # 第二个失败
    
    async def test_download_file_success(self, s3_client):
        """测试文件下载成功"""
        # 创建模拟会话
        mock_session = AsyncMock()
        s3_client.session = mock_session
        
        # 创建模拟响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"file content")
        
        # 直接模拟 get 方法返回响应对象
        mock_session.get = AsyncMock(return_value=mock_response)
        
        file_url = "http://localhost:9000/test_bucket/documents/test.pdf"
        
        result = await s3_client.download_file(file_url)
        
        # 验证结果
        assert result == b"file content"
        
        # 验证调用
        mock_session.get.assert_called_once_with(file_url)
    
    async def test_download_file_failure(self, s3_client):
        """测试文件下载失败"""
        # 创建模拟会话
        mock_session = AsyncMock()
        s3_client.session = mock_session
        
        # 创建模拟响应
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="File not found")
        
        # 直接模拟 get 方法返回响应对象
        mock_session.get = AsyncMock(return_value=mock_response)
        
        file_url = "http://localhost:9000/test_bucket/documents/notfound.pdf"
        
        with pytest.raises(S3Error, match="下载失败: 404"):
            await s3_client.download_file(file_url)
    
    def test_get_content_type(self, s3_client):
        """测试内容类型识别"""
        # 测试PDF文件
        assert s3_client._get_content_type("document.pdf") == "application/pdf"
        
        # 测试DOCX文件
        assert s3_client._get_content_type("document.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        # 测试图片文件
        assert s3_client._get_content_type("image.jpg") == "image/jpeg"
        assert s3_client._get_content_type("image.png") == "image/png"
        
        # 测试未知扩展名
        assert s3_client._get_content_type("unknown.xyz") == "application/octet-stream"
        
        # 测试无扩展名
        assert s3_client._get_content_type("filename") == "application/octet-stream"