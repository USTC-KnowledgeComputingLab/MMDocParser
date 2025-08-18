import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DocumentData(BaseModel):
    """文档数据类"""
    type: str
    name: str
    content: str
    description: str

class ParseResult(BaseModel):
    """解析结果类"""
    title: str
    document: list[DocumentData]
    processing_time: float
    success: bool
    error_message: str | None = None

class DocumentParser(ABC):
    """文档解析器基类"""

    def __init__(self) -> None:
        self.supported_formats: list[str] = []

    @abstractmethod
    async def parse(self, file_path: str) -> ParseResult:
        """解析文档"""
        pass

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """检查是否可以解析该文件"""
        pass
