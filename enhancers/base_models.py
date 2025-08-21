from abc import ABC, abstractmethod

from parsers.base_models import ChunkData


class InformationEnhancer(ABC):
    """信息增强器基类"""
    @abstractmethod
    async def enhance(self, information: ChunkData) -> ChunkData:
        """增强信息"""
        pass

class TableInformationEnhancer(InformationEnhancer):
    """表格信息增强器"""

    async def enhance(self, information: ChunkData) -> ChunkData:
        """增强信息"""
        return information

class FormulasInformationEnhancer(InformationEnhancer):
    """公式信息增强器"""

    async def enhance(self, information: ChunkData) -> ChunkData:
        """增强信息"""
        return information

class ImageInformationEnhancer(InformationEnhancer):
    """图片信息增强器"""

    async def enhance(self, information: ChunkData) -> ChunkData:
        """增强信息"""
        return information
