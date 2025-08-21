# Parsers package

from .base_models import ChunkData, ChunkType, DocumentData, DocumentParser
from .parser_registry import (
    PARSER_REGISTRY,
    get_parser,
    get_supported_formats,
    list_registered_parsers,
    register_parser,
)

__all__ = [
    'DocumentData',
    'DocumentParser',
    'ChunkData',
    'ChunkType',
    'PARSER_REGISTRY',
    'register_parser',
    'get_parser',
    'get_supported_formats',
    'list_registered_parsers',
    'load_all_parsers',
]

def load_all_parsers() -> list[str]:
    """加载所有解析器"""
    from .docx_parser import DocxDocumentParser
    from .excel_parser import ExcelParser
    return [DocxDocumentParser.__name__, ExcelParser.__name__]
