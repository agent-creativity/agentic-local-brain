"""
文本分块处理器模块

将长文本分割为更小的块以便于向量嵌入和检索。
支持可配置的分块大小、重叠和分隔符。
"""

import re
from typing import Any, Dict, List, Optional

from kb.processors.base import BaseProcessor, ProcessResult


class Chunker(BaseProcessor):
    """
    文本分块处理器

    将输入文本分割为固定大小的块，支持块之间的重叠。
    分块策略：
    1. 首先尝试按段落分隔符分割
    2. 如果段落仍然过大，按句子分割
    3. 如果句子仍然过大，按字符数分割
    4. 合并小段直到达到块大小
    5. 在连续块之间应用重叠

    使用示例：
        >>> from kb.processors.chunker import Chunker
        >>> chunker = Chunker(chunk_size=500, chunk_overlap=50)
        >>> result = chunker.process("长文本内容...")
        >>> if result.success:
        ...     for chunk in result.data:
        ...         print(chunk["content"])
    """

    # 默认句子分隔符（支持中英文）
    SENTENCE_SEPARATORS = [". ", "。", "!\n", "？\n", "!\n", "?\n", "\n"]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        separator: str = "\n\n",
        **kwargs: Any
    ) -> None:
        """
        初始化文本分块处理器

        Args:
            chunk_size: 每个块的最大字符数，默认为 1000
            chunk_overlap: 连续块之间的重叠字符数，默认为 100
            separator: 首选的分割分隔符，默认为段落分隔符 "\\n\\n"
            **kwargs: 额外的配置参数
        """
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    @classmethod
    def from_config(cls, config: Optional["Config"] = None) -> "Chunker":
        """
        从配置创建分块处理器实例

        Args:
            config: 配置对象，如果为 None 则使用默认配置

        Returns:
            Chunker: 分块处理器实例
        """
        if config is None:
            from kb.config import Config
            config = Config()

        chunking_config = config.get("chunking", {})
        chunk_size = chunking_config.get("max_chunk_size", 1000)
        chunk_overlap = chunking_config.get("chunk_overlap", 100)
        separator = chunking_config.get("separator", "\n\n")

        return cls(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=separator
        )

    def process(self, data: str, **kwargs: Any) -> ProcessResult:
        """
        处理文本并分割为块

        Args:
            data: 待分块的文本内容（字符串）
            **kwargs: 额外的处理参数
                - chunk_size: 覆盖默认的块大小
                - chunk_overlap: 覆盖默认的重叠大小
                - separator: 覆盖默认的分隔符

        Returns:
            ProcessResult: 处理结果
                - success: True 表示处理成功
                - data: 块列表，每个块包含 content, chunk_index, start_char, end_char
                - metadata: 包含 total_chunks, chunk_size, chunk_overlap
                - error: 错误信息（如果失败）
        """
        try:
            # 允许通过 kwargs 覆盖参数
            chunk_size = kwargs.get("chunk_size", self.chunk_size)
            chunk_overlap = kwargs.get("chunk_overlap", self.chunk_overlap)
            separator = kwargs.get("separator", self.separator)

            # 处理空输入
            if not data or not data.strip():
                return ProcessResult(
                    success=True,
                    data=[],
                    metadata={
                        "total_chunks": 0,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap
                    }
                )

            # 执行分块
            chunks = self._split_text(
                data,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separator=separator
            )

            return ProcessResult(
                success=True,
                data=chunks,
                metadata={
                    "total_chunks": len(chunks),
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap
                }
            )

        except Exception as e:
            return ProcessResult(
                success=False,
                data=None,
                error=str(e)
            )

    def _split_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        separator: str
    ) -> List[Dict[str, Any]]:
        """
        核心分块逻辑

        Args:
            text: 待分块的文本
            chunk_size: 块大小
            chunk_overlap: 重叠大小
            separator: 分隔符

        Returns:
            List[Dict]: 块列表
        """
        # 如果文本小于等于块大小，直接返回单个块
        if len(text) <= chunk_size:
            return [{
                "content": text,
                "chunk_index": 0,
                "start_char": 0,
                "end_char": len(text)
            }]

        # 第一步：按分隔符分割为段落
        paragraphs = self._split_by_separator(text, separator)

        # 第二步：处理过大的段落
        segments = []
        for para in paragraphs:
            if len(para) <= chunk_size:
                segments.append(para)
            else:
                # 段落过大，按句子分割
                sentences = self._split_by_sentences(para)
                for sent in sentences:
                    if len(sent) <= chunk_size:
                        segments.append(sent)
                    else:
                        # 句子仍然过大，按字符分割
                        char_chunks = self._split_by_chars(sent, chunk_size)
                        segments.extend(char_chunks)

        # 第三步：合并小段为块
        chunks = self._merge_segments(segments, chunk_size, chunk_overlap, text)

        return chunks

    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """
        按分隔符分割文本

        Args:
            text: 文本内容
            separator: 分隔符

        Returns:
            List[str]: 分割后的段落列表
        """
        parts = text.split(separator)
        # 过滤空段落并保留非空部分
        return [p for p in parts if p.strip()]

    def _split_by_sentences(self, text: str) -> List[str]:
        """
        按句子分割文本（支持中英文）

        Args:
            text: 文本内容

        Returns:
            List[str]: 句子列表
        """
        # 使用正则表达式按句子分隔符分割
        # 匹配句号、问号、感叹号等后面跟空格或换行
        pattern = r'(?<=[.。!！?？])\s*(?=\S)'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_by_chars(self, text: str, chunk_size: int) -> List[str]:
        """
        按字符数分割文本

        Args:
            text: 文本内容
            chunk_size: 块大小

        Returns:
            List[str]: 分割后的文本块
        """
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks

    def _merge_segments(
        self,
        segments: List[str],
        chunk_size: int,
        chunk_overlap: int,
        original_text: str
    ) -> List[Dict[str, Any]]:
        """
        合并小段为块，并应用重叠

        Args:
            segments: 段落/句子列表
            chunk_size: 块大小
            chunk_overlap: 重叠大小
            original_text: 原始文本（用于计算位置）

        Returns:
            List[Dict]: 块列表，包含位置信息
        """
        if not segments:
            return []

        chunks = []
        current_chunk = ""
        current_start = 0

        for segment in segments:
            # 检查添加此段是否会超出块大小
            if current_chunk:
                potential = current_chunk + self.separator + segment
            else:
                potential = segment

            if len(potential) <= chunk_size:
                # 可以添加到当前块
                current_chunk = potential
            else:
                # 当前块已满，保存并开始新块
                if current_chunk:
                    # 计算在原文中的位置
                    start_pos = original_text.find(current_chunk, current_start)
                    if start_pos == -1:
                        # 如果精确匹配失败，使用近似位置
                        start_pos = current_start
                    end_pos = start_pos + len(current_chunk)

                    chunks.append({
                        "content": current_chunk,
                        "chunk_index": len(chunks),
                        "start_char": start_pos,
                        "end_char": end_pos
                    })

                    # 应用重叠：从当前块末尾取 overlap 字符
                    if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                        overlap_text = current_chunk[-chunk_overlap:]
                        current_chunk = overlap_text + self.separator + segment
                        current_start = end_pos - chunk_overlap
                    else:
                        current_chunk = segment
                        current_start = end_pos
                else:
                    current_chunk = segment

        # 处理最后一个块
        if current_chunk:
            start_pos = original_text.find(current_chunk, current_start)
            if start_pos == -1:
                start_pos = current_start
            end_pos = start_pos + len(current_chunk)

            chunks.append({
                "content": current_chunk,
                "chunk_index": len(chunks),
                "start_char": start_pos,
                "end_char": end_pos
            })

        return chunks

    def _count_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量

        使用简单的近似方法：字符数除以 4
        对于中文文本，每个字符约等于 1-2 个 token
        对于英文文本，每 4 个字符约等于 1 个 token

        Args:
            text: 文本内容

        Returns:
            int: 估算的 token 数量
        """
        # 简单近似：字符数除以 4
        return len(text) // 4

    def process_with_pages(
        self,
        pages: List[Dict[str, Any]],
        **kwargs: Any
    ) -> ProcessResult:
        """
        按页分块处理 PDF 文本，保留 page_number 元数据

        对每一页的文本独立分块，每个 chunk 的 metadata 中带有 page_number。
        当一页文本小于 chunk_size 时，不跨页合并，保持页边界。

        Args:
            pages: 页列表，每项包含 page_number (int) 和 text (str)
            **kwargs: 额外的处理参数（chunk_size, chunk_overlap, separator）

        Returns:
            ProcessResult: 处理结果，data 中每个 chunk 包含 page_number 字段
        """
        try:
            chunk_size = kwargs.get("chunk_size", self.chunk_size)
            chunk_overlap = kwargs.get("chunk_overlap", self.chunk_overlap)
            separator = kwargs.get("separator", self.separator)

            if not pages:
                return ProcessResult(
                    success=True,
                    data=[],
                    metadata={
                        "total_chunks": 0,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap
                    }
                )

            all_chunks = []
            global_index = 0

            for page in pages:
                page_number = page.get("page_number", 0)
                text = page.get("text", "")

                if not text or not text.strip():
                    continue

                # Chunk this page independently
                page_chunks = self._split_text(
                    text,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separator=separator
                )

                # Add page_number to each chunk and update global index
                for chunk in page_chunks:
                    chunk["page_number"] = page_number
                    chunk["chunk_index"] = global_index
                    global_index += 1
                    all_chunks.append(chunk)

            return ProcessResult(
                success=True,
                data=all_chunks,
                metadata={
                    "total_chunks": len(all_chunks),
                    "total_pages": len(pages),
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap
                }
            )

        except Exception as e:
            return ProcessResult(
                success=False,
                data=None,
                error=str(e)
            )
