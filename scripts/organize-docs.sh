#!/bin/bash
# 文档整理脚本
# 用途：将项目文档按照规范重新组织

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否在项目根目录
if [ ! -f "README.md" ] || [ ! -d "kb" ]; then
    log_error "请在项目根目录运行此脚本"
    exit 1
fi

log_info "开始整理文档..."

# 备份当前状态
log_info "创建备份..."
BACKUP_DIR="docs_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r docs "$BACKUP_DIR/" 2>/dev/null || true
cp *.md "$BACKUP_DIR/" 2>/dev/null || true
log_info "备份已创建: $BACKUP_DIR"

# 创建新目录结构
log_info "创建新目录结构..."
mkdir -p docs/{guides,architecture,features,development,releases/v0.8.1,design,troubleshooting,blog,assets/images}

# 移动版本发布文档
log_info "整理版本发布文档..."
if [ -f "CHANGELOG_0.8.1.md" ]; then
    git mv CHANGELOG_0.8.1.md docs/releases/v0.8.1/changelog.md 2>/dev/null || mv CHANGELOG_0.8.1.md docs/releases/v0.8.1/changelog.md
fi

if [ -f "RELEASE_NOTES_0.8.1.md" ]; then
    git mv RELEASE_NOTES_0.8.1.md docs/releases/v0.8.1/release-notes.md 2>/dev/null || mv RELEASE_NOTES_0.8.1.md docs/releases/v0.8.1/release-notes.md
fi

if [ -f "DEVELOPMENT_SUMMARY_0.8.1.md" ]; then
    git mv DEVELOPMENT_SUMMARY_0.8.1.md docs/releases/v0.8.1/development-summary.md 2>/dev/null || mv DEVELOPMENT_SUMMARY_0.8.1.md docs/releases/v0.8.1/development-summary.md
fi

if [ -f "FINAL_SUMMARY_0.8.1.md" ]; then
    git mv FINAL_SUMMARY_0.8.1.md docs/releases/v0.8.1/final-summary.md 2>/dev/null || mv FINAL_SUMMARY_0.8.1.md docs/releases/v0.8.1/final-summary.md
fi

if [ -f "QUICK_REFERENCE_0.8.1.md" ]; then
    git mv QUICK_REFERENCE_0.8.1.md docs/releases/v0.8.1/quick-reference.md 2>/dev/null || mv QUICK_REFERENCE_0.8.1.md docs/releases/v0.8.1/quick-reference.md
fi

if [ -f "RELEASE_SUMMARY_0.8.1.md" ]; then
    git mv RELEASE_SUMMARY_0.8.1.md docs/releases/v0.8.1/release-summary.md 2>/dev/null || mv RELEASE_SUMMARY_0.8.1.md docs/releases/v0.8.1/release-summary.md
fi

if [ -f "TEST_REPORT_0.8.1.md" ]; then
    git mv TEST_REPORT_0.8.1.md docs/releases/v0.8.1/test-report.md 2>/dev/null || mv TEST_REPORT_0.8.1.md docs/releases/v0.8.1/test-report.md
fi

# 移动设计文档
log_info "整理设计文档..."
if [ -f "CONFIG_CLEANUP_SUMMARY.md" ]; then
    git mv CONFIG_CLEANUP_SUMMARY.md docs/design/2026-04-18-config-cleanup.md 2>/dev/null || mv CONFIG_CLEANUP_SUMMARY.md docs/design/2026-04-18-config-cleanup.md
fi

if [ -f "SETTINGS_UI_REDESIGN.md" ]; then
    git mv SETTINGS_UI_REDESIGN.md docs/design/2026-04-18-settings-ui-redesign.md 2>/dev/null || mv SETTINGS_UI_REDESIGN.md docs/design/2026-04-18-settings-ui-redesign.md
fi

# 移动 docs/ 目录中的设计文档
if [ -f "docs/2026-04-15-knowledge-base-backup-design.md" ]; then
    git mv docs/2026-04-15-knowledge-base-backup-design.md docs/design/2026-04-15-backup-design.md 2>/dev/null || mv docs/2026-04-15-knowledge-base-backup-design.md docs/design/2026-04-15-backup-design.md
fi

# 移动功能文档
log_info "整理功能文档..."
if [ -f "docs/backup-feature-design.md" ]; then
    git mv docs/backup-feature-design.md docs/features/backup.md 2>/dev/null || mv docs/backup-feature-design.md docs/features/backup.md
fi

# 移动架构文档
log_info "整理架构文档..."
if [ -f "docs/FRONTEND_ARCHITECTURE.md" ]; then
    git mv docs/FRONTEND_ARCHITECTURE.md docs/architecture/frontend.md 2>/dev/null || mv docs/FRONTEND_ARCHITECTURE.md docs/architecture/frontend.md
fi

# 移动问题解决文档
log_info "整理问题解决文档..."
if [ -f "docs/ollama-embedding-fix.md" ]; then
    git mv docs/ollama-embedding-fix.md docs/troubleshooting/ollama-embedding.md 2>/dev/null || mv docs/ollama-embedding-fix.md docs/troubleshooting/ollama-embedding.md
fi

if [ -f "docs/ollama-embedding-analysis.md" ]; then
    git mv docs/ollama-embedding-analysis.md docs/troubleshooting/ollama-embedding-analysis.md 2>/dev/null || mv docs/ollama-embedding-analysis.md docs/troubleshooting/ollama-embedding-analysis.md
fi

if [ -f "docs/web-ui-ollama-url-update.md" ]; then
    git mv docs/web-ui-ollama-url-update.md docs/troubleshooting/ollama-web-ui-config.md 2>/dev/null || mv docs/web-ui-ollama-url-update.md docs/troubleshooting/ollama-web-ui-config.md
fi

# 移动博客文章
log_info "整理博客文章..."
if [ -f "docs/article-two-weekends-ai-team.md" ]; then
    git mv docs/article-two-weekends-ai-team.md docs/blog/two-weekends-ai-team.md 2>/dev/null || mv docs/article-two-weekends-ai-team.md docs/blog/two-weekends-ai-team.md
fi

# 移动截图
log_info "整理资源文件..."
if [ -d "docs/screenshots" ]; then
    git mv docs/screenshots docs/assets/images/screenshots 2>/dev/null || mv docs/screenshots docs/assets/images/screenshots
fi

# 创建文档索引
log_info "创建文档索引..."
cat > docs/README.md << 'EOF'
# Agentic Local Brain 文档

欢迎来到 Agentic Local Brain 的文档中心！

## 📚 快速导航

### 用户指南
- [安装指南](guides/installation.md) - 如何安装和部署
- [快速开始](guides/quick-start.md) - 5 分钟快速上手
- [配置指南](guides/configuration.md) - 详细配置说明
- [故障排除](guides/troubleshooting.md) - 常见问题解决

### 🏗️ 架构设计
- [架构概览](architecture/overview.md) - 系统整体架构
- [前端架构](architecture/frontend.md) - 前端技术栈和设计
- [后端架构](architecture/backend.md) - 后端服务设计
- [数据流设计](architecture/data-flow.md) - 数据处理流程

### ✨ 功能文档
- [知识挖掘](features/knowledge-mining.md) - 自动知识提取和组织
- [备份功能](features/backup.md) - 数据备份和恢复
- [向量化](features/embedding.md) - 文本向量化和检索
- [LLM 集成](features/llm-integration.md) - 大语言模型集成

### 🔧 开发文档
- [开发环境搭建](development/setup.md) - 本地开发环境配置
- [编码规范](development/coding-standards.md) - 代码风格和最佳实践
- [测试指南](development/testing.md) - 单元测试和集成测试
- [API 参考](development/api-reference.md) - API 接口文档

### 📦 版本发布
- [v0.8.1](releases/v0.8.1/release-notes.md) - 最新版本
- [v0.8.0](releases/v0.8.0/release-notes.md)
- [v0.7.0](releases/v0.7.0/release-notes.md)

### 🎯 设计决策（ADR）
- [2026-04-19 - Ollama Embedding 修复](design/2026-04-19-ollama-embedding-fix.md)
- [2026-04-18 - 前端重构设计](design/2026-04-18-frontend-refactor.md)
- [2026-04-18 - 设置界面重设计](design/2026-04-18-settings-ui-redesign.md)
- [2026-04-18 - 配置清理](design/2026-04-18-config-cleanup.md)
- [2026-04-15 - 备份功能设计](design/2026-04-15-backup-design.md)
- [2026-04-05 - 知识挖掘设计](design/2026-04-05-v0.6-knowledge-mining-design.md)
- [2026-03-24 - 知识库设计](design/2026-03-24-knowledge-base-design.md)

### 🐛 问题解决
- [Ollama Embedding 配置](troubleshooting/ollama-embedding.md) - Ollama embedding 参数问题
- [Ollama 技术分析](troubleshooting/ollama-embedding-analysis.md) - 深入技术分析
- [Ollama Web UI 配置](troubleshooting/ollama-web-ui-config.md) - Web 界面配置更新
- [常见错误](troubleshooting/common-errors.md) - 常见错误和解决方案

### 📝 博客
- [两个周末打造 AI 团队](blog/two-weekends-ai-team.md) - 项目开发故事

## 🔍 文档搜索

使用 GitHub 搜索功能或 Ctrl+F 在页面内搜索。

## 📖 文档规范

- [文档组织方案](documentation-organization-plan.md) - 文档结构和维护规范

## 🤝 贡献

发现文档问题或想要改进？欢迎提交 Issue 或 Pull Request！

## 📧 联系我们

- GitHub Issues: [提交问题](https://github.com/your-repo/issues)
- 邮件: your-email@example.com
EOF

log_info "文档索引已创建: docs/README.md"

# 创建 CHANGELOG.md（如果不存在）
if [ ! -f "CHANGELOG.md" ]; then
    log_info "创建统一的 CHANGELOG.md..."
    cat > CHANGELOG.md << 'EOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/your-repo/compare/v0.8.1...HEAD
[0.8.1]: https://github.com/your-repo/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/your-repo/releases/tag/v0.8.0
EOF
fi

# 清理 .DS_Store 文件
log_info "清理临时文件..."
find docs/ -name ".DS_Store" -delete 2>/dev/null || true

# 显示结果
log_info "文档整理完成！"
echo ""
echo "📁 新的文档结构："
tree docs/ -L 2 -d 2>/dev/null || find docs/ -type d | head -20

echo ""
log_info "下一步："
echo "  1. 检查 docs/README.md 并更新链接"
echo "  2. 运行 'git status' 查看变更"
echo "  3. 运行 'git add .' 和 'git commit' 提交变更"
echo "  4. 如需恢复，备份在: $BACKUP_DIR"
echo ""
log_warn "注意：某些文档可能需要手动更新内部链接"
