"""
实体抽取器模块

基于 LLM 的实体和关系抽取，用于构建知识图谱。
在 processing pipeline 中与 TagExtractor 并行执行。

设计原则：
- extract() 负责 LLM 调用和解析，返回 Python 对象，可独立 mock 测试
- save() 负责写入 SQLite，可用 in-memory SQLite 测试
"""

import json
import logging
import re
import sqlite3
from typing import Any, Dict, List, Optional

from kb.config import Config
from kb.processors.base import BaseProcessor, ProcessResult
from kb.processors.tag_extractor import LLMProvider, LiteLLMProvider

logger = logging.getLogger(__name__)


class EntityExtractor(BaseProcessor):
    """
    实体和关系抽取处理器。

    从文档标题和内容中抽取实体（人物、概念、工具等）和实体间关系，
    写入 SQLite 构建知识图谱。
    """

    ENTITY_TYPES = {"person", "concept", "tool", "project", "organization"}
    RELATION_TYPES = {"uses", "belongs_to", "related_to", "depends_on", "created_by"}

    EXTRACTION_PROMPT = """You are a knowledge graph extraction assistant. Analyze the following document and extract entities and relationships.

Document title: {title}
Document content (truncated): {content}

Entity types allowed: person, concept, tool, project, organization
Relation types allowed: uses, belongs_to, related_to, depends_on, created_by

Requirements:
- Extract up to {max_entities} key entities
- Extract up to {max_relations} relationships between entities
- Each entity must have: name, type, description (1 sentence)
- Each relation must have: source entity name, target entity name, relation type, context (short quote from text)
- Use the same language as the document for names and descriptions
- Only use allowed entity types and relation types

Return ONLY a JSON object in this exact format, no other text:
{{"entities": [{{"name": "entity name", "type": "concept", "description": "brief description"}}], "relations": [{{"source": "entity A", "target": "entity B", "type": "related_to", "context": "brief context"}}]}}"""

    def __init__(
        self,
        provider: LLMProvider,
        db_path: Optional[str] = None,
        max_entities: int = 10,
        max_relations: int = 10,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.provider = provider
        self.db_path = db_path
        self.max_entities = max_entities
        self.max_relations = max_relations
        self.temperature = temperature

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "EntityExtractor":
        if config is None:
            config = Config()

        llm_config = config.get("llm", {})
        provider_name = llm_config.get("provider", "dashscope")
        model = llm_config.get("model", "qwen-plus")
        api_key = llm_config.get("api_key", "")

        if not api_key:
            raise ValueError("LLM API key is required in configuration")

        if provider_name == "litellm":
            provider = LiteLLMProvider(api_key=api_key, model=model)
        elif provider_name == "dashscope":
            litellm_model = model if "/" in model else f"dashscope/{model}"
            provider = LiteLLMProvider(api_key=api_key, model=litellm_model)
        elif provider_name == "openai_compatible":
            base_url = llm_config.get("base_url", "")
            if not base_url:
                raise ValueError("base_url is required for openai_compatible provider")
            litellm_model = model if "/" in model else f"openai/{model}"
            provider = LiteLLMProvider(
                api_key=api_key, model=litellm_model, api_base=base_url
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")

        mining_config = config.get("knowledge_mining", {})
        entity_config = mining_config.get("entity_extraction", {})

        from pathlib import Path

        data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
        db_path = str(data_dir / "db" / "metadata.db")

        return cls(
            provider=provider,
            db_path=db_path,
            max_entities=entity_config.get("max_entities_per_doc", 10),
            max_relations=entity_config.get("max_relations_per_doc", 10),
            temperature=entity_config.get("temperature", 0.1),
        )

    def extract(self, title: str, content: str) -> Dict[str, Any]:
        """
        LLM 抽取实体和关系。

        Args:
            title: 文档标题
            content: 文档内容

        Returns:
            {"entities": [...], "relations": [...]}
        """
        prompt = self.EXTRACTION_PROMPT.format(
            title=title[:500],
            content=content[:3000],
            max_entities=self.max_entities,
            max_relations=self.max_relations,
        )

        response = self.provider.generate(
            prompt=prompt, temperature=self.temperature, max_retries=3
        )

        return self._parse_response(response)

    def save(self, extracted: Dict[str, Any], knowledge_id: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, int]:
        """
        将抽取结果写入 SQLite。

        Args:
            extracted: extract() 的返回值
            knowledge_id: 关联的知识项 ID
            conn: SQLite 连接（可选，用于测试注入 in-memory DB）

        Returns:
            {"entities_saved": int, "relations_saved": int}
        """
        should_close = False
        if conn is None:
            if not self.db_path:
                raise ValueError("db_path is required for save()")
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            should_close = True

        try:
            entities = extracted.get("entities", [])
            relations = extracted.get("relations", [])

            entity_name_to_id = {}
            entities_saved = 0
            relations_saved = 0

            cursor = conn.cursor()

            for entity in entities:
                name = entity.get("name", "").strip()
                entity_type = entity.get("type", "").strip().lower()
                description = entity.get("description", "").strip()

                if not name or entity_type not in self.ENTITY_TYPES:
                    continue

                normalized_name = self._normalize_name(name)
                display_name = name

                # Upsert entity
                cursor.execute(
                    """INSERT INTO entities (name, display_name, type, description)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(name, type) DO UPDATE SET
                           mention_count = mention_count + 1,
                           updated_at = CURRENT_TIMESTAMP""",
                    (normalized_name, display_name, entity_type, description),
                )

                # Get entity ID
                cursor.execute(
                    "SELECT id FROM entities WHERE name = ? AND type = ?",
                    (normalized_name, entity_type),
                )
                row = cursor.fetchone()
                if row:
                    entity_id = row[0]
                    entity_name_to_id[normalized_name] = entity_id

                    # Add entity mention
                    cursor.execute(
                        """INSERT OR IGNORE INTO entity_mentions (entity_id, knowledge_id, context)
                           VALUES (?, ?, ?)""",
                        (entity_id, knowledge_id, description[:200]),
                    )
                    entities_saved += 1

            # Save relations
            for relation in relations:
                source_name = self._normalize_name(relation.get("source", ""))
                target_name = self._normalize_name(relation.get("target", ""))
                relation_type = relation.get("type", "").strip().lower()
                context = relation.get("context", "").strip()

                if relation_type not in self.RELATION_TYPES:
                    continue

                source_id = entity_name_to_id.get(source_name)
                target_id = entity_name_to_id.get(target_name)

                if not source_id or not target_id:
                    # Try to find entities by name across all types
                    if not source_id:
                        source_id = self._find_entity_id(cursor, source_name)
                    if not target_id:
                        target_id = self._find_entity_id(cursor, target_name)

                if not source_id or not target_id:
                    continue

                # Upsert relation
                cursor.execute(
                    """INSERT INTO entity_relations (source_entity_id, target_entity_id, relation_type)
                       VALUES (?, ?, ?)
                       ON CONFLICT(source_entity_id, target_entity_id, relation_type)
                       DO UPDATE SET weight = weight + 1""",
                    (source_id, target_id, relation_type),
                )

                # Get relation ID
                cursor.execute(
                    """SELECT id FROM entity_relations
                       WHERE source_entity_id = ? AND target_entity_id = ? AND relation_type = ?""",
                    (source_id, target_id, relation_type),
                )
                rel_row = cursor.fetchone()
                if rel_row:
                    relation_id = rel_row[0]

                    # Add relation source
                    cursor.execute(
                        """INSERT OR IGNORE INTO entity_relation_sources (relation_id, knowledge_id, context)
                           VALUES (?, ?, ?)""",
                        (relation_id, knowledge_id, context[:200]),
                    )
                    relations_saved += 1

            conn.commit()
            return {"entities_saved": entities_saved, "relations_saved": relations_saved}

        except Exception:
            conn.rollback()
            raise
        finally:
            if should_close:
                conn.close()

    def process(self, title: str, content: str, knowledge_id: str = None, conn: Optional[sqlite3.Connection] = None, **kwargs: Any) -> ProcessResult:
        """
        完整流程：extract -> save

        Args:
            title: 文档标题
            content: 文档内容
            knowledge_id: 知识项 ID（如果提供则同时保存）
            conn: SQLite 连接（可选）
        """
        if not title or not title.strip():
            return ProcessResult(success=False, error="Title cannot be empty")

        if not content or not content.strip():
            return ProcessResult(success=False, error="Content cannot be empty")

        try:
            extracted = self.extract(title, content)

            save_stats = None
            if knowledge_id is not None:
                save_stats = self.save(extracted, knowledge_id, conn=conn)

            return ProcessResult(
                success=True,
                data=extracted,
                metadata={
                    "entity_count": len(extracted.get("entities", [])),
                    "relation_count": len(extracted.get("relations", [])),
                    **(save_stats or {}),
                },
            )
        except Exception as e:
            return ProcessResult(success=False, error=str(e))

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into entities and relations."""
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM response as JSON")
                    return {"entities": [], "relations": []}
            else:
                logger.warning("No JSON found in LLM response")
                return {"entities": [], "relations": []}

        if not isinstance(data, dict):
            return {"entities": [], "relations": []}

        # Validate and filter entities
        entities = []
        for e in data.get("entities", [])[:self.max_entities]:
            if isinstance(e, dict) and e.get("name") and e.get("type"):
                entity_type = e["type"].strip().lower()
                if entity_type in self.ENTITY_TYPES:
                    entities.append({
                        "name": str(e["name"]).strip(),
                        "type": entity_type,
                        "description": str(e.get("description", "")).strip(),
                    })

        # Validate and filter relations
        relations = []
        entity_names = {self._normalize_name(e["name"]) for e in entities}
        for r in data.get("relations", [])[:self.max_relations]:
            if isinstance(r, dict) and r.get("source") and r.get("target") and r.get("type"):
                relation_type = r["type"].strip().lower()
                if relation_type in self.RELATION_TYPES:
                    source_norm = self._normalize_name(str(r["source"]))
                    target_norm = self._normalize_name(str(r["target"]))
                    if source_norm in entity_names and target_norm in entity_names:
                        relations.append({
                            "source": str(r["source"]).strip(),
                            "target": str(r["target"]).strip(),
                            "type": relation_type,
                            "context": str(r.get("context", "")).strip(),
                        })

        return {"entities": entities, "relations": relations}

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize entity name: lowercase, strip, collapse whitespace."""
        name = name.strip().lower()
        name = re.sub(r"\s+", " ", name)
        return name

    @staticmethod
    def _find_entity_id(cursor: sqlite3.Cursor, normalized_name: str) -> Optional[int]:
        """Find entity ID by normalized name (any type)."""
        cursor.execute("SELECT id FROM entities WHERE name = ? LIMIT 1", (normalized_name,))
        row = cursor.fetchone()
        return row[0] if row else None
