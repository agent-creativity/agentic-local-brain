"""
Base processor module

Defines the abstract base class for all processors, providing a unified interface and data models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProcessResult:
    """
    Processing result data class.

    Attributes:
        success: Whether processing was successful.
        data: Processed data.
        metadata: Additional metadata.
        error: Error message (if failed).
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
    Abstract base class for processors.

    All concrete processors (tag extraction, text chunking, embedding vector generation, etc.) should inherit this class 
    and implement the unified processing interface.

    Methods that subclasses must implement:
        - process: Execute processing operation.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize processor.

        Args:
            **kwargs: Processor configuration parameters.
        """
        self.config = kwargs

    @abstractmethod
    def process(self, data: Any, **kwargs: Any) -> ProcessResult:
        """
        Execute processing operation.

        Args:
            data: Data to be processed.
            **kwargs: Additional processing parameters.

        Returns:
            ProcessResult: Processing result.
        """
        pass
