# 文档整理方案总结

## 问题分析

当前项目文档存在以下问题：

1. **根目录混乱**：13 个 .md 文件堆积，其中 8 个是 v0.8.1 版本相关的临时文档
2. **分类不清**：设计、发布、技术文档混在一起
3. **命名不统一**：日期前缀、版本号后缀、全大写等多种风格并存
4. **缺乏索引**：没有统一的文档导航
5. **历史遗留**：多个版本的发布文档没有归档

## 推荐方案

### 目录结构

```
docs/
├── README.md                    # 📖 文档索引和导航
├── guides/                      # 📚 用户指南（安装、配置、使用）
├── architecture/                # 🏗️ 架构设计（系统架构、技术选型）
├── features/                    # ✨ 功能文档（功能说明、使用指南）
├── development/                 # 🔧 开发文档（开发环境、编码规范、测试）
├── releases/                    # 📦 版本发布（按版本归档）
│   └── v0.8.1/
├── design/                      # 🎯 设计决策（ADR - Architecture Decision Records）
├── troubleshooting/             # 🐛 问题解决（常见问题、故障排除）
├── blog/                        # 📝 博客文章（技术分享、项目故事）
└── assets/                      # 📁 资源文件（图片、图表）
    └── images/
```

### 命名规范

- **普通文档**：小写 + 连字符，如 `quick-start.md`
- **设计文档**：日期前缀，如 `2026-04-19-ollama-embedding-fix.md`
- **版本文档**：放在 `releases/vX.Y.Z/` 目录下

### 根目录保留

只保留核心文档：
- README.md / README_zh.md - 项目主文档
- CHANGELOG.md - 统一的变更日志
- AGENTS.md - Agent 配置
- requirements.txt - 依赖文件

## 实施方案

### 自动化脚本

已创建 `scripts/organize-docs.sh` 脚本，可以自动完成以下操作：

1. ✅ 创建备份（`docs_backup_YYYYMMDD_HHMMSS/`）
2. ✅ 创建新目录结构
3. ✅ 移动版本发布文档到 `docs/releases/v0.8.1/`
4. ✅ 移动设计文档到 `docs/design/`
5. ✅ 移动功能文档到 `docs/features/`
6. ✅ 移动架构文档到 `docs/architecture/`
7. ✅ 移动问题解决文档到 `docs/troubleshooting/`
8. ✅ 移动博客文章到 `docs/blog/`
9. ✅ 移动资源文件到 `docs/assets/images/`
10. ✅ 创建文档索引 `docs/README.md`
11. ✅ 创建统一的 `CHANGELOG.md`
12. ✅ 清理临时文件（.DS_Store）

### 使用方法

```bash
# 运行整理脚本
./scripts/organize-docs.sh

# 检查变更
git status

# 提交变更
git add .
git commit -m "docs: reorganize documentation structure"
```

## 文档清单

### 将被移动的文件

**根目录 → docs/releases/v0.8.1/**
- CHANGELOG_0.8.1.md → changelog.md
- RELEASE_NOTES_0.8.1.md → release-notes.md
- DEVELOPMENT_SUMMARY_0.8.1.md → development-summary.md
- FINAL_SUMMARY_0.8.1.md → final-summary.md
- QUICK_REFERENCE_0.8.1.md → quick-reference.md
- RELEASE_SUMMARY_0.8.1.md → release-summary.md
- TEST_REPORT_0.8.1.md → test-report.md

**根目录 → docs/design/**
- CONFIG_CLEANUP_SUMMARY.md → 2026-04-18-config-cleanup.md
- SETTINGS_UI_REDESIGN.md → 2026-04-18-settings-ui-redesign.md

**docs/ → docs/features/**
- backup-feature-design.md → backup.md

**docs/ → docs/architecture/**
- FRONTEND_ARCHITECTURE.md → frontend.md

**docs/ → docs/troubleshooting/**
- ollama-embedding-fix.md → ollama-embedding.md
- ollama-embedding-analysis.md → ollama-embedding-analysis.md
- web-ui-ollama-url-update.md → ollama-web-ui-config.md

**docs/ → docs/blog/**
- article-two-weekends-ai-team.md → two-weekends-ai-team.md

**docs/ → docs/assets/images/**
- screenshots/ → screenshots/

### 保留在原位置的文件

**根目录**
- README.md
- README_zh.md
- AGENTS.md
- requirements.txt
- RELEASE_NOTES.md（可选：合并到 CHANGELOG.md 后删除）

**docs/**
- 2026-03-24-knowledge-base-design.md → design/
- 2026-04-05-v0.6-knowledge-mining-design.md → design/
- 2026-04-15-knowledge-base-backup-design.md → design/
- 2026-04-16-phase1-delivery-report.md → design/
- IMPLEMENTATION_SUMMARY.md
- MODEL_SERVICE_TEST_REPORT.md
- TEST_DATA_SUMMARY.md
- CONFIG_TEMPLATE.md
- TODOS.md

## 维护规范

### 新增文档时

1. 确定文档类型，放入对应目录
2. 使用统一的命名规范
3. 更新 `docs/README.md` 索引

### 版本发布时

1. 在 `docs/releases/vX.Y.Z/` 创建新目录
2. 添加 release-notes.md、changelog.md、migration-guide.md
3. 更新根目录的 `CHANGELOG.md`

### 设计决策时

1. 使用 ADR 格式
2. 文件名：`YYYY-MM-DD-title.md`
3. 放入 `docs/design/` 目录

## 优势

整理后的文档结构具有以下优势：

1. ✅ **清晰的分类**：按用途组织，易于查找
2. ✅ **统一的命名**：遵循一致的命名规范
3. ✅ **版本归档**：历史版本文档有序管理
4. ✅ **易于维护**：明确的目录结构和规范
5. ✅ **便于导航**：统一的索引和链接
6. ✅ **可扩展性**：为未来文档预留空间
7. ✅ **专业性**：符合开源项目最佳实践

## 相关文档

- [详细方案](documentation-organization-plan.md) - 完整的文档组织方案
- [快速指南](QUICK_START_DOCS_ORGANIZATION.md) - 快速开始指南
- [整理脚本](../scripts/organize-docs.sh) - 自动化整理脚本

## 下一步

1. **立即执行**（高优先级）
   - 运行 `./scripts/organize-docs.sh`
   - 检查并提交变更

2. **本周完成**（中优先级）
   - 更新文档内部链接
   - 完善 `docs/README.md` 索引
   - 合并 CHANGELOG

3. **逐步完善**（低优先级）
   - 创建用户指南
   - 完善开发文档
   - 添加 API 文档

## 注意事项

1. **备份**：脚本会自动创建备份，但建议先提交当前更改
2. **链接**：整理后需要手动更新文档内部链接
3. **Git 历史**：脚本使用 `git mv` 保留文件历史
4. **团队沟通**：通知团队成员文档结构变更

## 总结

通过这次文档整理，我们将：

- 清理根目录，只保留 4 个核心文档
- 将 13 个散乱文档归档到合适的目录
- 建立清晰的文档分类和命名规范
- 创建统一的文档索引和导航
- 为未来文档维护建立良好基础

这将大大提升项目的专业性和可维护性！
