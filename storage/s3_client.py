import urllib.parse
from contextlib import AsyncExitStack
from datetime import timedelta
from io import BytesIO
from typing import Any, Protocol, Self, runtime_checkable

from aiobotocore.session import AioSession  # type: ignore


# ruff: noqa: N803
@runtime_checkable
class S3ClientProtocol(Protocol):
    async def put_object(
        self,
        *,
        Bucket: str | None,
        Key: str,
        Body: BytesIO,
        ContentType: str
    ) -> dict[str, Any]: ...

    async def get_object(
        self,
        *,
        Bucket: str | None,
        Key: str
    ) -> dict[str, Any]: ...

    async def generate_presigned_url(
        self,
        ClientMethod: str,
        Params: dict[str, str | None],
        ExpiresIn: int
    ) -> str: ...


class S3ClientNotInitializedError(Exception):
    """Raised when the S3 client is used before being initialized."""
    def __init__(self) -> None:
        super().__init__("S3 client not initialized")


class S3Error(Exception):
    """S3操作异常"""
    pass

class AsyncS3Client:
    def __init__(self,
                 endpoint_url: str | None,
                 access_key: str | None,
                 secret_key: str | None,
                 bucket: str | None,
                 region: str = "us-east-1") -> None:
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region
        self._stack = AsyncExitStack()
        self._client: S3ClientProtocol | None = None

    async def __aenter__(self) -> Self:
        session = AioSession()
        self._client = await self._stack.enter_async_context(
            session.create_client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._stack.aclose()

    def _encode_filename(self, filename: str) -> str:
        """对文件名进行URL编码，确保S3 key的安全性"""
        return urllib.parse.quote(filename, safe='')

    async def upload_file(self, filename: str, content: bytes) -> str:
        """上传文件，使用编码后的文件名作为key"""
        if self._client is None:
            raise S3ClientNotInitializedError

        # 对文件名进行编码
        encoded_key = self._encode_filename(filename)

        await self._client.put_object(
            Bucket=self.bucket,
            Key=encoded_key,
            Body=BytesIO(content),
            ContentType="application/octet-stream"
        )
        return await self.generate_presigned_url(encoded_key)

    async def download_file(self, key: str) -> Any:
        """下载文件内容"""
        if self._client is None:
            raise S3ClientNotInitializedError

        response = await self._client.get_object(
            Bucket=self.bucket,
            Key=key
        )

        # 读取文件内容
        async with response['Body'] as stream:
            content = await stream.read()

        return content

    async def download_file_by_filename(self, filename: str) -> Any:
        """通过原始文件名下载文件"""
        encoded_key = self._encode_filename(filename)
        return await self.download_file(encoded_key)

    async def generate_presigned_url(self, key: str, expires_days: int = 7) -> str:
        if self._client is None:
            raise S3ClientNotInitializedError
        return await self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=int(timedelta(days=expires_days).total_seconds())
        )
