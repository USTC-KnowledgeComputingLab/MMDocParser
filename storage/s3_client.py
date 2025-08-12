# storage/s3_client.py
import asyncio
import aiohttp
import hashlib
import os
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class S3Error(Exception):
    """S3操作异常"""
    pass

class AsyncS3Client:
    """异步S3客户端 - 核心功能版本"""
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, 
                 bucket: str, region: str):
        self.endpoint_url = endpoint_url.rstrip('/')
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region
        self.session = None
        
        # 验证配置
        if not all([endpoint_url, access_key, secret_key, bucket]):
            raise ValueError("所有S3配置参数都是必需的")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'MMDocParser-S3Client/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def upload_file(self, filename: str, content: bytes) -> str:
        """上传文件到S3"""
        try:
            if not self.session:
                raise S3Error("客户端未初始化，请使用异步上下文管理器")
            
            # 生成文件key
            file_hash = hashlib.md5(content).hexdigest()
            file_key = f"documents/{file_hash[:8]}/{filename}"
            
            # 构建上传URL
            upload_url = f"{self.endpoint_url}/{self.bucket}/{file_key}"
            
            # 上传文件
            response = await self.session.put(upload_url, data=content)
            if response.status not in [200, 201]:
                error_text = await response.text()
                raise S3Error(f"上传失败: {response.status} - {error_text}")
            
            # 生成访问URL
            access_url = f"{self.endpoint_url}/{self.bucket}/{file_key}"
            
            logger.info(f"文件 {filename} 已上传到 {access_url}")
            return access_url
            
        except Exception as e:
            logger.error(f"上传文件 {filename} 失败: {e}")
            raise S3Error(f"上传文件失败: {e}")
    
    async def upload_files(self, files: List[Tuple[str, bytes]]) -> List[str]:
        """批量上传文件"""
        upload_tasks = [self.upload_file(filename, content) for filename, content in files]
        return await asyncio.gather(*upload_tasks, return_exceptions=True)
    
    async def download_file(self, file_url: str) -> bytes:
        """从S3下载文件"""
        try:
            if not self.session:
                raise S3Error("客户端未初始化，请使用异步上下文管理器")
            
            response = await self.session.get(file_url)
            if response.status == 200:
                content = await response.read()
                logger.info(f"文件下载成功: {file_url}, 大小: {len(content)} bytes")
                return content
            else:
                error_text = await response.text()
                raise S3Error(f"下载失败: {response.status} - {error_text}")
                
        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            raise S3Error(f"下载文件失败: {e}")
    
    def _get_content_type(self, filename: str) -> str:
        """根据文件扩展名获取内容类型"""
        ext = os.path.splitext(filename)[1].lower()
        
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.txt': 'text/plain',
        }
        
        return content_types.get(ext, 'application/octet-stream')