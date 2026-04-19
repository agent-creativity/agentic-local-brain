# 本地知识管理系统设计方案

**创建日期**: 2026-03-24  
**作者**: QoderWork  
**状态**: 设计中

---

## 一、系统概述

### 1.1 系统定位

本地知识管理系统 (Personal Knowledge Management System),支持多种知识来源的收集、管理、检索和智能化处理。

### 1.2 核心目标

- **多源收集**: 支持本地文件、网页、书签、论文、邮件、笔记等多种知识来源
- **智能处理**: LLM 自动提取标签,向量化存储
- **灵活检索**: 支持语义搜索、关键词搜索、标签过滤
- **三重交互**: CLI 工具、Web 管理界面、QoderWork Skill 集成
- **完全本地**: 数据以文件系统存储,代码与数据分离

---

## 二、整体架构

### 2.1 架构设计

```
┌──────────────────────────────────────────────┐│                        用户交互层                              │
├────┬──────┬──────────┤│   CLI 工具     │   Web 管理界面    │    QoderWork Skill       │
│  (kb命令)      │   (FastAPI+Vue)  │  (knowledge-collector)   │
└─┬──┴──┬───┘           │                  │
           ▼                  ▼
┌──────────────────────────────────────────────┐│                    核心引擎层 (Python)                         │
├──────────────────────────────────────────────┤│                                                              │
│┌─┐┌──┐┌──┐
│  │  收集器模块  │  │  处理模块   │  │  查询模块    │          │
│  │ Collectors  │  │ Processors  │  │   Query      │          │
│ └┬┘└┬─┘└┬─┘
│           │               │               │                   │
│ ┌┴──┴──┐
│  │          统一知识管道 (Pipeline)             │            │
│  │  1. 内容提取 → 2. LLM打标 → 3. 分块 → 4. 向量化 │           │
│ └──────────┬──────────┘
│                     │                                         │
└─────────────┼─────────────────────────┘                      ▼
┌──────────────────────────────────────────────┐│                    数据存储层                                  │
├──────────────────────────────────────────────┤│                                                              │
│ ┌──┐┌──┐┌──┐
│  │  文件系统   │  │  Chroma DB   │  │  SQLite DB   │      │
│  │  (原始知识)  │  │  (向量索引)   │  │  (元数据)    │      │
│ └──┘└──┘└──┘
│                                                              │
└──────────────────────────────────────────────┘```

### 2.2 目录结构

```
# 程序代码 (通过 pip 安装)
/usr/local/bin/kb                          # CLI 可执行文件
/usr/local/lib/python3.x/site-packages/kb/ # Python 包

# 数据目录 (用户主目录)
~/knowledge-base/                          # 一目了然,易于访问
├ data/                                  # 原始知识文件
│   ├── raw/                               # 按类型分类
│   │   ├── files/                         # 本地文件
│   │   │   ├── 2026-03-23_rag-guide.pdf
│   │   │  └ 2026-03-22_python-notes.md
│   │   ├── urls/                          # 网页内容 (Markdown)
│   │   │   ├── 2026-03-23_openai-blog.md
│   │   │  └ 2026-03-22_hn-article.md
│   │   ├── bookmarks/                     # 书签 (Markdown)
│   │   │  └ 2026-03-23_safari-bookmarks.md
│   │   ├── papers/                        # 论文
│   │   │  └ 2301.12345/
│   │   │       ├── paper.pdf
│   │   │      └ metadata.md
│   │   ├── emails/                        # 邮件 (Markdown)
│   │   │  └ 2026-03-23_re-meeting.md
│   │  └ notes/                         # 一句话笔记
│   │       ├── 2026-03-23_001.md
│   │      └ 2026-03-23_002.md
│   │
│  └ chunks/                            # 处理后的分块
│       ├── file_001_chunk_1.md
│      └ file_001_chunk_2.md
│
├ chroma_db/                             # Chroma 向量数据库
├ knowledge.db                           # SQLite 索引 (只存元数据)
├ config.yaml                            # 配置文件
└ .git/                                  # 可选: Git 版本控制
```

---

## 三、核心功能模块

### 3.1 收集器模块 (Collectors)

支持多种知识来源:

#### 3.1.1 文件收集器 (FileCollector)

**功能**: 解析本地文件 (PDF/MD/DOCX/TXT)

**处理流程**:
1. 检测文件类型
2. 提取纯文本内容
3. LLM 提取标签
4. 复制到 `data/raw/files/`
5. 分块 + 向量化

**CLI 命令**:
```bash
kb collect file /path/to/document.pdf
```

#### 3.1.2 网页收集器 (URLCollector)

**功能**: 抓取网页内容并转换为 Markdown

**技术栈**:
- 网页抓取: `httpx` + `readability-lxml`
- HTML 转 Markdown: `markdownify`
- 动态网页: `playwright` (降级方案)

**处理流程**:
1. 抓取网页 HTML
2. 使用 Readability 提取正文
3. 转换为 Markdown
4. LLM 提取标签 (3-5个)
5. 保存到 `data/raw/urls/`

**CLI 命令**:
```bash
kb collect url https://example.com/article
```

**生成的文件示例**:
```markdown
---
id: url_20260324_143022
title: "如何优化 RAG 检索质量"
source: https://example.com/rag-optimization
content_type: url
collected_at: 2026-03-24T14:30:22
tags:
  - RAG
  - 向量检索
  - 检索优化
  - AI教程
word_count: 2500
status: processed
---

# 如何优化 RAG 检索质量

[完整的网页正文内容...]
```

#### 3.1.3 书签收集器 (BookmarkCollector)

**功能**: 从浏览器收集书签

**支持的浏览器**:
- Chrome/Edge (Chromium 系)
- Safari (macOS)
- Firefox
- 通用 HTML 导出格式

**处理流程**:
1. 解析浏览器书签文件 (JSON/plist/SQLite)
2. 提取 URL、标题、文件夹结构
3. 批量抓取网页内容 (并发控制)
4. 保存书签索引 (JSON)

**CLI 命令**:
```bash
# 从 Chrome 收集
kb bookmark collect --browser chrome

# 从 HTML 导出文件导入
kb bookmark import ~/Downloads/bookmarks.html
```

**优化策略**:
- 并发控制 (默认 5 个并发)
- 增量更新 (跳过已收集的书签)
- 失败重试 (最多 3 次)

#### 3.1.4 论文收集器 (PaperCollector)

**功能**: 从 arXiv 等学术平台收集论文

**处理流程**:
1. 调用 arXiv API 获取元数据
2. 下载 PDF
3. 提取摘要和关键信息
4. 保存到 `data/raw/papers/`

**CLI 命令**:
```bash
kb collect paper arxiv:2301.12345
```

#### 3.1.5 邮件收集器 (EmailCollector)

**功能**: 解析邮件文件 (MBOX/EML)

**处理流程**:
1. 解析邮件格式
2. 提取发件人、收件人、主题、正文
3. 转换为 Markdown
4. 保存到 `data/raw/emails/`

**CLI 命令**:
```bash
kb collect email ~/Downloads/export.mbox
```

#### 3.1.6 笔记收集器 (NoteCollector)

**功能**: 快速记录一句话笔记

**CLI 命令**:
```bash
kb note "这是一条快速笔记" --tags 想法,RAG
```

---

### 3.2 处理模块 (Processors)

#### 3.2.1 内容提取器 (ContentExtractor)

**职责**: 从不同格式的原始内容中提取纯文本

**支持格式**:
- PDF: `PyPDF2` / `pdfplumber`
- DOCX: `python-docx`
- HTML: `readability-lxml` + `BeautifulSoup`
- Markdown: 直接读取

#### 3.2.2 标签提取器 (TagExtractor)

**职责**: 调用 LLM 自动提取标签

**技术栈**:
- LLM: 百炼 (qwen-plus) 或自定义 OpenAI 兼容服务
- Prompt 设计: 引导生成 3-5 个高质量标签

**Prompt 示例**:
```
你是一个专业的内容分析助手。请为以下内容提取 3-5 个核心标签。

## 内容
标题: {title}
摘要: {content[:800]}...

## 要求
1. 标签数量: 3-5 个
2. 标签格式: 2-4 个汉字或英文单词,用逗号分隔
3. 标签类型:
   - 至少 1 个主题标签 (如: AI, 数据库, 前端)
   - 至少 1 个类型标签 (如: 教程, API文档, 研究论文)
   - 可选: 技术栈标签 (如: Python, React, RAG)
4. 不要包含"标签:"前缀
5. 不要使用过于宽泛的标签

## 示例
输入: "如何使用 Chroma 向量数据库"
输出: Chroma, 向量数据库, 教程, Python

请输出标签:
```

**实现代码**:
```python
class TagExtractor:
    async def extract_tags(self, title: str, content: str) -> list:
        prompt = self._build_prompt(title, content)
        response = await self.llm.generate(prompt)
        tags = self._parse_tags(response)
        return tags[:5]
```

#### 3.2.3 分块器 (Chunker)

**职责**: 将长文档分块,便于向量化和检索

**策略**:
- 固定大小分块: 800 tokens
- 重叠: 100 tokens
- 分隔符: 段落 (`\n\n`)

**配置**:
```yaml
processing:
  chunking:
    chunk_size: 800
    chunk_overlap: 100
    separator: "\n\n"
```

#### 3.2.4 向量化器 (Embedder)

**职责**: 调用 Embedding 模型生成向量

**支持的模型**:
- 百炼: `text-embedding-v4` (默认)
- 自定义 OpenAI 兼容: 本地 Ollama、vLLM 等

**配置**:
```yaml
embedding:
  provider: dashscope
  dashscope:
    model: text-embedding-v4
    api_key: ${DASHSCOPE_API_KEY}
```

---

### 3.3 查询模块 (Query)

#### 3.3.1 语义搜索 (SemanticSearch)

**功能**: 基于向量相似度的检索

**流程**:
1. 问题向量化
2. Chroma 检索 Top-K
3. 返回相关文档块

**CLI 命令**:
```bash
kb query "如何优化 RAG 检索质量?" --tags RAG --top-k 5
```

#### 3.3.2 关键词搜索 (KeywordSearch)

**功能**: 基于关键词的全文搜索

**实现**: `ripgrep` 或 SQLite FTS5

**CLI 命令**:
```bash
kb search "向量数据库" --type file
```

#### 3.3.3 RAG 查询 (RAGQuery)

**功能**: 检索 + LLM 生成回答

**流程**:
1. 检索相关文档块
2. 构建上下文
3. 调用 LLM 生成回答

**QoderWork 集成示例**:
```python
from kb.query.rag import RAGQuery

rag = RAGQuery()
results = rag.query(
    question="如何优化 RAG?",
    tags=["RAG"],
    top_k=5
)

# results 包含检索到的上下文,可作为 prompt 提供给 LLM
```

---

### 3.4 Web 管理界面

**技术栈**: FastAPI + Vue.js (或 Flask + HTMX)

**核心页面**:

1. **仪表盘**:
   - 知识总数、标签云、最近收集
   - 统计图表 (按类型、按时间)

2. **文档管理**:
   - 文档列表 (支持筛选、排序)
   - 文档预览
   - 标签编辑

3. **标签管理**:
   - 标签云可视化
   - 标签合并/删除
   - 按标签浏览文档

4. **搜索页面**:
   - 全文搜索
   - 高级筛选 (标签、类型、时间)

**启动命令**:
```bash
kb web
```

---

## 四、数据模型

### 4.1 文件系统存储

**核心原则**: 所有原始知识以 Markdown 文件形式存储,数据库只存索引和元数据

**文件格式**: Markdown + YAML Front Matter

**示例**:
```markdown
---
id: url_20260324_143022
title: "如何优化 RAG 检索质量"
source: https://example.com/rag-optimization
content_type: url
collected_at: 2026-03-24T14:30:22
tags:
  - RAG
  - 向量检索
  - 检索优化
word_count: 2500
status: processed
---

# 标题

[正文内容...]
```

### 4.2 SQLite 数据库

**职责**: 存储元数据索引,加速查询

**表结构**:

```sql
-- 知识条目表
CREATE TABLE knowledge (
    id TEXT PRIMARY KEY,
    title TEXT,
    content_type TEXT,  -- file/url/bookmark/paper/email/note
    source TEXT,        -- 原始来源
    collected_at TIMESTAMP,
    summary TEXT,
    word_count INTEGER,
    file_path TEXT      -- 文件系统路径
);

-- 标签表
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    count INTEGER
);

-- 知识-标签关联表
CREATE TABLE knowledge_tags (
    knowledge_id TEXT,
    tag_id INTEGER,
    PRIMARY KEY (knowledge_id, tag_id)
);

-- 文档块表 (与 Chroma 同步)
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    knowledge_id TEXT,
    chunk_index INTEGER,
    content TEXT,
    embedding_id TEXT
);
```

### 4.3 Chroma 向量数据库

**职责**: 存储向量和元数据,支持相似度检索

**集合结构**:
```python
{
    "ids": ["chunk_001", "chunk_002", ...],
    "embeddings": [[...], [...], ...],
    "metadatas": [
        {
            "knowledge_id": "kb_001",
            "title": "RAG 优化指南",
            "tags": ["RAG", "向量检索", "教程"],
            "content_type": "file",
            "chunk_index": 1,
            "collected_at": "2026-03-24"
        }
    ],
    "documents": ["文本内容...", ...]
}
```

---

## 五、模型配置

### 5.1 支持的模型类型

**Embedding 模型**:
- 百炼 (DashScope): `text-embedding-v4` (默认)
- 自定义 OpenAI 兼容: 本地 Ollama、vLLM 等

**LLM 模型**:
- 百炼 (DashScope): `qwen-plus`, `qwen-max`
- 自定义 OpenAI 兼容: 本地 Ollama、vLLM 等

### 5.2 配置文件

**`~/knowledge-base/config.yaml`**:

```yaml
# 数据目录
data_dir: ~/knowledge-base/data
chroma_db_path: ~/knowledge-base/chroma_db
sqlite_db_path: ~/knowledge-base/knowledge.db

# Embedding 模型
embedding:
  provider: dashscope
  dashscope:
    model: text-embedding-v4
    api_key: ${DASHSCOPE_API_KEY}
  
  openai_compatible:
    model: bge-m3
    api_key: ${EMBEDDING_API_KEY}
    base_url: http://localhost:11434/v1

# LLM 模型
llm:
  provider: dashscope
  dashscope:
    model: qwen-plus
    api_key: ${DASHSCOPE_API_KEY}
    temperature: 0.3
    max_tokens: 500
  
  openai_compatible:
    model: qwen2.5-7b-instruct
    api_key: ${LLM_API_KEY}
    base_url: http://localhost:11434/v1

# 处理配置
processing:
  chunking:
    chunk_size: 800
    chunk_overlap: 100
    separator: "\n\n"
  
  tagging:
    min_tags: 3
    max_tags: 5

# Web 服务
web:
  host: 127.0.0.1
  port: 11201
```

### 5.3 环境变量

```bash
# ~/.bashrc 或 ~/.zshrc
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxx"
export EMBEDDING_API_KEY="your-embedding-key"
export LLM_API_KEY="your-llm-key"
```

---

## 六、CLI 命令设计

### 6.1 初始化

```bash
# 创建默认知识库
kb init

# 自定义位置
kb init --data-dir ~/Documents/my-kb

# 交互式配置
kb init --interactive
```

### 6.2 收集知识

```bash
# 本地文件
kb collect file /path/to/document.pdf

# 网页
kb collect url https://example.com/article

# 论文
kb collect paper arxiv:2301.12345

# 邮件
kb collect email ~/Downloads/export.mbox

# 快速笔记
kb note "这是一条快速笔记" --tags 想法,RAG

# 书签
kb bookmark collect --browser chrome
kb bookmark import ~/Downloads/bookmarks.html
```

### 6.3 查询知识

```bash
# 语义搜索
kb query "如何优化 RAG 检索?" --tags RAG --top-k 5

# 关键词搜索
kb search "向量数据库" --type file

# 按标签查找
kb find --tags AI,教程 --limit 10
```

### 6.4 管理知识

```bash
# 标签管理
kb tags list
kb tags merge "机器学习" "ML"
kb tags delete "过时标签"

# 统计信息
kb stats

# 导出数据
kb export --format markdown --output ~/backup/kb-export

# 启动 Web 界面
kb web
```

### 6.5 配置管理

```bash
# 查看配置
kb config show

# 修改配置
kb config set embedding.provider dashscope
kb config set llm.dashscope.model qwen-plus

# 测试连接
kb test embedding
kb test llm
```

---

## 七、QoderWork 集成

### 7.1 Skill 1: knowledge-collector (收集知识)

**功能**: 通过 CLI 或 Python API 收集知识

**使用示例**:
```python
from kb.collectors import FileCollector, URLCollector

# 收集文件
collector = FileCollector()
collector.collect("/path/to/doc.pdf")

# 收集网页
url_collector = URLCollector()
url_collector.collect("https://example.com")
```

### 7.2 Skill 2: knowledge-rag (查询知识)

**功能**: 从本地知识库检索知识,提供 RAG 上下文

**使用示例**:
```python
from kb.query.rag import RAGQuery

rag = RAGQuery(kb_dir="~/knowledge-base")

# 查询并获取上下文
results = rag.query(
    question="如何优化 RAG?",
    tags=["RAG"],
    top_k=5
)

# results 包含检索到的文档块,可作为上下文提供给 LLM
for chunk in results:
    print(f"来源: {chunk.metadata['source']}")
    print(f"内容: {chunk.content[:200]}...")
```

---

## 八、技术栈总览

| 组件 | 技术 | 说明 |
|------|------|------|
| CLI 框架 | Click | Python CLI 库 |
| Web 框架 | FastAPI + Vue.js | 或 Flask + HTMX (简化) |
| 向量数据库 | Chroma | 轻量、支持元数据 |
| 关系数据库 | SQLite | 元数据存储 |
| Embedding | BGE-M3 / text-embedding-v4 | 本地或百炼 |
| LLM | qwen-plus / 自定义 | 标签提取 |
| 文档解析 | Unstructured, PyPDF2, readability-lxml | 多种格式 |
| 网页抓取 | httpx, Playwright | 动态网页支持 |
| HTML 转 Markdown | markdownify | 转换工具 |

---

## 九、核心优势

✅ **完全文件系统存储** - 所有知识都是可读可编辑的 Markdown 文件  
✅ **路径简单直观** - `~/knowledge-base/` 一目了然  
✅ **代码与数据分离** - 程序安装在系统目录,数据在用户目录  
✅ **易于备份** - 直接复制 `~/knowledge-base/` 文件夹  
✅ **版本控制友好** - 可以对 `data/raw/` 建立 Git 仓库  
✅ **跨工具兼容** - 可以用任意编辑器查看/编辑  
✅ **可搜索** - 用 `grep`/`ripgrep` 全局搜索  
✅ **多知识库支持** - 通过 `--data-dir` 创建多个独立知识库  
✅ **灵活模型配置** - 支持百炼和自定义 OpenAI 兼容服务  

---

## 十、实施计划

### Phase 1: 核心框架 (Week 1)
- [ ] 项目结构搭建
- [ ] CLI 框架 (Click)
- [ ] 配置管理 (config.yaml)
- [ ] 初始化和数据存储结构

### Phase 2: 收集器模块 (Week 2-3)
- [ ] FileCollector (本地文件)
- [ ] URLCollector (网页抓取)
- [ ] BookmarkCollector (书签收集)
- [ ] NoteCollector (快速笔记)
- [ ] PaperCollector (论文)
- [ ] EmailCollector (邮件)

### Phase 3: 处理模块 (Week 3-4)
- [ ] ContentExtractor (内容提取)
- [ ] TagExtractor (LLM 标签提取)
- [ ] Chunker (分块)
- [ ] Embedder (向量化)
- [ ] Chroma 存储集成
- [ ] SQLite 索引集成

### Phase 4: 查询模块 (Week 4-5)
- [ ] SemanticSearch (语义搜索)
- [ ] KeywordSearch (关键词搜索)
- [ ] RAGQuery (RAG 查询)
- [ ] CLI 查询命令

### Phase 5: Web 界面 (Week 5-6)
- [ ] FastAPI 后端
- [ ] Vue.js 前端
- [ ] 仪表盘页面
- [ ] 文档管理页面
- [ ] 标签管理页面
- [ ] 搜索页面

### Phase 6: QoderWork 集成 (Week 6-7)
- [ ] knowledge-collector Skill
- [ ] knowledge-rag Skill
- [ ] 文档和测试

### Phase 7: 优化和测试 (Week 7-8)
- [ ] 性能优化
- [ ] 错误处理
- [ ] 单元测试
- [ ] 用户文档

---

## 十一、后续优化方向

1. **智能去重**: 检测重复或高度相似的内容
2. **自动摘要**: LLM 生成文档摘要
3. **知识图谱**: 建立知识之间的关联关系
4. **定时同步**: 自动同步浏览器书签
5. **移动端支持**: iOS/Android App
6. **团队协作**: 多用户共享知识库
7. **插件系统**: 支持第三方扩展

---

**文档版本**: v1.0  
**最后更新**: 2026-03-24
