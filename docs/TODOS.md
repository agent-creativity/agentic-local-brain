# TODOS

## P2: ChromaDB ANN index for doc-level similarity
- **What:** Store document-level embeddings in a ChromaDB collection, use ANN index for similarity queries
- **Why:** Current brute-force O(n) approach in `DocRelationBuilder.find_similar_documents()` (line 126-156) loads all embeddings into memory. Won't scale past ~2000 items. Full rebuild of 5000 items would take ~14 hours.
- **Effort:** M (human: ~1wk / CC: ~20min)
- **Depends on:** Embedding serialization fix (JSON standardization)
- **Added:** 2026-04-05 by /plan-eng-review

## P3: DRY up LLM provider construction
- **What:** Extract `create_llm_provider(config) -> LLMProvider` helper from 4 duplicate 15-line blocks
- **Why:** EntityExtractor, TopicClusterer, RecommendationEngine, TagExtractor all copy-paste identical LLM provider setup. Adding a new provider means updating 4 files.
- **Files:** `kb/processors/entity_extractor.py:72-98`, `kb/processors/topic_clusterer.py:69-93`, `kb/processors/recommendation.py` (similar block), `kb/processors/tag_extractor.py`
- **Effort:** S (human: ~2hrs / CC: ~5min)
- **Depends on:** Nothing
- **Added:** 2026-04-05 by /plan-eng-review
