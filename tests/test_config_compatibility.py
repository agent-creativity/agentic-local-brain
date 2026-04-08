"""
Config 新老格式兼容测试

测试 LLM 配置的三种 provider 格式（dashscope/openai_compatible/litellm）解析，
以及 api_key 字段支持环境变量名和原始 key 两种方式。

覆盖场景：
1. dashscope 旧格式 → LiteLLMProvider 正确映射
2. openai_compatible 旧格式 → LiteLLMProvider 正确映射（含 base_url）
3. litellm 新格式 → LiteLLMProvider 直通
4. api_key 使用 ${ENV_VAR} 格式 → 正确替换
5. api_key 使用原始 key → 直接使用
6. 环境变量未设置时 → 保留 ${VAR} 原文
7. Config 加载 + TagExtractor.from_config() 端到端验证
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.config import Config, _expand_env_vars, _expand_env_vars_in_config


# ============================================================
# Test data: YAML config snippets for different formats
# ============================================================

DASHSCOPE_OLD_FORMAT = """
llm:
  provider: dashscope
  model: qwen-plus
  api_key: {api_key}
"""

OPENAI_COMPAT_OLD_FORMAT = """
llm:
  provider: openai_compatible
  model: custom-model
  api_key: {api_key}
  base_url: http://localhost:11434/v1
"""

LITELLM_NEW_FORMAT = """
llm:
  provider: litellm
  model: dashscope/qwen-plus
  api_key: {api_key}
"""

LITELLM_OPENAI_FORMAT = """
llm:
  provider: litellm
  model: openai/gpt-4o
  api_key: {api_key}
"""

LITELLM_ANTHROPIC_FORMAT = """
llm:
  provider: litellm
  model: anthropic/claude-3-5-sonnet-20241022
  api_key: {api_key}
"""

LITELLM_CUSTOM_ENDPOINT_FORMAT = """
llm:
  provider: litellm
  model: openai/qwen2.5:7b
  api_key: {api_key}
  base_url: http://localhost:11434/v1
"""


# ============================================================
# Helper: create a temp config file and load it
# ============================================================

def _make_config(tmp_path, yaml_content):
    """Write yaml_content to a temp file and return a Config instance."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")
    return Config(config_file)


# ============================================================
# 1. Environment variable expansion tests
# ============================================================

class TestEnvVarExpansion:
    """环境变量替换测试"""

    def test_expand_env_var_set(self, monkeypatch):
        """已设置的环境变量被正确替换"""
        monkeypatch.setenv("MY_API_KEY", "sk-abc123")
        assert _expand_env_vars("${MY_API_KEY}") == "sk-abc123"

    def test_expand_env_var_not_set(self):
        """未设置的环境变量保留原文 ${VAR}"""
        # Use a var name that is very unlikely to exist
        result = _expand_env_vars("${UNLIKELY_VAR_NAME_XYZ_999}")
        assert result == "${UNLIKELY_VAR_NAME_XYZ_999}"

    def test_expand_env_var_in_string(self, monkeypatch):
        """字符串中嵌入的环境变量被替换"""
        monkeypatch.setenv("MY_KEY", "secret")
        assert _expand_env_vars("Bearer ${MY_KEY}") == "Bearer secret"

    def test_expand_multiple_env_vars(self, monkeypatch):
        """多个环境变量同时替换"""
        monkeypatch.setenv("VAR_A", "aaa")
        monkeypatch.setenv("VAR_B", "bbb")
        result = _expand_env_vars("${VAR_A}-${VAR_B}")
        assert result == "aaa-bbb"

    def test_expand_env_vars_in_config_dict(self, monkeypatch):
        """递归替换嵌套字典中的环境变量"""
        monkeypatch.setenv("TEST_KEY", "replaced_value")
        config = {
            "llm": {
                "api_key": "${TEST_KEY}",
                "model": "qwen-plus",
            }
        }
        result = _expand_env_vars_in_config(config)
        assert result["llm"]["api_key"] == "replaced_value"
        assert result["llm"]["model"] == "qwen-plus"

    def test_raw_key_not_modified(self):
        """原始 key（不含 ${}）不被修改"""
        assert _expand_env_vars("sk-abc123def456") == "sk-abc123def456"

    def test_empty_string(self):
        """空字符串不变"""
        assert _expand_env_vars("") == ""


# ============================================================
# 2. Config loading with different LLM formats
# ============================================================

class TestConfigLLMFormats:
    """Config 加载不同 LLM 格式测试"""

    def test_dashscope_old_format_raw_key(self, tmp_path):
        """旧格式 dashscope + 原始 key"""
        yaml_content = DASHSCOPE_OLD_FORMAT.format(api_key="sk-dashscope-key-123")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["provider"] == "dashscope"
        assert llm["model"] == "qwen-plus"
        assert llm["api_key"] == "sk-dashscope-key-123"

    def test_dashscope_old_format_env_var(self, tmp_path, monkeypatch):
        """旧格式 dashscope + 环境变量"""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-from-env-123")
        yaml_content = DASHSCOPE_OLD_FORMAT.format(api_key="${DASHSCOPE_API_KEY}")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["api_key"] == "sk-from-env-123"

    def test_dashscope_old_format_env_var_unset(self, tmp_path):
        """旧格式 dashscope + 未设置的环境变量"""
        yaml_content = DASHSCOPE_OLD_FORMAT.format(api_key="${UNSET_DASHSCOPE_KEY_XYZ}")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["api_key"] == "${UNSET_DASHSCOPE_KEY_XYZ}"

    def test_openai_compatible_old_format(self, tmp_path):
        """旧格式 openai_compatible + 原始 key"""
        yaml_content = OPENAI_COMPAT_OLD_FORMAT.format(api_key="sk-openai-key-456")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["provider"] == "openai_compatible"
        assert llm["model"] == "custom-model"
        assert llm["api_key"] == "sk-openai-key-456"
        assert llm["base_url"] == "http://localhost:11434/v1"

    def test_openai_compatible_old_format_env_var(self, tmp_path, monkeypatch):
        """旧格式 openai_compatible + 环境变量"""
        monkeypatch.setenv("OPENAI_KEY", "sk-openai-from-env")
        yaml_content = OPENAI_COMPAT_OLD_FORMAT.format(api_key="${OPENAI_KEY}")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["api_key"] == "sk-openai-from-env"

    def test_litellm_new_format_dashscope(self, tmp_path):
        """新格式 litellm + dashscope/model"""
        yaml_content = LITELLM_NEW_FORMAT.format(api_key="sk-litellm-ds-key")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["provider"] == "litellm"
        assert llm["model"] == "dashscope/qwen-plus"
        assert llm["api_key"] == "sk-litellm-ds-key"

    def test_litellm_new_format_openai(self, tmp_path):
        """新格式 litellm + openai/model"""
        yaml_content = LITELLM_OPENAI_FORMAT.format(api_key="sk-openai-key")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["provider"] == "litellm"
        assert llm["model"] == "openai/gpt-4o"

    def test_litellm_new_format_anthropic(self, tmp_path):
        """新格式 litellm + anthropic/model"""
        yaml_content = LITELLM_ANTHROPIC_FORMAT.format(api_key="sk-ant-key")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["provider"] == "litellm"
        assert llm["model"] == "anthropic/claude-3-5-sonnet-20241022"

    def test_litellm_custom_endpoint(self, tmp_path):
        """新格式 litellm + 自定义 base_url"""
        yaml_content = LITELLM_CUSTOM_ENDPOINT_FORMAT.format(api_key="ollama")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["provider"] == "litellm"
        assert llm["model"] == "openai/qwen2.5:7b"
        assert llm["api_key"] == "ollama"
        assert llm["base_url"] == "http://localhost:11434/v1"

    def test_litellm_new_format_env_var(self, tmp_path, monkeypatch):
        """新格式 litellm + 环境变量"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env-key")
        yaml_content = LITELLM_ANTHROPIC_FORMAT.format(api_key="${ANTHROPIC_API_KEY}")
        config = _make_config(tmp_path, yaml_content)

        llm = config.get("llm")
        assert llm["api_key"] == "sk-ant-env-key"


# ============================================================
# 3. TagExtractor.from_config() end-to-end mapping tests
# ============================================================

class TestTagExtractorConfigMapping:
    """TagExtractor.from_config() 配置映射端到端测试"""

    def test_dashscope_maps_to_litellm_provider(self, tmp_path):
        """dashscope 旧格式 → LiteLLMProvider(model='dashscope/qwen-plus')"""
        yaml_content = DASHSCOPE_OLD_FORMAT.format(api_key="sk-test-key")
        config = _make_config(tmp_path, yaml_content)

        with patch('kb.processors.tag_extractor.LiteLLMProvider') as mock_cls:
            mock_cls.return_value = Mock()
            from kb.processors.tag_extractor import TagExtractor
            extractor = TagExtractor.from_config(config)

            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args
            assert call_kwargs[1]["model"] == "dashscope/qwen-plus" or call_kwargs[0][1] == "dashscope/qwen-plus" if len(call_kwargs[0]) > 1 else True
            # Verify model mapping via keyword args
            all_args = {**dict(zip(["api_key", "model"], call_kwargs[0])), **call_kwargs[1]}
            assert "dashscope/qwen-plus" in str(all_args)
            assert "sk-test-key" in str(all_args)

    def test_openai_compatible_maps_to_litellm_provider(self, tmp_path):
        """openai_compatible 旧格式 → LiteLLMProvider(model='openai/...', api_base=...)"""
        yaml_content = OPENAI_COMPAT_OLD_FORMAT.format(api_key="sk-compat-key")
        config = _make_config(tmp_path, yaml_content)

        with patch('kb.processors.tag_extractor.LiteLLMProvider') as mock_cls:
            mock_cls.return_value = Mock()
            from kb.processors.tag_extractor import TagExtractor
            extractor = TagExtractor.from_config(config)

            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args
            all_args = {**dict(zip(["api_key", "model"], call_kwargs[0])), **call_kwargs[1]}
            assert "openai/custom-model" in str(all_args)
            assert "sk-compat-key" in str(all_args)
            assert "http://localhost:11434/v1" in str(all_args)

    def test_litellm_direct_passthrough(self, tmp_path):
        """litellm 新格式 → LiteLLMProvider 直通，model 不变"""
        yaml_content = LITELLM_NEW_FORMAT.format(api_key="sk-direct-key")
        config = _make_config(tmp_path, yaml_content)

        with patch('kb.processors.tag_extractor.LiteLLMProvider') as mock_cls:
            mock_cls.return_value = Mock()
            from kb.processors.tag_extractor import TagExtractor
            extractor = TagExtractor.from_config(config)

            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args
            all_args = {**dict(zip(["api_key", "model"], call_kwargs[0])), **call_kwargs[1]}
            assert "dashscope/qwen-plus" in str(all_args)
            assert "sk-direct-key" in str(all_args)

    def test_unsupported_provider_raises(self, tmp_path):
        """不支持的 provider 抛出 ValueError"""
        yaml_content = """
llm:
  provider: unsupported_provider
  model: some-model
  api_key: sk-key
"""
        config = _make_config(tmp_path, yaml_content)

        from kb.processors.tag_extractor import TagExtractor
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            TagExtractor.from_config(config)

    def test_missing_api_key_raises(self, tmp_path):
        """缺少 api_key 抛出 ValueError"""
        yaml_content = """
llm:
  provider: dashscope
  model: qwen-plus
  api_key: ""
"""
        config = _make_config(tmp_path, yaml_content)

        from kb.processors.tag_extractor import TagExtractor
        with pytest.raises(ValueError, match="API key is required"):
            TagExtractor.from_config(config)

    def test_openai_compatible_missing_base_url_raises(self, tmp_path):
        """openai_compatible 缺少 base_url 抛出 ValueError"""
        yaml_content = """
llm:
  provider: openai_compatible
  model: some-model
  api_key: sk-key
  base_url: ""
"""
        config = _make_config(tmp_path, yaml_content)

        from kb.processors.tag_extractor import TagExtractor
        with pytest.raises(ValueError, match="base_url is required"):
            TagExtractor.from_config(config)


# ============================================================
# 4. Config validate_services tests
# ============================================================

class TestConfigValidateServices:
    """Config.validate_services() 测试"""

    def test_raw_key_marks_available(self, tmp_path):
        """原始 key → llm_available=True"""
        yaml_content = DASHSCOPE_OLD_FORMAT.format(api_key="sk-real-key")
        config = _make_config(tmp_path, yaml_content)
        status = config.validate_services()
        assert status["llm_available"] is True

    def test_env_var_resolved_marks_available(self, tmp_path, monkeypatch):
        """环境变量已设置 → llm_available=True"""
        monkeypatch.setenv("TEST_LLM_KEY", "sk-resolved")
        yaml_content = DASHSCOPE_OLD_FORMAT.format(api_key="${TEST_LLM_KEY}")
        config = _make_config(tmp_path, yaml_content)
        status = config.validate_services()
        assert status["llm_available"] is True

    def test_env_var_unresolved_marks_unavailable(self, tmp_path):
        """环境变量未设置 → llm_available=False"""
        yaml_content = DASHSCOPE_OLD_FORMAT.format(api_key="${UNSET_KEY_XYZ_999}")
        config = _make_config(tmp_path, yaml_content)
        status = config.validate_services()
        assert status["llm_available"] is False

    def test_empty_key_marks_unavailable(self, tmp_path):
        """空 key → llm_available=False"""
        yaml_content = """
llm:
  provider: dashscope
  model: qwen-plus
  api_key: ""
"""
        config = _make_config(tmp_path, yaml_content)
        status = config.validate_services()
        assert status["llm_available"] is False


# ============================================================
# 5. Config file sync test (kb/ vs root)
# ============================================================

class TestConfigTemplateSync:
    """config-template.yaml 同步检查"""

    def test_root_and_kb_templates_in_sync(self):
        """根目录和 kb/ 下的 config-template.yaml 内容一致"""
        root_template = project_root / "config-template.yaml"
        kb_template = project_root / "kb" / "config-template.yaml"

        if not root_template.exists() or not kb_template.exists():
            pytest.skip("One or both config-template.yaml files not found")

        root_content = root_template.read_text(encoding="utf-8")
        kb_content = kb_template.read_text(encoding="utf-8")
        assert root_content == kb_content, (
            "config-template.yaml files are out of sync between root and kb/ directories"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
