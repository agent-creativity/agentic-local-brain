# Ollama Embedding 配置问题修复

## 问题描述

使用 litellm 调用 ollama embedding 模型时，litellm 默认传递了 `encoding_format: 'float'` 参数，但 ollama 不支持这个参数，导致报错：

```
litellm.UnsupportedParamsError: Setting {'encoding_format': 'float'} is not supported by ollama.
```

## 根本原因

### LiteLLM 的两种 Ollama 调用方式

1. **使用 `ollama/` 前缀（原生支持）**
   - 调用 `ollama.ollama_embeddings()` 函数
   - 直接访问 ollama 的 `/api/embed` 端点
   - 不会传递 `encoding_format` 参数
   - ✅ 正确方式

2. **使用 `openai/` 前缀（OpenAI 兼容模式）**
   - 调用 `openai_like_embedding.embedding()` 函数
   - 访问 ollama 的 `/v1/embeddings` 端点
   - 会传递 `encoding_format` 参数
   - ❌ 导致错误

### 代码层面的问题

即使使用 `ollama/` 前缀，如果在配置文件中显式设置了 `encoding_format: float`，这个参数仍然会被传递给 litellm，导致报错。

问题代码位置：
- `kb/processors/embedder.py:556-558` - 从配置读取 `encoding_format`
- `kb/processors/embedder.py:468-470` - 传递给 litellm

## 解决方案

### 修复内容

我们在两个层面进行了修复：

#### 1. 配置读取层面（`embedder.py:556-560`）

```python
# Ollama doesn't support encoding_format parameter
# Only add encoding_format for providers that support it
if encoding_format and not model.startswith("ollama/"):
    extra_kwargs["encoding_format"] = encoding_format
```

**作用**：在创建 `LiteLLMEmbeddingProvider` 时，如果模型是 `ollama/` 前缀，就不传递 `encoding_format` 参数。

#### 2. API 调用层面（`embedder.py:468-477`）

```python
# Handle encoding_format based on provider
# Ollama doesn't support encoding_format parameter
if self.model.startswith("ollama/"):
    # Remove encoding_format for ollama
    call_kwargs.pop("encoding_format", None)
elif "encoding_format" not in call_kwargs or call_kwargs.get("encoding_format") is None:
    # Prevent litellm from sending encoding_format=None (rejected by some providers like DashScope)
    call_kwargs["encoding_format"] = "float"
```

**作用**：在实际调用 litellm API 时，再次检查并移除 ollama 的 `encoding_format` 参数。

### 双重保护的原因

采用两层过滤的原因：

1. **配置层过滤**：避免不必要的参数传递，提高代码清晰度
2. **调用层过滤**：作为最后一道防线，确保即使有其他途径传入 `encoding_format`，也能被正确过滤

## 正确的配置方式

### Ollama 配置（推荐）

```yaml
embedding:
  provider: litellm
  model: ollama/nomic-embed-text  # 使用 ollama/ 前缀
  api_key: not-needed
  base_url: http://localhost:11434  # 不需要 /v1 后缀
  # 注意：不要设置 encoding_format 参数
```

### DashScope 配置

```yaml
embedding:
  provider: litellm
  model: openai/text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  encoding_format: float  # DashScope 需要这个参数
```

### OpenAI 配置

```yaml
embedding:
  provider: litellm
  model: openai/text-embedding-3-small
  api_key: ${OPENAI_API_KEY}
  # encoding_format 可选，默认为 float
```

## 测试验证

运行测试脚本验证修复：

```bash
source .venv/bin/activate
python test_ollama_embedding_fix.py
```

测试覆盖：
- ✓ Ollama 模型不会传递 `encoding_format` 参数
- ✓ OpenAI 模型正确传递 `encoding_format` 参数
- ✓ DashScope 模型正确传递 `encoding_format` 参数

## 技术细节

### LiteLLM 源码分析

1. **OpenAI 兼容模式**（`main.py:4915-4919`）
   ```python
   if encoding_format is not None:
       optional_params["encoding_format"] = encoding_format
   else:
       # Omiting causes openai sdk to add default value of "float"
       optional_params["encoding_format"] = None
   ```

2. **Ollama 原生模式**（`llms/ollama/completion/handler.py:13-26`）
   ```python
   def _prepare_ollama_embedding_payload(
       model: str, prompts: List[str], optional_params: Dict[str, Any]
   ) -> Dict[str, Any]:
       data: Dict[str, Any] = {"model": model, "input": prompts}
       special_optional_params = ["truncate", "options", "keep_alive", "dimensions"]
       # 注意：special_optional_params 中没有 encoding_format
   ```

### 支持的 Ollama 参数

根据 litellm 源码，ollama embedding 支持的参数：
- `truncate` - 是否截断过长的输入
- `options` - 模型选项（如温度、top_p 等）
- `keep_alive` - 模型保持加载的时间
- `dimensions` - 输出向量的维度

**不支持**：`encoding_format`

## 相关文件

- `kb/processors/embedder.py` - 主要修复代码
- `kb/config-template.yaml` - 配置模板更新
- `test_ollama_embedding_fix.py` - 测试脚本
- `docs/ollama-embedding-fix.md` - 本文档

## 参考资料

- [LiteLLM Embedding 文档](https://docs.litellm.ai/docs/embedding/supported_embedding)
- [Ollama API 文档](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings)
- [LiteLLM 源码 - Ollama Handler](https://github.com/BerriAI/litellm/blob/main/litellm/llms/ollama/completion/handler.py)
