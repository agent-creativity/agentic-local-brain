# AGENTS.md 文档规范更新总结

## 更新内容

已将完整的文档维护规范添加到 `AGENTS.md` 文件中，确保后续 AI Agent 在生成文档时能够遵循统一的规范。

## 新增章节

### Documentation Standards

添加了一个完整的 "Documentation Standards" 章节，包含以下内容：

#### 1. 文档结构规范

定义了标准的 `docs/` 目录结构：

```
docs/
├── README.md              # 文档索引
├── guides/                # 用户指南
├── architecture/          # 架构设计
├── features/              # 功能文档
├── development/           # 开发文档
├── releases/              # 版本发布
├── design/                # 设计决策（ADR）
├── troubleshooting/       # 问题解决
├── blog/                  # 博客文章
└── assets/images/         # 资源文件
```

#### 2. 文件命名规范

- **普通文档**：小写 + 连字符（`quick-start.md`）
- **设计文档**：日期前缀（`2026-04-19-title.md`）
- **版本文档**：放在 `releases/vX.Y.Z/` 目录

#### 3. 文档结构规范

- 每个文档只有一个 H1 标题
- 使用 H2 作为主要章节
- 使用 H3 作为子章节
- 避免使用 H4，不跳过标题层级

#### 4. 创建新文档的步骤

1. 确定文档类型
2. 创建文档文件
3. 添加元数据（可选）
4. 更新文档索引

#### 5. 版本发布文档规范

每个版本需要包含：
- `release-notes.md` - 发布说明
- `changelog.md` - 变更日志
- `migration-guide.md` - 迁移指南
- `test-report.md` - 测试报告（可选）

#### 6. 设计决策记录（ADR）模板

提供了完整的 ADR 模板，包括：
- 上下文
- 决策
- 后果（正面、负面、中性）
- 替代方案
- 实施方法
- 参考资料

#### 7. 问题解决文档模板

提供了故障排除文档模板，包括：
- 问题描述
- 根本原因
- 解决方案
- 验证方法
- 预防措施

#### 8. 链接规范

- 使用相对链接（推荐）
- 避免绝对链接

#### 9. 代码示例规范

- 使用正确的语法高亮
- 包含上下文说明
- 提供完整可运行的示例

#### 10. 文档维护

- 定期审查和更新
- 链接检查
- 版本清理
- 索引更新

#### 11. 文档检查清单

提供了提交前的检查清单：
- [ ] 文件在正确目录
- [ ] 文件名符合规范
- [ ] 标题结构正确
- [ ] 代码示例完整
- [ ] 使用相对链接
- [ ] 更新索引
- [ ] 无拼写错误
- [ ] Markdown 格式正确

#### 12. 根目录文件规范

明确规定根目录只保留：
- README.md / README_zh.md
- CHANGELOG.md
- AGENTS.md
- CONTRIBUTING.md
- LICENSE

#### 13. 文档组织脚本

说明如何使用 `./scripts/organize-docs.sh` 脚本

#### 14. 示例对比

提供了好的和坏的文档结构示例

## 优势

将文档规范写入 AGENTS.md 后，带来以下优势：

### 1. AI Agent 自动遵循规范

当 AI Agent（如 Claude Code、GitHub Copilot）读取 AGENTS.md 时，会自动了解并遵循文档规范：

- ✅ 自动将文档放入正确的目录
- ✅ 使用正确的文件命名格式
- ✅ 遵循标准的文档结构
- ✅ 使用统一的模板
- ✅ 更新文档索引

### 2. 团队协作一致性

- 所有团队成员（人类和 AI）遵循相同的规范
- 减少代码审查中的文档格式问题
- 提高文档质量和可维护性

### 3. 自动化支持

- AI Agent 可以自动检查文档是否符合规范
- 可以自动生成符合规范的文档
- 可以自动更新文档索引

### 4. 降低学习成本

- 新成员（人类或 AI）可以快速了解文档规范
- 减少重复性的文档格式问题
- 提高文档创建效率

## 使用示例

### AI Agent 创建新功能文档

当 AI Agent 需要创建新功能文档时，会：

1. 读取 AGENTS.md 中的文档规范
2. 确定文档类型为 "功能文档"
3. 在 `docs/features/` 目录创建文件
4. 使用小写 + 连字符命名：`new-feature.md`
5. 使用标准的文档结构（一个 H1，多个 H2/H3）
6. 更新 `docs/README.md` 索引

### AI Agent 创建设计决策文档

当 AI Agent 需要记录设计决策时，会：

1. 读取 AGENTS.md 中的 ADR 模板
2. 在 `docs/design/` 目录创建文件
3. 使用日期前缀命名：`2026-04-19-decision-title.md`
4. 按照 ADR 模板填写内容
5. 包含上下文、决策、后果、替代方案等章节

### AI Agent 创建版本发布文档

当发布新版本时，AI Agent 会：

1. 创建 `docs/releases/v0.9.0/` 目录
2. 生成必需的文档：
   - `release-notes.md`
   - `changelog.md`
   - `migration-guide.md`
3. 更新根目录的 `CHANGELOG.md`
4. 更新 `docs/README.md` 索引

## 验证

可以通过以下方式验证 AI Agent 是否遵循规范：

```bash
# 检查文档结构
tree docs/ -L 2

# 检查文件命名
find docs/ -name "*.md" | grep -v "^docs/[a-z-]*.md$" | grep -v "^docs/design/[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-.*\.md$"

# 检查 Markdown 格式
markdownlint docs/**/*.md

# 检查链接
markdown-link-check docs/**/*.md
```

## 后续改进

可以进一步增强文档规范：

1. **添加文档模板**：在 `docs/templates/` 目录创建各类文档模板
2. **自动化检查**：创建 pre-commit hook 检查文档规范
3. **文档生成工具**：使用 MkDocs 或 Docusaurus 生成文档网站
4. **CI/CD 集成**：在 CI 中自动检查文档格式和链接

## 相关文件

- `AGENTS.md` - 已更新，包含完整的文档规范
- `docs/documentation-organization-plan.md` - 详细的文档组织方案
- `docs/QUICK_START_DOCS_ORGANIZATION.md` - 快速开始指南
- `docs/DOCUMENTATION_ORGANIZATION_SUMMARY.md` - 方案总结
- `scripts/organize-docs.sh` - 文档整理脚本

## 总结

通过将文档维护规范写入 AGENTS.md，我们实现了：

1. ✅ **标准化**：统一的文档结构和命名规范
2. ✅ **自动化**：AI Agent 自动遵循规范
3. ✅ **可维护**：清晰的维护指南和检查清单
4. ✅ **可扩展**：为未来文档类型预留空间
5. ✅ **专业性**：符合开源项目最佳实践

现在，无论是人类开发者还是 AI Agent，都能够按照统一的规范创建和维护项目文档，大大提升了文档质量和项目的专业性！
