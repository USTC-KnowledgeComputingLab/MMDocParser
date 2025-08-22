"""
PDF解析器测试模块

测试PdfDocumentParser的parse函数的各种场景
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from parsers.pdf_parser import PdfDocumentParser
from parsers.base_models import ChunkType


class TestPdfDocumentParserParse:
    """测试PdfDocumentParser的parse函数"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        parser = PdfDocumentParser()
        # 设置一个存在的输出目录
        parser.output_dir = Path("/tmp/pdf_test_output")
        return parser

    @pytest.fixture
    def mock_content_list(self):
        """模拟内容列表"""
        return [
            {
                "type": "text",
                "text": "文档标题",
                "text_level": 1
            },
            {
                "type": "text",
                "text": "文档内容",
                "text_level": 0
            },
            {
                "type": "table",
                "table_body": "<table><tr><td>姓名</td><td>年龄</td></tr></table>",
                "table_caption": ["人员信息表"],
                "table_footnote": []
            },
            {
                "type": "image",
                "img_path": "/path/to/image.jpg",
                "img_caption": ["示例图片"],
                "img_footnote": ["示例图片注脚"]
            }
        ]

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
    async def test_parse_success(self, parser, mock_content_list):
        """测试成功解析PDF文件"""
        file_path = Path("/path/to/test.pdf")
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content_list
            # 模拟 prepare_env 函数
            with patch('parsers.pdf_parser.prepare_env') as mock_prepare_env:
                mock_prepare_env.return_value = (Path("/tmp/test_images"), "auto")
                # 使用异步 mock 模拟图片文件的读取
                async_mock_file = self.create_async_mock_file(b'test_image_content')
                with patch('aiofiles.open', return_value=async_mock_file):
                    with patch('os.path.exists', return_value=True):
                        result = await parser.parse(file_path)
                    
                    # 验证返回结果
                    assert result.success is True
                    assert result.title == "文档标题"
                    assert result.processing_time > 0
                    assert result.error_message is None
                    
                    # 验证内容数量
                    assert len(result.texts) == 1  # 只有 text_level != 1 的文本会被处理
                    assert len(result.tables) == 1
                    assert len(result.images) == 1

    @pytest.mark.asyncio
    async def test_parse_error_handling(self, parser):
        """测试PDF解析错误处理"""
        file_path = Path("/path/to/invalid.pdf")
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.side_effect = Exception("解析失败")
            with pytest.raises(Exception, match="解析失败"):
                await parser.parse(Path(file_path))

    @pytest.mark.asyncio
    async def test_parse_empty_document(self, parser):
        """测试空PDF文档解析"""
        file_path = Path("/path/to/empty.pdf")
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = []
            
            result = await parser.parse(file_path)
            
            assert result.success is True
            assert result.title == "empty"
            assert len(result.texts) == 0
            assert len(result.tables) == 0
            assert len(result.images) == 0

    @pytest.mark.asyncio
    async def test_parse_with_image_processing(self, parser):
        """测试图片处理功能"""
        file_path = Path("/path/to/image.pdf")
        
        mock_content = [
            {
                "type": "image",
                "img_path": "/path/to/test_image.jpg",
                "img_caption": ["测试图片"],
                "img_footnote": []
            }
        ]
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content
            # 模拟 prepare_env 函数
            with patch('parsers.pdf_parser.prepare_env') as mock_prepare_env:
                mock_prepare_env.return_value = (Path("/tmp/test_images"), "auto")
                # 使用异步 mock 模拟图片文件，并确保文件路径存在
                async_mock_file = self.create_async_mock_file(b'fake_jpeg_data')
                with patch('aiofiles.open', return_value=async_mock_file):
                    with patch('os.path.exists', return_value=True):
                        result = await parser.parse(Path(file_path))
                    
                    assert result.success is True
                    assert len(result.images) == 1
                    
                    # 验证图片内容
                    image = result.images[0]
                    assert image.type == ChunkType.IMAGE
                    assert "data:image/jpeg;base64," in image.uri
                    assert image.caption == ["测试图片"]

    @pytest.mark.asyncio
    async def test_parse_with_table_processing(self, parser):
        """测试表格处理功能"""
        file_path = Path("/path/to/table.pdf")
        
        mock_content = [
            {
                "type": "table",
                "table_body": "<table><tr><th>列1</th><th>列2</th></tr><tr><td>数据1</td><td>数据2</td></tr></table>",
                "table_caption": ["测试表格"],
                "table_footnote": []
            }
        ]
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content
            
            result = await parser.parse(Path(file_path))
            
            assert result.success is True
            assert len(result.tables) == 1
            
            # 验证表格内容
            table = result.tables[0]
            assert table.type == ChunkType.TABLE
            assert table.rows == 2  # 标题行 + 数据行
            assert table.columns == 2
            assert table.caption == ["测试表格"]

    @pytest.mark.asyncio
    async def test_parse_with_formula_processing(self, parser):
        """测试公式处理功能"""
        file_path = Path("/path/to/formula.pdf")
        
        mock_content = [
            {
                "type": "equation",
                "text": "E = mc²",
                "text_format": "latex"
            }
        ]
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content
            
            result = await parser.parse(Path(file_path))
            
            assert result.success is True
            assert len(result.formulas) == 1
            
            # 验证公式内容
            formula = result.formulas[0]
            assert formula.type == ChunkType.FORMULA
            assert formula.text == "E = mc²"
            assert formula.text_format == "latex"

    @pytest.mark.asyncio
    async def test_parse_with_mixed_content(self, parser):
        """测试混合内容处理功能"""
        file_path = Path("/path/to/mixed.pdf")
        
        mock_content = [
            {"type": "text", "text": "标题", "text_level": 1},
            {"type": "image", "img_path": "/path/to/img.jpg", "img_caption": [], "img_footnote": []},
            {"type": "table", "table_body": "<table><tr><td>数据</td></tr></table>", "table_caption": [], "table_footnote": []},
            {"type": "equation", "text": "x + y = z", "text_format": "latex"}
        ]
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content
            # 模拟 prepare_env 函数
            with patch('parsers.pdf_parser.prepare_env') as mock_prepare_env:
                mock_prepare_env.return_value = (Path("/tmp/test_images"), "auto")
                # 使用异步 mock 模拟图片文件，并确保文件路径存在
                async_mock_file = self.create_async_mock_file(b'mixed_content_image')
                with patch('aiofiles.open', return_value=async_mock_file):
                    with patch('os.path.exists', return_value=True):
                        result = await parser.parse(Path(file_path))
                    
                    assert result.success is True
                    assert len(result.texts) == 0  # text_level=1 的文本被用作标题，不进入 texts 列表
                    assert len(result.images) == 1
                    assert len(result.tables) == 1
                    assert len(result.formulas) == 1
