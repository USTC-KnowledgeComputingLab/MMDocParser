"""
PDF解析器测试模块

测试PdfDocumentParser的parse函数的各种场景
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from parsers.pdf_parser import PdfDocumentParser
from parsers.base_models import ChunkType


class TestPdfDocumentParserParse:
    """测试PdfDocumentParser的parse函数"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return PdfDocumentParser()

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

    @pytest.mark.asyncio
    async def test_parse_success(self, parser, mock_content_list):
        """测试成功解析PDF文件"""
        file_path = Path("/path/to/test.pdf")
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content_list
            # 使用 mock_open 模拟图片文件的读取
            with patch('builtins.open', mock_open(read_data=b'test_image_content')):
                result = await parser.parse(file_path)
                
                # 验证返回结果
                assert result.success is True
                assert result.title == "文档标题"
                assert result.processing_time > 0
                assert result.error_message is None
                
                # 验证内容数量
                assert len(result.texts) == 1  # 标题 + 内容
                assert len(result.tables) == 1
                assert len(result.images) == 1

    @pytest.mark.asyncio
    async def test_parse_error_handling(self, parser):
        """测试PDF解析错误处理"""
        file_path = Path("/path/to/invalid.pdf")
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.side_effect = Exception("PDF解析失败")
            
            result = await parser.parse(file_path)
            
            assert result.success is False
            assert result.error_message == "PDF解析失败"
            assert result.processing_time > 0

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
            # 模拟不同格式的图片文件
            with patch('builtins.open', mock_open(read_data=b'fake_jpeg_data')):
                result = await parser.parse(file_path)
                
                assert result.success is True
                assert len(result.images) == 1
                
                # 验证图片内容
                image = result.images[0]
                assert image.type == ChunkType.IMAGE
                assert "data:image/jpeg;base64," in image.content.uri
                assert image.content.caption == ["测试图片"]

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
            
            result = await parser.parse(file_path)
            
            assert result.success is True
            assert len(result.tables) == 1
            
            # 验证表格内容
            table = result.tables[0]
            assert table.type == ChunkType.TABLE
            assert table.content.rows == 2  # 标题行 + 数据行
            assert table.content.columns == 2
            assert table.content.caption == ["测试表格"]
