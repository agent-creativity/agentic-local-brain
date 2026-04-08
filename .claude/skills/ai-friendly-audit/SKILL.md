---
name: ai-friendly-audit
version: 0.2.0
description: 代码仓库 AI 亲和度审计工具，支持前端、后端、全栈等各类项目。此技能用于检查给定的代码仓库对 AI Coding 工具的友好程度，生成详细的分析报告和改进建议。当用户需要评估代码仓库是否适合 AI 辅助开发、希望提升仓库的 AI 可操作性、或准备引入 AI Coding 工具前进行仓库评估时，应使用此技能。支持 TypeScript/JavaScript、Go、Java/Kotlin、Python、Rust 等主流技术栈。融合 OpenAI Harness Engineering 方法论，评估 Outer Loop（反馈闭环、评估门禁、机械化不变量）建设。
---

# AI Friendly Audit（AI 亲和度审计）v3.0

## 概述

此技能用于系统性评估代码仓库对 AI Coding 工具的友好程度。通过自动化脚本收集数据 + 人工审查相结合，生成量化评分和改进建议报告，帮助团队优化代码仓库以获得更好的 AI 协作体验。

**适用范围**: 前端、后端、全栈、SDK/库、Monorepo 等各类项目。

**v3.0 新增**: 融合 OpenAI Harness Engineering 方法论，新增"Outer Loop & 反馈闭环"维度，强调机械化不变量、评估门禁和自验证能力。

## 核心理念

AI 亲和的代码仓库应具备以下特质：

1. **信任链闭环（Inner Loop）** — AI 做出的修改可被快速验证（测试、类型检查、lint），形成"修改→验证→反馈"的快速循环
2. **最小可运行环境** — 降低环境依赖，便于 AI 理解和复现问题，能在本地快速启动和验证
3. **规范驱动开发（SDD）** — 文档即规范，AI 可据此生成和验证代码，而不是靠猜测
4. **上下文窗口友好** — 单文件可被完整读取，代码粒度适合 AI 处理，避免"记忆墙"问题
5. **代码自述性** — 文件和函数自带足够上下文，减少 AI 跳转查阅的需要
6. **机械化不变量（Outer Loop）** — 架构意图必须通过自动化手段（linter 规则、结构测试、评估门禁）机械化执行，而非仅靠文档约定。参考 OpenAI Harness Engineering："Agent 会按比例复制模式，架构约束必须机械化执行"

### Inner Loop 与 Outer Loop

```
┌──────────────────────────────────────────────────────────────┐
│  Inner Loop（Agent 执行循环）                                 │
│  prompt → 推理 → 工具调用 → 输出 → 再次推理 → ... → 完成    │
└──────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────┐
│  Outer Loop（质量保障闭环）                                   │
│  类型检查 → 单元测试 → 结构测试 → 覆盖率门禁 → 构建验证     │
│  AGENTS.md → 架构文档 → 评估门禁 → 回归检测                  │
└──────────────────────────────────────────────────────────────┘
```

- **Inner Loop**: AI Agent 的推理-执行循环，关注单次任务的正确执行
- **Outer Loop**: 围绕 Agent 构建的质量保障体系，确保 AI 生成的代码持续符合架构规范

## 审计工作流程

### 关于"记忆墙"问题

AI Coding 工具的上下文窗口有限。审计过程中，优先使用脚本自动收集数据并输出结构化结果，避免逐个文件手动检查导致上下文溢出。工作流设计为"脚本先行、人工补充"模式。

### Phase 1: 自动化扫描（脚本驱动）

运行自动化脚本收集仓库基础数据，这一步会输出结构化的 JSON 数据，覆盖大部分可自动检测的维度：

```bash
python3 scripts/repo_scan.py <repo_path> --json
```

脚本会自动检测并输出：
- 项目类型（前端/后端/全栈/库）和技术栈（语言、框架、包管理器）
- 各维度的自动化检查结果（文件存在性、配置检测等）
- 文件体积统计和评分
- Outer Loop 基础设施检测（结构测试、覆盖率门禁、质量脚本等）

如果只需要检查文件体积：

```bash
python3 scripts/check_file_size.py <src_path> --warn 500 --error 1000 --json
```

### Phase 2: 人工补充检查

脚本无法覆盖的维度（如代码质量、错误处理模式、架构合理性等）需要人工抽样检查。参考 `references/checklist.md` 中标注为"需人工检查"的项目。

人工检查时，聚焦于：
- 抽查 3-5 个核心源文件，评估代码自述性和命名规范
- 查看错误处理模式是否统一
- 评估模块边界是否清晰
- **[v3.0]** 检查是否存在结构测试（验证分层规则、导入约束等）
- **[v3.0]** 评估 AGENTS.md 是否为"目录式"结构（~100 行入口 + 独立文档），而非百科全书式

### Phase 3: 生成报告

根据脚本输出 + 人工检查结果，使用 `references/report_template.md` 模板生成最终报告。

---

## 审计维度（11 个维度）

以下维度适用于所有项目类型。每个维度满分 4 分，通过权重加权计算总分（满分 100）。

| # | 维度 | 权重 | 适用范围 | 关键检查点 |
|---|------|------|----------|------------|
| 1 | 最小可运行环境 | 11% | 全部 | 一键启动、依赖屏蔽/Mock、环境变量模板、依赖锁定 |
| 2 | 类型系统与静态分析 | 11% | 全部 | 静态类型、严格模式、类型覆盖率 |
| 3 | 测试体系 | 14% | 全部 | 单元测试、集成/E2E 测试、覆盖率、测试可独立运行 |
| 4 | 文档完备性 | 10% | 全部 | README、架构文档、API 文档、开发指南 |
| 5 | 代码规范与自动化 | 7% | 全部 | Linting、格式化、Git Hooks、提交规范 |
| 6 | 模块化架构 | 9% | 全部 | 分层清晰、低耦合、职责单一、无循环依赖 |
| 7 | 上下文窗口友好性 | 9% | 全部 | 文件行数、函数复杂度、模块粒度 |
| 8 | 代码自述性 | 7% | 全部 | 文件综述、语义化命名、关键注释 |
| 9 | AI 工具与 SDD 支持 | 8% | 全部 | AI 配置文件、API 规范、架构规范 |
| 10 | 依赖隔离与可复现性 | 5% | 全部 | 外部依赖可屏蔽、构建可复现、容器化支持 |
| **11** | **Outer Loop & 反馈闭环** | **9%** | **全部** | **结构测试、评估门禁、覆盖率阈值、质量脚本、机械化不变量** |

> **v3.0 变化**: 新增维度 11，其余维度权重微调以容纳新维度，总权重保持 100%。

---

## 各维度检查指南

### 1. 最小可运行环境（11%）

**核心目标**: AI Coding 工具可在本地快速启动应用并验证修改效果。

不同技术栈的检查重点：

| 技术栈 | 一键启动 | 依赖屏蔽 | 环境模板 | 依赖锁定 |
|--------|---------|---------|---------|---------|
| Node.js | `npm run dev` | MSW / json-server | `.env.example` | `package-lock.json` |
| Go | `make run` / `go run` | 接口 Mock / build tags | `.env.example` | `go.sum` + vendor |
| Java/Kotlin | `mvn spring-boot:run` | Spring Profiles + H2 | `application-local.properties` | `pom.xml` 版本锁定 |
| Python | `python -m app` | pytest fixtures / mock | `.env.example` | `requirements.txt` / `poetry.lock` |
| Rust | `cargo run` | feature flags / mock traits | `.env.example` | `Cargo.lock` |

**评分标准：**
- 4分：一键启动 + 依赖可屏蔽 + 环境模板 + 依赖锁定
- 3分：一键启动 + 有启动文档或部分 Mock
- 2分：可启动但需手动配置
- 1分：启动依赖外部服务，无 Mock 方案
- 0分：无明确启动方式或强依赖外部服务

### 2. 类型系统与静态分析（11%）

**核心目标**: 静态类型检查提供快速反馈，AI 生成的代码可被类型系统即时校验。

| 技术栈 | 类型系统 | 严格模式 | 检查命令 |
|--------|---------|---------|---------|
| TypeScript | `tsconfig.json` strict | `noImplicitAny` 等 | `npx tsc --noEmit` |
| Go | 内置强类型 | `go vet` + staticcheck | `go vet ./...` |
| Java/Kotlin | 内置强类型 | Error-Prone / NullAway | `mvn compile` |
| Python | mypy / pyright | strict mode | `mypy --strict src/` |
| Rust | 内置强类型 | `#![deny(warnings)]` | `cargo check` |

**评分标准：**
- 4分：强类型 + 严格模式 + 静态分析工具 + 无类型逃逸
- 3分：有类型系统，少量类型逃逸（any / unsafe / suppress）
- 2分：有类型系统但配置宽松
- 1分：部分代码有类型
- 0分：动态语言无类型注解

### 3. 测试体系（14%）

**核心目标**: AI 修改代码后可快速运行测试验证正确性，形成信任链闭环。

检查项：
- **测试框架配置**: Jest/Vitest、Go testing、JUnit/TestNG、pytest 等
- **测试覆盖率**: 配置覆盖率报告工具（Istanbul、JaCoCo、coverage.py 等）
- **测试可独立运行**: 不依赖外部服务（数据库、API 等），使用 mock/fixture/testcontainers
- **核心路径覆盖**: 关键业务逻辑有测试保护

**评分标准：**
- 4分：覆盖率 >70% + 核心路径有测试 + 测试可独立运行 + E2E/集成测试
- 3分：覆盖率 50-70% + 有单元测试框架 + 部分 mock
- 2分：有测试但覆盖率低或依赖外部服务
- 1分：有测试框架但测试极少
- 0分：无测试

### 4. 文档完备性（10%）

**核心目标**: AI 可通过文档理解项目上下文、架构决策和开发规范。

必查文档：
- **README.md** — 项目简介、快速开始、项目结构
- **架构文档** — 系统架构、模块关系、数据流（如 `docs/architecture.md`）
- **API 文档** — 接口定义、请求/响应格式（OpenAPI spec 或 Markdown）
- **开发规范** — 编码规范、目录约定、命名规则（如 `backend_dev_rule.md`）

**[v3.0] AGENTS.md 最佳实践** (参考 OpenAI Harness Engineering):
- AGENTS.md 应为**目录式结构**（~100 行入口），而非百科全书
- 详细规范应分散到独立文档（`.cursor/rules/`、`docs/` 等）
- 避免在 AGENTS.md 中堆砌过多内容，防止挤占 Agent 的任务上下文

**评分标准：**
- 4分：README + 架构文档 + API 文档 + 开发规范 + AI 指南
- 3分：README 完整 + 架构文档或 API 文档
- 2分：README 基本完整
- 1分：README 简单或过期
- 0分：无文档

### 5. 代码规范与自动化（7%）

**核心目标**: 代码风格一致，AI 生成代码可被自动校验和格式化。

| 技术栈 | Linting | 格式化 | Git Hooks |
|--------|---------|--------|-----------|
| TypeScript | ESLint / Biome | Prettier | husky + lint-staged |
| Go | golangci-lint | gofmt / goimports | pre-commit |
| Java | Checkstyle / Error-Prone | google-java-format | pre-commit |
| Python | ruff / pylint | black / ruff format | pre-commit |
| Rust | clippy | rustfmt | pre-commit |

**评分标准：**
- 4分：Lint + Format + Pre-commit + 提交规范
- 3分：Lint + Format + Pre-commit
- 2分：Lint + Format
- 1分：仅有 Lint 配置
- 0分：无规范约束

### 6. 模块化架构（9%）

**核心目标**: 代码结构清晰，AI 可理解边界并进行局部修改而不影响全局。

不同项目类型的模块化标准：

| 项目类型 | 良好结构 | 差的结构 |
|---------|---------|---------|
| 前端 | 按功能/页面组织，组件/hooks/services 分离 | 所有组件平铺在一个目录 |
| Go 后端 | `cmd/` + `pkg/` 或 `internal/`，按领域划分包 | 所有代码在一个 package |
| Java 后端 | controller → service → dao 分层，按模块划分包 | 所有类在一个包里 |
| Python 后端 | 按模块划分，清晰的 `__init__.py` 导出 | 单个巨大的 `app.py` |

**评分标准：**
- 4分：清晰分层 + 无循环依赖 + 职责单一 + 模块边界清晰
- 3分：合理分层，少量耦合
- 2分：有分层但边界模糊
- 1分：耦合较重，修改一处需要改多处
- 0分：意大利面代码

### 7. 上下文窗口友好性（9%）

**核心目标**: 确保代码文件可被 AI 完整读取和理解，避免因文件过长导致上下文截断。

使用脚本检查：

```bash
python3 scripts/check_file_size.py <src_path> --warn 500 --error 1000
```

**行数阈值建议**:

| 类型 | 推荐 | 警告 | 严重 |
|------|------|------|------|
| 源文件 | ≤500 行 | 500-1000 行 | >1000 行 |
| 函数/方法 | ≤80 行 | 80-150 行 | >150 行 |
| 类/组件 | ≤300 行 | 300-600 行 | >600 行 |
| 测试文件 | ≤800 行 | 800-1500 行 | >1500 行 |

**评分标准：**
- 4分：90% 文件 ≤500 行 + 无超过 1000 行的文件
- 3分：80% 文件 ≤500 行 + 少量 500-1000 行文件
- 2分：存在多个 500-1000 行文件，少量超过 1000 行
- 1分：多个文件超过 1000 行
- 0分：大量文件超过 1000 行或存在超过 2000 行的巨型文件

### 8. 代码自述性（7%）

**核心目标**: AI 无需跳转多个文件就能理解当前代码的目的和上下文。

检查要点：
- **文件综述**: 文件开头有注释说明职责（Go 的 package doc、Java 的 class Javadoc、Python 的 module docstring）
- **函数文档**: 公开函数/方法有文档注释说明参数、返回值和用途
- **语义化命名**: 变量、函数、文件名具有描述性，避免缩写和单字母
- **关键逻辑注释**: 复杂算法或业务逻辑有解释性注释

**评分标准：**
- 4分：90% 文件有综述 + 公开 API 有完整文档 + 语义化命名一致
- 3分：核心文件有综述 + 主要函数有文档
- 2分：部分文件有注释，命名基本规范
- 1分：注释稀少，命名不规范
- 0分：无注释，命名混乱

### 9. AI 工具与 SDD 支持（8%）

**核心目标**: 项目有 AI 工具配置和规范驱动开发支持，AI 可据此理解项目意图。

检查项：

| 类别 | 文件/工具 | 说明 |
|------|----------|------|
| AI 配置 | `.cursorrules` / `.cursor/rules/` | Cursor AI 编码规则 |
| AI 配置 | `AGENTS.md` | Claude Code 指南 |
| AI 配置 | `.github/copilot-instructions.md` | Copilot 指令 |
| AI 上下文 | Memory Bank / `.lingma/` | AI 助手项目上下文 |
| API 规范 | `openapi.yaml` / Swagger | 机器可读的 API 定义 |
| 开发规范 | `CONVENTIONS.md` / `*_dev_rule.md` | 编码规范文档 |
| 架构规范 | `Architecture.md` / 设计文档 | 架构决策记录 |
| AI 技能 | `.cursor/skills/` / `.claude/skills/` | 可复用的 AI 操作规范 |

**[v3.0] 机械化不变量** (参考 OpenAI Harness Engineering):
- 架构约束不能仅靠文档 — 必须有自动化手段执行
- 检查是否有自定义 linter 规则或结构测试验证分层/导入约束
- 示例：禁止 `pages/` 直接导入底层模块、验证 Tailwind 版本合规性

**评分标准：**
- 4分：AI 配置 + API 规范 + 开发规范 + 架构文档 + 机械化约束
- 3分：有 AI 配置 + 架构文档或 API 规范
- 2分：有架构文档或 AI 配置文件
- 1分：仅有基本 README
- 0分：无任何规范驱动文档

### 10. 依赖隔离与可复现性（5%）

**核心目标**: 外部依赖可被屏蔽或替换，构建结果可复现。

| 技术栈 | 依赖隔离方式 | 构建可复现 | 容器化 |
|--------|------------|-----------|--------|
| Node.js | MSW / mock service | lock 文件 + .nvmrc | Dockerfile |
| Go | interface mock / build tags | go.sum + vendor | Dockerfile |
| Java | Spring Profiles + H2/Testcontainers | Maven wrapper + 版本锁定 | Dockerfile |
| Python | pytest mock / dependency injection | poetry.lock / pip freeze | Dockerfile |

**评分标准：**
- 4分：外部依赖全部可屏蔽 + 构建可复现 + 有容器化
- 3分：主要依赖可屏蔽 + 构建可复现
- 2分：部分依赖可屏蔽
- 1分：强依赖外部服务，但有文档说明
- 0分：强依赖外部服务，无隔离方案

### 11. Outer Loop & 反馈闭环（9%）🆕

**核心目标**: 围绕 AI Agent 构建完整的质量保障闭环，确保 AI 生成的代码持续符合架构规范。

> 参考 OpenAI Harness Engineering: "人的角色从写代码变为设计环境——让 Agent 可靠地产出正确的代码。"
> 关键洞察："架构意图必须通过自定义 linter 和结构测试机械化执行，因为 Agent 会按比例复制模式。"

**检查项：**

| 类别 | 检查点 | 示例 |
|------|--------|------|
| **结构测试** | 是否有架构约束的自动化测试 | 分层导入规则、文件体积上限、JSDoc 覆盖率 |
| **评估门禁** | 是否有一键质量脚本 | `ai:check`、`quality_check.sh` |
| **覆盖率阈值** | 测试覆盖率是否有阈值门禁 | vitest coverage thresholds、jacoco minimums |
| **回归检测** | 是否可检测质量趋势变化 | IHS 报告、SonarQube、自定义趋势脚本 |
| **可观测性** | Agent 是否可访问日志/错误来自我验证 | 结构化日志、错误追踪集成 |

**各技术栈的 Outer Loop 实践：**

| 技术栈 | 结构测试 | 评估门禁 | 回归检测 |
|--------|---------|---------|---------|
| TypeScript | `architecture.test.ts`（导入约束、体积检查） | `npm run ai:check` | IHS 报告 / 覆盖率趋势 |
| Go | `go test` 包导入约束测试 | `make check` / `golangci-lint` | 覆盖率趋势 |
| Java | ArchUnit 测试（分层约束） | `mvn verify` | JaCoCo 报告 |
| Python | `pytest` 导入约束测试 | `tox` / `nox` | 覆盖率趋势 |

**评分标准：**
- 4分：结构测试 + 一键评估门禁 + 覆盖率阈值 + 回归检测
- 3分：一键评估门禁 + 覆盖率阈值
- 2分：有部分评估脚本
- 1分：仅有 CI 基础构建
- 0分：无任何质量保障闭环

---

## 评分等级

| 等级 | 分数范围 | 描述 |
|------|----------|------|
| A | 90-100 | AI 亲和度优秀，可高效协作 |
| B | 75-89 | AI 亲和度良好，有小幅改进空间 |
| C | 60-74 | AI 亲和度一般，需重点改进 |
| D | 40-59 | AI 亲和度较差，需系统性改造 |
| F | <40 | AI 亲和度极低，不适合 AI 协作 |

---

## 改进建议模板

报告中的改进建议应按技术栈给出具体可操作的步骤。以下是各类项目常见的改进方向：

### 后端项目常见改进

1. **添加 API 文档** — 为 REST/gRPC 接口生成 OpenAPI spec 或编写接口文档
2. **拆分大文件** — 将超过 1000 行的文件按职责拆分（如 Go 的 scheduler.go 拆为 filter.go、priority.go、scorer.go）
3. **添加本地开发配置** — 提供 `.env.example`、`application-local.properties`、`docker-compose.dev.yml` 等
4. **配置静态分析** — Go 项目添加 `.golangci.yml`，Java 项目配置 Error-Prone/Checkstyle
5. **编写架构文档** — 说明模块关系、数据流、关键设计决策
6. **添加 AI 配置文件** — 创建 `.cursorrules` 或 `AGENTS.md` 指导 AI 行为
7. **[v3.0] 添加结构测试** — 使用 ArchUnit (Java) 或自定义测试验证分层约束

### 前端项目常见改进

1. **配置 Mock 模式** — 使用 MSW 或 json-server 屏蔽后端依赖
2. **启用 TypeScript strict** — 开启严格模式，消除 any 类型
3. **添加组件文档** — Storybook 或组件级注释
4. **配置 E2E 测试** — Playwright/Cypress 覆盖关键流程
5. **[v3.0] 添加架构约束测试** — 验证导入方向、Tailwind 版本合规、文件体积上限

### 通用改进

1. **创建 `.cursorrules`** — 定义编码规范和 AI 协作指南
2. **为核心文件添加文件综述** — 文件开头说明职责和依赖
3. **运行 `check_file_size.py`** — 定期检查并拆分超标文件
4. **编写开发规范文档** — 明确目录约定、命名规则、错误处理模式
5. **[v3.0] 构建 Outer Loop** — 添加一键质量脚本、覆盖率阈值、结构测试

### Outer Loop 建设路线图（v3.0 新增）

| 阶段 | 目标 | 关键动作 |
|------|------|----------|
| L1 基础 | 可运行 + 可检查 | `ai:check` 脚本、lint + type-check |
| L2 门禁 | 覆盖率不退化 | 覆盖率阈值、pre-commit hooks |
| L3 约束 | 架构机械化 | 结构测试、自定义 linter 规则 |
| L4 闭环 | 趋势可追踪 | IHS/SonarQube 报告、回归检测 |
| L5 自治 | Agent 可自验证 | Agent 可访问日志/错误、自修复循环 |

---

## Harness Engineering 参考

> 以下要点提炼自 OpenAI Harness Engineering 文章 (2026-02)

### 核心观点

1. **工程师角色转变**: 从写代码变为设计环境——让 Agent 可靠地产出正确的代码
2. **机械化不变量**: 架构意图必须通过自定义 linter 和结构测试机械化执行，仅靠文档不够
3. **AGENTS.md 作为目录**: ~100 行入口，指向独立文档，避免百科全书式导致上下文挤占
4. **可观测性即自验证**: Agent 应能访问日志、指标、追踪来自我验证和修复
5. **评估门禁**: 结构化的"完成"标准（回归测试、安全检查），让 Agent 可自主判断任务完成
6. **人的注意力是稀缺资源**: 系统设计应最大化 Agent 的自主性，最小化人工审查负担

### 适用于审计的关键指标

| 指标 | 低成熟度 | 高成熟度 |
|------|---------|---------|
| 架构约束 | 仅文档描述 | 结构测试 + 自定义 linter 机械化执行 |
| 质量门禁 | 无或仅 CI 构建 | 一键脚本 + 覆盖率阈值 + 回归检测 |
| AGENTS.md | 无或百科全书式 | 目录入口 + 独立规范文档 |
| Agent 自验证 | 无 | 可访问日志/错误，闭环修复 |

---

## 资源文件

### scripts/
- `repo_scan.py` — 自动化仓库扫描脚本，收集基础信息并输出 JSON
- `check_file_size.py` — 文件体积检查脚本

### references/
- `checklist.md` — 完整的检查清单和评分细则
- `report_template.md` — 报告输出模板

## 快速开始

1. 运行 `python3 scripts/repo_scan.py <repo_path> --json` 获取自动化扫描数据
2. 阅读脚本输出，对照 11 个维度评估
3. 对脚本无法覆盖的维度（错误处理、代码自述性、Outer Loop 成熟度等）进行人工抽样
4. 使用 `references/report_template.md` 生成报告
5. 按优先级提出改进建议，优先推荐 Quick Wins
6. **[v3.0]** 特别关注 Outer Loop 建设成熟度，评估是否有结构测试和评估门禁
