# Multi-turn RAG Phase 3: Conversation Summarization + Auto Session Title

## Goal

支持长对话场景：(1) 当对话轮次超过阈值时，用 LLM 将旧轮次压缩为摘要 message，保留关键信息不丢失；(2) 首轮问答后自动生成会话标题，方便会话列表展示和管理。

## What I already know

### Phase 1/2 现状

- `_build_messages()` 构造 `[system, ...history turns, user]` 多轮 messages
- `get_recent_turns(limit=5)` 按 `history_turns_in_context: 5` 限制返回条数
- 动态 token budget 根据 conversation length 自动调整检索预算
- `ConversationManager` 管理 SQLite 持久化的会话和 turns

### 当前缺口

#### 摘要压缩
- `history_turns_in_context: 5` 硬截断，超过 5 轮的旧内容直接丢弃
- 无摘要机制 — 第 6 轮时第 1 轮的上下文完全消失
- `max_turns: 20` 配置存在但未被强制使用

#### 会话标题
- `rag_conversations` 表无 `title` 字段
- `list_sessions()` 用 `last_question` 代替标题展示
- 无自动标题生成机制

### 约束

- 摘要压缩需要一次 LLM 调用（额外成本）
- DB schema 变更需要 migration（加 title + summary 字段）
- 摘要应作为 system message 注入 messages[]，不是替换 history turns

## Open Questions

(all resolved)

## Decision (ADR-lite)

### D1: 摘要触发时机
**Context**: 对话超过 `history_turns_in_context` 后旧轮次被丢弃，需要摘要保留
**Decision**: Lazy summarization — 在 `run()` 执行时检查 turns 数量，超阈值则生成/更新摘要
**Consequences**: 不增加 add_turn 延迟，只在实际需要上下文时触发。首次超阈值的那轮 run() 会多一次 LLM 调用。

### D2: 标题生成时机
**Context**: 会话列表需要标题以供展示
**Decision**: 首轮问答完成后同步生成 — 在 `run()` 保存 turns 之后调用 LLM 生成标题（max_tokens=30）
**Consequences**: 首轮就有标题，UX 好。额外 LLM 成本极低，只第一轮触发。

## Requirements

### R1: 对话摘要压缩
- 当 turns 数量超过 `history_turns_in_context` 时，对超出范围的旧 turns 生成摘要
- 摘要存储在 session 级别（`rag_conversations` 表新增 `summary` 字段）
- 在 `_build_messages()` 中，摘要作为 system message 的一部分注入（在 system prompt 之后）
- 每次新轮次超过阈值时更新摘要

### R2: 会话标题自动生成
- DB schema: `rag_conversations` 表新增 `title` 字段
- 首轮问答完成后，用 LLM 根据 question + answer 生成短标题（≤30 字符）
- 标题存入 session
- `list_sessions()` 返回 title 字段
- 添加 `update_session_title()` 方法支持手动修改

### R3: 向后兼容
- Schema migration 用 `ALTER TABLE ADD COLUMN`（SQLite 支持）
- 旧 session 无 title/summary 时返回 None
- `list_sessions()` fallback 到 `last_question` 当 title 为空

## Acceptance Criteria (evolving)

- [ ] 超过 5 轮对话后，早期内容以摘要形式保留（不丢失）
- [ ] 摘要正确注入 messages[]（在 system prompt 后、history turns 前）
- [ ] 首轮问答后自动生成会话标题
- [ ] `list_sessions()` 返回 title（有则返回，无则 fallback last_question）
- [ ] Schema migration 不破坏现有数据
- [ ] 单轮对话行为不变
- [ ] 现有测试通过
- [ ] 新增摘要和标题的单元测试

## Definition of Done

- Tests added/updated (unit/integration where appropriate)
- Lint / typecheck / CI green

## Out of Scope (explicit)

- 前端适配
- 手动编辑标题的 API 端点（只提供 ConversationManager 方法）
- 摘要的精确 token 控制（Phase 2 的动态 budget 已处理）

## Technical Approach

### Schema Migration (`conversation.py`)

在 `_ensure_tables()` 中用 `ALTER TABLE` 安全添加列：

```python
# Add title column if not exists
try:
    cursor.execute("ALTER TABLE rag_conversations ADD COLUMN title TEXT")
except sqlite3.OperationalError:
    pass  # column already exists

# Add summary column if not exists
try:
    cursor.execute("ALTER TABLE rag_conversations ADD COLUMN summary TEXT")
except sqlite3.OperationalError:
    pass
```

### 摘要压缩流程

`ConversationManager` 新增方法：
- `get_summary(session_id)` — 读取 summary 字段
- `update_summary(session_id, summary)` — 更新 summary 字段
- `get_all_turns(session_id)` — 获取全部 turns（不限制条数，用于摘要生成）

`RetrievalPipeline` 新增方法：
- `_maybe_summarize(session_id, conversation_turns)` — 检查是否需要摘要，需要则调用 LLM 生成

在 `run()` 中，加载 turns 后：
```
all_turns = conversation_manager.get_all_turns(session_id)
if len(all_turns) > history_turns_in_context:
    # 获取超出部分的旧 turns
    old_turns = all_turns[:-history_turns_in_context]
    # 生成或更新摘要
    summary = self._generate_summary(old_turns, existing_summary)
    conversation_manager.update_summary(session_id, summary)
```

`_build_messages()` 修改：接受可选 `summary` 参数
```
messages = [{"role": "system", "content": system_prompt}]
if summary:
    messages.append({"role": "system", "content": f"Previous conversation summary:\n{summary}"})
if conversation_turns:
    for turn in conversation_turns:
        messages.append({"role": turn.role, "content": turn.content})
messages.append({"role": "user", "content": user_prompt})
```

### 标题生成流程

`RetrievalPipeline` 新增方法：
- `_generate_title(question, answer)` — 调用 LLM 生成 ≤30 字符标题

在 `run()` 保存 turns 后：
```
if is_new_session or history_turns == 0:
    title = self._generate_title(question, answer)
    conversation_manager.update_title(session_id, title)
```

### LLM 调用共用

摘要和标题的 LLM 调用复用 `_build_llm_kwargs()` 方法，使用较低的 temperature (0.1) 和不同的 max_tokens。

## Implementation Plan

1. **Schema + ConversationManager 方法**（`conversation.py`）
   - ALTER TABLE migration
   - `get_summary()`, `update_summary()`, `get_title()`, `update_title()`
   - `list_sessions()` 返回 title 字段

2. **摘要 + 标题生成**（`retrieval_pipeline.py`）
   - `_generate_summary()` 和 `_generate_title()` 方法
   - `_build_messages()` 接受 summary 参数
   - `run()` 和 `run_stream()` 集成

3. **测试**
   - Schema migration 测试
   - 摘要生成/注入测试
   - 标题生成测试
   - 向后兼容测试

## Technical Notes

### 关键文件
- `kb/query/conversation.py` — schema + title/summary CRUD
- `kb/query/retrieval_pipeline.py` — 摘要/标题 LLM 调用 + messages[] 注入
- `kb/web/routes/search.py` — `list_sessions` 返回 title（已有字段透传）
- `tests/test_retrieval_pipeline.py` — 测试
