# Multi-turn RAG Phase 2: Conversation-Aware Retrieval + Unified Token Budget

## Goal

提升多轮对话 RAG 的准确性和鲁棒性：(1) 利用前轮对话的实体和文档来增强当前轮的检索召回；(2) 统一管理 conversation messages[] 和 retrieval context 的 token 预算，防止长对话溢出模型上下文限制。

## What I already know

### Phase 1 现状（已实现）

- `retrieval_pipeline.py`: `_build_messages()` 构造 `[system, ...history turns, user(含context)]`
- `run()` 从 `get_recent_turns()` 加载结构化 turns（按 `history_turns_in_context: 5` 限制条数）
- `_turns_to_flat_text()` 将 turns 转为 flat text 给 query expander 做指代消解
- `run_stream()` SSE 流式生成

### 当前缺口

#### 检索层
- `_hybrid_retrieve()` 只用 expanded query 检索，不利用前轮提到的实体/文档 ID
- `query_expander` 提取了 entities，但这些 entities 只用于当前轮的查询扩展，不用于前轮 → 当前轮的传递
- 场景：用户先问"BERT 的架构"，再问"它的训练数据"。第二轮 expander 可能解析出"BERT"，但检索时不会优先匹配第一轮已返回的 BERT 相关文档

#### Token 预算层
- `HierarchicalContextBuilder` 管理检索 context 的预算（默认 4000 tokens），按 topics 2.5% / entities 5% / reserve 15% / 剩余给 sources 分配
- Conversation messages[] 完全在预算之外 — `_build_messages()` 把所有 turns 无限制塞进 messages
- 模型上下文窗口有限（如 qwen-plus 32K），长对话 + 大量检索 context 可能溢出
- token 估算用简单的 words * 1.3 启发式，无实际 tokenizer

### 约束

- LiteLLM 提供 `litellm.token_counter(model, messages)` 可做精确 token 计数
- 模型上下文窗口大小可从 `litellm.get_model_info(model)` 获取
- 现有 `ConversationTurn` 有 `sources` 字段（存了前轮检索到的文档 ID 和内容）

## Open Questions

(all resolved)

## Decision (ADR-lite)

### D1: 对话感知检索方式
**Context**: 需要利用前轮信息增强当前轮检索，有 entity 注入、document boost、两者结合三种方案
**Decision**: Document ID Boost — 从前轮 `ConversationTurn.sources` 提取文档 ID，在 RRF 融合后对匹配文档做 score boost
**Consequences**: 零额外 LLM 调用，复用已有数据，实现模式与 reading_history boost 一致。缺点是只能 boost 已被检索到的文档，不能召回全新文档。Entity 注入可在未来迭代中追加。

### D2: Token 预算策略
**Context**: conversation messages[] 和 retrieval context 各自独立管理 token，长对话可能溢出模型上下文
**Decision**: 动态计算 — `model_context_window - system_prompt - conversation_history - max_generation - safety_margin = retrieval_budget`
**Consequences**: 自适应对话长度，短对话时检索预算最大化，长对话时自动收缩。需要 token 估算函数（先用 heuristic，可选 litellm.token_counter）。

## Requirements

### R1: 对话感知检索 (Document ID Boost)
- 新增 `_extract_prior_source_ids()` 方法，从 conversation_turns 的 sources 字段提取文档 ID 集合
- 在 `_enrich_context()` 或单独的 boost 阶段，对出现在前轮 sources 中的 chunks 做 `final_score += 0.15`（boost 幅度可配置）
- Boost 后重新排序 chunks
- 单轮对话（无 turns/无 sources）时不做任何 boost

### R2: 统一 Token Budget
- 新增 `_estimate_tokens()` 工具方法（复用 context_builder 的 words * 1.3 heuristic）
- 新增 `_calculate_retrieval_budget()` 方法：
  - 默认模型上下文窗口：从配置读取或默认 32000（qwen-plus）
  - 计算 system_prompt tokens + conversation_turns tokens + max_generation tokens + safety_margin (500)
  - `retrieval_budget = model_context - 上述总和`
  - 下限保护：`max(retrieval_budget, 1000)`，确保至少有 1000 tokens 给检索
- 在 `run()` 和 `run_stream()` 中，Stage 5 `_build_context()` 的 budget 参数改为动态计算值（替代固定 config 值）
- 新增配置项 `query.rag.model_context_window`（可选，默认 32000）

### R3: 保持向后兼容
- 无 conversation_turns 时，retrieval_budget 等于配置的 context_budget（当前行为）
- Document ID Boost 只在有前轮 sources 时生效
- `context_builder.build()` 接口不变（已接受动态 budget 参数）

## Acceptance Criteria

- [ ] 多轮对话时，前轮 sources 中的文档在当前轮 reranked_chunks 中 score 被 boost
- [ ] 动态 token budget 正确计算：短对话时 budget 接近 config 值，长对话时自动缩减
- [ ] retrieval_budget 下限保护生效（≥ 1000 tokens）
- [ ] 单轮对话（无 session_id）行为不变
- [ ] `/rag/chat` 和 `/rag/chat/stream` 两个端点都使用新的 budget 逻辑
- [ ] 现有 32 个测试通过
- [ ] 新增 document ID boost 单元测试
- [ ] 新增 token budget 计算单元测试

## Definition of Done

- Tests added/updated (unit/integration where appropriate)
- Lint / typecheck / CI green

## Out of Scope (explicit)

- 对话摘要压缩（Phase 3）
- 前端适配
- 精确 tokenizer 集成（保持 heuristic，但可选 litellm.token_counter）

## Technical Approach

### Document ID Boost

在 `run()` 的 Stage 3 (Reranking) 和 Stage 4 (Context Enrichment) 之间，新增一个 conversation boost 步骤：

```
prior_source_ids = _extract_prior_source_ids(conversation_turns)
if prior_source_ids:
    for chunk in reranked_chunks:
        if chunk.source in prior_source_ids:
            chunk.final_score = min(1.0, chunk.final_score + CONVERSATION_BOOST)
    reranked_chunks.sort(key=lambda c: c.final_score, reverse=True)
```

`CONVERSATION_BOOST` 默认 0.15，可通过 `query.pipeline.conversation_boost` 配置。

### 动态 Token Budget

```
def _calculate_retrieval_budget(conversation_turns, system_prompt):
    model_window = config.get("query.rag.model_context_window", 32000)
    
    system_tokens = _estimate_tokens(system_prompt)
    conv_tokens = sum(_estimate_tokens(t.content) for t in conversation_turns)
    generation_reserve = self.max_tokens  # max_tokens for answer generation
    safety_margin = 500
    
    used = system_tokens + conv_tokens + generation_reserve + safety_margin
    retrieval_budget = max(model_window - used, 1000)
    return retrieval_budget
```

在 `run()`/`run_stream()` 中，Stage 5 `_build_context()` 的 budget 参数从固定 `self.context_budget` 改为 `min(self.context_budget, dynamic_budget)`。

## Implementation Plan

1. **Document ID Boost**（`retrieval_pipeline.py`）
   - 新增 `_extract_prior_source_ids()`
   - 新增 `_boost_conversation_sources()`
   - 在 `run()` 和 `run_stream()` 的 Stage 3-4 之间调用

2. **Token Budget**（`retrieval_pipeline.py`）
   - 新增 `_estimate_text_tokens()` (static)
   - 新增 `_calculate_retrieval_budget()`
   - 修改 `run()` 和 `run_stream()` 的 Stage 5 budget 参数

3. **测试**
   - `_extract_prior_source_ids()` 单元测试
   - `_boost_conversation_sources()` 单元测试
   - `_calculate_retrieval_budget()` 单元测试
   - 端到端多轮 boost 集成测试

## Technical Notes

### 关键文件
- `kb/query/retrieval_pipeline.py` — 核心：boost + budget 逻辑
- `kb/query/context_builder.py` — 无需改动（已接受动态 budget）
- `kb/query/models.py` — 无需改动
- `tests/test_retrieval_pipeline.py` — 新增测试
