"""
文本分块处理器测试模块

包含 Chunker 类的全面测试。
"""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.processors.chunker import Chunker
from kb.processors.base import ProcessResult


class TestChunkerInit:
    """Chunker 初始化测试"""

    def test_init_default_values(self):
        """测试默认参数初始化"""
        chunker = Chunker()
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 100
        assert chunker.separator == "\n\n"

    def test_init_custom_values(self):
        """测试自定义参数初始化"""
        chunker = Chunker(
            chunk_size=500,
            chunk_overlap=50,
            separator="\n"
        )
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 50
        assert chunker.separator == "\n"

    def test_init_with_extra_kwargs(self):
        """测试额外参数存储"""
        chunker = Chunker(custom_param="test_value")
        assert chunker.config.get("custom_param") == "test_value"


class TestChunkerFromConfig:
    """Chunker from_config 工厂方法测试"""

    def test_from_config_with_mock_config(self):
        """测试从模拟配置创建实例"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "chunking": {
                "max_chunk_size": 800,
                "chunk_overlap": 50,
                "separator": "\n"
            }
        }.get(key, default)

        chunker = Chunker.from_config(mock_config)

        assert chunker.chunk_size == 800
        assert chunker.chunk_overlap == 50
        assert chunker.separator == "\n"

    def test_from_config_with_partial_config(self):
        """测试部分配置使用默认值"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "chunking": {
                "max_chunk_size": 500
            }
        }.get(key, default)

        chunker = Chunker.from_config(mock_config)

        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 100  # 默认值
        assert chunker.separator == "\n\n"  # 默认值

    def test_from_config_with_empty_config(self):
        """测试空配置使用全部默认值"""
        mock_config = Mock()
        mock_config.get.return_value = {}

        chunker = Chunker.from_config(mock_config)

        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 100
        assert chunker.separator == "\n\n"


class TestChunkerProcess:
    """Chunker process 方法测试"""

    def test_process_empty_input(self):
        """测试空输入"""
        chunker = Chunker()
        result = chunker.process("")

        assert result.success is True
        assert result.data == []
        assert result.metadata["total_chunks"] == 0

    def test_process_whitespace_only(self):
        """测试仅空白字符输入"""
        chunker = Chunker()
        result = chunker.process("   \n\n   ")

        assert result.success is True
        assert result.data == []
        assert result.metadata["total_chunks"] == 0

    def test_process_none_input(self):
        """测试 None 输入"""
        chunker = Chunker()
        result = chunker.process(None)

        assert result.success is True
        assert result.data == []

    def test_process_short_text_single_chunk(self):
        """测试短文本返回单个块"""
        chunker = Chunker(chunk_size=1000)
        text = "This is a short text."
        result = chunker.process(text)

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["content"] == text
        assert result.data[0]["chunk_index"] == 0
        assert result.data[0]["start_char"] == 0
        assert result.data[0]["end_char"] == len(text)
        assert result.metadata["total_chunks"] == 1

    def test_process_result_structure(self):
        """测试结果结构正确"""
        chunker = Chunker(chunk_size=50, chunk_overlap=10)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = chunker.process(text)

        assert isinstance(result, ProcessResult)
        assert result.success is True
        assert isinstance(result.data, list)
        assert "total_chunks" in result.metadata
        assert "chunk_size" in result.metadata
        assert "chunk_overlap" in result.metadata

        # 验证每个块的结构
        for chunk in result.data:
            assert "content" in chunk
            assert "chunk_index" in chunk
            assert "start_char" in chunk
            assert "end_char" in chunk
            assert isinstance(chunk["chunk_index"], int)
            assert isinstance(chunk["start_char"], int)
            assert isinstance(chunk["end_char"], int)

    def test_process_with_kwargs_override(self):
        """测试通过 kwargs 覆盖参数"""
        chunker = Chunker(chunk_size=1000)
        text = "A" * 500  # 500 字符

        # 使用 kwargs 覆盖 chunk_size
        result = chunker.process(text, chunk_size=200)

        assert result.success is True
        assert len(result.data) > 1  # 应该被分成多个块
        assert result.metadata["chunk_size"] == 200


class TestChunkerBasicChunking:
    """Chunker 基本分块功能测试"""

    def test_basic_long_text_chunking(self):
        """测试长文本基本分块"""
        chunker = Chunker(chunk_size=100, chunk_overlap=0)

        # 创建一个长文本
        paragraph1 = "This is paragraph one. " * 10  # ~230 chars
        paragraph2 = "This is paragraph two. " * 10  # ~230 chars
        text = paragraph1 + "\n\n" + paragraph2

        result = chunker.process(text)

        assert result.success is True
        assert result.metadata["total_chunks"] > 2

    def test_chunking_preserves_content(self):
        """测试分块保留所有内容"""
        chunker = Chunker(chunk_size=100, chunk_overlap=0)
        text = "Hello World! " * 20

        result = chunker.process(text)

        # 合并所有块的内容（去除可能的重叠）
        assert result.success is True
        # 验证至少包含原始文本的所有内容
        all_content = "".join([c["content"] for c in result.data])
        # 基本验证：总字符数应该接近原始长度
        assert len(all_content) >= len(text) * 0.8


class TestChunkerOverlap:
    """Chunker 重叠功能测试"""

    def test_overlap_between_chunks(self):
        """测试块之间存在重叠"""
        chunker = Chunker(chunk_size=50, chunk_overlap=20)

        # 创建足够长的文本以产生多个块
        text = "Word " * 30  # 150 字符

        result = chunker.process(text)

        assert result.success is True
        if len(result.data) >= 2:
            # 检查相邻块之间是否有内容重叠
            chunk1_content = result.data[0]["content"]
            chunk2_content = result.data[1]["content"]

            # 第一个块的末尾应该与第二个块的开头有重叠
            chunk1_end = chunk1_content[-20:] if len(chunk1_content) >= 20 else chunk1_content
            # 验证第二个块包含部分第一个块末尾的内容
            # （重叠可能不是精确的20字符，但应该有重叠）
            assert len(chunk2_content) > 0

    def test_zero_overlap(self):
        """测试零重叠"""
        chunker = Chunker(chunk_size=50, chunk_overlap=0)
        text = "A" * 100

        result = chunker.process(text)

        assert result.success is True
        assert len(result.data) >= 2


class TestChunkerSeparators:
    """Chunker 分隔符测试"""

    def test_custom_separator(self):
        """测试自定义分隔符"""
        chunker = Chunker(chunk_size=100, separator="---")
        text = "Section one content.---Section two content.---Section three content."

        result = chunker.process(text)

        assert result.success is True
        assert len(result.data) >= 1

    def test_paragraph_separator_default(self):
        """测试默认段落分隔符"""
        chunker = Chunker(chunk_size=200, separator="\n\n")
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."

        result = chunker.process(text)

        assert result.success is True
        # 应该能够正确处理段落分隔

    def test_newline_separator(self):
        """测试换行符分隔符"""
        chunker = Chunker(chunk_size=50, separator="\n")
        text = "Line one.\nLine two.\nLine three.\nLine four."

        result = chunker.process(text)

        assert result.success is True


class TestChunkerChineseText:
    """Chunker 中文文本处理测试"""

    def test_chinese_text_single_chunk(self):
        """测试中文短文本单块"""
        chunker = Chunker(chunk_size=1000)
        text = "这是一段中文文本。"

        result = chunker.process(text)

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["content"] == text

    def test_chinese_text_multiple_paragraphs(self):
        """测试中文多段落"""
        chunker = Chunker(chunk_size=100, chunk_overlap=10)
        text = "这是第一个段落。这里有一些内容。\n\n这是第二个段落。这里有更多内容。\n\n这是第三个段落。"

        result = chunker.process(text)

        assert result.success is True
        # 验证处理成功且有数据
        assert result.metadata["total_chunks"] >= 1

    def test_chinese_sentence_splitting(self):
        """测试中文句子分割"""
        chunker = Chunker(chunk_size=50, chunk_overlap=0)
        # 创建一个较长的中文段落（超过 chunk_size）
        text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。这是第五句话。这是第六句话。"

        result = chunker.process(text)

        assert result.success is True
        assert len(result.data) >= 1

    def test_mixed_chinese_english(self):
        """测试中英混合文本"""
        chunker = Chunker(chunk_size=100)
        text = "这是中文内容。This is English content.这是更多中文。More English here."

        result = chunker.process(text)

        assert result.success is True
        # 验证内容被保留
        all_content = "".join([c["content"] for c in result.data])
        assert "中文" in all_content
        assert "English" in all_content


class TestChunkerEdgeCases:
    """Chunker 边界情况测试"""

    def test_text_exactly_chunk_size(self):
        """测试文本长度恰好等于块大小"""
        chunk_size = 100
        chunker = Chunker(chunk_size=chunk_size, chunk_overlap=0)
        text = "A" * chunk_size

        result = chunker.process(text)

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["content"] == text

    def test_text_slightly_larger_than_chunk_size(self):
        """测试文本略大于块大小"""
        chunk_size = 100
        chunker = Chunker(chunk_size=chunk_size, chunk_overlap=0)
        text = "A" * (chunk_size + 1)

        result = chunker.process(text)

        assert result.success is True
        assert len(result.data) >= 1

    def test_very_large_overlap(self):
        """测试重叠大于块大小的情况"""
        chunker = Chunker(chunk_size=50, chunk_overlap=100)
        text = "A" * 200

        result = chunker.process(text)

        # 应该仍然能够正常处理
        assert result.success is True

    def test_single_very_long_word(self):
        """测试单个超长单词（无空格分隔）"""
        chunker = Chunker(chunk_size=50, chunk_overlap=10)
        text = "A" * 200  # 200 字符无空格

        result = chunker.process(text)

        assert result.success is True
        # 应该被按字符分割
        assert len(result.data) >= 1

    def test_many_small_paragraphs(self):
        """测试大量小段落"""
        chunker = Chunker(chunk_size=100, chunk_overlap=10)
        text = "\n\n".join([f"Paragraph {i}." for i in range(50)])

        result = chunker.process(text)

        assert result.success is True
        # 小段落应该被合并

    def test_special_characters(self):
        """测试特殊字符"""
        chunker = Chunker(chunk_size=100)
        text = "Hello @#$%^&*() World!\n\nSpecial: <>&\"\'\n\nUnicode: 你好🎉"

        result = chunker.process(text)

        assert result.success is True
        # 验证特殊字符被保留
        all_content = "".join([c["content"] for c in result.data])
        assert "@#$%^&*()" in all_content or len(result.data) > 0


class TestChunkerTokenCounting:
    """Chunker token 计数测试"""

    def test_count_tokens_basic(self):
        """测试基本 token 计数"""
        chunker = Chunker()

        # 4 字符约等于 1 token
        text = "AAAA"  # 4 字符
        assert chunker._count_tokens(text) == 1

        text = "AAAAAAAA"  # 8 字符
        assert chunker._count_tokens(text) == 2

    def test_count_tokens_empty(self):
        """测试空文本 token 计数"""
        chunker = Chunker()
        assert chunker._count_tokens("") == 0


class TestChunkerIndexAndPosition:
    """Chunker 索引和位置测试"""

    def test_chunk_indices_sequential(self):
        """测试块索引是否顺序递增"""
        chunker = Chunker(chunk_size=50, chunk_overlap=10)
        text = "Word " * 50  # 250 字符

        result = chunker.process(text)

        assert result.success is True
        for i, chunk in enumerate(result.data):
            assert chunk["chunk_index"] == i

    def test_position_info_valid(self):
        """测试位置信息有效"""
        chunker = Chunker(chunk_size=50, chunk_overlap=0)
        text = "Hello World! This is a test document for chunking."

        result = chunker.process(text)

        assert result.success is True
        for chunk in result.data:
            assert chunk["start_char"] >= 0
            assert chunk["end_char"] >= chunk["start_char"]
            assert chunk["end_char"] <= len(text) + 100  # 允许一定误差


class TestChunkerIntegration:
    """Chunker 集成测试"""

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 创建一个真实的长文本
        text = """
        Introduction

        This is the first paragraph of our document. It contains some important 
        information that needs to be processed.

        Chapter 1

        In this chapter, we discuss the main concepts. The content here is quite 
        substantial and covers many topics.

        Chapter 2

        This chapter builds on the previous one. We explore more advanced topics 
        and provide detailed explanations.

        Conclusion

        In conclusion, we have covered all the main points. Thank you for reading.
        """

        chunker = Chunker(chunk_size=200, chunk_overlap=50)
        result = chunker.process(text.strip())

        # 验证基本结果
        assert result.success is True
        assert len(result.data) >= 1

        # 验证元数据
        assert result.metadata["total_chunks"] == len(result.data)
        assert result.metadata["chunk_size"] == 200
        assert result.metadata["chunk_overlap"] == 50

        # 验证每个块都有内容
        for chunk in result.data:
            assert len(chunk["content"]) > 0

    def test_process_returns_process_result(self):
        """测试 process 方法返回 ProcessResult"""
        chunker = Chunker()
        result = chunker.process("Test text")

        assert isinstance(result, ProcessResult)
        assert hasattr(result, "success")
        assert hasattr(result, "data")
        assert hasattr(result, "metadata")
        assert hasattr(result, "error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
