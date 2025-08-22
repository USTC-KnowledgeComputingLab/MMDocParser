"""
PDF文档解析器模块

该模块提供使用Mineru库解析PDF文档并提取结构化内容的功能。
支持标题、段落、列表、表格和图片的识别与输出。
"""

import asyncio
import base64
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import aiofiles  # type: ignore
from bs4 import BeautifulSoup
from loguru import logger
from mineru.backend.pipeline.model_json_to_middle_json import (  # type: ignore
    result_to_middle_json as pipeline_result_to_middle_json,
)
from mineru.backend.pipeline.pipeline_analyze import (  # type: ignore
    doc_analyze as pipeline_doc_analyze,
)
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import (  # type: ignore
    union_make as pipeline_union_make,
)
from mineru.cli.common import prepare_env, read_fn  # type: ignore
from mineru.data.data_reader_writer import FileBasedDataWriter  # type: ignore
from mineru.utils.enum_class import MakeMode  # type: ignore

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


@register_parser(['.pdf'])
class PdfDocumentParser(DocumentParser):
    """PDF文档解析器

    使用Mineru的现代解析管道提取PDF文档的结构化内容。
    支持异步解析接口，符合DocumentParser抽象基类。
    """

    def __init__(self) -> None:
        """初始化解析器"""
        super().__init__()
        self.output_dir = Path(__file__).parent.parent / "output"
        self.lang = "ch"
        self.parse_method = "auto"
        self.formula_enable = True
        self.table_enable = True

    async def parse(self, file_path: Path) -> DocumentData:
        start_time = time.time()
        try:
            # 执行同步转换（在异步中运行）
            pdf_file_name = file_path.stem
            local_image_dir, _ = prepare_env(self.output_dir, pdf_file_name, self.parse_method)
            loop = asyncio.get_event_loop()
            content_list = await loop.run_in_executor(
                None,
                self._parse_pdf_to_content_list,
                file_path, local_image_dir, self.lang, self.parse_method, self.formula_enable, self.table_enable
            )

            # 执行并行处理
            document_data = await self._process_content_parallel(file_path, content_list)

            shutil.rmtree(local_image_dir, ignore_errors=True)
            processing_time = time.time() - start_time
            document_data.processing_time = processing_time
            logger.info(f"Successfully parsed DOCX: {file_path} (took {processing_time:.2f}s)")
            return document_data

        except Exception as e:
            raise Exception(f"Failed to parse PDF file {file_path}: {type(e).__name__}: {e}") from e

    async def _process_content_parallel(self, file_path: Path, content_list: list[dict[str, Any]]) -> DocumentData:
        # 创建任务列表
        title = file_path.stem
        texts_task = []
        tables_task = []
        images_task = []
        formulas_task = []

        for idx, item in enumerate(content_list):
            if item["type"] == "image":
                images_task.append(self._process_image(idx, item))
            elif item["type"] == "table":
                tables_task.append(self._process_table_async(idx, item))
            elif item["type"] == "equation":
                formulas_task.append(self._process_formula_async(idx, item))
            elif item["type"] == "text":
                if item.get("text_level") == 1:
                    title = item.get("text", "")
                    continue
                texts_task.append(self._process_text_async(idx, item))


        texts_chunks = [item for item in (await asyncio.gather(*texts_task) if texts_task else []) if item is not None]
        tables_chunks = [item for item in (await asyncio.gather(*tables_task) if tables_task else []) if item is not None]
        images_chunks = [item for item in (await asyncio.gather(*images_task) if images_task else []) if item is not None]
        formulas_chunks = [item for item in (await asyncio.gather(*formulas_task) if formulas_task else []) if item is not None]

        return DocumentData(
                title=title,
                texts=texts_chunks,
                tables=tables_chunks,
                images=images_chunks,
                formulas=formulas_chunks,
                success=True
            )

    def _parse_pdf_to_content_list(
        self,
        file_path: Path,
        local_image_dir: Path,
        lang: str = "ch",
        parse_method: str = "auto",
        formula_enable: bool = True,
        table_enable: bool = True,
    ) -> list[dict[str, Any]]:

        # 1. 读取 PDF bytes
        try:
            pdf_bytes = read_fn(file_path)
        except Exception as e:
            logger.error(f"Failed to read PDF file {file_path}: {e}")
            raise

        image_writer = FileBasedDataWriter(local_image_dir)

        # 4. 执行 pipeline 解析
        try:
            infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(
                [pdf_bytes], [lang], parse_method=parse_method,
                formula_enable=formula_enable, table_enable=table_enable
            )
            model_list = infer_results[0]
            images_list = all_image_lists[0]
            pdf_doc = all_pdf_docs[0]
            _lang = lang_list[0]
            _ocr_enable = ocr_enabled_list[0]
        except Exception as e:
            logger.error(f"Failed in pipeline_doc_analyze: {e}")
            raise

        # 5. 生成 middle_json
        try:
            middle_json = pipeline_result_to_middle_json(
                model_list, images_list, pdf_doc, image_writer, _lang, _ocr_enable, formula_enable
            )
            pdf_info = middle_json["pdf_info"]
        except Exception as e:
            logger.error(f"Failed in pipeline_result_to_middle_json: {e}")
            raise

        # 6. 生成 content_list（不写入文件）
        try:
            content_list = pipeline_union_make(pdf_info, MakeMode.CONTENT_LIST, str(local_image_dir))
        except Exception as e:
            logger.error(f"Failed in pipeline_union_make: {e}")
            raise
        return list(content_list)

    async def _process_image(self, idx:int,image:dict[str, Any]) -> ImageDataItem|None:
        if not image.get("img_path") or not os.path.exists(str(image.get("img_path"))):
            return None
        image_path = Path(str(image.get("img_path")))

        async with aiofiles.open(image_path, 'rb') as img_file:
            img_data = await img_file.read()

            base64_data = base64.b64encode(img_data).decode("utf-8")
            ext = os.path.splitext(image_path.name)[1].lower()
            mime_type = "image/jpeg"
            if ext == ".png":
                mime_type = "image/png"
            elif ext == ".gif":
                mime_type = "image/gif"

            return ImageDataItem(
                type=ChunkType.IMAGE,
                name=f"#/pictures/{idx}",
                uri=f"data:{mime_type};base64,{base64_data}",
                caption=image.get("img_caption", []),
                footnote=image.get("img_footnote", [])
            )


    async def _process_table_async(self, idx:int, table:dict[str, Any]) -> TableDataItem|None:
        """异步处理表格（在线程池中执行）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._process_table, idx, table)

    async def _process_formula_async(self, idx:int, formula:dict[str, Any]) -> FormulaDataItem|None:
        """异步处理公式（在线程池中执行）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._process_formula, idx, formula)

    async def _process_text_async(self, idx:int, text:dict[str, Any]) -> TextDataItem|None:
        """异步处理文本（在线程池中执行）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._process_text, idx, text)

    def _process_table(self, idx:int,table:dict[str, Any]) -> TableDataItem:
        """同步处理表格"""
        html_str = table.get("table_body", "")
        soup = BeautifulSoup(html_str, 'html.parser')
        table_body = soup.find('table')
        if not table_body:
            return TableDataItem(
                type=ChunkType.TABLE,
                name=f"#/tables/{idx}",
                rows=0,
                columns=0)
        # 使用网格处理 rowspan 和 colspan
        grid: list[list[str]] = []
        max_col = 0

        for row_idx, tr in enumerate(table_body.find_all('tr')): # type: ignore
            while len(grid) <= row_idx:
                grid.append([])
            current_row: list[str] = grid[row_idx]
            col_idx = 0

            # 跳过被 rowspan 占据的位置
            while col_idx < len(current_row) and current_row[col_idx] is not None:
                col_idx += 1

            for cell in tr.find_all(['td', 'th']):
                text = ''.join(cell.stripped_strings)
                text = re.sub(r'\s+', ' ', text).strip()
                if not text:
                    text = ""

                rowspan = int(cell.get('rowspan', 1))
                colspan = int(cell.get('colspan', 1))

                # 找到下一个空位
                while col_idx < len(current_row) and current_row[col_idx] is not None:
                    col_idx += 1

                # 扩展行
                while len(current_row) < col_idx + colspan:
                    current_row.append("")

                # 填入内容
                for r in range(rowspan):
                    actual_row_idx = row_idx + r
                    while len(grid) <= actual_row_idx:
                        grid.append([])
                    actual_row = grid[actual_row_idx]
                    while len(actual_row) < col_idx + colspan:
                        actual_row.append("")
                    for c in range(colspan):
                        actual_row[col_idx + c] = text

                col_idx += colspan

            max_col = max(max_col, len(current_row))

        # 确保所有行长度一致
        for row in grid:
            while len(row) < max_col:
                row.append("")
        # 5. 创建并返回 TableDataItem 实例
        table_data = TableDataItem(
            rows=len(grid),
            columns=max_col,
            grid=grid,
            caption=table.get("table_caption", []),
            footnote=table.get("table_footnote", [])
        )
        return TableDataItem(
            type=ChunkType.TABLE,
            name=f"#/tables/{idx}",
            rows=table_data.rows,
            columns=table_data.columns,
            grid=table_data.grid,
            caption=table_data.caption,
            footnote=table_data.footnote
        )

    def _process_formula(self, idx:int,formula:dict[str, Any]) -> FormulaDataItem:
        """同步处理公式"""
        return FormulaDataItem(
            type=ChunkType.FORMULA,
            name=f"#/formulas/{idx}",
            text=str(formula.get("text")),
            text_format=formula.get("text_format")
        )

    def _process_text(self, idx:int,text:dict[str, Any]) -> TextDataItem:
        """同步处理文本"""
        return TextDataItem(
            type=ChunkType.TEXT,
            name=f"#/texts/{idx}",
            text=str(text.get("text")),
            text_level=int(text.get("text_level", 0))
        )
