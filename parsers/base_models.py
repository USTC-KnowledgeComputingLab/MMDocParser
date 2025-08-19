import logging
from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ChunkType(str, Enum):
    """块类型"""
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    FORMULA = "formula"

class ChunkData(BaseModel):
    """块数据类"""
    type: ChunkType
    name: str
    content: str = ""
    description: str = ""

class DocumentData(BaseModel):
    """解析结果类"""
    title: str = ""
    chunks: list[ChunkData] = []
    processing_time: float = 0
    success: bool
    error_message: str | None = None

class DocumentParser(ABC):
    """文档解析器基类"""

    def __init__(self) -> None:
        self.supported_formats: list[str] = []

    @abstractmethod
    async def parse(self, file_path: str) -> DocumentData:
        """解析文档"""
        pass

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """检查是否可以解析该文件"""
        pass
