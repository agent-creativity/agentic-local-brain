"""
配置管理模块

负责读取、解析和管理知识库配置文件。
支持环境变量替换和默认配置。
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


# 默认配置
DEFAULT_CONFIG: Dict[str, Any] = {
    "data_dir": "~/.knowledge-base",
    "update_server_url": "https://localbrain.io.alibaba-inc.com",
    "embedding": {
        "provider": "dashscope",
        "model": "text-embedding-v4",
    },
    "llm": {
        "provider": "dashscope",
        "model": "qwen-plus",  # Use qwen-plus, qwen-turbo, qwen-max, or qwen2.5-xx-instruct
    },
    "chunking": {
        "max_chunk_size": 1000,
        "chunk_overlap": 100,
    },
    "storage": {
        "type": "chroma",
        "persist_directory": "~/.knowledge-base/db/chroma",
    },
    "logging": {
        "log_dir": "",  # empty means default to ~/.localbrain/logs/
        "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
        "max_bytes": 10485760,  # 10MB per log file
        "backup_count": 5,  # number of rotated log files to keep
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
}


def _expand_env_vars(value: str) -> str:
    """
    替换字符串中的环境变量引用 ${VAR_NAME}。

    Args:
        value: 包含环境变量引用的字符串

    Returns:
        替换后的字符串
    """
    pattern = r"\$\{(\w+)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replacer, value)


def _expand_env_vars_in_config(config: Any) -> Any:
    """
    递归替换配置中的所有环境变量引用。

    Args:
        config: 配置对象（字典、列表或基本类型）

    Returns:
        替换后的配置对象
    """
    if isinstance(config, dict):
        return {k: _expand_env_vars_in_config(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_expand_env_vars_in_config(item) for item in config]
    elif isinstance(config, str):
        return _expand_env_vars(config)
    return config


def expand_path(path_str: str) -> Path:
    """
    展开路径字符串，支持 ~ 和环境变量。

    Args:
        path_str: 路径字符串

    Returns:
        展开后的 Path 对象
    """
    expanded = os.path.expanduser(path_str)
    expanded = _expand_env_vars(expanded)
    return Path(expanded)


class Config:
    """配置管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置管理器。

        Args:
            config_path: 配置文件路径，默认为 ~/.knowledge-base/config.yaml
        """
        if config_path is None:
            config_path = Path.home() / ".localbrain" / "config.yaml"
        self._config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """从配置文件加载配置"""
        # 从默认配置开始
        self._config = DEFAULT_CONFIG.copy()

        # 如果配置文件存在，读取并合并
        if self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    self._deep_merge(self._config, file_config)

        # 展开环境变量
        self._config = _expand_env_vars_in_config(self._config)

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        深度合并两个字典。

        Args:
            base: 基础字典（会被修改）
            override: 覆盖字典
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键。

        Args:
            key: 配置键，如 "embedding.model"
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def data_dir(self) -> Path:
        """获取数据目录路径"""
        return expand_path(self.get("data_dir", DEFAULT_CONFIG["data_dir"]))

    @property
    def config_path(self) -> Path:
        """获取配置文件路径"""
        return self._config_path

    def to_dict(self) -> Dict[str, Any]:
        """返回配置的字典表示"""
        return self._config.copy()

    @property
    def update_server_url(self) -> str:
        """Get the update server URL."""
        return self.get("update_server_url", DEFAULT_CONFIG["update_server_url"])

    @property
    def install_dir(self) -> Path:
        """Get the installation directory (~/.localbrain/)."""
        return Path.home() / ".localbrain"

    @property
    def install_info_path(self) -> Path:
        """Get the install-info.json file path."""
        return self.install_dir / ".install-info"

    def get_log_dir(self) -> Path:
        """
        获取日志目录路径。

        如果配置中未设置 log_dir，则默认使用 ~/.localbrain/logs/
        如果目录不存在，会自动创建。

        Returns:
            日志目录的 Path 对象
        """
        log_dir_str = self.get("logging.log_dir", "")
        if not log_dir_str:
            log_dir = Path.home() / ".localbrain" / "logs"
        else:
            log_dir = expand_path(log_dir_str)
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def get_log_config(self) -> Dict[str, Any]:
        """
        获取完整的日志配置字典。

        Returns:
            包含日志配置的字典，包括:
            - log_dir: 日志目录路径（已展开并创建）
            - level: 日志级别
            - max_bytes: 单个日志文件最大字节数
            - backup_count: 保留的备份文件数量
            - format: 日志格式字符串
        """
        return {
            "log_dir": self.get_log_dir(),
            "level": self.get("logging.level", "INFO"),
            "max_bytes": self.get("logging.max_bytes", 10485760),
            "backup_count": self.get("logging.backup_count", 5),
            "format": self.get(
                "logging.format",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            ),
        }

    def save(self, path: Optional[Path] = None) -> None:
        """
        保存配置到文件。

        Args:
            path: 保存路径，默认使用初始化时的路径
        """
        save_path = path or self._config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

    def validate_services(self) -> dict:
        """Check service configs and return availability status.

        Returns a dict with keys:
          - embedding_available: True if embedding API key is properly configured
          - llm_available: True if LLM API key is properly configured

        Logs warnings for unavailable services but never raises exceptions.
        """
        status = {"embedding_available": False, "llm_available": False}

        # Check embedding config
        emb_config = self.get("embedding") or {}
        emb_provider = emb_config.get("provider", "dashscope")

        # Get API key from provider-specific nested config
        if emb_provider == "dashscope":
            emb_api_key = emb_config.get("dashscope", {}).get("api_key", "")
        elif emb_provider == "openai_compatible":
            emb_api_key = emb_config.get("openai_compatible", {}).get("api_key", "")
        else:
            # Fallback: check top-level api_key
            emb_api_key = emb_config.get("api_key", "")

        if emb_api_key and not emb_api_key.startswith("${"):
            status["embedding_available"] = True
        else:
            logger.warning(
                "Embedding service not configured. "
                "Semantic search and vectorization will be unavailable. "
                "Use 'localbrain test embedding' to verify configuration."
            )

        # Check LLM config
        llm_config = self.get("llm") or {}
        llm_api_key = llm_config.get("api_key", "")
        if llm_api_key and not llm_api_key.startswith("${"):
            status["llm_available"] = True
        else:
            logger.warning(
                "LLM service not configured. "
                "Auto-tagging and RAG will be unavailable. "
                "Use 'localbrain test llm' to verify configuration."
            )

        return status
