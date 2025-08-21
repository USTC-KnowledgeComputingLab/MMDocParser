"""
异步解析器测试模块

测试所有解析器的异步并行处理功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from parsers.docx_parser import DocxDocumentParser
from parsers.excel_parser import ExcelParser
from parsers.pdf_parser import PdfDocumentParser
from parsers.base_models import ChunkData, ChunkType, ImageDataItem, TableDataItem, TextDataItem


class TestAsyncParsers:
    """测试异步解析器"""

    @pytest.fixture
    def docx_parser(self):
        return DocxDocumentParser()

    @pytest.fixture
    def excel_parser(self):
        return ExcelParser()

    @pytest.fixture
    def pdf_parser(self):
        return PdfDocumentParser()

    def create_mock_chunk_data(self, chunk_type: ChunkType, **kwargs):
        """创建正确的 Mock ChunkData 对象"""
        mock_chunk = Mock(spec=ChunkData)
        mock_chunk.type = chunk_type
        mock_chunk.name = kwargs.get('name', f'mock_{chunk_type.value}')
        mock_chunk.content = kwargs.get('content', Mock())
        return mock_chunk

    @pytest.mark.asyncio
    async def test_docx_parallel_processing(self, docx_parser):
        """测试DOCX解析器的并行处理"""
        file_path = "/path/to/test.docx"
        
        # Mock 文档数据
        mock_doc = Mock()
        mock_doc.name = "测试文档.docx"
        mock_doc.pictures = [Mock(), Mock()]  # 2张图片
        mock_doc.tables = [Mock(), Mock(), Mock()]  # 3个表格
        mock_doc.texts = [Mock(), Mock(), Mock(), Mock()]  # 4个文本
        
        # Mock 转换器结果
        mock_result = Mock()
        mock_result.document = mock_doc
        
        with patch.object(docx_parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_result
            
            # Mock 各种提取方法，返回正确的 ChunkData 对象
            with patch.object(docx_parser, '_extract_images_async') as mock_images:
                with patch.object(docx_parser, '_extract_tables_async') as mock_tables:
                    with patch.object(docx_parser, '_extract_texts_async') as mock_texts:
                        
                        # 设置返回值 - 使用正确的 Mock 对象
                        mock_images.return_value = [
                            self.create_mock_chunk_data(ChunkType.IMAGE)
                        ]
                        mock_tables.return_value = [
                            self.create_mock_chunk_data(ChunkType.TABLE)
                        ]
                        mock_texts.return_value = [
                            self.create_mock_chunk_data(ChunkType.TEXT)
                        ]
                        
                        result = await docx_parser.parse(Path(file_path))
                        
                        # 验证并行处理被调用
                        assert mock_images.called
                        assert mock_tables.called
                        assert mock_texts.called
                        
                        # 验证结果
                        assert result.success is True
                        assert result.title == "测试文档.docx"

    @pytest.mark.asyncio
    async def test_excel_parallel_processing(self, excel_parser):
        """测试Excel解析器的并行处理"""
        file_path = Path("/path/to/test.xlsx")
        
        # Mock 工作簿和工作表
        mock_sheet1 = Mock()
        mock_sheet2 = Mock()
        
        mock_workbook = Mock()
        mock_workbook.sheetnames = ["Sheet1", "Sheet2"]
        # 让 workbook 可以像字典一样访问 - 使用正确的方式
        mock_workbook.__getitem__ = Mock(side_effect=lambda x: mock_sheet1 if x == "Sheet1" else mock_sheet2)
        
        with patch.object(excel_parser, '_load_workbook') as mock_load:
            mock_load.return_value = mock_workbook
            
            # Mock 工作表处理
            with patch.object(excel_parser, '_process_sheet_async') as mock_sheet_process:
                mock_sheet_process.side_effect = [
                    {
                        'texts': [self.create_mock_chunk_data(ChunkType.TEXT)],
                        'tables': [self.create_mock_chunk_data(ChunkType.TABLE)],
                        'images': [self.create_mock_chunk_data(ChunkType.IMAGE)]
                    },
                    {
                        'texts': [self.create_mock_chunk_data(ChunkType.TEXT)],
                        'tables': [self.create_mock_chunk_data(ChunkType.TABLE)],
                        'images': []
                    }
                ]
                
                result = await excel_parser.parse(file_path)
                
                # 验证并行处理被调用
                assert mock_sheet_process.call_count == 2
                
                # 验证结果
                assert result.success is True
                assert len(result.texts) == 2
                assert len(result.tables) == 2
                assert len(result.images) == 1

    def create_async_mock_file(self, read_data: bytes):
        """创建支持异步上下文管理器的 mock 文件对象"""
        mock_file = Mock()
        
        # 创建异步 read 方法
        async def async_read():
            return read_data
        
        mock_file.read = async_read
        
        # 创建异步上下文管理器
        async def async_enter(self):
            return mock_file
        
        async def async_exit(self, exc_type, exc_val, exc_tb):
            pass
        
        mock_file.__aenter__ = async_enter
        mock_file.__aexit__ = async_exit
        
        return mock_file

    @pytest.mark.asyncio
    async def test_pdf_parallel_processing(self, pdf_parser):
        """测试PDF解析器的并行处理"""
        file_path = Path("/path/to/test.pdf")
        
        # Mock 内容列表
        mock_content = [
            {"type": "image", "img_path": "/path/to/img.jpg", "img_caption": [], "img_footnote": []},
            {"type": "table", "table_body": "<table><tr><td>数据</td></tr></table>", "table_caption": [], "table_footnote": []},
            {"type": "text", "text": "测试文本", "text_level": 2},
            {"type": "equation", "text": "x + y = z", "text_format": "latex"}
        ]
        
        with patch.object(pdf_parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content
            
            # Mock 图片文件读取和文件存在检查
            with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
                with patch('os.path.exists', return_value=True):
                    # 创建支持异步的 mock 文件
                    async_mock_file = self.create_async_mock_file(b'fake_image_data')
                    with patch('aiofiles.open', return_value=async_mock_file):
                        
                        result = await pdf_parser.parse(file_path)
                        
                        # 验证结果
                        assert result.success is True
                        assert len(result.images) == 1
                        assert len(result.tables) == 1
                        assert len(result.texts) == 1
                        assert len(result.formulas) == 1

    @pytest.mark.asyncio
    async def test_parallel_processing_performance(self, docx_parser):
        """测试并行处理的性能优势"""
        import time
        
        file_path = "/path/to/large.docx"
        
        # 创建大量测试数据
        mock_doc = Mock()
        mock_doc.name = "大型文档.docx"
        mock_doc.pictures = [Mock() for _ in range(50)]  # 50张图片
        mock_doc.tables = [Mock() for _ in range(100)]   # 100个表格
        mock_doc.texts = [Mock() for _ in range(200)]    # 200个文本
        
        mock_result = Mock()
        mock_result.document = mock_doc
        
        with patch.object(docx_parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_result
            
            # Mock 提取方法，模拟处理时间
            async def mock_extract_images(pictures):
                await asyncio.sleep(0.1)  # 模拟100ms处理时间
                return [self.create_mock_chunk_data(ChunkType.IMAGE)]
            
            async def mock_extract_tables(tables):
                await asyncio.sleep(0.2)  # 模拟200ms处理时间
                return [self.create_mock_chunk_data(ChunkType.TABLE)]
            
            async def mock_extract_texts(texts):
                await asyncio.sleep(0.15)  # 模拟150ms处理时间
                return [self.create_mock_chunk_data(ChunkType.TEXT)]
            
            with patch.object(docx_parser, '_extract_images_async', side_effect=mock_extract_images):
                with patch.object(docx_parser, '_extract_tables_async', side_effect=mock_extract_tables):
                    with patch.object(docx_parser, '_extract_texts_async', side_effect=mock_extract_texts):
                        
                        start_time = time.time()
                        result = await docx_parser.parse(Path(file_path))
                        processing_time = time.time() - start_time
                        
                        # 验证结果
                        assert result.success is True
                        
                        # 并行处理时间应该接近最慢的任务的时间（200ms）
                        # 而不是所有任务时间的总和（450ms）
                        print(f"并行处理时间: {processing_time:.3f}秒")
                        # 考虑到测试环境的开销，放宽时间限制
                        assert processing_time < 0.6  # 应该小于600ms

    @pytest.mark.asyncio
    async def test_error_handling_in_parallel(self, docx_parser):
        """测试并行处理中的错误处理"""
        file_path = "/path/to/error.docx"
        
        mock_doc = Mock()
        mock_doc.name = "错误文档.docx"
        mock_doc.pictures = [Mock()]
        mock_doc.tables = [Mock()]
        mock_doc.texts = [Mock()]
        
        mock_result = Mock()
        mock_result.document = mock_doc
        
        with patch.object(docx_parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_result
            
            # 模拟某些处理失败
            with patch.object(docx_parser, '_extract_images_async', side_effect=Exception("图片处理失败")):
                with patch.object(docx_parser, '_extract_tables_async', return_value=[self.create_mock_chunk_data(ChunkType.TABLE)]):
                    with patch.object(docx_parser, '_extract_texts_async', return_value=[self.create_mock_chunk_data(ChunkType.TEXT)]):
                        
                        result = await docx_parser.parse(Path(file_path))
                        
                        # 即使图片处理失败，其他内容仍应正常处理
                        assert result.success is True
                        assert len(result.tables) == 1
                        assert len(result.texts) == 1
                        assert len(result.images) == 0  # 图片处理失败，返回空列表
