# Agentic Local Brain

[English](README.md) | [简体中文](README.zh-CN.md)

> 个人知识管理系统 — 从多个来源收集、处理和查询知识。

## 快速开始

在你的桌面 Agent（OpenClaw / Hermes / Claude / Qoder / Codex / Trae 等）中，发出如下聊天内容即可启动你的构建本地大脑之旅：

```
帮我安装或更新这个知识收集技能：http://localbrain.oss-cn-shanghai.aliyuncs.com/skills/localbrain-collect/SKILL.md
```

就这么简单，Agent 会帮你完成一切。

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

## 许可证

MIT

