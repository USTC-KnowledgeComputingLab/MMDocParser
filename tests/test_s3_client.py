import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from io import BytesIO

from storage.s3_client import (
    AsyncS3Client,
    S3ClientNotInitializedError,
    S3ClientProtocol
)


class TestAsyncS3Client:
    """测试AsyncS3Client类的功能"""

    @pytest.fixture
    def s3_client(self):
        """创建S3客户端实例"""
        return AsyncS3Client(
            endpoint_url="http://localhost:9000",
            access_key="test_access_key",
            secret_key="test_secret_key",
            bucket="test_bucket",
            region="us-east-1"
        )

    @pytest.fixture
    def mock_s3_client(self):
        """创建模拟的S3客户端"""
        mock_client = AsyncMock(spec=S3ClientProtocol)
        mock_client.put_object = AsyncMock()
        mock_client.get_object = AsyncMock()
        mock_client.generate_presigned_url = AsyncMock(return_value="https://example.com/presigned_url")
        return mock_client

    @pytest.mark.asyncio
    async def test_init(self, s3_client):
        """测试初始化"""
        assert s3_client.endpoint_url == "http://localhost:9000"
        assert s3_client.access_key == "test_access_key"
        assert s3_client.secret_key == "test_secret_key"
        assert s3_client.bucket == "test_bucket"
        assert s3_client.region == "us-east-1"
        assert s3_client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self, s3_client):
        """测试异步上下文管理器"""
        with patch('storage.s3_client.AioSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            
            mock_client = AsyncMock()
            mock_session.create_client.return_value = mock_client
            
            async with s3_client as client:
                assert client is s3_client
                assert s3_client._client is not None
                mock_session.create_client.assert_called_once_with(
                    "s3",
                    endpoint_url="http://localhost:9000",
                    aws_access_key_id="test_access_key",
                    aws_secret_access_key="test_secret_key",
                    region_name="us-east-1",
                )

    def test_encode_filename(self, s3_client):
        """测试文件名编码功能"""
        # 测试普通文件名
        assert s3_client._encode_filename("test.txt") == "test.txt"
        
        # 测试包含空格的文件名
        assert s3_client._encode_filename("my file.txt") == "my%20file.txt"
        
        # 测试包含特殊字符的文件名
        assert s3_client._encode_filename("file with spaces & symbols!.pdf") == "file%20with%20spaces%20%26%20symbols%21.pdf"
        
        # 测试中文文件名
        assert s3_client._encode_filename("测试文件.txt") == "%E6%B5%8B%E8%AF%95%E6%96%87%E4%BB%B6.txt"
        
        # 测试包含路径分隔符的文件名
        assert s3_client._encode_filename("folder/subfolder/file.txt") == "folder%2Fsubfolder%2Ffile.txt"

    @pytest.mark.asyncio
    async def test_upload_file_success(self, s3_client, mock_s3_client):
        """测试成功上传文件"""
        s3_client._client = mock_s3_client
        content = b"test file content"
        
        result = await s3_client.upload_file("test file.txt", content)
        
        # 验证put_object被调用
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="test_bucket",
            Key="test%20file.txt",
            Body=ANY,  # 使用ANY忽略BytesIO对象的内存地址
            ContentType="application/octet-stream"
        )
        
        # 验证generate_presigned_url被调用（通过mock的客户端）
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test_bucket", "Key": "test%20file.txt"},
            ExpiresIn=604800  # 7天的秒数
        )
        
        assert result == "https://example.com/presigned_url"

    @pytest.mark.asyncio
    async def test_upload_file_not_initialized(self, s3_client):
        """测试未初始化的客户端上传文件"""
        with pytest.raises(S3ClientNotInitializedError):
            await s3_client.upload_file("test.txt", b"content")

    @pytest.mark.asyncio
    async def test_download_file_success(self, s3_client, mock_s3_client):
        """测试成功下载文件"""
        s3_client._client = mock_s3_client
        
        # 模拟响应对象
        mock_body = AsyncMock()
        mock_body.__aenter__ = AsyncMock(return_value=mock_body)
        mock_body.read = AsyncMock(return_value=b"downloaded content")
        mock_response = {
            'Body': mock_body
        }
        mock_s3_client.get_object.return_value = mock_response
        
        result = await s3_client.download_file("test%20file.txt")
        
        # 验证get_object被调用
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test_bucket",
            Key="test%20file.txt"
        )
        
        assert result == b"downloaded content"

    @pytest.mark.asyncio
    async def test_download_file_by_filename(self, s3_client, mock_s3_client):
        """测试通过文件名下载文件"""
        s3_client._client = mock_s3_client
        
        # 模拟响应对象
        mock_body = AsyncMock()
        mock_body.__aenter__ = AsyncMock(return_value=mock_body)
        mock_body.read = AsyncMock(return_value=b"downloaded content")
        mock_response = {
            'Body': mock_body
        }
        mock_s3_client.get_object.return_value = mock_response
        
        result = await s3_client.download_file_by_filename("test file.txt")
        
        # 验证get_object被调用，使用编码后的key
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test_bucket",
            Key="test%20file.txt"
        )
        
        assert result == b"downloaded content"

    @pytest.mark.asyncio
    async def test_download_file_not_initialized(self, s3_client):
        """测试未初始化的客户端下载文件"""
        with pytest.raises(S3ClientNotInitializedError):
            await s3_client.download_file("test.txt")
        
        with pytest.raises(S3ClientNotInitializedError):
            await s3_client.download_file_by_filename("test.txt")

    @pytest.mark.asyncio
    async def test_generate_presigned_url_success(self, s3_client, mock_s3_client):
        """测试成功生成预签名URL"""
        s3_client._client = mock_s3_client
        
        result = await s3_client.generate_presigned_url("test%20file.txt", expires_days=1)
        
        # 验证generate_presigned_url被调用
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test_bucket", "Key": "test%20file.txt"},
            ExpiresIn=86400  # 1天的秒数
        )
        
        assert result == "https://example.com/presigned_url"

    @pytest.mark.asyncio
    async def test_generate_presigned_url_not_initialized(self, s3_client):
        """测试未初始化的客户端生成预签名URL"""
        with pytest.raises(S3ClientNotInitializedError):
            await s3_client.generate_presigned_url("test.txt")

    @pytest.mark.asyncio
    async def test_generate_presigned_url_default_expires(self, s3_client, mock_s3_client):
        """测试默认过期时间的预签名URL"""
        s3_client._client = mock_s3_client
        
        await s3_client.generate_presigned_url("test.txt")
        
        # 验证默认7天过期时间
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test_bucket", "Key": "test.txt"},
            ExpiresIn=604800  # 7天的秒数
        )