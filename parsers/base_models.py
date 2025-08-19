import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ChunkType(str, Enum):
    """块类型"""
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    FORMULA = "formula"

class TableDataItem(BaseModel):
    """表格数据类"""
    rows: int  # 行数
    columns: int  # 列数
    row_headers: list[Any] = Field(default_factory=list)  # 行头
    column_headers: list[Any] = Field(default_factory=list)  # 列头
    data: list[list[str]] = Field(default_factory=list)  # 数据

class ChunkData(BaseModel):
    """块数据类"""
    type: ChunkType
    name: str
    content: str|TableDataItem = ""
    description: str = ""

class DocumentData(BaseModel):
    """解析结果类"""
    title: str = ""
    texts: list[ChunkData] = Field(default_factory=list)
    tables: list[ChunkData] = Field(default_factory=list)
    images: list[ChunkData] = Field(default_factory=list)
    formulas: list[ChunkData] = Field(default_factory=list)
    processing_time: float = 0
    success: bool
    error_message: str | None = None

class DocumentParser(ABC):
    """文档解析器基类"""

    def __init__(self) -> None:
        self.supported_formats: list[str] = Field(default_factory=list)

    @abstractmethod
    async def parse(self, file_path: str) -> DocumentData:
        """解析文档"""
        pass

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """检查是否可以解析该文件"""
        return any(file_path.lower().endswith(fmt) for fmt in self.supported_formats)
