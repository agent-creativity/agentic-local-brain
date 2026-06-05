# Multi-turn RAG Phase 1: proper messages[] + streaming

## Goal

改善多轮对话 RAG 的核心体验：(1) 将对话历史从 flat text 注入改为 LLM 原生的 multi-turn messages[] 格式，提升模型对上下文的理解能力；(2) 添加 SSE streaming 端点，让前端可以逐 token 渲染回答。

## What I already know

### 现状分析（来自代码审查）

- `retrieval_pipeline.py:1052-1055`：`_generate_answer()` 只构造 2 条 messages `[system, user]`，对话历史被塞进 system prompt 的尾部或 user prompt 的模板里
- `conversation.py:360-402`：`format_history_for_prompt()` 返回 `"User: ...\nAssistant: ..."` 的 flat text，硬截断 4000 chars (~1000 tokens)
- `prompt_templates.py:156`：conversation_history 作为 `## Previous Conversation` section 注入模板
- `retrieval_pipeline.py:1067`：使用同步 `litellm.completion()`，无 streaming
- `search.py:243-299`：`/rag/chat` 端点同步返回完整 JSON
- `conversation.py:199-239`：`get_recent_turns()` 已返回结构化 `ConversationTurn` 对象（含 role/content），可直接用于构建 messages[]
- 现有测试：`tests/test_retrieval_pipeline.py`

### 约束

- LLM 调用通过 LiteLLM 统一，需使用 `litellm.completion(stream=True)` 和/或 `litellm.acompletion(stream=True)`
- FastAPI SSE 需要 `sse-starlette` 或手写 `StreamingResponse`
- 现有 `/rag/chat` 端点的同步接口必须保留（向后兼容），streaming 作为新端点添加
- ConversationManager 的 DB schema 无需改动

## Assumptions (temporary)

- 前端（Dashboard）暂不在本任务范围，只提供 API 层 streaming 能力
- Token budget 统一管理（Phase 2 scope）暂不做，但 messages[] 改造时需考虑总 token 数不超限
- 不引入新的 Python 依赖（`sse-starlette` 如已在 deps 中则可用，否则用 FastAPI 原生 `StreamingResponse`）

## Open Questions

(all resolved)

## Decision (ADR-lite)

### D1: Streaming 端点设计
**Context**: SSE streaming 和 JSON 是完全不同的响应格式，需要决定是共用端点还是分离
**Decision**: 独立端点 `POST /rag/chat/stream`
**Consequences**: 清晰分离两种响应格式，OpenAPI schema 更准确，前端按需选择

### D2: 对话历史 token 控制
**Context**: 现有 `format_history_for_prompt()` 用 4000 chars 硬截断，改为 messages[] 后不再合理
**Decision**: 改为按 turns 数量限制（沿用配置 `history_turns_in_context: 5`），不做 chars 截断
**Consequences**: 更自然，极端长回答可能占用更多 token，但实际场景中 5 轮对话不太可能溢出。精确 token 控制留给 Phase 2

## Requirements

### R1: Proper multi-turn messages[]
- 将 `_generate_answer()` 中的 messages 构造逻辑改为：`[system, ...历史user/assistant交替, 当前user(含context)]`
- 新增 `_build_messages()` 私有方法，接收 conversation_turns（`List[ConversationTurn]`）、system_prompt、user_prompt，返回 `List[dict]`
- Pipeline `run()` 方法中，从 `get_recent_turns()` 获取结构化 turns，传给 `_generate_answer()` 代替 flat text `conversation_history`
- System prompt 不再拼接对话历史
- 模板渲染仍使用 `PromptTemplateManager`，但 `{conversation_history}` 传空字符串（历史通过 messages[] 注入）
- 空对话历史（第一轮）：messages 退化为 `[system, user]`，与当前单轮行为一致

### R2: SSE Streaming 端点
- 新增 `POST /rag/chat/stream` 端点，请求体复用 `RAGChatRequest`
- Pipeline Stage 1-5（检索、重排、上下文构建）同步执行
- Stage 6 使用 `litellm.completion(stream=True)` 获取流式响应
- 通过 FastAPI `StreamingResponse(media_type="text/event-stream")` 逐 chunk 发送
- SSE 事件格式：
  - 检索阶段完成：`data: {"type": "sources", "sources": [...]}\n\n`
  - 逐 token：`data: {"type": "token", "content": "..."}\n\n`
  - 完成：`data: {"type": "done", "session_id": "...", "confidence": 0.x}\n\n`
  - 错误：`data: {"type": "error", "message": "..."}\n\n`
- Streaming 完成后保存完整回答到 ConversationManager
- 在 `RetrievalPipeline` 中新增 `run_stream()` 方法，yield SSE events（generator）

### R3: 保持向后兼容
- 现有 `/rag/chat` 同步端点行为不变（内部也改用 messages[]，但响应格式不变）
- `format_history_for_prompt()` 保留不删除（可能被外部调用），但 pipeline 内部不再使用
- Legacy `/rag` 端点不改动

### R4: Edge cases
- ConversationManager 不可用时：降级为无历史的单轮模式（当前行为）
- LLM streaming 异常/中断：发送 error event，已生成的部分文本仍保存到 conversation turns
- `litellm` 未安装：streaming 端点返回 503

## Acceptance Criteria

- [ ] `/rag/chat` 同步端点行为与改造前一致（回归测试通过）
- [ ] 多轮对话时，LLM 收到的 messages 包含正确的历史 user/assistant 交替（至少 system + N 轮历史 + 当前 user）
- [ ] 单轮对话（无 session_id）仍正常工作，messages 为 `[system, user]`
- [ ] `POST /rag/chat/stream` 返回 `text/event-stream`，包含 sources/token/done 三类事件
- [ ] Streaming 端点支持多轮对话（传入 session_id）
- [ ] Streaming 完成后 conversation turns 正确保存
- [ ] 现有测试 `test_retrieval_pipeline.py` 通过
- [ ] 新增 messages[] 构造的单元测试
- [ ] 新增 streaming 端点的基本集成测试

## Definition of Done

- Tests added/updated (unit/integration where appropriate)
- Lint / typecheck / CI green
- Docs/notes updated if behavior changes

## Out of Scope (explicit)

- 前端 Dashboard 的 streaming UI 适配
- 对话摘要压缩（Phase 3）
- 对话感知检索（Phase 2：用前轮实体 boost 检索）
- 统一 Token budget 管理（Phase 2）
- 会话标题自动生成

## Technical Approach

### Messages[] 构造（核心变更）

`_generate_answer()` 新增参数 `conversation_turns: Optional[List[ConversationTurn]]`，替代现有 `conversation_history: Optional[str]`。新增 `_build_messages()` 方法：

```
messages = [{"role": "system", "content": system_prompt}]
if conversation_turns:
    for turn in conversation_turns:
        messages.append({"role": turn.role, "content": turn.content})
messages.append({"role": "user", "content": user_prompt_with_context})
```

`run()` 方法中，将 `conversation_history`（flat text）替换为 `conversation_turns`（structured turns），通过 `get_recent_turns()` 获取。`conversation_history` flat text 仍传给 `_expand_query()`（query expander 的 prompt 格式不同，不需要 messages[]）。

### Streaming 实现

`RetrievalPipeline` 新增 `run_stream()` 方法，复用 `run()` 的 Stage 1-5 逻辑，Stage 6 改为：
1. yield `{"type": "sources", ...}` 事件（检索结果）
2. 调用 `litellm.completion(stream=True)`，逐 chunk yield `{"type": "token", ...}`
3. 收集完整回答，保存 conversation turns
4. yield `{"type": "done", ...}` 事件

Web 层 `search.py` 新增 `POST /rag/chat/stream`，包装 `run_stream()` 为 `StreamingResponse`。

## Implementation Plan

1. **PR1: messages[] 改造**（`retrieval_pipeline.py`, `prompt_templates.py`, tests）
   - 新增 `_build_messages()` 方法
   - 修改 `_generate_answer()` 签名和内部逻辑
   - 修改 `run()` 传递 conversation_turns 而非 flat text
   - 模板渲染时 `conversation_history` 传空
   - 更新现有测试 + 新增 messages 构造测试

2. **PR2: streaming 端点**（`retrieval_pipeline.py`, `search.py`, tests）
   - 新增 `run_stream()` generator 方法
   - 新增 `/rag/chat/stream` 端点
   - 新增 streaming 集成测试

## Technical Notes

### 关键文件
- `kb/query/retrieval_pipeline.py` — `_generate_answer()` + 新增 `_build_messages()` 和 `run_stream()`
- `kb/query/conversation.py` — `get_recent_turns()` 已可用，无需改动
- `kb/query/prompt_templates.py` — 渲染时 `conversation_history` 传空
- `kb/web/routes/search.py` — 新增 streaming 端点
- `kb/query/models.py` — 无需改动
- `tests/test_retrieval_pipeline.py` — 需更新测试
