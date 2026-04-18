# 配置文件说明

## 配置模板位置

**唯一的配置模板文件**: `kb/config-template.yaml`

这是代码中实际使用的配置模板文件，位于 `kb` 包内部。

## 为什么只有一个模板文件？

之前根目录也有一个 `config-template.yaml`，但这会导致：
1. 两个文件容易不同步
2. 开发者不清楚应该修改哪个
3. 用户可能看到过时的配置示例

因此我们删除了根目录的模板文件，只保留 `kb/config-template.yaml`。

## 代码引用

在 `kb/commands/utils.py` 中：
```python
TEMPLATE_FILE = Path(__file__).parent.parent / "config-template.yaml"
```

这会解析为 `kb/config-template.yaml`。

## 如何修改配置模板

1. 编辑 `kb/config-template.yaml`
2. 同步更新 `kb/config.py` 中的 `DEFAULT_CONFIG`
3. 提交更改

## 用户配置文件

用户的实际配置文件位于：
- `~/.localbrain/config.yaml`

这个文件在运行 `localbrain init setup` 时从 `kb/config-template.yaml` 复制而来。

## 配置迁移

当添加新的配置项时：
1. 更新 `kb/config-template.yaml`
2. 更新 `kb/config.py` 中的 `DEFAULT_CONFIG`
3. `localbrain init setup` 会自动检测并添加缺失的配置项到用户的配置文件

## 当前配置结构

```yaml
data_dir: ~/.knowledge-base
update_server_url: http://localbrain.oss-cn-shanghai.aliyuncs.com

embedding:
  provider: litellm
  model: openai/text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1

llm:
  provider: litellm
  model: dashscope/qwen-plus
  api_key: ${DASHSCOPE_API_KEY}

chunking:
  max_chunk_size: 1000
  chunk_overlap: 100

storage:
  type: chroma
  persist_directory: ~/.knowledge-base/db/chroma

query:
  rag: {...}
  pipeline: {...}

logging:
  log_dir: ""
  level: INFO
  max_bytes: 10485760
  backup_count: 5

wiki:
  enabled: true
  max_source_tokens_per_topic: 8000
  entity_card_threshold: 3
  temperature: 0.3

backup:
  enabled: false
  schedule: "0 2 * * *"
  retention_days: 30
  backup_dir: ~/.knowledge-base/backups
  include_db: true
  include_files: true
  compression: true
  cloud_provider: oss
  oss: {...}
  s3: {...}
```

## 注意事项

- 不要在根目录创建新的配置模板文件
- 所有配置修改都应该在 `kb/config-template.yaml` 中进行
- 修改后记得同步更新 `DEFAULT_CONFIG`
