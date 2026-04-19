# 文档整理方案

## 问题分析

当前项目文档存在以下问题：

1. **根目录混乱**：13 个 .md 文件堆积在根目录，其中大部分是版本相关的临时文档
2. **分类不清**：设计文档、发布文档、技术文档混在一起
3. **命名不统一**：有的用日期前缀，有的用版本号后缀，有的全大写
4. **缺乏索引**：没有统一的文档导航和索引
5. **历史遗留**：多个版本的发布文档没有归档

## 推荐的文档结构

```
agentic-local-brain/
├── README.md                    # 项目主文档（英文）
├── README_zh.md                 # 项目主文档（中文）
├── CHANGELOG.md                 # 统一的变更日志（合并所有版本）
├── CONTRIBUTING.md              # 贡献指南（新增）
├── LICENSE                      # 许可证
├── requirements.txt             # 依赖文件
│
├── docs/                        # 📁 文档目录
│   ├── README.md                # 文档索引和导航
│   │
│   ├── guides/                  # 📁 用户指南
│   │   ├── installation.md      # 安装指南
│   │   ├── quick-start.md       # 快速开始
│   │   ├── configuration.md     # 配置指南
│   │   └── troubleshooting.md   # 故障排除
│   │
│   ├── architecture/            # 📁 架构设计
│   │   ├── overview.md          # 架构概览
│   │   ├── frontend.md          # 前端架构
│   │   ├── backend.md           # 后端架构
│   │   └── data-flow.md         # 数据流设计
│   │
│   ├── features/                # 📁 功能文档
│   │   ├── knowledge-mining.md  # 知识挖掘
│   │   ├── backup.md            # 备份功能
│   │   ├── embedding.md         # 向量化
│   │   └── llm-integration.md   # LLM 集成
│   │
│   ├── development/             # 📁 开发文档
│   │   ├── setup.md             # 开发环境搭建
│   │   ├── coding-standards.md  # 编码规范
│   │   ├── testing.md           # 测试指南
│   │   └── api-reference.md     # API 参考
│   │
│   ├── releases/                # 📁 版本发布
│   │   ├── v0.8.1/              # 📁 0.8.1 版本
│   │   │   ├── release-notes.md
│   │   │   ├── changelog.md
│   │   │   ├── test-report.md
│   │   │   └── migration-guide.md
│   │   ├── v0.8.0/              # 📁 0.8.0 版本
│   │   └── v0.7.0/              # 📁 0.7.0 版本
│   │
│   ├── design/                  # 📁 设计文档（ADR - Architecture Decision Records）
│   │   ├── 2026-03-24-knowledge-base-design.md
│   │   ├── 2026-04-05-knowledge-mining-design.md
│   │   ├── 2026-04-15-backup-design.md
│   │   ├── 2026-04-18-frontend-refactor.md
│   │   └── 2026-04-19-ollama-embedding-fix.md
│   │
│   ├── troubleshooting/         # 📁 问题解决
│   │   ├── ollama-embedding.md  # Ollama embedding 问题
│   │   ├── config-issues.md     # 配置问题
│   │   └── common-errors.md     # 常见错误
│   │
│   ├── blog/                    # 📁 博客文章
│   │   └── two-weekends-ai-team.md
│   │
│   └── assets/                  # 📁 资源文件
│       ├── images/              # 图片
│       └── diagrams/            # 图表
│
├── .github/                     # GitHub 配置
│   ├── ISSUE_TEMPLATE/          # Issue 模板
│   └── PULL_REQUEST_TEMPLATE.md # PR 模板
│
└── scripts/                     # 脚本目录
    └── organize-docs.sh         # 文档整理脚本
```

## 文档命名规范

### 1. 文件命名

- **小写 + 连字符**：`quick-start.md`、`api-reference.md`
- **设计文档**：使用日期前缀 `YYYY-MM-DD-title.md`
- **版本文档**：放在 `releases/vX.Y.Z/` 目录下

### 2. 标题规范

```markdown
# 一级标题（文档标题）

## 二级标题（主要章节）

### 三级标题（子章节）

#### 四级标题（细节）
```

### 3. 元数据（可选）

在文档开头添加元数据：

```markdown
---
title: Ollama Embedding 配置指南
date: 2026-04-19
author: AI Team
tags: [ollama, embedding, configuration]
status: active
---
```

## 迁移计划

### 阶段 1：创建新目录结构

```bash
mkdir -p docs/{guides,architecture,features,development,releases,design,troubleshooting,blog,assets/{images,diagrams}}
```

### 阶段 2：移动和重命名文件

#### 2.1 版本发布文档 → `docs/releases/v0.8.1/`

```bash
mkdir -p docs/releases/v0.8.1
mv CHANGELOG_0.8.1.md docs/releases/v0.8.1/changelog.md
mv RELEASE_NOTES_0.8.1.md docs/releases/v0.8.1/release-notes.md
mv DEVELOPMENT_SUMMARY_0.8.1.md docs/releases/v0.8.1/development-summary.md
mv FINAL_SUMMARY_0.8.1.md docs/releases/v0.8.1/final-summary.md
mv QUICK_REFERENCE_0.8.1.md docs/releases/v0.8.1/quick-reference.md
mv RELEASE_SUMMARY_0.8.1.md docs/releases/v0.8.1/release-summary.md
mv TEST_REPORT_0.8.1.md docs/releases/v0.8.1/test-report.md
```

#### 2.2 设计文档 → `docs/design/`

```bash
# 根目录的设计文档
mv CONFIG_CLEANUP_SUMMARY.md docs/design/2026-04-18-config-cleanup.md
mv SETTINGS_UI_REDESIGN.md docs/design/2026-04-18-settings-ui-redesign.md

# docs/ 目录的设计文档已经在正确位置，只需重命名
cd docs/
mv 2026-04-15-knowledge-base-backup-design.md design/2026-04-15-backup-design.md
```

#### 2.3 功能文档 → `docs/features/`

```bash
mv docs/backup-feature-design.md docs/features/backup.md
```

#### 2.4 架构文档 → `docs/architecture/`

```bash
mv docs/FRONTEND_ARCHITECTURE.md docs/architecture/frontend.md
```

#### 2.5 问题解决文档 → `docs/troubleshooting/`

```bash
mv docs/ollama-embedding-fix.md docs/troubleshooting/ollama-embedding.md
mv docs/ollama-embedding-analysis.md docs/troubleshooting/ollama-embedding-analysis.md
mv docs/web-ui-ollama-url-update.md docs/troubleshooting/ollama-web-ui-config.md
```

#### 2.6 博客文章 → `docs/blog/`

```bash
mv docs/article-two-weekends-ai-team.md docs/blog/two-weekends-ai-team.md
```

#### 2.7 资源文件 → `docs/assets/`

```bash
mv docs/screenshots docs/assets/images/
```

### 阶段 3：创建索引文档

创建 `docs/README.md` 作为文档导航：

```markdown
# Agentic Local Brain 文档

## 📚 用户指南

- [安装指南](guides/installation.md)
- [快速开始](guides/quick-start.md)
- [配置指南](guides/configuration.md)
- [故障排除](guides/troubleshooting.md)

## 🏗️ 架构设计

- [架构概览](architecture/overview.md)
- [前端架构](architecture/frontend.md)
- [后端架构](architecture/backend.md)

## ✨ 功能文档

- [知识挖掘](features/knowledge-mining.md)
- [备份功能](features/backup.md)
- [向量化](features/embedding.md)

## 🔧 开发文档

- [开发环境搭建](development/setup.md)
- [编码规范](development/coding-standards.md)
- [测试指南](development/testing.md)

## 📦 版本发布

- [v0.8.1](releases/v0.8.1/release-notes.md)
- [v0.8.0](releases/v0.8.0/release-notes.md)

## 🎯 设计决策（ADR）

- [2026-04-19 - Ollama Embedding 修复](design/2026-04-19-ollama-embedding-fix.md)
- [2026-04-18 - 前端重构](design/2026-04-18-frontend-refactor.md)
- [2026-04-15 - 备份功能设计](design/2026-04-15-backup-design.md)

## 🐛 问题解决

- [Ollama Embedding 配置问题](troubleshooting/ollama-embedding.md)
- [常见错误](troubleshooting/common-errors.md)

## 📝 博客

- [两个周末打造 AI 团队](blog/two-weekends-ai-team.md)
```

### 阶段 4：更新 CHANGELOG

合并所有版本的 CHANGELOG 到根目录的 `CHANGELOG.md`：

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.1] - 2026-04-18

### Added
- ...

### Changed
- ...

### Fixed
- ...

## [0.8.0] - 2026-04-10

...
```

### 阶段 5：清理和验证

```bash
# 删除空文件和临时文件
find docs/ -type f -name ".DS_Store" -delete

# 验证所有链接
# 可以使用工具如 markdown-link-check

# 更新 README.md 中的文档链接
```

## 维护规范

### 1. 新增文档时

- 确定文档类型（指南、架构、功能、开发、设计）
- 放入对应目录
- 更新 `docs/README.md` 索引
- 使用统一的命名规范

### 2. 版本发布时

- 在 `docs/releases/vX.Y.Z/` 创建新目录
- 包含：release-notes.md、changelog.md、migration-guide.md
- 更新根目录的 `CHANGELOG.md`

### 3. 设计决策时

- 使用 ADR（Architecture Decision Record）格式
- 文件名：`YYYY-MM-DD-title.md`
- 放入 `docs/design/` 目录
- 包含：背景、决策、后果、替代方案

### 4. 问题解决文档

- 记录常见问题和解决方案
- 放入 `docs/troubleshooting/` 目录
- 包含：问题描述、原因分析、解决方案、验证方法

## 工具推荐

### 1. 文档生成

- **MkDocs**：Python 文档生成工具
- **Docusaurus**：React 文档网站生成器
- **VuePress**：Vue 文档生成工具

### 2. 文档检查

- **markdownlint**：Markdown 格式检查
- **markdown-link-check**：链接有效性检查
- **vale**：文档风格检查

### 3. 图表工具

- **Mermaid**：文本生成图表
- **PlantUML**：UML 图表
- **draw.io**：在线图表工具

## 实施建议

### 优先级

1. **高优先级**（立即执行）
   - 创建新目录结构
   - 移动版本发布文档到 `docs/releases/v0.8.1/`
   - 创建 `docs/README.md` 索引

2. **中优先级**（本周完成）
   - 移动设计文档到 `docs/design/`
   - 移动功能文档到对应目录
   - 合并 CHANGELOG

3. **低优先级**（逐步完善）
   - 创建用户指南
   - 完善开发文档
   - 添加 API 文档

### 注意事项

1. **保持向后兼容**：如果有外部链接引用旧文档路径，考虑添加重定向或保留副本
2. **Git 历史**：使用 `git mv` 而不是 `mv`，保留文件历史
3. **团队沟通**：通知团队成员文档结构变更
4. **CI/CD 更新**：如果有自动化流程引用文档路径，需要更新

## 示例脚本

创建 `scripts/organize-docs.sh`：

```bash
#!/bin/bash
# 文档整理脚本

set -e

echo "开始整理文档..."

# 创建目录结构
mkdir -p docs/{guides,architecture,features,development,releases/v0.8.1,design,troubleshooting,blog,assets/images}

# 移动版本文档
git mv CHANGELOG_0.8.1.md docs/releases/v0.8.1/changelog.md
git mv RELEASE_NOTES_0.8.1.md docs/releases/v0.8.1/release-notes.md
# ... 其他移动命令

echo "文档整理完成！"
echo "请检查 docs/README.md 并更新索引"
```

## 总结

通过这个文档整理方案，可以：

1. ✅ **清理根目录**：只保留核心文档
2. ✅ **分类清晰**：按类型组织文档
3. ✅ **易于维护**：统一的命名和结构
4. ✅ **便于查找**：清晰的索引和导航
5. ✅ **版本管理**：历史版本归档
6. ✅ **可扩展性**：为未来文档预留空间

建议分阶段实施，先完成高优先级任务，再逐步完善其他部分。
