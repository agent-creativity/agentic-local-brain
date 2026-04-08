"""
处理器基类模块

定义所有处理器的抽象基类，提供统一的接口和数据模型。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProcessResult:
    """
    处理结果数据类

    Attributes:
        success: 是否处理成功
        data: 处理后的数据
        metadata: 额外的元数据信息
        error: 错误信息（如果失败）
    """

    success: bool
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def __repr__(self) -> str:
        if self.success:
            return f"ProcessResult(success=True, metadata={self.metadata})"
        return f"ProcessResult(success=False, error={self.error})"


class BaseProcessor(ABC):
    """
    处理器抽象基类

    所有具体的处理器（标签提取、文本分块、嵌入向量生成等）都应继承此类，
    实现统一的处理接口。

    子类需要实现的方法：
        - process: 执行处理操作
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        初始化处理器

        Args:
            **kwargs: 处理器配置参数
        """
        self.config = kwargs

    @abstractmethod
    def process(self, data: Any, **kwargs: Any) -> ProcessResult:
        """
        执行处理操作

        Args:
            data: 待处理的数据
            **kwargs: 额外的处理参数

        Returns:
            ProcessResult: 处理结果
        """
        pass
