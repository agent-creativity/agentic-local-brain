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

## 安装

### 方式一：Python方式安装（推荐）

在所有平台上均可正常工作，无安全警告。需要 Python 3.8+。

**macOS / Linux：**
```bash
curl -fsSL https://localbrain.io.alibaba-inc.com/python_installer/install.sh | sh
```

**Windows (PowerShell)：**
```powershell
irm https://localbrain.io.alibaba-inc.com/python_installer/install.ps1 | iex
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
curl -fsSL https://localbrain.io.alibaba-inc.com/binary_installer/install.sh | sh
```

**Windows (PowerShell)：**
```powershell
irm https://localbrain.io.alibaba-inc.com/binary_installer/install.ps1 | iex
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

## Web API

启动 Web 服务：
```bash
localbrain web                    # 前台运行
localbrain web -b                 # 后台运行（守护进程）
localbrain web -b -p 9090         # 自定义端口，后台运行
localbrain web --stop             # 停止后台服务
localbrain web --status           # 查看服务状态
```

API 端点（默认：http://localhost:8080）：

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

服务运行时可访问 `http://localhost:8080/docs` 查看 API 文档。

## 配置

配置文件：`~/.localbrain/config.yaml`

```yaml
data_dir: ~/.knowledge-base

# 更新服务器（用于自更新功能）
update_server_url: https://localbrain.io.alibaba-inc.com

embedding:
  provider: dashscope
  model: text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}

llm:
  provider: dashscope
  model: qwen-plus
  api_key: ${DASHSCOPE_API_KEY}

chunking:
  max_chunk_size: 1000
  overlap: 100

logging:
  level: INFO
  max_bytes: 10485760    # 10MB
  backup_count: 5
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
