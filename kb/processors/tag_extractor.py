"""
标签提取器模块

基于 LLM 的标签提取功能，通过 LiteLLM 统一调用各类 LLM。
从文档标题和内容中提取 3-5 个相关标签。
"""

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from kb.config import Config
from kb.processors.base import BaseProcessor, ProcessResult


class LLMProvider(ABC):
    """LLM 提供者抽象基类"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        生成文本响应

        Args:
            prompt: 提示词
            **kwargs: 额外的生成参数

        Returns:
            str: 生成的文本
        """
        pass


class LiteLLMProvider(LLMProvider):
    """
    LiteLLM 统一 Provider

    通过 litellm SDK 统一调用各类 LLM，支持 dashscope、openai 等。
    """

    def __init__(self, model: str, api_key: str, **kwargs: Any) -> None:
        """
        初始化 LiteLLM 提供者

        Args:
            model: LiteLLM 格式的模型名，如 "dashscope/qwen-plus" 或 "openai/gpt-4"
            api_key: API 密钥
            **kwargs: 传递给 litellm.completion() 的额外参数（如 api_base）
        """
        self.model = model
        self.api_key = api_key
        self.extra_kwargs = kwargs

    def generate(self, prompt: str, max_retries: int = 3, **kwargs: Any) -> str:
        """
        通过 LiteLLM 生成文本

        Args:
            prompt: 提示词
            max_retries: 最大重试次数，默认为 3
            **kwargs: 额外的生成参数

        Returns:
            str: 生成的文本

        Raises:
            ImportError: litellm 未安装
            Exception: API 调用失败
        """
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "litellm package is required. Install it with: pip install litellm"
            )

        last_error = None
        for attempt in range(max_retries):
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=self.api_key,
                    num_retries=0,
                    **{**self.extra_kwargs, **kwargs}
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e

            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1
                time.sleep(wait_time)

        raise last_error or Exception("LiteLLM call failed after maximum retries")


class TagExtractor(BaseProcessor):
    """
    基于 LLM 的标签提取器

    从文档标题和内容中提取 3-5 个相关标签。支持多种 LLM 提供者。

    使用示例：
        >>> from kb.processors.tag_extractor import TagExtractor
        >>> extractor = TagExtractor.from_config()
        >>> result = extractor.process(
        ...     title="机器学习入门",
        ...     content="机器学习是人工智能的一个分支..."
        ... )
        >>> print(result.data)  # ['机器学习', '人工智能', '深度学习']
    """

    # Tag and summary extraction prompt template
    EXTRACTION_PROMPT = """You are a content analysis assistant. Analyze the following document and extract:
1. Tags: 3-5 relevant keywords or short phrases that describe the core topics
2. Summary: A comprehensive summary of the document (up to {max_length} characters)

Document title: {title}
Document content (truncated): {content}

Requirements:
- Tags should be 2-6 word keywords or short phrases
- Tags should accurately reflect the document's core topics
- Use the same language as the document for tags
- Summary should be comprehensive and detailed, capturing key points and main ideas
- Summary should not exceed {max_length} characters, but should be as detailed as possible within this limit

Return ONLY a JSON object in this exact format, no other text:
{{"tags": ["tag1", "tag2", "tag3"], "summary": "Comprehensive summary of the document."}}"""

    def __init__(
        self,
        provider: LLMProvider,
        min_tags: int = 3,
        max_tags: int = 5,
        summary_max_length: int = 512,
        **kwargs: Any
    ) -> None:
        """
        初始化标签提取器

        Args:
            provider: LLM 提供者实例
            min_tags: 最少提取标签数，默认为 3
            max_tags: 最多提取标签数，默认为 5
            summary_max_length: 摘要最大长度（字符数），默认为 512
            **kwargs: 额外的配置参数
        """
        super().__init__(**kwargs)
        self.provider = provider
        self.min_tags = min_tags
        self.max_tags = max_tags
        self.summary_max_length = summary_max_length

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "TagExtractor":
        """
        从配置创建标签提取器实例

        Args:
            config: 配置对象，如果为 None 则使用默认配置

        Returns:
            TagExtractor: 标签提取器实例

        Raises:
            ValueError: 配置无效或缺少必需字段
        """
        if config is None:
            config = Config()

        llm_config = config.get("llm", {})
        provider_name = llm_config.get("provider", "dashscope")
        model = llm_config.get("model", "qwen-plus")
        api_key = llm_config.get("api_key", "")

        if not api_key:
            raise ValueError("LLM API key is required in configuration")

        # 根据提供者类型创建相应的实例
        if provider_name == "litellm":
            # LiteLLM provider: model 已经是 "provider/model" 格式
            provider = LiteLLMProvider(api_key=api_key, model=model)
        elif provider_name == "dashscope":
            # 向后兼容：自动映射旧格式到 litellm 的 "dashscope/model" 格式
            litellm_model = model if "/" in model else f"dashscope/{model}"
            provider = LiteLLMProvider(api_key=api_key, model=litellm_model)
        elif provider_name == "openai_compatible":
            # 向后兼容：映射到 litellm，使用 api_base 传递自定义端点
            base_url = llm_config.get("base_url", "")
            if not base_url:
                raise ValueError(
                    "base_url is required for openai_compatible provider"
                )
            litellm_model = model if "/" in model else f"openai/{model}"
            provider = LiteLLMProvider(
                api_key=api_key,
                model=litellm_model,
                api_base=base_url
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")

        # 从配置中读取标签数量限制和摘要长度限制
        tag_config = config.get("tag_extraction", {})
        min_tags = tag_config.get("min_tags", 3)
        max_tags = tag_config.get("max_tags", 5)

        extraction_config = config.get("extraction", {})
        summary_max_length = extraction_config.get("summary_max_length", 512)

        return cls(
            provider=provider,
            min_tags=min_tags,
            max_tags=max_tags,
            summary_max_length=summary_max_length
        )

    def process(
        self,
        title: str,
        content: str,
        **kwargs: Any
    ) -> ProcessResult:
        """
        从标题和内容中提取标签

        Args:
            title: 文档标题
            content: 文档内容
            **kwargs: 额外的处理参数
                - max_retries: 最大重试次数，默认为 3
                - temperature: 生成温度，默认为 0.3

        Returns:
            ProcessResult: 包含提取标签的处理结果

        Raises:
            ValueError: 标题或内容为空
        """
        if not title or not title.strip():
            return ProcessResult(
                success=False,
                error="Title cannot be empty"
            )

        if not content or not content.strip():
            return ProcessResult(
                success=False,
                error="Content cannot be empty"
            )

        max_retries = kwargs.get("max_retries", 3)
        temperature = kwargs.get("temperature", 0.3)

        try:
            # Build prompt
            prompt = self.EXTRACTION_PROMPT.format(
                title=title[:500],  # Limit title length
                content=content[:2000],  # Limit content length
                max_length=self.summary_max_length
            )

            # Call LLM to generate tags and summary
            response = self.provider.generate(
                prompt=prompt,
                temperature=temperature,
                max_retries=max_retries
            )

            # Parse response
            parsed_result = self._parse_response(response)
            tags = parsed_result["tags"]
            summary = parsed_result["summary"]

            # Truncate summary if it exceeds max length
            if len(summary) > self.summary_max_length:
                summary = summary[:self.summary_max_length].rsplit(' ', 1)[0] + '...'
                parsed_result["summary"] = summary

            # Validate tag count
            if len(tags) < self.min_tags:
                tags = self._pad_tags(tags, title)
            elif len(tags) > self.max_tags:
                tags = tags[:self.max_tags]

            # Update parsed result with validated tags
            parsed_result["tags"] = tags

            return ProcessResult(
                success=True,
                data=parsed_result,
                metadata={
                    "tag_count": len(tags),
                    "summary_length": len(summary),
                    "raw_response": response[:200]  # Save truncated raw response
                }
            )

        except Exception as e:
            return ProcessResult(
                success=False,
                error=str(e)
            )

    def _parse_response(self, response_text: str) -> dict:
        """Parse LLM response into tags and summary.

        Args:
            response_text: LLM generated text

        Returns:
            dict: {"tags": List[str], "summary": str}
        """
        # Try JSON format first (new format)
        try:
            # Clean up potential markdown code blocks
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)

            data = json.loads(cleaned)
            if isinstance(data, dict):
                tags = data.get("tags", [])
                summary = data.get("summary", "")
                if isinstance(tags, list):
                    # Clean tags
                    tags = [str(t).strip() for t in tags if str(t).strip() and len(str(t).strip()) >= 2]
                    return {"tags": tags, "summary": str(summary).strip()}
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: parse as comma-separated tags (old format)
        response = response_text.strip()

        # Try parsing JSON array format
        if response.startswith('[') and response.endswith(']'):
            try:
                tags = json.loads(response)
                if isinstance(tags, list):
                    return {"tags": [str(tag).strip() for tag in tags if tag], "summary": ""}
            except json.JSONDecodeError:
                pass

        # Split by comma or newline
        tags = re.split(r'[,\n、，]', response)

        # Clean tags
        cleaned_tags = []
        for tag in tags:
            tag = tag.strip().strip('"').strip("'").strip('[]')
            if tag and len(tag) >= 2:  # Filter too short tags
                cleaned_tags.append(tag)

        # Deduplicate and keep order
        seen = set()
        unique_tags = []
        for tag in cleaned_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return {"tags": unique_tags, "summary": ""}

    def _pad_tags(self, tags: List[str], title: str) -> List[str]:
        """
        If tag count is insufficient, extract supplementary tags from title

        Args:
            tags: Current tag list
            title: Document title

        Returns:
            List[str]: Padded tag list
        """
        # Extract keywords from title as supplement
        title_words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', title)

        for word in title_words:
            if len(tags) >= self.min_tags:
                break
            if word not in tags and len(word) >= 2:
                tags.append(word)

        return tags

    def extract_tags_and_summary(self, title: str, content: str,
                                 user_tags: list = None, user_summary: str = None) -> dict:
        """Smart extraction with 3-tier fallback: user-provided > LLM > built-in.

        Args:
            title: Document title
            content: Document content
            user_tags: User-provided tags (if any), skips tag extraction
            user_summary: User-provided summary (if any), skips summary extraction

        Returns:
            Dict with "tags" (list) and "summary" (str)
        """
        result_tags = list(user_tags) if user_tags else None
        result_summary = user_summary if user_summary else None

        # If both provided by user, skip extraction entirely
        if result_tags and result_summary:
            logger.info("Using user-provided tags and summary, skipping extraction.")
            return {"tags": result_tags, "summary": result_summary}

        # Try LLM extraction for missing fields
        if not result_tags or not result_summary:
            try:
                llm_result = self.process(title=title, content=content)
                if llm_result.success and isinstance(llm_result.data, dict):
                    if not result_tags:
                        result_tags = llm_result.data.get("tags", [])
                    if not result_summary:
                        result_summary = llm_result.data.get("summary", "")
                    logger.info("LLM extraction successful.")
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")

        # Built-in fallback for anything still missing
        if not result_tags or not result_summary:
            from kb.processors.builtin_extractor import BuiltinExtractor
            builtin = BuiltinExtractor()
            if not result_tags:
                result_tags = builtin.extract_tags(title, content)
                logger.info("Using built-in tag extraction (LLM unavailable or failed).")
            if not result_summary:
                result_summary = builtin.extract_summary(title, content, max_length=self.summary_max_length)
                logger.info("Using built-in summary extraction (LLM unavailable or failed).")

        return {"tags": result_tags or [], "summary": result_summary or ""}

    @classmethod
    def smart_extract(cls, config, title: str, content: str,
                      user_tags: list = None, user_summary: str = None) -> dict:
        """Factory method: tries LLM extraction, falls back to built-in.

        Unlike from_config(), this never raises on missing LLM config.
        """
        try:
            extractor = cls.from_config(config)
            return extractor.extract_tags_and_summary(title, content, user_tags, user_summary)
        except Exception as e:
            logger.warning(f"Could not create LLM extractor: {e}. Using built-in extraction.")
            # Direct built-in fallback
            result_tags = list(user_tags) if user_tags else None
            result_summary = user_summary if user_summary else None

            # Get max_length from config
            extraction_config = config.get("extraction", {})
            summary_max_length = extraction_config.get("summary_max_length", 512)

            from kb.processors.builtin_extractor import BuiltinExtractor
            builtin = BuiltinExtractor()
            if not result_tags:
                result_tags = builtin.extract_tags(title, content)
            if not result_summary:
                result_summary = builtin.extract_summary(title, content, max_length=summary_max_length)

            return {"tags": result_tags or [], "summary": result_summary or ""}
