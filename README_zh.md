# Agentic Local Brain

> 本文档为中文版，English version: [README.md](README.md)

> 个人知识管理系统 —— 从多个来源收集、处理和查询知识。

## 功能特性

- **多源收集**：文件（PDF、Markdown、文本）、网页、书签、学术论文、邮件和笔记
- **智能提取**：三层标签和摘要提取（用户提供 → LLM → 内置降级方案）
- **智能搜索**：语义搜索、关键词搜索、基于 RAG 的问答 —— 支持优雅降级
- **双界面**：CLI（`localbrain`）和 REST API（FastAPI）
- **后台 Web 服务**：以守护进程方式运行 Web 界面
- **优雅降级**：无需 LLM/嵌入服务即可工作，使用内置降级算法
- **跨平台支持**：灵活多样的安装方式 — Python 包安装（推荐，无安全警告）、独立二进制文件（无需 Python）、或从源码安装
- **知识挖掘** (v0.6)：自动知识图谱构建、跨文档关系发现、主题聚类与趋势分析、基于阅读模式的智能推荐
- **增强检索** (v0.7)：多阶段检索管线（查询扩展 → 混合检索 → LLM 重排序 → 上下文增强 → 答案生成）、多轮对话支持、可配置提示词模板
- **LLM Wiki 知识百科** (v0.7)：利用 LLM 将知识合成为主题文章和实体摘要卡片、Wiki 链接交叉引用、过期追踪与自动重编译、Web 百科浏览器

## 安装

### 方式一：Python方式安装（推荐）

在所有平台上均可正常工作，无安全警告。需要 Python 3.8+。

**macOS / Linux：**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
```

**Windows (PowerShell)：**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

安装程序将会：
- 检查 Python 3.8+ 是否已安装
- 在 `~/.localbrain/venv` 创建虚拟环境
- 下载并安装 wheel 包
- 将 `localbrain` 添加到 PATH

### 方式二：二进制安装（无需 Python）

适用于没有 Python 的系统。独立二进制文件，无依赖，但是安装过程中有可能被安全软件报警，忽略即可。

**macOS / Linux：**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

**Windows (PowerShell)：**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

**macOS 注意事项：** 二进制文件需要绕过 Gatekeeper：
```bash
xattr -cr ~/.localbrain/bin/localbrain
```

### 方式三：从源码安装

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

安装完成后，验证并初始化：

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
| `localbrain self-update --check` | 检查更新但不安装 |
| `localbrain self-update --rollback` | 回滚到上一个版本 |
| `localbrain uninstall` | 卸载 LocalBrain（保留数据） |

## 快速开始

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
localbrain collect note add "关于机器学习的重要见解" --tags "ml" --summary "机器学习见解笔记"

# 搜索
localbrain search semantic "machine learning"
localbrain search keyword "python"
localbrain search rag "What is deep learning?"

# 管理标签
localbrain tag list
localbrain tag merge "ml" "machine-learning"

# 启动 Web 界面
localbrain web
localbrain web -b          # 后台模式
localbrain web --status    # 查看状态
localbrain web --stop      # 停止后台服务
```

## CLI 命令参考

CLI 采用**对象优先（名词-动词）模式**以保持一致性。主命令为 `localbrain`（`kb` 作为向后兼容的别名可用）。

### 收集命令

所有收集命令均支持：
- `--tags, -t` —— 手动提供标签（可多次指定）
- `--summary, -s` —— 手动提供摘要
- `--auto-extract / --no-auto-extract` —— 自动提取标签和摘要（默认：启用）
- `--skip-existing` —— 如果文档已收集则跳过

| 命令 | 描述 |
|---------|-------------|
| `localbrain collect file add <path>` | 添加本地文件（PDF、Markdown、文本） |
| `localbrain collect webpage add <url>` | 添加网页 |
| `localbrain collect paper add <source>` | 添加学术论文（arxiv:ID 或 URL） |
| `localbrain collect email add <path>` | 添加邮件（.eml 或 .mbox） |
| `localbrain collect bookmark add <url>` | 添加单个书签 |
| `localbrain collect bookmark import --browser <type>` | 从浏览器导入书签 |
| `localbrain collect bookmark import --file <html_file>` | 从 HTML 导出文件导入书签 |
| `localbrain collect note add <text>` | 创建知识笔记 |

### 搜索命令

所有搜索操作统一在 `search` 分组下：

| 命令 | 描述 |
|---------|-------------|
| `localbrain search semantic <query>` | 基于向量的语义搜索 |
| `localbrain search keyword <keywords>` | 基于文本的关键词搜索 |
| `localbrain search rag <question>` | 基于 RAG 的问答，生成 AI 回答 |
| `localbrain search tags -t <tag>` | 按标签查找条目 |

### 管理命令

| 命令 | 描述 |
|---------|-------------|
| `localbrain init` | 初始化知识库和配置 |
| `localbrain config show` | 显示当前配置 |
| `localbrain stats` | 显示知识库统计信息 |
| `localbrain tag list` | 列出所有标签 |
| `localbrain tag merge <source> <target>` | 合并两个标签 |
| `localbrain tag delete <name>` | 删除标签 |
| `localbrain export` | 导出知识库（markdown 或 JSON） |
| `localbrain test embedding` | 测试嵌入服务连接 |
| `localbrain test llm` | 测试 LLM 服务连接 |
| `localbrain mine run` | 运行批量知识挖掘（图谱、关系、主题、推荐） |
| `localbrain graph rebuild` | 重建知识图谱 |
| `localbrain graph stats` | 显示知识图谱统计信息 |
| `localbrain topics rebuild` | 重建主题聚类 |
| `localbrain topics list` | 列出所有主题聚类 |
| `localbrain web` | 启动 Web 界面（支持 -b 后台模式） |
| `localbrain doctor` | 运行系统诊断 |
| `localbrain self-update` | 更新到最新版本 |
| `localbrain self-update --check` | 检查更新 |
| `localbrain uninstall` | 卸载 LocalBrain（保留数据） |

## 智能提取

收集文档时，标签和摘要通过**三层降级策略**自动提取：

```
┌─────────────────────────────────────────────────────┐
│ Tier 1: User-Provided (highest priority)            │
│   --tags "ai,ml" --summary "About ML"               │
│   → Used directly, extraction skipped               │
├─────────────────────────────────────────────────────┤
│ Tier 2: LLM Extraction (DashScope / OpenAI)         │
│   Extracts 3-5 tags + 1-2 sentence summary          │
│   via configurable LLM (qwen-plus, qwen-max, etc.)  │
├─────────────────────────────────────────────────────┤
│ Tier 3: Built-in Extraction (always available)       │
│   Tags: TF-IDF keyword scoring with title boosting   │
│   Summary: Extractive (selects best sentences)       │
│   Zero AI dependencies, works offline                │
└─────────────────────────────────────────────────────┘
```

使用 `--no-auto-extract` 禁用自动提取：
```bash
localbrain collect file add paper.pdf --no-auto-extract
```

## 优雅降级

当 LLM 或嵌入服务不可用时，系统仍可继续工作：

| 场景 | 影响 | 降级方案 |
|----------|--------|----------|
| 嵌入服务不可用 | 语义搜索禁用 | 降级为关键词搜索 |
| LLM 不可用 | RAG 回答生成禁用 | 返回搜索结果，无 AI 回答 |
| LLM 不可用 | 自动标签降级 | 使用内置 TF-IDF 提取 |
| 两者均不可用 | 极简模式 | 仅关键词搜索 + 内置提取 |

无论服务可用性如何，文档**始终保存**到文件系统和 SQLite。使用 `localbrain test embedding` 和 `localbrain test llm` 验证服务连接。

## 增强 RAG (v0.7)

增强 RAG 系统采用多阶段检索管线，提供高质量的 AI 问答体验：

### 多阶段检索管线

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 查询扩展 (Query Expansion)                                   │
│     → LLM 重写和扩展查询以提高召回率                              │
├─────────────────────────────────────────────────────────────────┤
│  2. 混合检索 (Hybrid Retrieval)                                  │
│     → 关键词搜索 + 语义搜索（RRF 融合排序）                        │
├─────────────────────────────────────────────────────────────────┤
│  3. LLM 重排序 (LLM Reranking)                                   │
│     → 使用 LLM 对候选文档进行相关性评分和重新排序                   │
├─────────────────────────────────────────────────────────────────┤
│  4. 上下文增强 (Context Enrichment)                              │
│     → 注入相关实体、主题和知识图谱关系                              │
├─────────────────────────────────────────────────────────────────┤
│  5. Token 感知组装 (Token-Aware Assembly)                        │
│     → 智能打包上下文以适应 LLM 上下文窗口                          │
├─────────────────────────────────────────────────────────────────┤
│  6. 答案生成 (Answer Generation)                                 │
│     → 使用可配置提示词模板生成带引用的答案                          │
└─────────────────────────────────────────────────────────────────┘
```

### 多轮对话支持

维护跨多轮对话的会话上下文：

```bash
# 开始新对话（自动创建会话）
localbrain search rag "解释机器学习"

# 继续对话（使用 --conversation 指定会话 ID）
localbrain search rag "深度学习和它有什么区别？" --conversation <session_id>

# 查看所有对话会话
# 通过 Web API: GET /api/rag/conversations

# 删除对话
# 通过 Web API: DELETE /api/rag/conversations/{session_id}
```

### 可配置提示词模板

选择适合您查询类型的提示词模板：

| 模板 | 用途 | 特点 |
|------|------|------|
| `general` | 通用问答 | 平衡、对话式回答 |
| `technical` | 技术文档 | 精确、结构化、包含代码示例 |
| `academic` | 学术研究 | 正式、引用驱动、方法论 |
| `creative` | 头脑风暴 | 开放式、探索性、多角度 |

在配置文件中设置默认模板：
```yaml
query:
  rag:
    templates:
      default: technical
```

### CLI 使用示例

```bash
# 基本 RAG 查询
localbrain search rag "什么是向量数据库？"

# 使用特定模板
localbrain search rag "解释 RAG 架构" --template technical

# 多轮对话（后续问题）
localbrain search rag "有哪些流行的实现？" --conversation <session_id>

# 获取查询建议
# 通过 Web API: POST /api/rag/suggest
```

### Web API 使用示例

```bash
# 多轮对话 RAG
curl -X POST http://localhost:11201/api/rag/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "解释 RAG 检索管线",
    "template": "technical",
    "session_id": "optional-existing-session"
  }'

# 响应包含：
# - answer: 生成的答案
# - sources: 带相关性和置信度分数的引用来源
# - session_id: 用于后续问题的会话 ID
# - confidence: 整体答案置信度
```

## LLM Wiki 知识百科 (v0.7)

LLM Wiki 功能利用大型语言模型将您收集的知识合成为结构化的主题文章和实体摘要卡片，创建可浏览、可交叉引用的知识百科。

### 功能特性

**主题文章 (Topic Articles)**
- 从主题聚类自动生成全面的主题文章
- 包含摘要、关键点、相关概念和引用来源
- 分层组织，支持分类和子分类

**实体摘要卡片 (Entity Cards)**
- 为频繁出现的实体（人物、组织、概念）创建摘要卡片
- 显示定义、属性、相关主题和出现次数
- 自动链接到相关主题文章

**Wiki 链接与交叉引用**
- 文章之间的双向链接（`[[Article Name]]` 语法）
- 自动发现相关主题和实体
- 通过知识图谱关系进行导航

**过期追踪与重编译**
- 追踪源文档修改时间
- 当底层知识变化时自动检测过期文章
- 支持增量重编译（仅更新变更的主题）

**Web 百科浏览器**
- 在 Web UI 中浏览所有 Wiki 文章
- 支持分类视图和搜索
- 查看文章历史版本

### CLI 命令

| 命令 | 描述 |
|---------|-------------|
| `localbrain wiki compile` | 将主题聚类编译为 Wiki 文章 |
| `localbrain wiki compile --force` | 重新生成所有文章（忽略过期状态） |
| `localbrain wiki list` | 列出所有编译的 Wiki 文章（分层视图） |
| `localbrain wiki list --flat` | 以扁平列表形式显示文章 |
| `localbrain wiki list --type topic` | 仅显示主题文章 |
| `localbrain wiki list --type entity` | 仅显示实体卡片 |
| `localbrain wiki show <slug>` | 在终端中显示 Wiki 文章内容 |

### CLI 使用示例

```bash
# 编译 Wiki 文章（仅更新过期的主题）
localbrain wiki compile

# 强制重新编译所有文章
localbrain wiki compile --force

# 以分层视图列出所有文章
localbrain wiki list

# 扁平列表视图
localbrain wiki list --flat

# 仅显示实体卡片
localbrain wiki list --type entity

# 在终端中阅读文章
localbrain wiki show "machine-learning"
```

### 与知识挖掘集成

Wiki 编译与知识挖掘管线集成：

```bash
# 运行完整挖掘（包括 Wiki 生成）
localbrain mine run

# 挖掘步骤包括：
# 1. 实体提取
# 2. 主题聚类
# 3. 跨文档关系发现
# 4. 生成推荐
# 5. 编译 Wiki 文章 ← 最后一步
```

### Web UI 浏览器

启动 Web 界面以浏览 Wiki：

```bash
localbrain web
```

然后访问 `http://localhost:11201` 并点击导航菜单中的 **"Wiki"** 以：
- 按分类浏览文章
- 阅读格式化的 Markdown 文章
- 点击 Wiki 链接导航
- 查看相关主题和实体

## Web API

启动 Web 服务：
```bash
localbrain web                    # 前台运行
localbrain web -b                 # 后台运行（守护进程）
localbrain web -b -p 9090         # 自定义端口，后台运行
localbrain web --stop             # 停止后台服务
localbrain web --status           # 查看服务状态
```

API 端点（默认：http://localhost:11201）：

| 方法 | 端点 | 描述 |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | 知识库统计信息 |
| GET | `/api/items` | 列出知识条目 |
| GET | `/api/items/{id}` | 按 ID 获取条目 |
| GET | `/api/tags` | 列出所有标签 |
| POST | `/api/search/keyword` | 关键词搜索 |
| POST | `/api/search/semantic` | 语义搜索 |
| POST | `/api/search/rag` | RAG 查询 |
| GET | `/api/graph` | 知识图谱数据 |
| GET | `/api/knowledge/{id}/related` | 相关文档 |
| GET | `/api/topics` | 主题聚类 |
| GET | `/api/topics/{id}/documents` | 主题下的文档 |
| GET | `/api/topics/trend` | 主题趋势 |
| GET | `/api/recommendations` | 智能推荐 |
| POST | `/api/rag/chat` | 支持多轮对话的增强 RAG |
| GET | `/api/rag/conversations` | 列出对话会话 |
| GET | `/api/rag/conversations/{session_id}` | 获取完整对话 |
| DELETE | `/api/rag/conversations/{session_id}` | 删除对话 |
| POST | `/api/rag/suggest` | 查询建议 |
| GET | `/api/dashboard/rag-stats` | RAG 分析统计 |
| GET | `/api/wiki/tree` | Wiki 结构树 |
| GET | `/api/wiki/articles` | 文章列表（参数: article_type, limit, offset） |
| GET | `/api/wiki/articles/{article_id}` | 获取文章内容 |
| GET | `/api/wiki/search` | 搜索百科文章 |
| GET | `/api/wiki/categories/{category_id}/articles` | 按分类查看文章 |
| GET | `/api/wiki/topics/{topic_id}/articles` | 按主题查看文章 |
| GET | `/api/wiki/entities` | 实体卡片列表 |
| GET | `/api/wiki/entities/{entity_id}` | 获取实体卡片 |
| GET | `/api/wiki/stats` | 百科统计 |

服务运行时可访问 `http://localhost:11201/docs` 查看 API 文档。

## 配置

配置文件：`~/.localbrain/config.yaml`

```yaml
# 数据目录路径
data_dir: ~/.knowledge-base

# 更新服务器（用于自更新功能）
update_server_url: http://localbrain.oss-cn-shanghai.aliyuncs.com

# 嵌入模型配置（通过 LiteLLM 统一调用）
embedding:
  provider: litellm
  model: openai/text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  encoding_format: float

# 大语言模型配置（通过 LiteLLM 统一调用）
llm:
  provider: litellm
  model: dashscope/qwen-plus
  api_key: ${DASHSCOPE_API_KEY}

# 文本分块配置
chunking:
  max_chunk_size: 1000
  chunk_overlap: 100

# 存储配置
storage:
  type: chroma
  persist_directory: ~/.knowledge-base/db/chroma

# 查询配置
query:
  # RAG 查询配置
  rag:
    top_k: 5                    # RAG 检索的文档数量
    temperature: 0.3             # LLM 生成温度
    max_tokens: 1000             # LLM 最大 token 数
    context_budget: 4000         # LLM 上下文 token 预算
    context_format: hierarchical # 上下文格式: hierarchical (分层) 或 flat (扁平)
    # 重排序配置（使用 LLM 对检索结果进行相关性评分）
    reranking:
      enabled: true              # 是否启用 LLM 重排序
      top_n_candidates: 20       # 参与重排序的候选文档数量
      weight_retrieval: 0.4      # 检索分数权重
      weight_rerank: 0.6         # 重排序分数权重
    # 多轮对话配置
    conversation:
      max_turns: 20              # 单个会话最大轮数
      session_timeout_minutes: 30  # 会话超时时间（分钟）
      history_turns_in_context: 5  # 注入上下文的最近轮数
    # 提示词模板配置
    templates:
      default: general           # 默认模板: general, technical, academic, creative
      # 自定义模板示例 (取消注释以启用):
      # custom: |
      #   You are a specialized assistant for {domain}.
      #   {context}
      #   Question: {question}
  # 检索流水线配置
  pipeline:
    top_k: 10                    # 检索阶段返回的文档数量
    rerank_top_k: 5              # 重排序后返回的文档数量
    context_budget: 4000         # LLM 上下文 token 预算（备用）

# 日志配置（用于后台 Web 服务模式）
logging:
  log_dir: ""              # 日志目录（默认: ~/.localbrain/logs/）
  level: INFO              # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
  max_bytes: 10485760      # 日志文件最大字节数（默认: 10MB）
  backup_count: 5          # 保留的轮转备份文件数量
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Wiki 编译配置
wiki:
  enabled: true                        # 挖掘期间启用 Wiki 文章生成
  max_source_tokens_per_topic: 8000    # 每个主题的最大源文档 token 数
  entity_card_threshold: 3             # 实体卡片的最小主题出现次数
  temperature: 0.3                     # 编译的 LLM 温度
  model: null                          # null = 使用默认 LLM 模型
  max_article_words: 3000              # 每篇文章的目标最大字数
  max_subcategories: 5                 # 每个主题的最大子分类数
```

### 环境变量

| 变量 | 描述 |
|----------|-------------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API 密钥，用于嵌入和 LLM |
| `OPENAI_API_KEY` | OpenAI API 密钥（如使用 OpenAI 提供商） |
| `KB_CONFIG_PATH` | 自定义配置文件路径（可选，默认为 `~/.localbrain/config.yaml`） |

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│  ┌──────────────┐              ┌─────────────────────┐  │
│  │ CLI (Click)  │              │  Web API (FastAPI)   │  │
│  │ localbrain   │              │  REST + Dashboard    │  │
│  └──────┬───────┘              └──────────┬──────────┘  │
└─────────┼────────────────────────────────┼──────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Core Modules                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Collectors  │  │  Processors  │  │     Query      │  │
│  │ - File      │  │ - Chunker    │  │ - Semantic     │  │
│  │ - Webpage   │  │ - Embedder   │  │ - Keyword      │  │
│  │ - Bookmark  │  │ - TagExtract │  │ - RAG          │  │
│  │ - Paper     │  │ - BuiltinExt │  │ - Graph        │  │
│  │ - Email     │  │ - EntityExt  │  │ - Topics       │  │
│  │ - Note      │  │ - TopicClust │  │ - Recommend    │  │
│  │             │  │ - DocRelation│  │                │  │
│  │             │  │ - Recommend  │  │                │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Storage Layer                         │
│  ┌─────────────────────┐    ┌─────────────────────────┐ │
│  │   SQLite Storage    │    │    ChromaDB Storage      │ │
│  │ (Metadata + Tags)   │    │  (Vector Embeddings)     │ │
│  └─────────────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 开发

### 开发环境设置

```bash
# 以开发模式安装
pip install -e .

# 运行测试
pytest tests/ -v

# 格式化代码
black kb/
isort kb/
```

### 构建 Python Wheel 包

构建 Python wheel 包用于分发：

```bash
# 构建当前版本的 wheel 包
python scripts/build_wheel.py --version 0.5.0

# 输出：
# dist/localbrain-0.5.0-py3-none-any.whl
# dist/localbrain-0.5.0-py3-none-any.whl.sha256
```

安装 wheel 包：

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

构建的二进制文件位于 `dist/` 目录，包含 SHA256 校验和文件。

### 构建完整发布包

构建完整的发布包，可直接部署到服务器：

```bash
# 构建全部（wheel 包 + 当前平台二进制）
python scripts/build_release.py --version 0.5.0

# 仅构建 Python wheel 包
python scripts/build_release.py --version 0.5.0 --wheel-only

# 仅构建特定平台的二进制文件
python scripts/build_release.py --version 0.5.0 --binary-only --platform macos-arm64
```

### 发布结构

`dist/` 目录组织如下，便于部署到 Web 服务器：

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

**部署方式：** 将整个 `dist/` 目录复制到 Web 服务器。安装脚本会根据 `version.json` 中的相对路径下载文件。

## 许可证

MIT
