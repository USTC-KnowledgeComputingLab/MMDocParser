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

            # 并行处理不同类型的内容
            document_data = await self._process_content_parallel(doc_data)

            processing_time = time.time() - start_time
            document_data.processing_time = processing_time
            logger.info(f"Successfully parsed DOCX: {file_path} (took {processing_time:.2f}s)")
            return document_data

        except Exception as e:
            raise Exception(f"Failed to parse DOCX file {file_path}") from e

    async def _process_content_parallel(self, doc_data: DoclingDocument) -> DocumentData:
        """并行处理文档内容"""
        # 创建任务列表
        tasks_images = []
        tasks_tables = []
        tasks_texts = []

        # 添加图片处理任务
        if doc_data.pictures:
            tasks_images.append(self._extract_images_async(doc_data.pictures))
        images_results = await asyncio.gather(*tasks_images) if tasks_images else []
        images = images_results[0] if images_results else []

        # 添加表格处理任务
        if doc_data.tables:
            tasks_tables.append(self._extract_tables_async(doc_data.tables))
        tables_results = await asyncio.gather(*tasks_tables) if tasks_tables else []
        tables = tables_results[0] if tables_results else []

        # 添加文本处理任务
        if doc_data.texts:
            tasks_texts.append(self._extract_texts_async(doc_data.texts))
        texts_and_formulas_results = await asyncio.gather(*tasks_texts) if tasks_texts else []
        texts_and_formulas = texts_and_formulas_results[0] if texts_and_formulas_results else ([], [])
        texts, formulas = texts_and_formulas

        # 提取标题
        title = self._extract_title(doc_data)

        return DocumentData(
            title=title,
            texts=texts,
            tables=tables,
            images=images,
            formulas=formulas,
            success=True
        )

    def _extract_images(self, pictures: list[PictureItem]) -> list[ImageDataItem]:
        """提取文档中的图片

        Args:
            pictures: 图片列表

        Returns:
            List[ImageDataItem]: 图片列表
        """
        image_items: list[ImageDataItem] = []
        for idx, picture in enumerate(pictures):
            if not picture.image:
                continue
            image_uri = str(picture.image.uri)
            caption = [caption.cref for caption in picture.captions]
            footnote = [footnote.cref for footnote in picture.footnotes]
            image_items.append(
                ImageDataItem(
                    type=ChunkType.IMAGE,
                    name=f"image-{idx}",
                    uri=image_uri,
                    caption=caption,
                    footnote=footnote
                )
            )

        return image_items

    def _extract_tables(self, tables: list[TableItem]) -> list[TableDataItem]:
        """提取文档中的表格

        Args:
            tables: 表格列表

        Returns:
            List[ChunkData]: 表格列表
        """
        table_items: list[TableDataItem] = []
        for table in tables:
            caption = [caption.cref for caption in table.captions]
            footnote = [footnote.cref for footnote in table.footnotes]
            grid = [[cell.text if cell.text else '' for cell in row] for row in table.data.grid]
            table_items.append(
                TableDataItem(
                    type=ChunkType.TABLE,
                    name=f"#/tables/{len(table_items)}",
                    rows=table.data.num_rows,
                    columns=table.data.num_cols,
                    grid=grid,
                    caption=caption,
                    footnote=footnote
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

    def _extract_texts(self, texts:list[TitleItem|SectionHeaderItem|ListItem|CodeItem|FormulaItem|TextItem]) -> tuple[list[TextDataItem], list[FormulaDataItem]]:
        """提取文档中的文本

        Args:
            text: 文本列表

        Returns:
            List[ChunkData]: 文本列表
        """
        text_items: list[TextDataItem] = []
        formula_items: list[FormulaDataItem] = []

        for item in texts:
            if not hasattr(item, 'label'):
                continue
            if not hasattr(item, 'text') or len(item.text) == 0:
                continue
            match item.label:
                case DocItemLabel.FORMULA:
                    formula_items.append(
                        FormulaDataItem(
                            type=ChunkType.FORMULA,
                            name=f"formula-{len(formula_items)}",
                            text=item.text
                        )
                    )
                case DocItemLabel.TITLE:
                    continue
                case _:
                    text_items.append(
                        TextDataItem(
                            type=ChunkType.TEXT,
                            name=f"text-{len(text_items)}",
                            text=item.text
                        )
                    )
        return text_items, formula_items

    async def _extract_images_async(self, pictures: list[PictureItem]) -> list[ImageDataItem]:
        """异步提取文档中的图片"""
        loop = asyncio.get_event_loop() 
        return await loop.run_in_executor(None, self._extract_images, pictures)

    async def _extract_tables_async(self, tables: list[TableItem]) -> list[TableDataItem]:
        """异步提取文档中的表格"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract_tables, tables)

    async def _extract_texts_async(self, texts: list[TitleItem|SectionHeaderItem|ListItem|CodeItem|FormulaItem|TextItem]) -> tuple[list[TextDataItem], list[FormulaDataItem]]:
        """异步提取文档中的文本"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract_texts, texts)
