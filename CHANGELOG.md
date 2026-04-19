# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.3...HEAD
[0.8.3]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/agent-creativity/agentic-local-brain/releases/tag/v0.8.0
