"""
解析器注册器模块

提供基于装饰器的解析器自动注册机制，支持多种文件格式的解析器注册和查找。
"""

import logging
from collections.abc import Callable
from pathlib import Path

from .base_models import DocumentParser

logger = logging.getLogger(__name__)

# 全局解析器注册表
PARSER_REGISTRY: dict[str, type[DocumentParser]] = {}


def register_parser(suffixes: list[str]) -> Callable[[type[DocumentParser]], type[DocumentParser]]:
    """
    解析器注册装饰器

    Args:
        suffixes: 支持的文件扩展名列表，如 ['.docx', '.doc']

    Returns:
        装饰器函数

    Example:
        @register_parser(['.docx'])
        class DocxDocumentParser(DocumentParser):
            ...
    """
    def decorator(cls: type[DocumentParser]) -> type[DocumentParser]:
        # 验证类是否继承自 DocumentParser
        if not issubclass(cls, DocumentParser):
            raise TypeError(f"解析器类 {cls.__name__} 必须继承自 DocumentParser")

        # 注册到全局注册表
        for suffix in suffixes:
            suffix = suffix.lower()  # 统一转换为小写
            if suffix in PARSER_REGISTRY:
                logger.warning(f"覆盖已存在的解析器: {suffix} -> {cls.__name__}")
            PARSER_REGISTRY[suffix] = cls
            logger.info(f"注册解析器: {suffix} -> {cls.__name__}")

        return cls

    return decorator


def get_parser(file_path: str) -> DocumentParser | None:
    """
    根据文件路径获取合适的解析器实例

    Args:
        file_path: 文件路径

    Returns:
        解析器实例，如果没有找到则返回 None
    """
    file = Path(file_path)
    suffix = file.suffix.lower()

    if suffix not in PARSER_REGISTRY:
        logger.warning(f"未找到支持 {suffix} 格式的解析器")
        return None

    parser_class = PARSER_REGISTRY[suffix]
    try:
        return parser_class()
    except Exception as e:
        logger.error(f"创建解析器实例失败: {parser_class.__name__}, 错误: {e}")
        return None

def get_supported_formats() -> list[str]:
    """
    获取所有支持的文件格式

    Returns:
        支持的文件扩展名列表
    """
    return list(PARSER_REGISTRY.keys())


def get_parser_class(suffix: str) -> type[DocumentParser] | None:
    """
    根据文件扩展名获取解析器类

    Args:
        suffix: 文件扩展名，如 '.docx'

    Returns:
        解析器类，如果没有找到则返回 None
    """
    return PARSER_REGISTRY.get(suffix.lower())


def list_registered_parsers() -> dict[str, str]:
    """
    列出所有已注册的解析器

    Returns:
        扩展名到解析器类名的映射字典
    """
    return {suffix: cls.__name__ for suffix, cls in PARSER_REGISTRY.items()}
