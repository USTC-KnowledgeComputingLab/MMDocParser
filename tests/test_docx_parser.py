"""
DOCX解析器测试模块

测试DocxDocumentParser的parse函数的各种场景
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from parsers.docx_parser import DocxDocumentParser
from parsers.base_models import DocumentData, ChunkData, ChunkType, TableDataItem


class TestDocxDocumentParserParse:
    """测试DocxDocumentParser的parse函数"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return DocxDocumentParser()

    @pytest.fixture
    def mock_doc_data(self):
        """模拟文档数据"""
        mock_doc = Mock()
        mock_doc.name = "测试文档.docx"
        
        # 模拟图片数据
        mock_picture = Mock()
        mock_picture.image.uri = "/path/to/image.jpg"
        mock_picture.captions = [Mock(cref="图片说明")]
        mock_picture.footnotes = []
        mock_doc.pictures = [mock_picture]
        
        # 模拟表格数据
        mock_table = Mock()
        mock_table.captions = [Mock(cref="表格标题")]
        mock_table.footnotes = []
        mock_table.data.num_rows = 2
        mock_table.data.num_cols = 3
        mock_table.data.grid = [
            [Mock(text="列1", row_header=False, column_header=True),
             Mock(text="列2", row_header=False, column_header=True),
             Mock(text="列3", row_header=False, column_header=True)],
            [Mock(text="数据1", row_header=False, column_header=False),
             Mock(text="数据2", row_header=False, column_header=False),
             Mock(text="数据3", row_header=False, column_header=False)]
        ]
        mock_doc.tables = [mock_table]
        
        # 模拟文本数据
        mock_title = Mock()
        mock_title.text = "文档标题"
        mock_title.label = "title"
        
        mock_text = Mock()
        mock_text.text = "这是正文内容"
        mock_text.label = "text"
        
        mock_formula = Mock()
        mock_formula.text = "E = mc²"
        mock_formula.label = "formula"
        
        mock_doc.texts = [mock_title, mock_text, mock_formula]
        
        return mock_doc

    @pytest.fixture
    def mock_converter_result(self, mock_doc_data):
        """模拟转换器结果"""
        mock_result = Mock()
        mock_result.document = mock_doc_data
        return mock_result

    @pytest.mark.asyncio
    async def test_parse_success(self, parser, mock_converter_result):
        """测试成功解析DOCX文件"""
        file_path = "/path/to/test.docx"
        
        with patch.object(parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_converter_result
            result = await parser.parse(file_path)
            
            # 验证返回结果
            assert result.success is True
            assert result.title == "文档标题"
            assert result.processing_time > 0
            assert result.error_message is None
            
            # 验证文本内容
            assert len(result.texts) == 3  # 标题不算在texts中
            assert result.texts[0].type == ChunkType.TEXT
            assert result.texts[0].content.text == "文档标题"
            assert result.texts[1].type == ChunkType.TEXT
            assert result.texts[1].content.text == "这是正文内容"
            assert result.texts[2].type == ChunkType.FORMULA
            assert result.texts[2].content.text == "E = mc²"
            
            # 验证表格
            assert len(result.tables) == 1
            assert result.tables[0].type == ChunkType.TABLE
            assert isinstance(result.tables[0].content, TableDataItem)
            assert result.tables[0].content.rows == 2
            assert result.tables[0].content.columns == 3
            
            # 验证图片
            assert len(result.images) == 1
            assert result.images[0].type == ChunkType.IMAGE
            assert result.images[0].content.uri == "/path/to/image.jpg"
            assert result.images[0].content.caption == ["图片说明"]
            assert result.images[0].content.footnote == []

    @pytest.mark.asyncio
    async def test_parse_without_title(self, parser):
        """测试没有标题的文档解析"""
        file_path = "/path/to/test.docx"
        
        # 创建没有标题的模拟数据
        mock_doc = Mock()
        mock_doc.name = "无标题文档.docx"
        mock_doc.pictures = []
        mock_doc.tables = []
        
        mock_text = Mock()
        mock_text.text = "只有正文内容"
        mock_text.label = "text"
        mock_doc.texts = [mock_text]
        
        mock_result = Mock()
        mock_result.document = mock_doc
        
        with patch.object(parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_result
            
            result = await parser.parse(file_path)
            
            # 验证使用文件名作为标题
            assert result.success is True
            assert result.title == "无标题文档.docx"
            assert len(result.texts) == 1
            assert len(result.tables) == 0
            assert len(result.images) == 0

    @pytest.mark.asyncio
    async def test_parse_empty_document(self, parser):
        """测试空文档解析"""
        file_path = "/path/to/empty.docx"
        
        mock_doc = Mock()
        mock_doc.name = "空文档.docx"
        mock_doc.pictures = []
        mock_doc.tables = []
        mock_doc.texts = []
        
        mock_result = Mock()
        mock_result.document = mock_doc
        
        with patch.object(parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_result
            
            result = await parser.parse(file_path)
            
            assert result.success is True
            assert result.title == "空文档.docx"
            assert len(result.texts) == 0
            assert len(result.tables) == 0
            assert len(result.images) == 0

    @pytest.mark.asyncio
    async def test_parse_converter_error(self, parser):
        """测试转换器错误处理"""
        file_path = "/path/to/invalid.docx"
        
        with patch.object(parser, '_converter') as mock_converter:
            mock_converter.convert.side_effect = Exception("转换失败")
            
            result = await parser.parse(file_path)
            
            assert result.success is False
            assert result.error_message == "转换失败"
            assert result.processing_time > 0
            assert result.title is None
            assert len(result.texts) == 0
            assert len(result.tables) == 0
            assert len(result.images) == 0

    @pytest.mark.asyncio
    async def test_parse_with_complex_table(self, parser):
        """测试复杂表格解析"""
        file_path = "/path/to/table.docx"
        
        mock_doc = Mock()
        mock_doc.name = "表格文档.docx"
        mock_doc.pictures = []
        mock_doc.texts = []
        
        # 创建复杂表格
        mock_table = Mock()
        mock_table.captions = [Mock(cref="复杂表格")]
        mock_table.footnotes = []
        mock_table.data.num_rows = 3
        mock_table.data.num_cols = 4
        
        # 第一行作为列头
        mock_table.data.grid = [
            [Mock(text="姓名", row_header=False, column_header=True),
             Mock(text="年龄", row_header=False, column_header=True),
             Mock(text="职业", row_header=False, column_header=True),
             Mock(text="薪资", row_header=False, column_header=True)],
            [Mock(text="张三", row_header=False, column_header=False),
             Mock(text="25", row_header=False, column_header=False),
             Mock(text="工程师", row_header=False, column_header=False),
             Mock(text="15000", row_header=False, column_header=False)],
            [Mock(text="李四", row_header=False, column_header=False),
             Mock(text="30", row_header=False, column_header=False),
             Mock(text="设计师", row_header=False, column_header=False),
             Mock(text="18000", row_header=False, column_header=False)]
        ]
        mock_doc.tables = [mock_table]
        
        mock_result = Mock()
        mock_result.document = mock_doc
        
        with patch.object(parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_result
        
            result = await parser.parse(file_path)
            
            assert result.success is True
            assert len(result.tables) == 1
            
            table = result.tables[0].content
            assert table.rows == 3
            assert table.columns == 4
            assert table.grid == [["姓名", "年龄", "职业", "薪资"], ["张三", "25", "工程师", "15000"], ["李四", "30", "设计师", "18000"]]
            assert table.caption == ["复杂表格"]
            assert table.footnote == []

    @pytest.mark.asyncio
    async def test_parse_with_multiple_images(self, parser):
        """测试多图片解析"""
        file_path = "/path/to/images.docx"
        
        mock_doc = Mock()
        mock_doc.name = "图片文档.docx"
        mock_doc.tables = []
        mock_doc.texts = []
        
        # 创建多个图片
        mock_pictures = []
        for i in range(3):
            mock_pic = Mock()
            mock_pic.image.uri = f"/path/to/image{i+1}.jpg"
            mock_pic.captions = [Mock(cref=f"图片{i+1}说明")]
            mock_pic.footnotes = []
            mock_pictures.append(mock_pic)
        
        mock_doc.pictures = mock_pictures
        
        mock_result = Mock()
        mock_result.document = mock_doc
        
        with patch.object(parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_result
            
            result = await parser.parse(file_path)
            
            assert result.success is True
            assert len(result.images) == 3
            
            for i, img in enumerate(result.images):
                assert img.type == ChunkType.IMAGE
                assert img.content.uri == f"/path/to/image{i+1}.jpg"
                assert img.content.caption == [f"图片{i+1}说明"]
                assert img.content.footnote == []

    @pytest.mark.asyncio
    async def test_parse_with_section_headers(self, parser):
        """测试包含章节标题的文档解析"""
        file_path = "/path/to/sections.docx"
        
        mock_doc = Mock()
        mock_doc.name = "章节文档.docx"
        mock_doc.pictures = []
        mock_doc.tables = []
        
        # 创建章节标题
        mock_section = Mock()
        mock_section.text = "第一章 引言"   
        mock_section.label = "section_header"
        
        mock_doc.texts = [mock_section]
        
        mock_result = Mock()
        mock_result.document = mock_doc
        
        with patch.object(parser, '_converter') as mock_converter:
            mock_converter.convert.return_value = mock_result
            
            result = await parser.parse(file_path)
            
            assert result.success is True
            assert len(result.texts) == 1
            assert result.texts[0].type == ChunkType.TEXT
            assert result.texts[0].content.text == "第一章 引言"
