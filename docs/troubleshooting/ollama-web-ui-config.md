# Web UI Ollama 配置更新

## 修改内容

将 Web 配置页面中 Ollama 的默认 URL 从 `http://localhost:11434/v1` 更新为 `http://localhost:11434`（去掉 `/v1` 后缀）。

## 修改的文件

### 1. `kb/web/static/index.html`

#### LLM 配置部分（第 4826、4830 行）

**修改前：**
```html
{{ locale === 'en' ? '(optional, default: http://localhost:11434/v1)' : '（可选，默认：http://localhost:11434/v1）' }}
...
:placeholder="llmSettings.provider === 'ollama' ? 'http://localhost:11434/v1' : 'https://your-api-endpoint/v1'"
```

**修改后：**
```html
{{ locale === 'en' ? '(optional, default: http://localhost:11434)' : '（可选，默认：http://localhost:11434）' }}
...
:placeholder="llmSettings.provider === 'ollama' ? 'http://localhost:11434' : 'https://your-api-endpoint/v1'"
```

#### Embedding 配置部分（第 4945、4949 行）

**修改前：**
```html
{{ locale === 'en' ? '(optional, default: http://localhost:11434/v1)' : '（可选，默认：http://localhost:11434/v1）' }}
...
:placeholder="embeddingSettings.provider === 'ollama' ? 'http://localhost:11434/v1' : ..."
```

**修改后：**
```html
{{ locale === 'en' ? '(optional, default: http://localhost:11434)' : '（可选，默认：http://localhost:11434）' }}
...
:placeholder="embeddingSettings.provider === 'ollama' ? 'http://localhost:11434' : ..."
```

### 2. 文档文件

- `kb/web/static/docs/configuration.html` - 配置文档
- `kb/web/static/docs/config-reference.html` - 配置参考文档

所有文档中的 `http://localhost:11434/v1` 都已更新为 `http://localhost:11434`。

## 原因

根据前面的分析，使用 Ollama 时应该：

1. **使用 `ollama/` 前缀**：`model: ollama/nomic-embed-text`
2. **使用原生 API 端点**：`base_url: http://localhost:11434`（不带 `/v1`）
3. **不传递 `encoding_format` 参数**

Ollama 的原生 API 端点是 `/api/embed`（embedding）和 `/api/generate`（completion），完整 URL 为：
- Embedding: `http://localhost:11434/api/embed`
- Completion: `http://localhost:11434/api/generate`

而 `/v1/embeddings` 是 OpenAI 兼容端点，会导致 `encoding_format` 参数问题。

## 验证

运行以下命令验证修改：

```bash
# 检查 index.html 中是否还有 /v1 后缀
grep "11434/v1" kb/web/static/index.html
# 应该返回 0 行

# 检查新的 URL
grep "localhost:11434" kb/web/static/index.html | grep -E "(placeholder|default)"
# 应该显示不带 /v1 的 URL
```

## 用户体验改进

修改后，用户在 Web UI 配置 Ollama 时：

1. **提示文本**显示正确的默认 URL：`http://localhost:11434`
2. **输入框占位符**显示正确的示例 URL：`http://localhost:11434`
3. **中英文界面**都已更新

这样可以避免用户配置错误的 URL，减少 `encoding_format` 参数冲突的问题。

## 相关修复

此修改配合以下代码修复：

- `kb/processors/embedder.py` - 自动过滤 ollama 的 `encoding_format` 参数
- `kb/config-template.yaml` - 更新配置模板示例
- `docs/ollama-embedding-fix.md` - 详细文档
- `docs/ollama-embedding-analysis.md` - 技术分析

## 测试建议

1. 启动 Web 服务器
2. 访问设置页面
3. 选择 Ollama 作为 LLM 或 Embedding provider
4. 验证 Base URL 的提示文本和占位符显示为 `http://localhost:11434`（不带 `/v1`）
5. 保存配置并测试连接
