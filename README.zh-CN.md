# Agentic Local Brain

[English](README.md) | [简体中文](README.zh-CN.md)

> 个人知识管理系统 — 从多个来源收集、处理和查询知识。

## 快速开始

**方式一：通过桌面 Agent 安装**

在你的桌面 Agent（OpenClaw / Hermes / Claude / Qoder / Codex / Trae 等）中，发出如下聊天内容即可启动你的构建本地大脑之旅：

```
帮我安装或更新这个知识收集技能：http://localbrain.oss-cn-shanghai.aliyuncs.com/skills/localbrain-collect/SKILL.md
```

就这么简单，Agent 会帮你完成一切。

**方式二：通过 CLI 安装**

如果你使用的是 CLI 命令行 Agent，可以直接安装技能：

```bash
npx skills add agent-creativity/agentic-local-brain
```

## 功能特性

- **多源收集**：文件（PDF、Markdown、文本）、网页、书签、学术论文、邮件和笔记
- **智能提取**：3 层标签和摘要提取（用户提供 → LLM → 内置回退）
- **智能搜索**：语义搜索、关键词搜索、基于 RAG 的问答 — 具有优雅降级
- **双重界面**：CLI（`localbrain`）和 REST API（FastAPI）
- **后台 Web 服务器**：以守护进程模式运行 Web 界面
- **优雅降级**：在没有 LLM/嵌入服务的情况下使用内置回退算法工作
- **跨平台**：灵活的安装选项 — Python 包（推荐，无安全警告）、独立二进制文件（无需 Python）或从源码安装
- **知识挖掘**（v0.6）：自动知识图谱构建、跨文档关系发现、主题聚类和趋势分析、基于阅读模式的智能推荐
- **增强检索**（v0.7）：多轮 RAG 对话，支持查询扩展、混合检索（关键词 + 语义融合 via RRF）、LLM 重排序、知识图谱上下文增强、可配置提示模板和对话历史管理
- **LLM Wiki**（v0.7）：使用 LLM 合成从主题集群自动生成 wiki 文章，包含实体摘要卡片、wiki 链接交叉引用（`[[entity-slug]]`）、过期跟踪和自动重新编译
- **知识库备份**（v0.8）：支持多种存储选项（本地、阿里云 OSS、AWS S3）的自动备份，使用 cron 表达式的定时备份、保留策略和一键恢复

## 安装

### 选项 1：Python 包安装（推荐）

适用于所有平台，无安全警告。需要 Python 3.8+。

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

安装程序将：
- 检查是否安装了 Python 3.8+
- 在 `~/.localbrain/venv` 创建虚拟环境
- 下载并安装 wheel 包
- 将 `localbrain` 添加到 PATH

### 选项 2：二进制安装（无需 Python）

适用于没有 Python 的系统。独立二进制文件，无依赖。

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

**macOS 注意：** 二进制文件需要绕过 Gatekeeper：
```bash
xattr -cr ~/.localbrain/bin/localbrain
```

### 选项 3：从源码安装

用于开发或自定义构建：

```bash
# 克隆仓库
git clone <repository-url>
cd agentic-local-brain

# 以开发模式安装
pip install -e .

# 验证安装
localbrain --version
```

### 安装后

安装后，验证并初始化：

```bash
# 检查安装
localbrain doctor

# 初始化知识库
localbrain init setup
```

### CLI 维护命令

| 命令 | 描述 |
|---------|-------------|
| `localbrain --version` | 显示已安装版本 |
| `localbrain doctor` | 运行系统诊断并验证配置 |
| `localbrain self-update` | 更新到最新版本 |
| `localbrain self-update --check` | 检查更新而不安装 |
| `localbrain self-update --rollback` | 回滚到上一个版本 |
| `localbrain uninstall` | 删除 LocalBrain（保留数据）|

## 使用示例

```bash
# 初始化知识库
localbrain init

# 收集知识
localbrain collect file add ~/documents/paper.pdf
localbrain collect webpage add https://example.com/article
localbrain collect paper add arxiv:2401.12345
localbrain collect email add ~/emails/message.eml
localbrain collect bookmark add https://example.com --tags "reference"
localbrain collect bookmark import --browser chrome
localbrain collect note add "关于机器学习的重要见解" --tags "ml" --summary "ML 见解笔记"

# 搜索
localbrain search semantic "机器学习"
localbrain search keyword "python"
localbrain search rag "什么是深度学习？"

# 管理标签
localbrain tag list
localbrain tag merge "ml" "machine-learning"

# 启动 Web 界面
localbrain web
localbrain web -b          # 后台模式
localbrain web --status    # 检查状态
localbrain web --stop      # 停止后台服务器
```

## CLI 命令参考

CLI 使用**对象优先（名词-动词）模式**以保持一致性。主要命令是 `localbrain`（`kb` 作为向后兼容的别名可用）。

### 收集命令

所有收集命令支持：
- `--tags, -t` — 手动提供标签（允许多个）
- `--summary, -s` — 手动提供摘要
- `--auto-extract / --no-auto-extract` — 自动提取标签和摘要（默认：启用）
- `--skip-existing` — 如果文档已收集则跳过

| 命令 | 描述 |
|---------|-------------|
| `localbrain collect file add <path>` | 添加本地文件（PDF、Markdown、文本）|
| `localbrain collect webpage add <url>` | 添加网页 |
| `localbrain collect paper add <source>` | 添加学术论文（arxiv:ID 或 URL）|
| `localbrain collect email add <path>` | 添加邮件（.eml 或 .mbox）|
| `localbrain collect bookmark add <url>` | 添加单个书签 |
| `localbrain collect bookmark import --browser <type>` | 从浏览器导入书签 |
| `localbrain collect bookmark import --file <html_file>` | 从 HTML 导出导入书签 |
| `localbrain collect note add <text>` | 创建知识笔记 |

### 搜索命令

所有搜索操作统一在 `search` 组下：

| 命令 | 描述 |
|---------|-------------|
| `localbrain search semantic <query>` | 基于向量的语义搜索 |
| `localbrain search keyword <keywords>` | 基于文本的关键词搜索 |
| `localbrain search rag <question>` | 基于 RAG 的问答，带 AI 生成答案 |
| `localbrain search tags -t <tag>` | 按标签查找项目 |

### 管理命令

| 命令 | 描述 |
|---------|-------------|
| `localbrain init` | 初始化知识库和配置 |
| `localbrain config show` | 显示当前配置 |
| `localbrain stats` | 显示知识库统计信息 |
| `localbrain tag list` | 列出所有标签 |
| `localbrain tag merge <source> <target>` | 合并两个标签 |
| `localbrain tag delete <name>` | 删除标签 |
| `localbrain export` | 导出知识库（markdown 或 JSON）|
| `localbrain test embedding` | 测试嵌入服务连接 |
| `localbrain test llm` | 测试 LLM 服务连接 |
| `localbrain mine run` | 运行批量知识挖掘（图谱、关系、主题、推荐）|
| `localbrain graph rebuild` | 重建知识图谱 |
| `localbrain graph stats` | 显示知识图谱统计信息 |
| `localbrain topics rebuild` | 重建主题集群 |
| `localbrain topics list` | 列出所有主题集群 |
| `localbrain web` | 启动 Web 界面（支持 -b 后台模式）|
| `localbrain doctor` | 运行系统诊断 |
| `localbrain self-update` | 更新到最新版本 |
| `localbrain self-update --check` | 检查更新 |
| `localbrain backup create` | 创建手动备份 |
| `localbrain backup list` | 列出所有备份 |
| `localbrain backup restore <filename>` | 从备份恢复 |
| `localbrain backup delete <filename>` | 删除备份 |
| `localbrain uninstall` | 删除 LocalBrain（保留数据）|

## 知识库备份（v0.8）

使用自动备份保护您的知识库，支持本地存储或云服务商：

**存储选项：**
- **本地** — 将备份存储在 `~/.localbrain/backups/`
- **阿里云 OSS** — 上传到 OSS 存储桶，支持自动生命周期管理
- **AWS S3** — 上传到 S3 存储桶，支持版本控制

**功能特性：**
- 定时自动备份（cron 表达式）
- 可配置的保留策略（自动删除旧备份）
- 从任何备份一键恢复
- 后台任务执行，带进度跟踪
- Web UI 备份管理和云存储配置

**CLI 命令：**
```bash
# 创建手动备份
localbrain backup create                    # 本地存储（默认）
localbrain backup create --cloud oss        # 上传到 OSS
localbrain backup create --cloud s3         # 上传到 S3

# 列出备份
localbrain backup list                      # 本地备份
localbrain backup list --cloud oss          # OSS 备份
localbrain backup list --cloud s3           # S3 备份

# 从备份恢复
localbrain backup restore backup-20260420-120000.tar.gz
localbrain backup restore backup-20260420-120000.tar.gz --cloud oss

# 删除备份
localbrain backup delete backup-20260420-120000.tar.gz
localbrain backup delete backup-20260420-120000.tar.gz --cloud oss
```

**Web UI 配置：**

在 Web 界面配置备份设置（设置 → 备份）：
1. 启用/禁用自动备份
2. 设置备份计划（cron 表达式，例如 `0 2 * * *` 表示每天凌晨 2 点）
3. 配置保留策略（保留备份的天数）
4. 选择存储位置（本地、OSS 或 S3）
5. 配置云存储凭证（端点、访问密钥、存储桶）

**配置示例：**
```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"        # 每天凌晨 2 点
  retention_days: 30            # 保留备份 30 天
  storage_location: oss         # local、oss 或 s3
  
  # 阿里云 OSS
  oss:
    endpoint: oss-cn-shanghai.aliyuncs.com
    access_key_id: ${OSS_ACCESS_KEY_ID}
    access_key_secret: ${OSS_ACCESS_KEY_SECRET}
    bucket: my-localbrain-backups
  
  # AWS S3
  s3:
    region: us-west-2
    access_key_id: ${AWS_ACCESS_KEY_ID}
    secret_access_key: ${AWS_SECRET_ACCESS_KEY}
    bucket: my-localbrain-backups
```

## 智能提取

收集文档时，标签和摘要使用**三层回退策略**自动提取：

```
┌─────────────────────────────────────────────────────┐
│ 第 1 层：用户提供（最高优先级）                      │
│   --tags "ai,ml" --summary "关于 ML"                │
│   → 直接使用，跳过提取                               │
├─────────────────────────────────────────────────────┤
│ 第 2 层：LLM 提取（DashScope / OpenAI）              │
│   提取 3-5 个标签 + 1-2 句摘要                       │
│   通过可配置的 LLM（qwen-plus、qwen-max 等）         │
├─────────────────────────────────────────────────────┤
│ 第 3 层：内置提取（始终可用）                         │
│   标签：TF-IDF 关键词评分，标题加权                   │
│   摘要：抽取式（选择最佳句子）                        │
│   零 AI 依赖，离线可用                               │
└─────────────────────────────────────────────────────┘
```

使用 `--no-auto-extract` 禁用自动提取：
```bash
localbrain collect file add paper.pdf --no-auto-extract
```

## 优雅降级

当 LLM 或嵌入服务不可用时，系统继续工作：

| 场景 | 影响 | 回退方案 |
|----------|--------|----------|
| 嵌入服务不可用 | 语义搜索禁用 | 回退到关键词搜索 |
| LLM 不可用 | RAG 答案生成禁用 | 返回搜索结果，不带 AI 答案 |
| LLM 不可用 | 自动标签降级 | 使用内置 TF-IDF 提取 |
| 两者都不可用 | 最小模式 | 仅关键词搜索 + 内置提取 |

无论服务可用性如何，文档**始终保存**到文件系统和 SQLite。使用 `localbrain test embedding` 和 `localbrain test llm` 验证服务连接。

## 增强 RAG（v0.7）

增强 RAG 系统提供多阶段检索管道，以获得更准确和上下文相关的答案：

```
查询 → 查询扩展 → 混合检索 → LLM 重排序 → 上下文增强 → 答案生成
       （重写与       （关键词 +        （相关性          （实体 + 主题）
        扩展）       语义 RRF）        评分）
```

**管道阶段：**
1. **查询扩展** — 重写和扩展查询以提高召回率
2. **混合检索** — 结合关键词（FTS5）和语义搜索，使用倒数排名融合（RRF）
3. **LLM 重排序** — 使用 LLM 按相关性评分和重新排序结果
4. **上下文增强** — 从知识图谱添加实体和主题上下文
5. **上下文组装** — 在预算内感知 token 的上下文构建
6. **答案生成** — LLM 合成带来源引用的答案

**多轮对话：**
```bash
# CLI：RAG 查询（单轮）
localbrain search rag "什么是机器学习？"

# API：带会话管理的多轮对话
POST /api/rag/chat
{
  "query": "能详细说说神经网络吗？",
  "session_id": "optional-session-id"
}
```

**可配置的提示模板：**
- `general` — 适用于日常问题的平衡模板
- `technical` — 针对代码和技术内容优化
- `academic` — 为研究主题结构化
- `creative` — 灵活用于创意探索

## LLM Wiki（v0.7）

LLM Wiki 功能将收集的知识合成为可读的 wiki 文章：

**功能说明：**
- **主题文章** — LLM 从主题集群中合成文档为连贯的参考文章
- **实体摘要卡片** — 跨多个文档出现的实体的简洁摘要
- **Wiki 链接交叉引用** — 文章使用 `[[entity-slug]]` 语法链接到相关实体
- **过期跟踪** — 自动检测源文档变更并标记文章需要重新编译

**CLI 命令：**
```bash
# 从主题集群编译 wiki 文章
localbrain wiki compile                 # 仅编译过期文章
localbrain wiki compile --force         # 重新编译所有文章

# 列出已编译的文章
localbrain wiki list                    # 层级视图（默认）
localbrain wiki list --flat             # 平面列表视图
localbrain wiki list --type entity      # 仅实体卡片

# 查看文章
localbrain wiki show <article-slug>     # 显示文章内容
```

**Web UI：** 通过 Web 界面的 Wiki 页面浏览，支持按主题和分类的层级导航。

**与挖掘管道集成：** Wiki 编译作为 `localbrain mine run` 的第 5 步集成。如需跳过，使用 `--skip-wiki`。

## Web API

启动 Web 服务器：
```bash
localbrain web                    # 前台运行
localbrain web -b                 # 后台运行（守护进程）
localbrain web -b -p 9090         # 自定义端口，后台运行
localbrain web --stop             # 停止后台服务器
localbrain web --status           # 检查服务器状态
```

API 端点（默认：http://localhost:11201）：

| 方法 | 端点 | 描述 |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | 知识库统计信息 |
| GET | `/api/items` | 列出知识项目 |
| GET | `/api/items/{id}` | 按 ID 获取项目 |
| GET | `/api/tags` | 列出所有标签 |
| POST | `/api/search/keyword` | 关键词搜索 |
| POST | `/api/search/semantic` | 语义搜索 |
| POST | `/api/search/rag` | RAG 查询 |
| GET | `/api/graph` | 知识图谱数据 |
| GET | `/api/knowledge/{id}/related` | 相关文档 |
| GET | `/api/topics` | 主题集群 |
| GET | `/api/topics/{id}/documents` | 主题中的文档 |
| GET | `/api/topics/trend` | 主题趋势 |
| GET | `/api/recommendations` | 智能推荐 |
| POST | `/api/rag/chat` | 增强 RAG 多轮对话 |
| GET | `/api/rag/conversations` | 列出对话会话 |
| GET | `/api/rag/conversations/{session_id}` | 获取完整对话 |
| DELETE | `/api/rag/conversations/{session_id}` | 删除对话 |
| POST | `/api/rag/suggest` | 查询建议 |
| GET | `/api/dashboard/rag-stats` | RAG 分析 |
| GET | `/api/wiki/tree` | Wiki 结构树 |
| GET | `/api/wiki/articles` | 列出文章（参数：article_type、limit、offset）|
| GET | `/api/wiki/articles/{article_id}` | 获取文章内容 |
| GET | `/api/wiki/search` | 搜索 wiki 文章 |
| GET | `/api/wiki/categories/{category_id}/articles` | 按分类获取文章 |
| GET | `/api/wiki/topics/{topic_id}/articles` | 按主题获取文章 |
| GET | `/api/wiki/entities` | 列出实体卡片 |
| GET | `/api/wiki/entities/{entity_id}` | 获取实体卡片 |
| GET | `/api/wiki/stats` | Wiki 统计信息 |

服务器运行时，API 文档可在 `http://localhost:11201/docs` 查看。

## 配置

配置文件：`~/.localbrain/config.yaml`

```yaml
data_dir: ~/.knowledge-base

# 更新服务器 URL（用于自更新功能）
update_server_url: http://localbrain.oss-cn-shanghai.aliyuncs.com

embedding:
  provider: litellm
  model: openai/text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  encoding_format: float

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
  rag:
    top_k: 5
    temperature: 0.3
    max_tokens: 1000
    context_budget: 4000
    context_format: hierarchical
    reranking:
      enabled: true
      top_n_candidates: 20
      weight_retrieval: 0.4
      weight_rerank: 0.6
    conversation:
      max_turns: 20
      session_timeout_minutes: 30
      history_turns_in_context: 5
    templates:
      default: general
  pipeline:
    top_k: 10
    rerank_top_k: 5
    context_budget: 4000

logging:
  log_dir: ""
  level: INFO
  max_bytes: 10485760
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

wiki:
  enabled: true
  max_source_tokens_per_topic: 8000
  entity_card_threshold: 3
  temperature: 0.3
  model: null
  max_article_words: 3000
  max_subcategories: 5
```

### 环境变量

| 变量 | 描述 |
|----------|-------------|
| `DASHSCOPE_API_KEY` | 阿里巴巴 DashScope API 密钥，用于嵌入和 LLM |
| `OPENAI_API_KEY` | OpenAI API 密钥（如果使用 OpenAI 提供商）|
| `KB_CONFIG_PATH` | 自定义配置文件路径（可选，默认 `~/.localbrain/config.yaml`）|

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户界面                            │
│  ┌──────────────┐              ┌─────────────────────┐  │
│  │ CLI (Click)  │              │  Web API (FastAPI)   │  │
│  │ localbrain   │              │  REST + 仪表板        │  │
│  └──────┬───────┘              └──────────┬──────────┘  │
└─────────┼────────────────────────────────┼──────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                      核心模块                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │   收集器    │  │    处理器    │  │     查询       │  │
│  │ - 文件      │  │ - 分块器    │  │ - 语义搜索     │  │
│  │ - 网页      │  │ - 嵌入器    │  │ - 关键词搜索   │  │
│  │ - 书签      │  │ - 标签提取  │  │ - RAG          │  │
│  │ - 论文      │  │ - 内置提取  │  │ - 图谱         │  │
│  │ - 邮件      │  │ - 实体提取  │  │ - 主题         │  │
│  │ - 笔记      │  │ - 主题聚类  │  │ - 推荐         │  │
│  │             │  │ - 文档关系  │  │                │  │
│  │             │  │ - 推荐      │  │                │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                      存储层                              │
│  ┌─────────────────────┐    ┌─────────────────────────┐ │
│  │   SQLite 存储       │    │    ChromaDB 存储         │ │
│  │ （元数据 + 标签）    │    │  （向量嵌入）            │ │
│  └─────────────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 开发

### 开发环境设置

```bash
# 克隆仓库
git clone <repository-url>
cd agentic-local-brain
```

### 构建 Python Wheel

构建 Python wheel 包用于分发：

```bash
# 为当前版本构建 wheel
python scripts/build_wheel.py --version 0.5.0

# 输出：
# dist/localbrain-0.5.0-py3-none-any.whl
# dist/localbrain-0.5.0-py3-none-any.whl.sha256
```

安装 wheel：

```bash
pip install dist/localbrain-0.5.0-py3-none-any.whl
```

### 构建二进制文件

构建独立二进制文件用于分发：

```bash
# 为当前平台构建
python scripts/build_binary.py --version 0.5.0

# 为特定平台构建
python scripts/build_binary.py --version 0.5.0 --platform macos-arm64
python scripts/build_binary.py --version 0.5.0 --platform linux-x64
python scripts/build_binary.py --version 0.5.0 --platform win-x64
```

构建的二进制文件放在 `dist/` 目录中，附带 SHA256 校验和。

### 构建完整发布包

构建准备部署的完整发布包：

```bash
# 构建全部（wheel + 当前平台二进制文件）
python scripts/build_release.py --version 0.5.0

# 仅构建 Python wheel
python scripts/build_release.py --version 0.5.0 --wheel-only

# 仅为特定平台构建二进制文件
python scripts/build_release.py --version 0.5.0 --binary-only --platform macos-arm64
```

### 发布目录结构

`dist/` 目录结构便于部署到 Web 服务器：

```
dist/
├── version.json                      # 版本信息，用于更新检查
├── python_installer/
│   ├── install.sh                    # macOS/Linux Python 安装脚本
│   ├── install.ps1                   # Windows PowerShell 安装脚本
│   └── packages/
│       ├── localbrain-0.5.0-py3-none-any.whl
│       └── localbrain-0.5.0-py3-none-any.whl.sha256
└── binary_installer/
    ├── install.sh                    # macOS/Linux 二进制安装脚本
    ├── install.ps1                   # Windows 二进制安装脚本
    └── releases/
        └── v0.5.0/
            ├── localbrain-macos-arm64
            ├── localbrain-macos-arm64.sha256
            ├── localbrain-macos-x64
            ├── localbrain-linux-arm64
            ├── localbrain-linux-x64
            ├── localbrain-win-x64.exe
            └── ...
```

**部署：** 将整个 `dist/` 目录复制到 Web 服务器。安装脚本根据 `version.json` 中的相对路径下载文件。

## 许可证

MIT

