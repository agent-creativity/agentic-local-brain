# 文档整理快速指南

## 概述

本指南帮助你快速整理项目文档，将散乱的文档按照规范重新组织。

## 当前问题

- ✗ 根目录有 13 个 .md 文件，大部分是版本相关的临时文档
- ✗ 文档分类不清晰，设计、发布、技术文档混在一起
- ✗ 命名不统一，有日期前缀、版本号后缀、全大写等多种风格
- ✗ 缺乏统一的文档索引和导航

## 整理后的结构

```
docs/
├── README.md                    # 📖 文档索引（新增）
├── guides/                      # 📚 用户指南
├── architecture/                # 🏗️ 架构设计
├── features/                    # ✨ 功能文档
├── development/                 # 🔧 开发文档
├── releases/                    # 📦 版本发布
│   └── v0.8.1/                  # 各版本文档归档
├── design/                      # 🎯 设计决策（ADR）
├── troubleshooting/             # 🐛 问题解决
├── blog/                        # 📝 博客文章
└── assets/                      # 📁 资源文件
    └── images/                  # 图片和截图
```

## 快速开始

### 方式 1：自动整理（推荐）

```bash
# 1. 运行整理脚本
./scripts/organize-docs.sh

# 2. 检查变更
git status

# 3. 提交变更
git add .
git commit -m "docs: reorganize documentation structure"
```

### 方式 2：手动整理

参考 [文档组织方案](docs/documentation-organization-plan.md) 中的详细步骤。

## 整理内容

### 自动处理的文件

脚本会自动移动以下文件：

**版本发布文档** → `docs/releases/v0.8.1/`
- CHANGELOG_0.8.1.md → changelog.md
- RELEASE_NOTES_0.8.1.md → release-notes.md
- DEVELOPMENT_SUMMARY_0.8.1.md → development-summary.md
- FINAL_SUMMARY_0.8.1.md → final-summary.md
- QUICK_REFERENCE_0.8.1.md → quick-reference.md
- RELEASE_SUMMARY_0.8.1.md → release-summary.md
- TEST_REPORT_0.8.1.md → test-report.md

**设计文档** → `docs/design/`
- CONFIG_CLEANUP_SUMMARY.md → 2026-04-18-config-cleanup.md
- SETTINGS_UI_REDESIGN.md → 2026-04-18-settings-ui-redesign.md

**功能文档** → `docs/features/`
- backup-feature-design.md → backup.md

**架构文档** → `docs/architecture/`
- FRONTEND_ARCHITECTURE.md → frontend.md

**问题解决** → `docs/troubleshooting/`
- ollama-embedding-fix.md → ollama-embedding.md
- ollama-embedding-analysis.md → ollama-embedding-analysis.md
- web-ui-ollama-url-update.md → ollama-web-ui-config.md

**博客文章** → `docs/blog/`
- article-two-weekends-ai-team.md → two-weekends-ai-team.md

**资源文件** → `docs/assets/images/`
- screenshots/ → screenshots/

### 保留在根目录的文件

- README.md - 项目主文档
- README_zh.md - 中文文档
- CHANGELOG.md - 统一的变更日志（新增）
- AGENTS.md - Agent 配置
- requirements.txt - 依赖文件

## 验证整理结果

```bash
# 查看新的文档结构
tree docs/ -L 2

# 检查文档索引
cat docs/README.md

# 验证所有链接（可选）
# npm install -g markdown-link-check
# find docs/ -name "*.md" -exec markdown-link-check {} \;
```

## 后续维护

### 新增文档时

1. **确定文档类型**
   - 用户指南 → `docs/guides/`
   - 架构设计 → `docs/architecture/`
   - 功能文档 → `docs/features/`
   - 开发文档 → `docs/development/`
   - 设计决策 → `docs/design/YYYY-MM-DD-title.md`
   - 问题解决 → `docs/troubleshooting/`

2. **使用统一命名**
   - 小写 + 连字符：`quick-start.md`
   - 设计文档：`YYYY-MM-DD-title.md`

3. **更新索引**
   - 在 `docs/README.md` 中添加链接

### 版本发布时

```bash
# 创建新版本目录
mkdir -p docs/releases/v0.9.0

# 添加版本文档
# - release-notes.md
# - changelog.md
# - migration-guide.md

# 更新 CHANGELOG.md
```

## 文档规范

### 文件命名

- ✅ `quick-start.md` - 小写 + 连字符
- ✅ `2026-04-19-ollama-fix.md` - 设计文档带日期
- ❌ `QuickStart.md` - 避免驼峰命名
- ❌ `quick_start.md` - 避免下划线

### 标题层级

```markdown
# 一级标题（文档标题，每个文档只有一个）

## 二级标题（主要章节）

### 三级标题（子章节）

#### 四级标题（细节，尽量少用）
```

### 链接格式

```markdown
# 相对链接（推荐）
[配置指南](../guides/configuration.md)

# 绝对链接（避免）
[配置指南](/docs/guides/configuration.md)
```

## 常见问题

### Q: 整理后原来的链接会失效吗？

A: 是的，内部链接需要更新。脚本会提示你手动检查和更新链接。

### Q: 如何恢复到整理前的状态？

A: 脚本会自动创建备份目录 `docs_backup_YYYYMMDD_HHMMSS/`，可以从中恢复。

### Q: 可以只整理部分文档吗？

A: 可以，编辑 `scripts/organize-docs.sh` 注释掉不需要的部分。

### Q: 如何添加新的文档分类？

A: 在 `docs/` 下创建新目录，并在 `docs/README.md` 中添加索引。

## 工具推荐

### 文档生成

- **MkDocs** - Python 文档生成工具
  ```bash
  pip install mkdocs
  mkdocs new .
  mkdocs serve
  ```

- **Docusaurus** - React 文档网站
  ```bash
  npx create-docusaurus@latest docs classic
  ```

### 文档检查

- **markdownlint** - Markdown 格式检查
  ```bash
  npm install -g markdownlint-cli
  markdownlint docs/**/*.md
  ```

- **markdown-link-check** - 链接检查
  ```bash
  npm install -g markdown-link-check
  find docs/ -name "*.md" -exec markdown-link-check {} \;
  ```

## 参考资料

- [Keep a Changelog](https://keepachangelog.com/) - 变更日志规范
- [Semantic Versioning](https://semver.org/) - 语义化版本
- [Architecture Decision Records](https://adr.github.io/) - ADR 规范
- [Write the Docs](https://www.writethedocs.org/) - 文档写作指南

## 需要帮助？

- 查看详细方案：[文档组织方案](docs/documentation-organization-plan.md)
- 提交 Issue：[GitHub Issues](https://github.com/your-repo/issues)
- 联系维护者：your-email@example.com
