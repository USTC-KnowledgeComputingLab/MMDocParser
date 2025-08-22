# Parsers package

from .base_models import (
    ChunkType,
    DocumentData,
    DocumentParser,
    FormulaDataItem,
    ImageDataItem,
    TableDataItem,
    TextDataItem,
)
from .parser_registry import (
    PARSER_REGISTRY,
    get_parser,
    get_supported_formats,
    list_registered_parsers,
    register_parser,
)

__all__ = [
    'ChunkType',
    'DocumentData',
    'DocumentParser',
    'TableDataItem',
    'TextDataItem',
    'ImageDataItem',
    'FormulaDataItem',
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
