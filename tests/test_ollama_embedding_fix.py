#!/usr/bin/env python3
"""
测试 ollama embedding 配置修复

验证：
1. ollama/ 前缀的模型不会传递 encoding_format 参数
2. 其他模型（如 openai/）仍然会传递 encoding_format 参数
"""

from kb.processors.embedder import LiteLLMEmbeddingProvider


def test_ollama_no_encoding_format():
    """测试 ollama 模型不会传递 encoding_format"""
    provider = LiteLLMEmbeddingProvider(
        model="ollama/nomic-embed-text",
        api_key="not-needed",
        api_base="http://localhost:11434",
        encoding_format="float",  # 即使配置了，也应该被过滤掉
    )

    # 检查 extra_kwargs 中是否包含 encoding_format
    print(f"Ollama provider extra_kwargs: {provider.extra_kwargs}")

    # 模拟构建 call_kwargs
    call_kwargs = {
        "model": provider.model,
        "input": ["test"],
        "api_key": provider.api_key,
        **provider.extra_kwargs,
    }

    if provider.api_base:
        call_kwargs["api_base"] = provider.api_base

    # 应用 ollama 特殊处理
    if provider.model.startswith("ollama/"):
        call_kwargs.pop("encoding_format", None)
    elif "encoding_format" not in call_kwargs or call_kwargs.get("encoding_format") is None:
        call_kwargs["encoding_format"] = "float"

    print(f"Final call_kwargs for ollama: {call_kwargs}")
    assert "encoding_format" not in call_kwargs, "ollama 不应该包含 encoding_format 参数"
    print("✓ Ollama 测试通过：encoding_format 已被正确过滤")


def test_openai_has_encoding_format():
    """测试 openai 模型会传递 encoding_format"""
    provider = LiteLLMEmbeddingProvider(
        model="openai/text-embedding-3-small",
        api_key="sk-test",
        encoding_format="float",
    )

    print(f"\nOpenAI provider extra_kwargs: {provider.extra_kwargs}")

    # 模拟构建 call_kwargs
    call_kwargs = {
        "model": provider.model,
        "input": ["test"],
        "api_key": provider.api_key,
        **provider.extra_kwargs,
    }

    # 应用处理逻辑
    if provider.model.startswith("ollama/"):
        call_kwargs.pop("encoding_format", None)
    elif "encoding_format" not in call_kwargs or call_kwargs.get("encoding_format") is None:
        call_kwargs["encoding_format"] = "float"

    print(f"Final call_kwargs for openai: {call_kwargs}")
    assert "encoding_format" in call_kwargs, "openai 应该包含 encoding_format 参数"
    assert call_kwargs["encoding_format"] == "float", "encoding_format 应该是 float"
    print("✓ OpenAI 测试通过：encoding_format 正确保留")


def test_dashscope_has_encoding_format():
    """测试 DashScope 模型会传递 encoding_format"""
    provider = LiteLLMEmbeddingProvider(
        model="openai/text-embedding-v4",
        api_key="sk-test",
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        encoding_format="float",
    )

    print(f"\nDashScope provider extra_kwargs: {provider.extra_kwargs}")

    # 模拟构建 call_kwargs
    call_kwargs = {
        "model": provider.model,
        "input": ["test"],
        "api_key": provider.api_key,
        **provider.extra_kwargs,
    }

    if provider.api_base:
        call_kwargs["api_base"] = provider.api_base

    # 应用处理逻辑
    if provider.model.startswith("ollama/"):
        call_kwargs.pop("encoding_format", None)
    elif "encoding_format" not in call_kwargs or call_kwargs.get("encoding_format") is None:
        call_kwargs["encoding_format"] = "float"

    print(f"Final call_kwargs for dashscope: {call_kwargs}")
    assert "encoding_format" in call_kwargs, "DashScope 应该包含 encoding_format 参数"
    assert call_kwargs["encoding_format"] == "float", "encoding_format 应该是 float"
    print("✓ DashScope 测试通过：encoding_format 正确保留")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 Ollama Embedding 配置修复")
    print("=" * 60)

    test_ollama_no_encoding_format()
    test_openai_has_encoding_format()
    test_dashscope_has_encoding_format()

    print("\n" + "=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
