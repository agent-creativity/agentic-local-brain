# Trellis Spec 初始化：按项目实际情况填充 backend spec

## 目标

本仓库（Agentic Local Brain）首次引入 Trellis 工作流。`trellis init` 生成的 `.trellis/spec/backend/` 下 5 个 spec 文件均为空模板（"To be filled by the team"）。需要根据项目实际代码结构、技术栈和编码惯例，将模板填充为项目专属的开发规范，使 AI 辅助开发和新成员 onboarding 有据可依。

## 需求

### 需要填充的 5 个 spec 文件

1. **directory-structure.md** — 填入 `kb/` 的实际目录布局和模块组织规范
   - 顶层目录职责（collectors / commands / processors / query / scheduler / storage / web）
   - 模块命名约定（snake_case 文件名，类名 PascalCase）
   - 新功能模块的放置规则

2. **database-guidelines.md** — 填入 SQLite + ChromaDB 的实际使用规范
   - SQLiteStorage 的事务模式（contextmanager `_transaction`）
   - ChromaDB 集合管理和向量操作模式
   - Schema 迁移方式（`_migrate_schema` 方法）
   - FTS5 全文索引约定

3. **error-handling.md** — 填入项目实际的错误处理模式
   - 结果数据类模式（CollectResult 的 success/error 字段）
   - 优雅降级策略（embedding 失败 → keyword fallback）
   - CLI 层 Click exception handling
   - FastAPI 路由错误响应格式

4. **quality-guidelines.md** — 填入代码质量工具和标准
   - Black (line-length=88) + isort + mypy 配置
   - pytest 测试规范和 markers（integration / slow）
   - Google-style docstrings 要求
   - 禁止模式清单

5. **logging-guidelines.md** — 填入日志使用规范
   - `logging.getLogger(__name__)` 标准模式
   - 各级别使用场景（DEBUG/INFO/WARNING/ERROR）
   - 不应记录的内容（API keys, PII）
   - CLI 输出 vs 日志的区分

### 同时更新

6. **spec/backend/index.md** — 更新索引，反映已填充状态
7. **.trellis/config.yaml** — 确认配置无需调整（当前默认配置已适用）

## 验收标准

- [ ] 5 个 backend spec 文件从模板变为项目实际规范，包含代码示例
- [ ] 每个 spec 包含：概述、约定、示例代码、禁止模式
- [ ] spec 内容与实际代码一致（可通过 code review 验证）
- [ ] index.md 更新为已填充状态
- [ ] guides/ 下 2 个文件保持不变（通用指南，无需项目定制）

## 非目标

- 不新增 spec 层（如 api / collector / ai-ml），仅填充 backend 层现有模板
- 不修改任何业务代码
- 不修改 CLAUDE.md 或其他非 .trellis 文件
- 不引入 Trellis 外的工具或流程

## 技术备注

- 涉及仓库/模块：`.trellis/spec/backend/` 下 6 个文件（5 spec + 1 index）
- 关键约束：spec 内容必须从实际代码中提取，不可凭空编写
- 参考实现：`CLAUDE.md` 已有精简版技术栈和模式描述，可作为 spec 内容的 seed
- 数据源：`kb/` 源码、`tests/`、`pyproject.toml`、`requirements.txt`
