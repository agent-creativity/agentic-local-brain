# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.6] - 2026-04-28

### Fixed
- 修复主题聚类重建时的外键约束错误（正确的表删除顺序）
- 修复 `localbrain mine run --full` 在主题聚类阶段的 FK 约束失败问题

## [0.8.5] - 2026-04-27

### Added
- 用户批注功能（user_notes 字段）
- 知识条目标题编辑功能
- Web UI 批注和标题编辑对话框
- 中英文 i18n 翻译支持

<img width="1194" height="1550" alt="image" src="https://github.com/user-attachments/assets/9c3a820f-a430-4aa9-9b1e-9a3c6fb7f708" />


### Changed
- 更新 API 支持 user_notes 和 title 字段更新
- 优化知识详情页面 UI 布局

### Fixed
- 修复重复翻译条目导致的 JS 语法错误

## [0.8.4] - 2026-04-21

### Added
- 可配置的摘要最大长度（extraction.summary_max_length）
- 配置模板中添加摘要长度配置项

### Changed
- README 文档更新（新增功能说明和安装选项）
- 完整翻译 README.zh-CN.md 与英文版保持一致
- 添加首页和知识图谱截图到文档

### Fixed
- 修复全量重建时 ChromaDB embedding 维度不匹配问题（自动重置）
- 修复主题聚类中的外键约束失败问题

## [0.8.3] - 2026-04-20

### Added
- 云存储配置界面（支持阿里云 OSS、AWS S3、本地存储）
- 备份列表分页功能（每页 20 个备份/任务）
- 云存储备份自动列表查询（OSS/S3）
- 备份配置保存和加载功能
- 系统配置页面"备份配置"标签页
- 补充缺失的依赖包：schedule、croniter、oss2

### Changed
- 简化备份管理页面（移除冗余字段和下拉框）
- 备份创建自动使用系统配置中的默认云存储设置
- 统一显示本地备份和云存储备份
- 简化删除流程（移除确认对话框）
- 改进备份删除 API（支持通过 id 或 filename 删除）

### Fixed
- 备份删除错误处理增强
- 云存储备份显示和管理
- 修复 cron 表达式验证错误（croniter 需要基准时间参数）

详细内容请查看 [v0.8.3 发布说明](docs/releases/v0.8.3/release-notes.md)

## [0.8.2] - 2026-04-19

### Added
- Documentation organization script for automated structure management
- Comprehensive documentation standards in AGENTS.md
- Ollama embedding troubleshooting guides
- Test cases for embedding parameter filtering
- Unified CHANGELOG.md and documentation index

### Changed
- Reorganized all documentation into structured directories (9 subdirectories)
- Root directory reduced from 14 files to 6 core files
- Enhanced embedder with dual-layer parameter filtering for Ollama
- Updated Web UI Ollama default URL (removed /v1 suffix)
- Standardized file naming conventions across all documentation

### Fixed
- Ollama embedding encoding_format parameter conflict
- Web UI default configuration for Ollama
- Configuration template examples for Ollama

See [v0.8.2 Release Notes](docs/releases/v0.8.2/release-notes.md) for details.

## [0.8.1] - 2026-04-18

详细内容请查看 [v0.8.1 发布说明](docs/releases/v0.8.1/release-notes.md)

### Added
- Ollama embedding 参数自动过滤
- Web UI 配置页面优化

### Changed
- 文档结构重组

### Fixed
- Ollama embedding encoding_format 参数冲突

## [0.8.0] - 2026-04-10

详细内容请查看 [v0.8.0 发布说明](docs/releases/v0.8.0/release-notes.md)

---

[Unreleased]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.6...HEAD
[0.8.6]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.5...v0.8.6
[0.8.5]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.4...v0.8.5
[0.8.4]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.3...v0.8.4
[0.8.3]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/agent-creativity/agentic-local-brain/releases/tag/v0.8.0
