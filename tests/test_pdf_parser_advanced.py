"""
PDF解析器高级测试模块

展示不同的mock技术来测试PDF解析器
"""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from pathlib import Path
import base64

from parsers.pdf_parser import PdfDocumentParser
from parsers.base_models import ChunkType


class TestPdfParserAdvancedMocking:
    """测试PDF解析器的高级mock技术"""

    @pytest.fixture
    def parser(self):
        return PdfDocumentParser()

    def test_mock_open_basic(self):
        """基本的mock_open使用"""
        # 方法1: 简单的mock_open
        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            with open('/fake/path/image.jpg', 'rb') as f:
                data = f.read()
                assert data == b'fake_image_data'

    def test_mock_open_with_context_manager(self):
        """使用上下文管理器的mock_open"""
        # 方法2: 模拟文件对象的方法
        mock_file = Mock()
        mock_file.read.return_value = b'fake_image_data'
        mock_file.__enter__.return_value = mock_file
        mock_file.__exit__.return_value = None
        
        with patch('builtins.open', return_value=mock_file):
            with open('/fake/path/image.jpg', 'rb') as f:
                data = f.read()
                assert data == b'fake_image_data'

    def test_mock_open_with_side_effect(self):
        """使用side_effect的mock_open"""
        # 方法3: 根据文件路径返回不同内容
        def mock_open_side_effect(path, mode='r'):
            if 'image1.jpg' in str(path):
                return mock_open(read_data=b'image1_data')()
            elif 'image2.png' in str(path):
                return mock_open(read_data=b'image2_data')()
            else:
                return mock_open(read_data=b'default_data')()
        
        with patch('builtins.open', side_effect=mock_open_side_effect):
            # 测试不同文件
            with open('/path/to/image1.jpg', 'rb') as f:
                assert f.read() == b'image1_data'
            
            with open('/path/to/image2.png', 'rb') as f:
                assert f.read() == b'image2_data'

    @pytest.mark.asyncio
    async def test_parse_with_custom_mock_open(self, parser):
        """使用自定义mock_open测试解析器"""
        file_path = Path("/path/to/test.pdf")
        
        # 创建自定义的mock_open
        def custom_mock_open(path, mode='r'):
            mock_file = Mock()
            if mode == 'rb':
                # 根据文件路径返回不同的模拟数据
                if 'image.jpg' in str(path):
                    mock_file.read.return_value = b'fake_jpeg_data'
                elif 'image.png' in str(path):
                    mock_file.read.return_value = b'fake_png_data'
                else:
                    mock_file.read.return_value = b'default_data'
            else:
                mock_file.read.return_value = 'text_data'
            
            mock_file.__enter__.return_value = mock_file
            mock_file.__exit__.return_value = None
            return mock_file
        
        mock_content = [
            {
                "type": "image",
                "img_path": "/path/to/image.jpg",
                "img_caption": ["JPEG图片"],
                "img_footnote": []
            },
            {
                "type": "image",
                "img_path": "/path/to/image.png",
                "img_caption": ["PNG图片"],
                "img_footnote": []
            }
        ]
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content
            with patch('builtins.open', side_effect=custom_mock_open):
                result = await parser.parse(file_path)
                
                assert result.success is True
                assert len(result.images) == 2
                
                # 验证图片内容
                for img in result.images:
                    assert img.type == ChunkType.IMAGE
                    assert "data:image/" in img.content.uri

    @pytest.mark.asyncio
    async def test_parse_with_magic_mock(self, parser):
        """使用MagicMock测试解析器"""
        file_path = Path("/path/to/test.pdf")
        
        # 使用MagicMock自动创建方法
        mock_file = MagicMock()
        mock_file.read.return_value = b'magic_mock_data'
        
        mock_content = [
            {
                "type": "image",
                "img_path": "/path/to/image.jpg",
                "img_caption": ["MagicMock图片"],
                "img_footnote": []
            }
        ]
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content
            with patch('builtins.open', return_value=mock_file):
                result = await parser.parse(file_path)
                
                assert result.success is True
                assert len(result.images) == 1

    def test_mock_open_with_file_operations(self):
        """测试文件操作的mock"""
        # 模拟文件的不同操作
        mock_file = Mock()
        mock_file.read.side_effect = [b'first_read', b'second_read', b'third_read']
        mock_file.seek.return_value = None
        mock_file.tell.return_value = 0
        mock_file.__enter__.return_value = mock_file
        mock_file.__exit__.return_value = None
        
        with patch('builtins.open', return_value=mock_file):
            with open('/fake/path/file.txt', 'rb') as f:
                # 测试多次读取
                assert f.read() == b'first_read'
                assert f.read() == b'second_read'
                assert f.read() == b'third_read'
                
                # 测试其他方法
                f.seek(0)
                f.tell()
                
                # 验证调用
                assert mock_file.read.call_count == 3
                mock_file.seek.assert_called_with(0)

    @pytest.mark.asyncio
    async def test_parse_with_error_simulation(self, parser):
        """测试错误情况的模拟"""
        file_path = Path("/path/to/error.pdf")
        
        # 模拟文件读取错误
        def mock_open_error(path, mode='r'):
            if mode == 'rb':
                raise IOError("文件读取失败")
            return mock_open(read_data='text')()
        
        mock_content = [
            {
                "type": "image",
                "img_path": "/path/to/image.jpg",
                "img_caption": ["错误图片"],
                "img_footnote": []
            }
        ]
        
        with patch.object(parser, '_parse_pdf_to_content_list') as mock_parse:
            mock_parse.return_value = mock_content
            with patch('builtins.open', side_effect=mock_open_error):
                # 这里应该会抛出异常，因为图片处理失败
                with pytest.raises(IOError):
                    await parser.parse(file_path)


# 实用的mock工具函数
class MockFileHelper:
    """文件mock辅助类"""
    
    @staticmethod
    def create_mock_image_file(image_data: bytes, mime_type: str = 'image/jpeg'):
        """创建模拟的图片文件"""
        mock_file = Mock()
        mock_file.read.return_value = image_data
        mock_file.__enter__.return_value = mock_file
        mock_file.__exit__.return_value = None
        return mock_file
    
    @staticmethod
    def create_mock_text_file(text_data: str):
        """创建模拟的文本文件"""
        mock_file = Mock()
        mock_file.read.return_value = text_data.encode('utf-8')
        mock_file.__enter__.return_value = mock_file
        mock_file.__exit__.return_value = None
        return mock_file
    
    @staticmethod
    def patch_file_operations(file_path: str, mock_file):
        """patch文件操作"""
        return patch(f'builtins.open', return_value=mock_file)
