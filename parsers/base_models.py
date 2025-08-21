import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ChunkType(str, Enum):
    """块类型"""
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    FORMULA = "formula"

class DataItem(BaseModel):
    """数据项基类"""
    type: str|None = None  # 数据项类型
    name: str|None = None  # 数据项名称

class TableDataItem(DataItem):
    """表格数据类"""
    rows: int  # 行数
    columns: int  # 列数
    grid: list[list[str]] = Field(default_factory=list)  # 网格数据
    row_headers: list[Any] = Field(default_factory=list)  # 行头
    column_headers: list[Any] = Field(default_factory=list)  # 列头
    data: list[list[str]] = Field(default_factory=list)  # 数据
    caption: list[str] = Field(default_factory=list)  # 表格标题
    footnote: list[str] = Field(default_factory=list)  # 表格注脚
    description: str|None = None  # 表格描述

class TextDataItem(DataItem):
    """文本数据类"""
    text: str  # 文本
    text_level: int|None = None  # 文本级别

class ImageDataItem(DataItem):
    """图片数据类"""
    uri: str|None = None  # 图片 URI
    caption: list[str] = Field(default_factory=list)  # 图片标题
    footnote: list[str] = Field(default_factory=list)  # 图片注脚
    description: str|None = None  # 图片描述

class FormulaDataItem(DataItem):
    """公式数据类"""
    text: str  # 公式
    text_format: str|None = None  # 公式格式
    description: str|None = None  # 公式描述

class DocumentData(BaseModel):
    """解析结果类"""
    title: str|None = None
    texts: list[TextDataItem] = Field(default_factory=list)
    tables: list[TableDataItem] = Field(default_factory=list)
    images: list[ImageDataItem] = Field(default_factory=list)
    formulas: list[FormulaDataItem] = Field(default_factory=list)
    processing_time: float = 0
    success: bool = False
    error_message: str | None = None

class DocumentParser(ABC):
    """文档解析器基类"""

    @abstractmethod
    async def parse(self, file_path: Path) -> DocumentData:
        """解析文档"""
        pass
