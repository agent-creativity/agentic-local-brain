# LiteLLM Ollama Embedding 参数配置分析与解决方案

## 问题总结

使用 litellm 调用 ollama embedding 模型时，litellm 默认传递了 `encoding_format: 'float'` 参数，但 ollama 不支持这个参数，导致报错。

## 分析结果

### 1. LiteLLM 的 Ollama 支持方式

LiteLLM 支持两种方式调用 ollama embedding：

| 方式 | Model 前缀 | API 端点 | 是否传递 encoding_format | 结果 |
|------|-----------|----------|------------------------|------|
| 原生支持 | `ollama/` | `/api/embed` | ❌ 否 | ✅ 正常工作 |
| OpenAI 兼容 | `openai/` | `/v1/embeddings` | ✅ 是 | ❌ 报错 |

### 2. 问题根源

即使使用 `ollama/` 前缀，如果在配置文件中显式设置了 `encoding_format: float`，这个参数仍然会被传递，导致 ollama 报错。

**代码路径**：
```
配置文件 (config.yaml)
  ↓ encoding_format: float
embedder.py:556-558 (读取配置)
  ↓ extra_kwargs["encoding_format"] = encoding_format
LiteLLMEmbeddingProvider.__init__()
  ↓ self.extra_kwargs = kwargs
_embed_batch()
  ↓ call_kwargs = {..., **self.extra_kwargs}
litellm.embedding(**call_kwargs)
  ↓ 传递给 ollama
❌ 报错：UnsupportedParamsError
```

## 解决方案

### 实施的修复

我们在 `kb/processors/embedder.py` 中实施了**双重过滤机制**：

#### 修复 1：配置读取层面（第 556-560 行）

```python
encoding_format = embedding_config.get("encoding_format")

# Ollama doesn't support encoding_format parameter
# Only add encoding_format for providers that support it
if encoding_format and not model.startswith("ollama/"):
    extra_kwargs["encoding_format"] = encoding_format
```

**作用**：在创建 Provider 时就过滤掉 ollama 的 `encoding_format`。

#### 修复 2：API 调用层面（第 468-477 行）

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

**作用**：在调用 litellm API 前再次过滤，作为最后一道防线。

### 为什么需要双重过滤？

1. **配置层过滤**：提前过滤，避免不必要的参数传递
2. **调用层过滤**：兜底保护，确保即使有其他途径传入也能被过滤

这种设计确保了系统的健壮性。

## 配置指南

### ✅ 正确的 Ollama 配置

```yaml
embedding:
  provider: litellm
  model: ollama/nomic-embed-text  # 使用 ollama/ 前缀
  api_key: not-needed
  base_url: http://localhost:11434  # 不需要 /v1 后缀
  # 不要设置 encoding_format
```

### ✅ DashScope 配置（需要 encoding_format）

```yaml
embedding:
  provider: litellm
  model: openai/text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  encoding_format: float  # DashScope 需要此参数
```

### ✅ OpenAI 配置

```yaml
embedding:
  provider: litellm
  model: openai/text-embedding-3-small
  api_key: ${OPENAI_API_KEY}
  # encoding_format 可选
```

## 技术细节

### Ollama 支持的参数

根据 LiteLLM 源码分析（`llms/ollama/completion/handler.py:17`），ollama embedding 支持：

- ✅ `truncate` - 截断过长输入
- ✅ `options` - 模型选项
- ✅ `keep_alive` - 模型保持加载时间
- ✅ `dimensions` - 输出向量维度
- ❌ `encoding_format` - **不支持**

### LiteLLM 源码关键位置

1. **OpenAI 兼容模式处理**（`main.py:4915-4919`）
   - 强制设置 `encoding_format`，即使为 `None` 也会传递

2. **Ollama 原生处理**（`llms/ollama/completion/handler.py:13-26`）
   - 只处理特定参数，不包含 `encoding_format`

3. **OpenAI-like Handler**（`llms/openai_like/embedding/handler.py:108-111`）
   - 过滤空值参数，但不会过滤 `encoding_format`

## 测试验证

运行测试：

```bash
source .venv/bin/activate
python test_ollama_embedding_fix.py
```

测试结果：
```
✓ Ollama 测试通过：encoding_format 已被正确过滤
✓ OpenAI 测试通过：encoding_format 正确保留
✓ DashScope 测试通过：encoding_format 正确保留
```

## 相关文件

- ✅ `kb/processors/embedder.py` - 核心修复代码
- ✅ `kb/config-template.yaml` - 配置模板更新
- ✅ `test_ollama_embedding_fix.py` - 测试脚本
- ✅ `docs/ollama-embedding-fix.md` - 详细文档
- ✅ `docs/ollama-embedding-analysis.md` - 本分析文档

## 结论

通过在配置读取和 API 调用两个层面实施过滤机制，我们成功解决了 ollama embedding 的 `encoding_format` 参数冲突问题。

**关键要点**：
1. 使用 `ollama/` 前缀而不是 `openai/` 前缀
2. 不要在配置中为 ollama 设置 `encoding_format`
3. 代码会自动过滤不支持的参数
4. 其他 provider（OpenAI、DashScope）不受影响

修复后，用户可以在配置文件中统一设置 `encoding_format: float`（为 DashScope 等需要的 provider），系统会自动为 ollama 过滤掉这个参数。
