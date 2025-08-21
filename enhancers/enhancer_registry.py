"""
解析器注册器模块

提供基于装饰器的解析器自动注册机制，支持多种文件格式的解析器注册和查找。
"""

import logging
from collections.abc import Callable

from enhancers.base_models import InformationEnhancer
from parsers.base_models import ChunkType

logger = logging.getLogger(__name__)

# 全局解析器注册表
ENHANCER_REGISTRY: dict[str, type[InformationEnhancer]] = {}


def register_enhancer(modalities: list[str]) -> Callable[[type[InformationEnhancer]], type[InformationEnhancer]]:
    """
    信息增强器注册装饰器

    Args:
        modalities: 支持的模态类型列表，如 [ChunkType.TEXT, ChunkType.IMAGE, ChunkType.TABLE]

    Returns:
        装饰器函数

    Example:
        @register_enhancer([ChunkType.TEXT, ChunkType.IMAGE, ChunkType.TABLE])
        class TextInformationEnhancer(InformationEnhancer):
            ...
    """
    def decorator(cls: type[InformationEnhancer]) -> type[InformationEnhancer]:
        # 验证类是否继承自 InformationEnhancer
        if not issubclass(cls, InformationEnhancer):
            raise TypeError(f"信息增强器类 {cls.__name__} 必须继承自 InformationEnhancer")

        # 注册到全局注册表
        for modality in modalities:
            modality = modality.lower()  # 统一转换为小写
            if modality in ENHANCER_REGISTRY:
                logger.warning(f"覆盖已存在的信息增强器: {modality} -> {cls.__name__}")
            ENHANCER_REGISTRY[modality] = cls
            logger.info(f"注册信息增强器: {modality} -> {cls.__name__}")

        return cls

    return decorator


def get_enhancer(modality: ChunkType) -> InformationEnhancer | None:
    """
    根据模态类型获取合适的信息增强器实例

    Args:
        modality: 模态类型

    Returns:
        信息增强器实例，如果没有找到则返回 None
    """
    modality_type = modality.value.lower()

    if modality_type not in ENHANCER_REGISTRY:
        logger.warning(f"未找到支持 {modality} 格式的信息增强器")
        return None

    enhancer_class = ENHANCER_REGISTRY[modality_type]
    try:
        return enhancer_class()
    except Exception as e:
        logger.error(f"创建信息增强器实例失败: {enhancer_class.__name__}, 错误: {e}")
        return None

def get_supported_modalities() -> list[str]:
    """
    获取所有支持的模态类型

    Returns:
        支持的模态类型列表
    """
    return list(ENHANCER_REGISTRY.keys())


def get_enhancer_class(modality: ChunkType) -> type[InformationEnhancer] | None:
    """
    根据模态类型获取信息增强器类

    Args:
        modality: 模态类型

    Returns:
        信息增强器类，如果没有找到则返回 None
    """
    return ENHANCER_REGISTRY.get(modality.value.lower())


def list_registered_enhancers() -> dict[str, str]:
    """
    列出所有已注册的信息增强器

    Returns:
        模态类型到信息增强器类名的映射字典
    """
    return {modality: cls.__name__ for modality, cls in ENHANCER_REGISTRY.items()}
