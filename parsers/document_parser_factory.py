import logging

from parsers.document_parser import DocumentParser, ParseResult
from parsers.excel_parser import ExcelParser

logger = logging.getLogger(__name__)

class DocumentParserFactory:
    """文档解析器工厂"""

    def __init__(self) -> None:
        self.parsers: list[DocumentParser] = [
            ExcelParser()
        ]

    def get_parser(self, file_path: str) -> DocumentParser | None:
        """根据文件路径获取合适的解析器"""
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        return None

    async def parse_document(self, file_path: str) -> ParseResult:
        """解析文档"""
        parser = self.get_parser(file_path)
        if not parser:
            raise ValueError(f"不支持的文件格式: {file_path}")

        return await parser.parse(file_path)
