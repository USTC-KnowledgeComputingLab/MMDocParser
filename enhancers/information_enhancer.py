from abc import ABC, abstractmethod
from typing import Any

class InformationEnhancer(ABC):
    """信息增强器基类"""

    def __init__(self) -> None:
        pass

    @abstractmethod
    async def enhance(self, information: dict[str, Any]) -> dict[str, Any]:
        """增强信息"""
        pass

class TableInformationEnhancer(InformationEnhancer):
    """表格信息增强器"""

    def __init__(self) -> None:
        super().__init__()

    async def enhance(self, information: dict[str, Any]) -> dict[str, Any]:
        """增强信息"""
        return information

class FormulasInformationEnhancer(InformationEnhancer):
    """公式信息增强器"""

    def __init__(self) -> None:
        super().__init__()

    async def enhance(self, information: dict[str, Any]) -> dict[str, Any]:
        """增强信息"""
        return information

class ImageInformationEnhancer(InformationEnhancer):
    """图片信息增强器"""

    def __init__(self) -> None:
        super().__init__()

    async def enhance(self, information: dict[str, Any]) -> dict[str, Any]:
        """增强信息"""
        return information

class InformationEnhancerFactory:
    """信息增强器工厂"""

    def __init__(self) -> None:
        self.enhancers = [
            TableInformationEnhancer(),
            FormulasInformationEnhancer(),
            ImageInformationEnhancer()
        ]

    def get_enhancer(self, information: dict[str, Any]) -> InformationEnhancer:
        """获取信息增强器"""
        match information.get("type"):
            case "table":
                return TableInformationEnhancer()
            case "formulas":
                return FormulasInformationEnhancer()
            case "image":
                return ImageInformationEnhancer()
            case _:
                return None
    
    async def enhance_information(self, information: dict[str, Any]) -> dict[str, Any]:
        """增强信息"""
        enhancer = self.get_enhancer(information)
        if not enhancer:
            raise ValueError(f"不支持的模态类型: {information.get('type')}")
        return await enhancer.enhance(information)
        
