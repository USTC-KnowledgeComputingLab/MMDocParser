"""
DOCX文档解析器模块

该模块提供使用Docling库解析DOCX文档并提取结构化内容的功能。
支持标题、段落、列表、表格和图片的识别与输出。
"""

import asyncio
import logging
import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, WordFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from docling_core.types.doc.document import (
    CodeItem,
    DocItemLabel,
    DoclingDocument,
    FormulaItem,
    ListItem,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)

from parsers.base_models import (
    ChunkData,
    ChunkType,
    DocumentData,
    DocumentParser,
    FormulaDataItem,
    ImageDataItem,
    TableDataItem,
    TextDataItem,
)
from parsers.parser_registry import register_parser

logger = logging.getLogger(__name__)


@register_parser(['.docx'])
class DocxDocumentParser(DocumentParser):
    """DOCX文档解析器

    使用Docling的现代解析管道提取DOCX文档的结构化内容。
    支持异步解析接口，符合DocumentParser抽象基类。
    """

    def __init__(self) -> None:
        """初始化解析器"""
        super().__init__()
        self._converter = DocumentConverter(
            format_options={InputFormat.DOCX: WordFormatOption(pipeline_cls=SimplePipeline)},
            allowed_formats=[InputFormat.DOCX]
        )
        logger.debug("DocxDocumentParser initialized with SimplePipeline")

    async def parse(self, file_path: Path) -> DocumentData:
        """异步解析DOCX文件

        Args:
            file_path: DOCX文件路径

        Returns:
            DocumentData: 解析结果，包含标题、内容、处理时间和错误信息
        """
        start_time = time.time()
        try:
            # 执行同步转换（在异步中运行）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._converter.convert, file_path)
            doc_data = result.document

            title = self._extract_title(doc_data)
            images = self._extract_images(doc_data.pictures)
            tables = self._extract_tables(doc_data.tables)
            texts = self._extract_texts(doc_data.texts)

            processing_time = time.time() - start_time
            logger.info(f"Successfully parsed DOCX: {file_path} (took {processing_time:.2f}s)")
            return DocumentData(
                title=title,
                texts=texts,
                tables=tables,
                images=images,
                processing_time=processing_time,
                success=True
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to parse DOCX file {file_path}: {type(e).__name__}: {e}"
            logger.exception(error_msg)  # 记录完整堆栈
            return DocumentData(
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )

    def _extract_images(self, pictures: list[PictureItem]) -> list[ChunkData]:
        """提取文档中的图片

        Args:
            pictures: 图片列表

        Returns:
            List[ChunkData]: 图片列表
        """
        image_items: list[ChunkData] = []
        for idx, picture in enumerate(pictures):
            if not picture.image:
                continue
            image_uri = str(picture.image.uri)
            caption = [caption.cref for caption in picture.captions]
            footnote = [footnote.cref for footnote in picture.footnotes]
            image_items.append(
                ChunkData(
                    type=ChunkType.IMAGE,
                    name=f"#/pictures/{idx}",
                    content=ImageDataItem(
                        uri=image_uri,
                        caption=caption,
                        footnote=footnote
                    )
                )
            )

        return image_items

    def _extract_tables(self, tables: list[TableItem]) -> list[ChunkData]:
        """提取文档中的表格

        Args:
            tables: 表格列表

        Returns:
            List[ChunkData]: 表格列表
        """
        table_items: list[ChunkData] = []
        for table in tables:
            caption = [caption.cref for caption in table.captions]
            footnote = [footnote.cref for footnote in table.footnotes]
            grid = [[cell.text if cell.text else '' for cell in row] for row in table.data.grid]
            table_data = TableDataItem(
                rows=table.data.num_rows,
                columns=table.data.num_cols,
                grid=grid,
                caption=caption,
                footnote=footnote
            )
            table_items.append(
                ChunkData(
                    type=ChunkType.TABLE,
                    name=f"#/tables/{len(table_items)}",
                    content=table_data
                )
            )

        return table_items

    def _extract_title(self, doc_data: DoclingDocument) -> str:
        """提取文档中的标题
        Args:
            doc_data: 文档数据
        Returns:
            str: 标题
        """
        title = ""
        for item in doc_data.texts:
            if hasattr(item, 'label') and item.label == DocItemLabel.TITLE:
                title = item.text
                break
        return title if title else doc_data.name

    def _extract_texts(self, texts:list[TitleItem|SectionHeaderItem|ListItem|CodeItem|FormulaItem|TextItem]) -> list[ChunkData]:
        """提取文档中的文本

        Args:
            text: 文本列表

        Returns:
            List[ChunkData]: 文本列表
        """
        text_items: list[ChunkData] = []

        for item in texts:
            if not hasattr(item, 'label'):
                continue
            if not hasattr(item, 'text') or len(item.text) == 0:
                continue
            match item.label:
                case DocItemLabel.FORMULA:
                    text_items.append(
                        ChunkData(
                            type=ChunkType.FORMULA,
                            name=f"formula-{len(text_items)}",
                            content=FormulaDataItem(
                                text=item.text
                            )
                        )
                    )
                case _:
                    text_items.append(
                        ChunkData(
                            type=ChunkType.TEXT,
                            name=f"#/texts/{len(text_items)}",
                            content=TextDataItem(
                                text=item.text
                            )
                        )
                    )
        return text_items
