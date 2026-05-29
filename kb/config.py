"""
Configuration management module

Reads, parses, and manages knowledge base configuration files.
Supports environment variable substitution and default configuration.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "data_dir": "~/.knowledge-base",
    "update_server_url": "http://localbrain.oss-cn-shanghai.aliyuncs.com",
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
    "query": {
        "rag": {
            "top_k": 5,
            "temperature": 0.3,
            "max_tokens": 1000,
            "context_budget": 4000,
            "context_format": "hierarchical",
            "reranking": {
                "enabled": True,
                "top_n_candidates": 20,
                "weight_retrieval": 0.4,
                "weight_rerank": 0.6,
            },
            "conversation": {
                "max_turns": 20,
                "session_timeout_minutes": 30,
                "history_turns_in_context": 5,
            },
            "templates": {
                "default": "general",
            },
        },
        "pipeline": {
            "top_k": 10,
            "rerank_top_k": 5,
            "context_budget": 4000,
        },
    },
    "logging": {
        "log_dir": "",  # empty means default to ~/.localbrain/logs/
        "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
        "max_bytes": 10485760,  # 10MB per log file
        "backup_count": 5,  # number of rotated log files to keep
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
    "extraction": {
        "summary_max_length": 512,  # Maximum summary length in characters
    },
    "wiki": {
        "enabled": True,
        "max_source_tokens_per_topic": 8000,
        "entity_card_threshold": 3,
        "temperature": 0.3,
        "model": None,
        "max_article_words": 3000,
        "max_subcategories": 5,
    },
    "backup": {
        "enabled": False,
        "schedule": "0 2 * * *",  # Daily at 2 AM
        "retention_days": 30,
        "backup_dir": "~/.knowledge-base/backups",
        "include_db": True,
        "include_files": True,
        "compression": True,
        "cloud_provider": "oss",
        "oss": {
            "endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "access_key_id": "",
            "access_key_secret": "",
            "bucket": "localbrain-backups",
        },
        "s3": {
            "region": "us-west-2",
            "access_key_id": "",
            "secret_access_key": "",
            "bucket": "localbrain-backups",
        },
    },
}


def _expand_env_vars(value: str) -> str:
    """
    Replace environment variable references ${VAR_NAME} in a string.

    Args:
        value: String containing environment variable references.

    Returns:
        String with substitutions applied.
    """
    pattern = r"\$\{(\w+)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replacer, value)


def _expand_env_vars_in_config(config: Any) -> Any:
    """
    Recursively replace all environment variable references in config.

    Args:
        config: Config object (dict, list, or primitive type).

    Returns:
        Config object with substitutions applied.
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
    Expand a path string, supporting ~ and environment variables.

    Args:
        path_str: Path string.

    Returns:
        Expanded Path object.
    """
    expanded = os.path.expanduser(path_str)
    expanded = _expand_env_vars(expanded)
    return Path(expanded)


class Config:
    """Configuration manager."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Config file path. Defaults to ~/.knowledge-base/config.yaml.
        """
        if config_path is None:
            config_path = Path.home() / ".localbrain" / "config.yaml"
        self._config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        # Start from default configuration
        self._config = DEFAULT_CONFIG.copy()

        # If config file exists, read and merge
        if self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    self._deep_merge(self._config, file_config)

        # Expand environment variables
        self._config = _expand_env_vars_in_config(self._config)

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        Deep-merge two dictionaries.

        Args:
            base: Base dictionary (will be modified in place).
            override: Override dictionary.
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a config value, supporting dot-separated nested keys.

        Args:
            key: Config key, e.g. "embedding.model".
            default: Default value.

        Returns:
            Config value.
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
        """Get the data directory path."""
        return expand_path(self.get("data_dir", DEFAULT_CONFIG["data_dir"]))

    @property
    def config_path(self) -> Path:
        """Get the config file path."""
        return self._config_path

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the config."""
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
        Get the log directory path.

        If log_dir is not set in config, defaults to ~/.localbrain/logs/
        Creates the directory if it does not exist.

        Returns:
            Path object for the log directory.
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
        Get the full logging configuration dictionary.

        Returns:
            Dictionary containing log config, including:
            - log_dir: Log directory path (expanded and created).
            - level: Log level.
            - max_bytes: Max bytes per log file.
            - backup_count: Number of backup files to retain.
            - format: Log format string.
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
        Save configuration to file.

        Args:
            path: Save path. Defaults to the path used during initialization.
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

    def get_wiki_dir(self) -> Path:
        """
        Get wiki directory path, creating it if needed.

        The wiki directory is located at <data_dir>/2_process/wiki/ with
        subdirectories for topics/ and entities/.

        Returns:
            Path object pointing to the wiki directory.
        """
        wiki_dir = self.data_dir / "2_process" / "wiki"
        (wiki_dir / "topics").mkdir(parents=True, exist_ok=True)
        (wiki_dir / "entities").mkdir(parents=True, exist_ok=True)
        return wiki_dir
