# LocalBrain macOS App — 设计与详细计划

## 1. 产品定位

将 Agentic Local Brain 从浏览器 Web 应用升级为 macOS 桌面应用，内嵌后端服务，双击即用。保留所有现有 Web 功能，同时利用桌面端能力提升体验。

## 2. 技术架构

```
LocalBrain.app (DMG 分发)
├── Tauri 2.0 Shell (Rust)
│   ├── WebView (WKWebView)
│   │   └── Vue 3 SPA (Vite + TypeScript)
│   │       ├── Radix Vue (无样式组件)
│   │       ├── TailwindCSS (macOS 风格)
│   │       ├── Vue Router (路由)
│   │       ├── Pinia (状态管理)
│   │       ├── ECharts (图表/知识图谱)
│   │       └── vue-i18n (国际化)
│   │
│   ├── Tauri Commands (Rust ↔ JS bridge)
│   │   ├── 文件拖拽采集
│   │   ├── 系统通知
│   │   └── 菜单栏/全局快捷键
│   │
│   └── Sidecar (PyInstaller binary)
│       └── localbrain server (FastAPI + SQLite + ChromaDB)
```

### 运行流程

1. 用户双击 LocalBrain.app
2. Tauri 启动 → 拉起 sidecar (localbrain server)
3. 健康检查循环 → 等待 `/health` 返回 200
4. 加载 Vue SPA → 连接 `http://localhost:{port}/api/*`
5. 用户关闭窗口 → Tauri 停止 sidecar → 退出

### 数据目录

继续使用 `~/.localbrain/`，与 CLI 版本共享数据：
- `~/.localbrain/config.yaml` — 配置
- `~/.localbrain/data/knowledge.db` — SQLite
- `~/.localbrain/data/chroma/` — ChromaDB
- `~/.localbrain/backups/` — 备份

## 3. 前端页面清单

从现有 Web 提取，共 17 个页面/视图：

| # | 页面 | 路由 | 核心 API | 复杂度 |
|---|------|------|----------|--------|
| 1 | 仪表盘 | `/` | `GET /stats`, `GET /recent`, `GET /rag-stats` | 中 |
| 2 | 笔记列表 | `/items/note` | `GET /items?type=note` | 低 |
| 3 | 书签列表 | `/items/bookmark` | `GET /items?type=bookmark` | 低 |
| 4 | 网页列表 | `/items/webpage` | `GET /items?type=webpage` | 低 |
| 5 | 论文列表 | `/items/paper` | `GET /items?type=paper` | 低 |
| 6 | 邮件列表 | `/items/email` | `GET /items?type=email` | 低 |
| 7 | 文件列表 | `/items/file` | `GET /items?type=file` | 低 |
| 8 | 知识详情 | `/items/:id` | `GET /items/:id`, `GET /items/:id/preview` | 中 |
| 9 | 标签管理 | `/tags` | `GET /tags`, `POST /tags/merge`, `DELETE /tags/:name` | 中 |
| 10 | 知识图谱 | `/graph` | `GET /graph`, `GET /graph/stats`, `GET /graph/entity/:id` | 高 |
| 11 | 主题聚类 | `/topics` | `GET /topics`, `GET /topics/:id/documents`, `GET /topics/timeline` | 高 |
| 12 | 时间线 | `/timeline` | `GET /topics/timeline`, `GET /topics/trend` | 中 |
| 13 | 推荐 | `/recommendations` | `GET /recommendations`, `GET /reading-history` | 低 |
| 14 | Wiki | `/wiki` | `GET /wiki/tree`, `GET /wiki/articles`, `GET /wiki/entities` | 高 |
| 15 | RAG 对话 | `/rag` | `POST /rag/chat`, `GET /rag/conversations` | 高 |
| 16 | 备份管理 | `/backup` | `POST /backup/create`, `GET /backup/list` | 中 |
| 17 | 系统设置 | `/settings` | `GET /settings`, `PUT /settings/*`, `POST /settings/test-*` | 高 |

## 4. macOS 原生风格设计规范

### 4.1 视觉系统

- **窗口**：标准 macOS 窗口，左上角红绿灯按钮，可拖拽标题栏
- **侧边栏**：仿 Finder 侧边栏，半透明背景（vibrancy），分组折叠
- **颜色**：
  - 主色：系统蓝 `#007AFF`
  - 背景：`#F5F5F7`（亮）/ `#1E1E1E`（暗）
  - 侧边栏背景：半透明 `rgba(246,246,246,0.8)`
  - 分割线：`rgba(0,0,0,0.1)`
- **字体**：SF Pro（系统字体 `-apple-system`），中文回退 `PingFang SC`
- **圆角**：卡片 10px，按钮 6px，输入框 6px
- **阴影**：卡片 `0 1px 3px rgba(0,0,0,0.08)`
- **暗色模式**：跟随系统，通过 Tailwind `dark:` 前缀实现

### 4.2 布局结构

```
┌──────────────────────────────────────────────┐
│ ●●●  ←     →     Local Brain    🔍 搜索      │ ← 标题栏 + 工具栏
├──────────┬───────────────────────────────────┤
│ 概览     │                                   │
│ ─────── │         主内容区域                  │
│ 知识收集  │                                   │
│  笔记    │                                   │
│  书签    │                                   │
│  网页    │                                   │
│  论文    │                                   │
│  邮件    │                                   │
│  文件    │                                   │
│ ─────── │                                   │
│ 发现     │                                   │
│  图谱    │                                   │
│  主题    │                                   │
│  推荐    │                                   │
│ ─────── │                                   │
│ 工具     │                                   │
│  Wiki   │                                   │
│  RAG    │                                   │
│  备份    │                                   │
│  设置    │                                   │
└──────────┴───────────────────────────────────┘
```

### 4.3 交互规范

- **导航**：侧边栏点击切换页面，无页面刷新
- **列表**：虚拟滚动（超过 100 条），支持键盘上下导航
- **搜索**：全局搜索栏（Cmd+K 唤起），类似 Spotlight
- **详情**：右侧面板滑入，或全屏弹窗
- **删除**：macOS 风格确认对话框
- **加载**：骨架屏（Skeleton），不用 spinner
- **Toast**：右上角通知，3 秒自动消失

## 5. 项目结构

```
localbrain-app/
├── src-tauri/                    # Tauri (Rust)
│   ├── Cargo.toml
│   ├── tauri.conf.json           # App 配置（窗口、sidecar、权限）
│   ├── src/
│   │   ├── main.rs               # 入口
│   │   ├── sidecar.rs            # Sidecar 生命周期管理
│   │   ├── commands.rs           # Tauri Commands (JS↔Rust)
│   │   └── tray.rs               # 菜单栏图标
│   └── binaries/                 # PyInstaller 打包的 localbrain binary
│
├── src/                          # Vue 3 前端
│   ├── App.vue
│   ├── main.ts
│   ├── router/
│   │   └── index.ts              # Vue Router 路由定义
│   ├── stores/                   # Pinia 状态管理
│   │   ├── app.ts                # 全局状态（语言、主题、服务状态）
│   │   ├── items.ts              # 知识条目
│   │   ├── tags.ts               # 标签
│   │   ├── search.ts             # 搜索/RAG
│   │   ├── wiki.ts               # Wiki
│   │   └── graph.ts              # 知识图谱
│   ├── api/                      # API 层
│   │   ├── client.ts             # Axios/fetch 封装
│   │   ├── dashboard.ts
│   │   ├── items.ts
│   │   ├── search.ts
│   │   ├── tags.ts
│   │   ├── wiki.ts
│   │   ├── graph.ts
│   │   ├── topics.ts
│   │   ├── backup.ts
│   │   ├── settings.ts
│   │   ├── mining.ts
│   │   └── recommendations.ts
│   ├── components/               # 可复用组件
│   │   ├── layout/
│   │   │   ├── AppSidebar.vue
│   │   │   ├── AppToolbar.vue
│   │   │   └── AppLayout.vue
│   │   ├── common/
│   │   │   ├── SearchBar.vue     # Cmd+K 全局搜索
│   │   │   ├── TagBadge.vue
│   │   │   ├── ConfirmDialog.vue
│   │   │   ├── Toast.vue
│   │   │   ├── Skeleton.vue
│   │   │   └── EmptyState.vue
│   │   ├── items/
│   │   │   ├── ItemCard.vue
│   │   │   ├── ItemDetail.vue
│   │   │   └── ItemList.vue
│   │   └── graph/
│   │       └── KnowledgeGraph.vue
│   ├── views/                    # 页面组件
│   │   ├── DashboardView.vue
│   │   ├── ItemsView.vue
│   │   ├── TagsView.vue
│   │   ├── GraphView.vue
│   │   ├── TopicsView.vue
│   │   ├── TimelineView.vue
│   │   ├── RecommendationsView.vue
│   │   ├── WikiView.vue
│   │   ├── RagView.vue
│   │   ├── BackupView.vue
│   │   └── SettingsView.vue
│   ├── i18n/                     # 国际化
│   │   ├── en.ts
│   │   └── zh.ts
│   └── styles/
│       └── tailwind.css
│
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── README.md
```

## 6. 分期计划

### Phase 1 — 项目骨架 + 核心页面（预计 2 周）

**目标**：App 可运行，核心流程跑通

**任务拆解**：

1.1 **项目初始化**
- 创建 Tauri 2.0 + Vite + Vue 3 + TypeScript 项目
- 配置 TailwindCSS + Radix Vue
- 配置 vue-i18n（迁移现有中英文翻译）
- 配置 Vue Router + Pinia

1.2 **App Shell**
- AppLayout：侧边栏 + 工具栏 + 内容区
- macOS 风格侧边栏（分组、图标、高亮）
- 暗色模式跟随系统
- 全局搜索栏（Cmd+K）UI 骨架

1.3 **API 层**
- HTTP client 封装（base URL 配置、错误处理）
- 所有 API endpoint 的 TypeScript 类型定义
- 请求/响应拦截器

1.4 **仪表盘页面**
- 统计卡片（知识总数、标签总数、各类型计数）
- RAG 使用统计
- 各类型最近条目列表
- ECharts 标签云

1.5 **知识列表页面（6 个子类型）**
- 通用 ItemList 组件（搜索、筛选、分页、虚拟滚动）
- 6 个类型视图复用同一组件，不同展示模式
- 标签筛选、类型筛选、关键词搜索

1.6 **知识详情**
- 详情面板/弹窗
- Markdown 内容渲染
- 标签显示、编辑标题、用户批注
- 删除确认

1.7 **Sidecar 集成**
- Tauri sidecar 配置
- 启动/停止 localbrain server
- 健康检查 + 启动等待
- 启动画面（Splash screen）

---

### Phase 2 — 发现与工具页面（预计 2 周）

**目标**：所有页面功能完成

2.1 **标签管理**
- 标签列表 + 词云
- 标签合并
- 标签删除
- 按标签查看条目

2.2 **知识图谱**
- ECharts 力导向图
- 实体类型筛选
- 节点点击 → 实体详情
- 缩放、全屏、对数缩放

2.3 **主题聚类 + 时间线**
- 主题列表 + 文档关联
- 时间线可视化
- 趋势图
- 主题重建触发

2.4 **推荐**
- 推荐列表
- 阅读历史

2.5 **Wiki**
- 分类树导航
- 文章列表 + 搜索
- 文章详情（Markdown 渲染）
- 实体卡片
- Wiki 编译触发

2.6 **RAG 对话**
- 对话列表侧栏
- 多轮对话界面（聊天气泡）
- 来源引用展示
- 实体/主题上下文
- 置信度显示
- 会话管理（新建/删除/清空）

2.7 **备份管理**
- 创建备份
- 备份列表（本地 + 云）
- 状态跟踪
- 删除备份

2.8 **系统设置**
- LLM 配置（provider/model/key/url）
- Embedding 配置
- 备份配置（云存储）
- 连通性测试
- Doctor 诊断

---

### Phase 3 — 桌面特性 + 打包发布（预计 1.5 周）

**目标**：生产级 macOS App

3.1 **macOS 桌面特性**
- 菜单栏常驻图标（系统托盘）
- 全局快捷键（Cmd+Shift+Space 唤起搜索）
- 文件拖拽到窗口 → 自动采集
- 系统通知（挖掘完成、备份完成）

3.2 **性能优化**
- 列表虚拟滚动
- 路由懒加载
- API 请求缓存（SWR 模式）
- 图表按需加载

3.3 **打包与分发**
- PyInstaller 打包 localbrain → 单二进制
- Tauri 打包 → .dmg
- Developer ID 签名
- 自动更新机制（Tauri updater）
- CI/CD（GitHub Actions：构建 + 签名 + 发布）

3.4 **测试**
- 组件单元测试（Vitest）
- E2E 测试（Playwright）
- sidecar 启停测试

---

## 7. 团队分工建议

| 角色 | 负责范围 |
|------|---------|
| @Allen (TL) | 架构设计、Tauri/Rust 集成、sidecar 管理、代码审查、发布流程 |
| @Tom (全栈) | Vue 3 前端页面实现（Phase 1-2 所有页面组件）、API 层、i18n |
| @Alice (QA) | 页面功能测试、交互验证、跨页面回归、E2E 测试编写 |

## 8. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| PyInstaller 打包后 ChromaDB 兼容性 | sidecar 启动失败 | 提前验证，Phase 1 就做 sidecar 集成 |
| ECharts 在 WebView 中的性能 | 知识图谱卡顿 | 限制节点数、启用 canvas 渲染、降级方案 |
| 大知识库下 SQLite 性能 | 列表加载慢 | 虚拟滚动 + 分页 + API 缓存 |
| macOS 签名/公证 | 用户打不开 App | 使用 Developer ID + notarize，或提供 bypass 说明 |
