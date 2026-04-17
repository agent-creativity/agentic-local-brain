"""
Wiki Compiler Module

Compiles topic clusters and entity graphs into wiki articles using LLM.
Generates standalone reference articles from source documents with proper
wiki-link syntax for entity references.
"""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb.config import Config
from kb.processors.tag_extractor import LLMProvider, LiteLLMProvider

logger = logging.getLogger(__name__)


class WikiCompiler:
    """
    Wiki article compiler.

    Synthesizes multiple source documents into coherent wiki articles
    using LLM. Supports topic articles and entity summary cards.
    """

    TOPIC_PROMPT_TEMPLATE = """You are a knowledge compiler. Your task is to synthesize multiple source documents into a single, coherent wiki article about: "{cluster_label}"

## Source Documents
{source_docs}

## Entities Found in These Documents
{entities}

## Instructions
1. Write a standalone reference article — not a list of document summaries
2. Organize into logical sections with clear headings
3. When sources provide complementary information, merge them naturally
4. When sources contradict, note both perspectives
5. Reference related entities using [[entity-slug]] wiki-link syntax
6. Write in the same language as the source documents
7. Target 1500-3000 words for substantial topics, 500-1000 for narrow ones

## Output Format
Return a JSON object:
{{
  "title": "Article Title",
  "sections": [
    {{"heading": "...", "content": "..."}},
    ...
  ],
  "entity_refs": ["entity-slug-1", "entity-slug-2"],
  "summary": "2-3 sentence abstract"
}}"""

    ENTITY_PROMPT_TEMPLATE = """You are a knowledge compiler. Create a concise summary card for the entity: "{entity_name}"

## Entity Information
- Name: {entity_name}
- Type: {entity_type}
- Description: {entity_description}

## Appears in Topics
{topic_titles}

## Context from Source Documents
{contexts}

## Instructions
1. Write a focused summary of this entity (200-500 words)
2. Explain what it is, why it matters, and key related concepts
3. Use [[wiki-link]] syntax for related entities mentioned
4. Write in the same language as the source documents

## Output Format
Return a JSON object:
{{
  "title": "Entity Display Name",
  "description": "Comprehensive entity description...",
  "topic_refs": ["topic-slug-1", "topic-slug-2"],
  "related_entities": ["related-entity-1", "related-entity-2"],
  "summary": "1-2 sentence summary"
}}"""

    SUBCATEGORY_PROMPT = """Given the following {doc_count} documents belonging to the topic "{topic_label}":

{doc_summaries}

Based on the documents' content, tags, and summaries, suggest 2-{max_subcategories} meaningful subcategories that organize these documents. Each document should be assigned to exactly one subcategory. The subcategory names should be concise and descriptive.

Return a JSON object with this exact format:
{{"categories": [{{"name": "Category Name", "description": "Brief one-sentence description", "doc_ids": ["id1", "id2"]}}]}}

Important:
- Every document ID must appear in exactly one category
- Category names should be concise (2-5 words)
- Return valid JSON only, no markdown formatting"""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        db_path: Optional[str] = None,
        wiki_dir: Optional[Path] = None,
        config_wiki: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the wiki compiler.

        Args:
            provider: LLM provider (LiteLLMProvider instance)
            db_path: Path to SQLite metadata.db
            wiki_dir: Path to wiki directory (~/.knowledge-base/2_process/wiki/)
            config_wiki: Dict of wiki config settings
        """
        self.provider = provider
        self.db_path = db_path
        self.wiki_dir = wiki_dir
        self.config_wiki = config_wiki or {}

        # Configuration settings
        self.temperature = self.config_wiki.get("temperature", 0.3)
        self.model = self.config_wiki.get("model")  # None means use default LLM
        self.max_source_tokens = self.config_wiki.get(
            "max_source_tokens_per_topic", 8000
        )
        self.entity_card_threshold = self.config_wiki.get("entity_card_threshold", 3)
        self.max_article_words = self.config_wiki.get("max_article_words", 3000)

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "WikiCompiler":
        """Factory method following TopicClusterer pattern."""
        if config is None:
            config = Config()

        # LLM provider setup (same as topic_clusterer)
        llm_config = config.get("llm", {})
        provider_name = llm_config.get("provider", "dashscope")
        model = llm_config.get("model", "qwen-plus")
        api_key = llm_config.get("api_key", "")

        provider = None
        if api_key:
            if provider_name == "litellm":
                provider = LiteLLMProvider(api_key=api_key, model=model)
            elif provider_name == "dashscope":
                litellm_model = model if "/" in model else f"dashscope/{model}"
                provider = LiteLLMProvider(api_key=api_key, model=litellm_model)
            elif provider_name == "openai_compatible":
                base_url = llm_config.get("base_url", "")
                litellm_model = model if "/" in model else f"openai/{model}"
                provider = LiteLLMProvider(
                    api_key=api_key, model=litellm_model, api_base=base_url
                )

        # Get paths
        data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
        db_path = str(data_dir / "db" / "metadata.db")
        wiki_dir = config.get_wiki_dir()

        # Wiki config
        config_wiki = config.get("wiki", {})

        return cls(
            provider=provider,
            db_path=db_path,
            wiki_dir=wiki_dir,
            config_wiki=config_wiki,
        )

    def compile_all(self, progress_callback=None, force: bool = False) -> dict:
        """
        Main entry: compile all stale topics into wiki articles.

        Three-phase process:
        1. Subcategory generation - Incremental LLM classification per topic
        2. Article compilation per category (only for changed/new categories)
        3. Entity card compilation

        Args:
            progress_callback: Optional callback function(msg: str) for progress updates
            force: If True, recompile all topics/categories from scratch

        Returns:
            {compiled: int, skipped: int, errors: int, entity_cards: int}
        """
        if not self.provider:
            raise ValueError("LLM provider is required for wiki compilation")

        if not self.db_path:
            raise ValueError("db_path is required")

        results = {"compiled": 0, "skipped": 0, "errors": 0, "entity_cards": 0}

        conn = self._get_connection()
        try:
            # Load all topic clusters from SQLite
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, label, description, document_count
                   FROM topic_clusters
                   ORDER BY document_count DESC"""
            )
            clusters = cursor.fetchall()
            cursor.close()

            if not clusters:
                logger.info("No topic clusters found for wiki compilation")
                return results

            # Import storage for category operations
            from kb.storage.sqlite_storage import SQLiteStorage

            storage = SQLiteStorage(self.db_path)

            # Track entity appearances across clusters
            entity_appearances: Dict[int, List[Dict]] = {}

            # =====================================================================
            # PHASE 1: Incremental Subcategory Generation
            # =====================================================================
            if progress_callback:
                progress_callback("Phase 1: Generating subcategories...")

            for cluster_row in clusters:
                cluster_id = cluster_row[0]
                cluster_label = cluster_row[1]
                topic_slug = self._slugify(cluster_label)

                try:
                    # Load source documents for this cluster
                    source_docs = self._load_source_docs(cluster_id, conn)

                    if not source_docs:
                        logger.warning(f"No source docs found for cluster {cluster_id}")
                        continue

                    # Get all doc_ids for this topic
                    all_doc_ids = {doc.get("id") for doc in source_docs if doc.get("id")}

                    if force:
                        # Force mode: delete all and regenerate from scratch
                        categories = self._generate_subcategories(
                            cluster_id=cluster_id,
                            cluster_label=cluster_label,
                            source_docs=source_docs,
                            conn=conn,
                        )

                        if not categories:
                            categories = [{
                                "name": "Overview",
                                "description": f"All documents related to {cluster_label}",
                                "doc_ids": list(all_doc_ids),
                            }]

                        # Delete old categories for this topic
                        storage.delete_wiki_categories_by_topic(cluster_id)

                        # Save new categories
                        for cat in categories:
                            cat_name = cat.get("name", "Untitled")
                            category_id = f"{topic_slug}--{self._slugify(cat_name)}"
                            storage.save_wiki_category(
                                category_id=category_id,
                                topic_id=cluster_id,
                                name=cat_name,
                                description=cat.get("description", ""),
                                doc_ids=cat.get("doc_ids", []),
                            )

                        if progress_callback:
                            progress_callback(f"Generated {len(categories)} subcategories for: {cluster_label}")

                    else:
                        # Incremental mode: preserve existing, classify only new docs
                        existing_categories = storage.list_wiki_categories(topic_id=cluster_id)

                        # Get all doc_ids already assigned to categories
                        assigned_doc_ids = set()
                        for cat in existing_categories:
                            assigned_doc_ids.update(cat.get("doc_ids", []))

                        # Find unassigned docs
                        unassigned_doc_ids = all_doc_ids - assigned_doc_ids

                        if not unassigned_doc_ids:
                            # No new docs, skip Phase 1 for this topic
                            logger.debug(f"No unassigned docs for {cluster_label}, skipping Phase 1")
                            continue

                        # Get new doc objects
                        new_docs = [doc for doc in source_docs if doc.get("id") in unassigned_doc_ids]

                        # Generate subcategories for new docs
                        incremental_categories = self._generate_incremental_subcategories(
                            cluster_id=cluster_id,
                            cluster_label=cluster_label,
                            new_docs=new_docs,
                            existing_categories=existing_categories,
                            conn=conn,
                        )

                        if not incremental_categories:
                            # Fallback: create "Other" category
                            incremental_categories = [{
                                "name": "Other",
                                "description": "Additional documents related to this topic",
                                "doc_ids": list(unassigned_doc_ids),
                                "is_new": True,
                            }]

                        # Merge incremental results with existing categories
                        for inc_cat in incremental_categories:
                            cat_name = inc_cat.get("name", "Untitled")
                            is_new = inc_cat.get("is_new", True)
                            new_doc_ids = inc_cat.get("doc_ids", [])

                            if is_new:
                                # Create new category
                                category_id = f"{topic_slug}--{self._slugify(cat_name)}"
                                storage.save_wiki_category(
                                    category_id=category_id,
                                    topic_id=cluster_id,
                                    name=cat_name,
                                    description=inc_cat.get("description", ""),
                                    doc_ids=new_doc_ids,
                                )
                            else:
                                # Update existing category - find by name and merge doc_ids
                                for existing_cat in existing_categories:
                                    if existing_cat.get("name") == cat_name:
                                        # Merge doc_ids
                                        merged_doc_ids = list(set(
                                            existing_cat.get("doc_ids", []) + new_doc_ids
                                        ))
                                        storage.save_wiki_category(
                                            category_id=existing_cat.get("category_id"),
                                            topic_id=cluster_id,
                                            name=cat_name,
                                            description=existing_cat.get("description", ""),
                                            doc_ids=merged_doc_ids,
                                        )
                                        break

                        if progress_callback:
                            progress_callback(
                                f"Classified {len(unassigned_doc_ids)} new docs for: {cluster_label}"
                            )

                except Exception as e:
                    logger.error(f"Failed to generate subcategories for {cluster_label}: {e}")
                    results["errors"] += 1
                    if progress_callback:
                        progress_callback(f"Error generating subcategories for {cluster_label}: {e}")
                    continue

            # =====================================================================
            # PHASE 2: Category-Level Article Compilation
            # =====================================================================
            if progress_callback:
                progress_callback("Phase 2: Compiling category articles...")

            for cluster_row in clusters:
                cluster_id = cluster_row[0]
                cluster_label = cluster_row[1]

                try:
                    # Load all source docs for this cluster (for entity tracking)
                    all_source_docs = self._load_source_docs(cluster_id, conn)

                    if not all_source_docs:
                        logger.warning(f"No source docs found for cluster {cluster_id}")
                        continue

                    # Load entities mentioned in these documents
                    entities = self._load_entities_for_cluster(cluster_id, conn)

                    # Track entity appearances for entity cards
                    for entity in entities:
                        entity_id = entity.get("id")
                        if entity_id:
                            if entity_id not in entity_appearances:
                                entity_appearances[entity_id] = {
                                    "entity": entity,
                                    "clusters": [],
                                }
                            entity_appearances[entity_id]["clusters"].append(
                                {"cluster_id": cluster_id, "cluster_label": cluster_label}
                            )

                    # Get categories for this topic
                    categories = storage.list_wiki_categories(topic_id=cluster_id)

                    if not categories:
                        # Fallback: compile as single article (no categories)
                        article_data = self.compile_topic(
                            cluster_id=cluster_id,
                            cluster_label=cluster_label,
                            source_docs=all_source_docs,
                            entities=entities,
                            conn=conn,
                        )
                        results["compiled"] += 1
                        if progress_callback:
                            progress_callback(f"Compiled: {article_data.get('title', cluster_label)}")
                    else:
                        # Determine which categories need compilation
                        categories_to_compile = self._get_categories_needing_compilation(
                            topic_id=cluster_id,
                            categories=categories,
                            conn=conn,
                            force=force,
                        )

                        # Track skipped categories
                        skipped_count = len(categories) - len(categories_to_compile)
                        if skipped_count > 0:
                            results["skipped"] += skipped_count

                        # Compile only categories that need it
                        for category in categories:
                            cat_name = category.get("name", "Unknown")

                            if category in categories_to_compile:
                                try:
                                    article_data = self.compile_topic(
                                        cluster_id=cluster_id,
                                        cluster_label=cluster_label,
                                        source_docs=all_source_docs,
                                        entities=entities,
                                        conn=conn,
                                        category_name=cat_name,
                                        category_doc_ids=category.get("doc_ids", []),
                                        category_id=category.get("category_id"),
                                    )
                                    results["compiled"] += 1
                                    if progress_callback:
                                        progress_callback(f"Compiled: {article_data.get('title', cat_name)}")
                                except Exception as e:
                                    logger.error(f"Failed to compile category {cat_name}: {e}")
                                    results["errors"] += 1
                                    if progress_callback:
                                        progress_callback(f"Error compiling {cat_name}: {e}")
                            else:
                                if progress_callback:
                                    progress_callback(f"Skipped (up-to-date): {cat_name}")

                except Exception as e:
                    logger.error(f"Failed to compile topic {cluster_label}: {e}")
                    results["errors"] += 1
                    if progress_callback:
                        progress_callback(f"Error compiling {cluster_label}: {e}")
                    continue

            storage.close()

            # =====================================================================
            # PHASE 3: Entity Card Compilation (unchanged)
            # =====================================================================
            if progress_callback:
                progress_callback("Phase 3: Compiling entity cards...")

            for entity_id, data in entity_appearances.items():
                if len(data["clusters"]) >= self.entity_card_threshold:
                    try:
                        self.compile_entity_card(
                            entity=data["entity"],
                            topic_appearances=data["clusters"],
                            conn=conn,
                        )
                        results["entity_cards"] += 1
                        if progress_callback:
                            progress_callback(
                                f"Compiled entity card: {data['entity'].get('display_name', data['entity'].get('name'))}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to compile entity card for {data['entity'].get('name')}: {e}"
                        )
                        results["errors"] += 1

            return results

        finally:
            conn.close()

    def compile_topic(
        self,
        cluster_id: int,
        cluster_label: str,
        source_docs: List[Dict],
        entities: List[Dict],
        conn: sqlite3.Connection,
        category_name: str = None,
        category_doc_ids: List[str] = None,
        category_id: str = None,
    ) -> dict:
        """
        Compile a single topic cluster or subcategory into one wiki article.

        Args:
            cluster_id: Topic cluster ID
            cluster_label: Human-readable cluster label
            source_docs: List of dicts with {id, title, content/summary}
            entities: List of entity dicts relevant to this cluster
            conn: SQLite connection
            category_name: Optional subcategory name (if compiling per-category)
            category_doc_ids: Optional list of doc IDs to include (if per-category)
            category_id: Optional category ID for database reference

        Returns:
            Article metadata dict
        """
        # Filter source docs if category_doc_ids is provided
        if category_doc_ids:
            filtered_docs = [doc for doc in source_docs if doc.get("id") in category_doc_ids]
            if not filtered_docs:
                # Fallback to all docs if filtering results in empty list
                filtered_docs = source_docs
        else:
            filtered_docs = source_docs

        # Build prompt with optional category context
        prompt = self._build_topic_prompt(
            cluster_label=cluster_label,
            source_docs=filtered_docs,
            entities=entities,
            category_name=category_name,
        )

        # Call LLM (model is handled by provider internally)
        response = self.provider.generate(
            prompt=prompt, temperature=self.temperature
        )

        # Parse JSON response
        article_data = self._parse_llm_response(response)

        # Generate slug from title
        title = article_data.get("title", category_name or cluster_label)
        slug = self._slugify(title)

        # Render Markdown
        source_doc_ids = [doc.get("id") for doc in filtered_docs if doc.get("id")]
        markdown = self._render_markdown(
            article_data=article_data,
            article_type="topic",
            cluster_id=f"cluster_{cluster_id:03d}",
            source_doc_ids=source_doc_ids,
            category_id=category_id,
        )

        # Write to file (nested path for categories)
        topic_slug = self._slugify(cluster_label)
        if category_name:
            file_path = self.wiki_dir / "topics" / topic_slug / f"{slug}.md"
        else:
            file_path = self.wiki_dir / "topics" / f"{topic_slug}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(markdown, encoding="utf-8")

        # Save to SQLite
        word_count = len(markdown.split())
        entity_refs = article_data.get("entity_refs", [])

        self._save_wiki_article(
            conn=conn,
            article_id=slug,
            article_type="topic",
            topic_id=f"cluster_{cluster_id:03d}",
            title=title,
            file_path=str(file_path),
            source_doc_ids=source_doc_ids,
            entity_refs=entity_refs,
            word_count=word_count,
            category_id=category_id,
        )

        return {
            "article_id": slug,
            "title": title,
            "file_path": str(file_path),
            "word_count": word_count,
            "entity_refs": entity_refs,
            "category_id": category_id,
        }

    def compile_entity_card(
        self,
        entity: Dict,
        topic_appearances: List[Dict],
        conn: sqlite3.Connection,
    ) -> dict:
        """
        Compile an entity summary card for high-frequency entities.

        Args:
            entity: Entity dict with {id, name, display_name, type, description}
            topic_appearances: List of {cluster_id, cluster_label} where entity appears
            conn: SQLite connection

        Returns:
            Article metadata dict
        """
        entity_name = entity.get("display_name") or entity.get("name", "")
        entity_type = entity.get("type", "unknown")
        entity_description = entity.get("description", "")

        # Build topic titles list
        topic_titles = "\n".join(
            f"- {ta.get('cluster_label', 'Unknown')}" for ta in topic_appearances
        )

        # Load contexts from documents mentioning this entity
        contexts = self._load_entity_contexts(entity.get("id"), conn)
        contexts_text = "\n\n".join(contexts[:5])  # Limit to 5 contexts

        # Build prompt
        prompt = self.ENTITY_PROMPT_TEMPLATE.format(
            entity_name=entity_name,
            entity_type=entity_type,
            entity_description=entity_description,
            topic_titles=topic_titles,
            contexts=contexts_text,
        )

        # Call LLM (model is handled by provider internally)
        response = self.provider.generate(
            prompt=prompt, temperature=self.temperature
        )

        # Parse JSON response
        card_data = self._parse_llm_response(response)

        # Generate slug
        title = card_data.get("title", entity_name)
        slug = self._slugify(title)

        # Render Markdown
        markdown = self._render_markdown(
            article_data=card_data,
            article_type="entity",
            cluster_id=f"entity_{entity.get('id', 'unknown'):03d}",
            source_doc_ids=[],
        )

        # Write to file
        file_path = self.wiki_dir / "entities" / f"{slug}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(markdown, encoding="utf-8")

        # Save to SQLite
        word_count = len(markdown.split())
        topic_refs = card_data.get("topic_refs", [])

        self._save_wiki_article(
            conn=conn,
            article_id=slug,
            article_type="entity",
            topic_id=f"entity_{entity.get('id', 'unknown'):03d}",
            title=title,
            file_path=str(file_path),
            source_doc_ids=[],
            entity_refs=card_data.get("related_entities", []),
            word_count=word_count,
        )

        return {
            "article_id": slug,
            "title": title,
            "file_path": str(file_path),
            "word_count": word_count,
            "topic_refs": topic_refs,
        }

    def _get_compiled_doc_ids_for_category(
        self, category_id: str, conn: sqlite3.Connection
    ) -> List[str]:
        """
        Get the source_doc_ids from the compiled article for a category.

        Args:
            category_id: The category ID to check
            conn: SQLite connection

        Returns:
            List of source document IDs that were compiled for this category.
            Empty list if no article exists.
        """
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT source_doc_ids FROM wiki_articles
                   WHERE category_id = ? AND article_type = 'topic'""",
                (category_id,),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0]) if row[0] else []
            return []
        finally:
            cursor.close()

    def _get_categories_needing_compilation(
        self,
        topic_id: int,
        categories: List[Dict],
        conn: sqlite3.Connection,
        force: bool = False,
    ) -> List[Dict]:
        """
        Determine which categories need compilation.

        A category needs compilation if:
        1. It has NO existing article at all (new category), OR
        2. It has new source documents that weren't part of the last compilation

        Args:
            topic_id: The topic cluster ID
            categories: List of category dicts with 'category_id' and 'doc_ids'
            conn: SQLite connection
            force: If True, return all categories (force recompilation)

        Returns:
            List of category dicts that need compilation
        """
        if force:
            return categories

        categories_needing_compilation = []
        for category in categories:
            category_id = category.get("category_id")
            current_doc_ids = set(category.get("doc_ids", []))

            # Get the compiled source doc IDs for this category
            compiled_doc_ids = set(self._get_compiled_doc_ids_for_category(category_id, conn))

            # Check if compilation needed
            if not compiled_doc_ids:
                # No existing article for this category
                categories_needing_compilation.append(category)
                logger.debug(f"Category {category_id} needs compilation: no existing article")
            elif current_doc_ids != compiled_doc_ids:
                # Doc IDs have changed (new docs added or removed)
                categories_needing_compilation.append(category)
                logger.debug(
                    f"Category {category_id} needs compilation: "
                    f"docs changed from {len(compiled_doc_ids)} to {len(current_doc_ids)}"
                )

        return categories_needing_compilation

    def _is_stale(self, topic_id: int, conn: sqlite3.Connection) -> bool:
        """
        Check if topic needs recompilation.

        DEPRECATED: Use _get_categories_needing_compilation() instead.
        Kept for backward compatibility with force=True mode.

        Returns True if no existing article found (needs compilation).
        """
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT compiled_at FROM wiki_articles
                   WHERE topic_id = ? AND article_type = 'topic'""",
                (f"cluster_{topic_id:03d}",),
            )
            row = cursor.fetchone()
            # If no existing article, it's stale (needs compilation)
            return row is None
        finally:
            cursor.close()

    def _build_topic_prompt(
        self,
        cluster_label: str,
        source_docs: List[Dict],
        entities: List[Dict],
        category_name: str = None,
    ) -> str:
        """Build LLM prompt for wiki article synthesis."""
        # Format source documents (truncate to fit token budget)
        docs_text = []
        current_tokens = 0

        for doc in source_docs:
            title = doc.get("title", "Untitled")
            content = doc.get("content", "") or doc.get("summary", "")

            # Truncate content (rough estimate: 1 token ≈ 4 chars)
            max_chars = self.max_source_tokens * 4 // len(source_docs) if source_docs else self.max_source_tokens * 4
            if len(content) > max_chars:
                content = content[:max_chars] + "..."

            doc_text = f"### {title}\n{content}"
            doc_tokens = len(doc_text) // 4

            if current_tokens + doc_tokens > self.max_source_tokens:
                break

            docs_text.append(doc_text)
            current_tokens += doc_tokens

        source_docs_str = "\n\n".join(docs_text)

        # Format entities
        entities_str = "\n".join(
            f"- {e.get('display_name') or e.get('name', 'Unknown')} "
            f"({e.get('type', 'unknown')}): {e.get('description', '')[:100]}"
            for e in entities[:20]  # Limit to 20 entities
        )

        # Build the topic label (include category context if provided)
        if category_name:
            topic_label = f"{category_name} (within {cluster_label})"
        else:
            topic_label = cluster_label

        return self.TOPIC_PROMPT_TEMPLATE.format(
            cluster_label=topic_label,
            source_docs=source_docs_str,
            entities=entities_str,
        )

    def _build_entity_prompt(
        self,
        entity: Dict,
        topic_titles: List[str],
        contexts: List[str],
    ) -> str:
        """Build LLM prompt for entity summary card."""
        # This is handled inline in compile_entity_card for simplicity
        pass

    def _slugify(self, title: str) -> str:
        """Convert title to URL-safe slug."""
        # Lowercase
        slug = title.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        # Collapse multiple hyphens
        slug = re.sub(r"-+", "-", slug)
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        return slug or "untitled"

    def _render_markdown(
        self,
        article_data: Dict,
        article_type: str,
        cluster_id: str,
        source_doc_ids: List[str],
        category_id: str = None,
    ) -> str:
        """Render LLM JSON output to Markdown with YAML front matter."""
        title = article_data.get("title", "Untitled")
        sections = article_data.get("sections", [])
        entity_refs = article_data.get("entity_refs", [])
        summary = article_data.get("summary", "")

        # YAML front matter
        front_matter = {
            "topic_id": cluster_id,
            "title": title,
            "article_type": article_type,
            "source_documents": source_doc_ids,
            "entity_refs": entity_refs,
            "compiled_at": datetime.now().isoformat(),
            "version": 1,
            "word_count": sum(len(s.get("content", "").split()) for s in sections),
        }

        # Add category_id if provided
        if category_id:
            front_matter["category_id"] = category_id

        yaml_lines = ["---"]
        for key, value in front_matter.items():
            if isinstance(value, list):
                yaml_lines.append(f"{key}:")
                for item in value:
                    yaml_lines.append(f"  - {item}")
            else:
                yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---")

        # Body content
        body_lines = []
        if summary:
            body_lines.append(f"> {summary}")
            body_lines.append("")

        for section in sections:
            heading = section.get("heading", "")
            content = section.get("content", "")
            if heading:
                body_lines.append(f"## {heading}")
                body_lines.append("")
            if content:
                body_lines.append(content)
                body_lines.append("")

        return "\n".join(yaml_lines + [""] + body_lines)

    def _parse_llm_response(self, response_text: str) -> dict:
        """Parse JSON from LLM response with error handling."""
        # Try direct JSON parsing first
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try to extract JSON from markdown code blocks
        try:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: return a basic structure
        logger.warning("Failed to parse LLM response as JSON, using fallback")
        return {
            "title": "Untitled Article",
            "sections": [{"heading": "Content", "content": response_text[:2000]}],
            "entity_refs": [],
            "summary": "",
        }

    def _get_connection(self) -> sqlite3.Connection:
        """Get a SQLite connection."""
        if not self.db_path:
            raise ValueError("db_path is required")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _get_default_model(self) -> str:
        """Get the default LLM model from config."""
        # This is handled by the provider, but we need to return something
        # The provider already has the model configured
        return self.provider.model if self.provider else "qwen-plus"

    def _load_source_docs(
        self, cluster_id: int, conn: sqlite3.Connection
    ) -> List[Dict]:
        """Load source documents for a cluster."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT k.id, k.title, k.summary, k.word_count
                   FROM knowledge_topics kt
                   JOIN knowledge k ON kt.knowledge_id = k.id
                   WHERE kt.cluster_id = ?
                   ORDER BY kt.confidence DESC""",
                (cluster_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "word_count": row[3],
                }
                for row in rows
            ]
        finally:
            cursor.close()

    def _load_entities_for_cluster(
        self, cluster_id: int, conn: sqlite3.Connection
    ) -> List[Dict]:
        """Load entities mentioned in documents of a cluster."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT DISTINCT e.id, e.name, e.display_name, e.type, e.description
                   FROM entities e
                   JOIN entity_mentions em ON e.id = em.entity_id
                   JOIN knowledge_topics kt ON em.knowledge_id = kt.knowledge_id
                   WHERE kt.cluster_id = ?""",
                (cluster_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "display_name": row[2],
                    "type": row[3],
                    "description": row[4],
                }
                for row in rows
            ]
        finally:
            cursor.close()

    def _load_entity_contexts(
        self, entity_id: int, conn: sqlite3.Connection
    ) -> List[str]:
        """Load context snippets for an entity."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT context FROM entity_mentions
                   WHERE entity_id = ?
                   LIMIT 10""",
                (entity_id,),
            )
            return [row[0] for row in cursor.fetchall() if row[0]]
        finally:
            cursor.close()

    def _save_wiki_article(
        self,
        conn: sqlite3.Connection,
        article_id: str,
        article_type: str,
        topic_id: str,
        title: str,
        file_path: str,
        source_doc_ids: List[str],
        entity_refs: List[str],
        word_count: int,
        category_id: str = None,
    ) -> bool:
        """Save wiki article metadata to SQLite."""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            source_doc_ids_json = json.dumps(source_doc_ids or [])
            entity_refs_json = json.dumps(entity_refs or [])

            cursor = conn.cursor()
            # Check if article exists (for version increment)
            cursor.execute(
                "SELECT version FROM wiki_articles WHERE article_id = ?",
                (article_id,),
            )
            existing = cursor.fetchone()
            version = (existing[0] + 1) if existing else 1

            # Check if category_id column exists (schema migration support)
            try:
                cursor.execute(
                    """INSERT OR REPLACE INTO wiki_articles
                       (article_id, article_type, topic_id, title, file_path,
                        source_doc_ids, entity_refs, compiled_at, version, word_count, category_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        article_id,
                        article_type,
                        topic_id,
                        title,
                        file_path,
                        source_doc_ids_json,
                        entity_refs_json,
                        now,
                        version,
                        word_count,
                        category_id,
                    ),
                )
            except sqlite3.OperationalError:
                # Fallback: category_id column might not exist yet
                cursor.execute(
                    """INSERT OR REPLACE INTO wiki_articles
                       (article_id, article_type, topic_id, title, file_path,
                        source_doc_ids, entity_refs, compiled_at, version, word_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        article_id,
                        article_type,
                        topic_id,
                        title,
                        file_path,
                        source_doc_ids_json,
                        entity_refs_json,
                        now,
                        version,
                        word_count,
                    ),
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save wiki article: {e}")
            return False

    def _load_tags_for_doc(self, doc_id: str, conn: sqlite3.Connection) -> List[str]:
        """Load tags for a specific document."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT t.name FROM tags t
                JOIN knowledge_tags kt ON t.id = kt.tag_id
                WHERE kt.knowledge_id = ?
                ORDER BY t.name
                """,
                (doc_id,),
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()

    def _generate_subcategories(
        self,
        cluster_id: int,
        cluster_label: str,
        source_docs: List[Dict],
        conn: sqlite3.Connection,
    ) -> List[Dict]:
        """
        Generate subcategories for a topic cluster using LLM.

        Args:
            cluster_id: Topic cluster ID
            cluster_label: Human-readable cluster label
            source_docs: List of dicts with {id, title, summary, content}
            conn: SQLite connection

        Returns:
            List of category dicts: [{"name": ..., "description": ..., "doc_ids": [...]}]
        """
        if not source_docs:
            return []

        # Get max_subcategories from config
        max_subcategories = self.config_wiki.get("max_subcategories", 5)

        # Build doc_summaries with tags for each doc
        doc_summaries = []
        for doc in source_docs:
            doc_id = doc.get("id", "")
            title = doc.get("title", "Untitled")
            summary = doc.get("content", "") or doc.get("summary", "")
            tags = self._load_tags_for_doc(doc_id, conn)
            tags_str = ", ".join(tags) if tags else "none"

            doc_text = f"Document ID: {doc_id}\nTitle: {title}\nTags: {tags_str}\nSummary: {summary[:300]}..."
            doc_summaries.append(doc_text)

        doc_summaries_str = "\n\n".join(doc_summaries)

        # Format prompt
        prompt = self.SUBCATEGORY_PROMPT.format(
            doc_count=len(source_docs),
            topic_label=cluster_label,
            doc_summaries=doc_summaries_str,
            max_subcategories=max_subcategories,
        )

        # Call LLM (NO model= parameter - handled by provider internally)
        response = self.provider.generate(prompt=prompt, temperature=self.temperature)

        # Parse JSON response
        try:
            data = self._parse_llm_response(response)
            categories = data.get("categories", [])
        except Exception as e:
            logger.error(f"Failed to parse subcategory response: {e}")
            categories = []

        # Validate and fix categories
        all_doc_ids = {doc.get("id") for doc in source_docs if doc.get("id")}
        assigned_doc_ids = set()

        # Track which docs are assigned
        for cat in categories:
            for doc_id in cat.get("doc_ids", []):
                assigned_doc_ids.add(doc_id)

        # Find unassigned docs
        unassigned = all_doc_ids - assigned_doc_ids

        # If there are unassigned docs, create a catch-all category
        if unassigned:
            categories.append({
                "name": "Other",
                "description": "Additional documents related to this topic",
                "doc_ids": list(unassigned),
            })

        # If LLM returns more categories than max, truncate and merge excess
        if len(categories) > max_subcategories:
            # Keep first (max-1) categories, merge remaining into last
            kept_categories = categories[: max_subcategories - 1]
            excess_categories = categories[max_subcategories - 1 :]

            # Collect all doc_ids from excess categories
            merged_doc_ids = []
            for cat in excess_categories:
                merged_doc_ids.extend(cat.get("doc_ids", []))

            # Add merged category
            kept_categories.append({
                "name": "Other",
                "description": "Additional documents related to this topic",
                "doc_ids": merged_doc_ids,
            })
            categories = kept_categories

        return categories

    INCREMENTAL_SUBCATEGORY_PROMPT = """Given the following {doc_count} NEW documents that need to be classified for the topic "{topic_label}":

Existing categories for this topic:
{existing_categories}

NEW documents to classify:
{doc_summaries}

Based on the documents' content, tags, and summaries, assign each new document to either:
1. One of the existing categories listed above, OR
2. A NEW category if none of the existing ones fit well

Return a JSON object with this exact format:
{{"categories": [{{"name": "Category Name", "description": "Brief description", "doc_ids": ["id1"], "is_new": false}}]}}

Important:
- Use the EXACT existing category name when assigning to existing categories
- Set "is_new" to false for existing categories, true for new ones
- Only create new categories when documents don't fit existing ones
- Every new document ID must appear in exactly one category
- Category names should be concise (2-5 words)
- Return valid JSON only, no markdown formatting"""

    def _generate_incremental_subcategories(
        self,
        cluster_id: int,
        cluster_label: str,
        new_docs: List[Dict],
        existing_categories: List[Dict],
        conn: sqlite3.Connection,
    ) -> List[Dict]:
        """
        Generate subcategories for new documents using LLM, preserving existing categories.

        This method is called when there are new/unassigned documents for a topic that
        already has existing categories. It asks the LLM to classify new docs into
        existing categories or propose new ones.

        Args:
            cluster_id: Topic cluster ID
            cluster_label: Human-readable cluster label
            new_docs: List of NEW dicts with {id, title, summary, content} to classify
            existing_categories: List of existing category dicts with {name, description, doc_ids}
            conn: SQLite connection

        Returns:
            List of category dicts that need to be created or updated:
            [{"name": ..., "description": ..., "doc_ids": [...], "is_new": bool}]
        """
        if not new_docs:
            return []

        max_subcategories = self.config_wiki.get("max_subcategories", 5)

        # Build existing categories info
        existing_cats_text = []
        for cat in existing_categories:
            cat_name = cat.get("name", "Unknown")
            cat_desc = cat.get("description", "")
            existing_cats_text.append(f"- {cat_name}: {cat_desc}")
        existing_categories_str = "\n".join(existing_cats_text) if existing_cats_text else "None (this is a new topic)"

        # Build new doc summaries
        doc_summaries = []
        for doc in new_docs:
            doc_id = doc.get("id", "")
            title = doc.get("title", "Untitled")
            summary = doc.get("content", "") or doc.get("summary", "")
            tags = self._load_tags_for_doc(doc_id, conn)
            tags_str = ", ".join(tags) if tags else "none"

            doc_text = f"Document ID: {doc_id}\nTitle: {title}\nTags: {tags_str}\nSummary: {summary[:300]}..."
            doc_summaries.append(doc_text)

        doc_summaries_str = "\n\n".join(doc_summaries)

        # Format prompt
        prompt = self.INCREMENTAL_SUBCATEGORY_PROMPT.format(
            doc_count=len(new_docs),
            topic_label=cluster_label,
            existing_categories=existing_categories_str,
            doc_summaries=doc_summaries_str,
        )

        # Call LLM
        response = self.provider.generate(prompt=prompt, temperature=self.temperature)

        # Parse JSON response
        try:
            data = self._parse_llm_response(response)
            categories = data.get("categories", [])
        except Exception as e:
            logger.error(f"Failed to parse incremental subcategory response: {e}")
            # Fallback: create an "Other" category for all new docs
            return [{
                "name": "Other",
                "description": "Additional documents related to this topic",
                "doc_ids": [doc.get("id") for doc in new_docs if doc.get("id")],
                "is_new": True,
            }]

        # Validate - ensure all new docs are assigned
        all_new_doc_ids = {doc.get("id") for doc in new_docs if doc.get("id")}
        assigned_doc_ids = set()

        for cat in categories:
            for doc_id in cat.get("doc_ids", []):
                assigned_doc_ids.add(doc_id)

        # Find unassigned docs
        unassigned = all_new_doc_ids - assigned_doc_ids

        if unassigned:
            categories.append({
                "name": "Other",
                "description": "Additional documents related to this topic",
                "doc_ids": list(unassigned),
                "is_new": True,
            })

        # Filter to only include docs that are actually new (LLM might hallucinate)
        for cat in categories:
            cat["doc_ids"] = [doc_id for doc_id in cat.get("doc_ids", []) if doc_id in all_new_doc_ids]

        return categories
