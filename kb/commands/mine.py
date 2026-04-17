"""
CLI Knowledge Mining Commands

Commands for running the knowledge mining pipeline:
entity extraction, embedding generation, relation discovery, topic clustering.
"""

import click

from kb.commands.utils import CONFIG_FILE, _get_sqlite_storage
from kb.config import Config


@click.group()
def mine() -> None:
    """Knowledge mining pipeline."""
    pass


@mine.command("run")
@click.option("--full", is_flag=True, help="Full rebuild (clear existing data first).")
@click.option("--skip-entities", is_flag=True, help="Skip entity extraction (slow, requires LLM).")
@click.option("--skip-embeddings", is_flag=True, help="Skip document embedding generation.")
@click.option("--skip-relations", is_flag=True, help="Skip cross-document relation building.")
@click.option("--skip-topics", is_flag=True, help="Skip topic clustering.")
@click.option("--skip-wiki", is_flag=True, help="Skip wiki compilation.")
@click.option("--workers", default=3, type=int, help="Number of concurrent workers for entity extraction (default: 3).")
def mine_run(full, skip_entities, skip_embeddings, skip_relations, skip_topics, skip_wiki, workers):
    """Run knowledge mining pipeline on all documents.

    Processes existing documents through the full mining pipeline:
    1. Entity extraction (LLM-based, builds knowledge graph)
    2. Document embedding generation (for similarity search)
    3. Cross-document relation discovery
    4. Topic clustering (HDBSCAN)
    5. Wiki compilation (LLM-based article synthesis)
    """
    config = Config(CONFIG_FILE)
    storage = _get_sqlite_storage()

    try:
        cursor = storage.conn.cursor()
        cursor.execute("SELECT id, title, summary, content_type FROM knowledge ORDER BY collected_at DESC")
        documents = cursor.fetchall()
        cursor.close()

        if not documents:
            click.echo("No documents found in knowledge base.")
            return

        click.echo(f"Found {len(documents)} documents to process.")
        click.echo("=" * 60)

        # Step 1: Entity Extraction (concurrent)
        if not skip_entities:
            actual_workers = max(1, min(workers, 10))
            click.echo(f"\n[1/5] Entity Extraction ({actual_workers} workers)...")
            try:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                from pathlib import Path
                from kb.processors.entity_extractor import EntityExtractor
                extractor = EntityExtractor.from_config(config)

                # Pre-load all document content in main thread (SQLite reads)
                doc_items = []
                for doc in documents:
                    doc_id, title, summary, content_type = doc[0], doc[1], doc[2], doc[3]
                    content = summary or ""
                    cursor2 = storage.conn.cursor()
                    cursor2.execute("SELECT file_path FROM knowledge WHERE id = ?", (doc_id,))
                    row = cursor2.fetchone()
                    cursor2.close()
                    if row and row[0]:
                        try:
                            fp = Path(row[0])
                            if fp.exists():
                                content = fp.read_text(encoding="utf-8")[:3000]
                        except Exception:
                            pass
                    if not content or not content.strip():
                        content = title or ""
                    doc_items.append((doc_id, title or "", content))

                # Phase 1: Parallel LLM extraction
                click.echo(f"  Extracting entities from {len(doc_items)} documents...")
                extract_results = {}

                def _extract_one(item):
                    did, t, c = item
                    return did, extractor.extract(t, c)

                with ThreadPoolExecutor(max_workers=actual_workers) as pool:
                    futures = {pool.submit(_extract_one, item): item[0] for item in doc_items}
                    done_count = 0
                    for future in as_completed(futures):
                        done_count += 1
                        doc_id = futures[future]
                        try:
                            did, extracted = future.result()
                            extract_results[did] = extracted
                        except Exception as e:
                            if done_count <= 3:
                                click.echo(f"  Warning: {doc_id[:8]}: {e}")
                        if done_count % 10 == 0:
                            click.echo(f"  Extract progress: {done_count}/{len(doc_items)}")

                # Phase 2: Sequential SQLite saves (single connection)
                success = 0
                failed = 0
                for doc_id, title, content in doc_items:
                    extracted = extract_results.get(doc_id)
                    if extracted is None:
                        failed += 1
                        continue
                    try:
                        extractor.save(extracted, doc_id, conn=storage.conn)
                        success += 1
                    except Exception as e:
                        failed += 1
                        if failed <= 3:
                            click.echo(f"  Save warning: {doc_id[:8]}: {e}")

                click.echo(f"  Done: {success} success, {failed} failed")
            except ValueError as e:
                click.echo(f"  Skipped: {e}", err=True)
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
        else:
            click.echo("\n[1/5] Entity Extraction... skipped")

        # Step 2: Document Embeddings
        if not skip_embeddings:
            click.echo("\n[2/5] Document Embedding Generation...")
            try:
                from kb.processors.doc_embedding import DocEmbeddingService
                embedding_svc = DocEmbeddingService.from_config(config)

                if full:
                    result = embedding_svc.generate_all()
                    click.echo(f"  Done: {result.get('processed', 0)} generated, {result.get('failed', 0)} failed")
                else:
                    result = embedding_svc.generate_incremental()
                    click.echo(f"  Done: {result.get('processed', 0)} generated, {result.get('skipped', 0)} skipped, {result.get('failed', 0)} failed")
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
        else:
            click.echo("\n[2/5] Document Embedding Generation... skipped")

        # Step 3: Cross-document Relations
        if not skip_relations:
            click.echo("\n[3/5] Cross-document Relation Discovery...")
            try:
                from kb.processors.doc_relation_builder import DocRelationBuilder
                builder = DocRelationBuilder(storage=storage, config=config)

                if full:
                    result = builder.rebuild_all_relations()
                else:
                    # Incremental: build for all documents
                    result = {"embedding_similarity": 0, "shared_entity": 0}
                    for i, doc in enumerate(documents):
                        counts = builder.build_relations_for_document(doc[0])
                        result["embedding_similarity"] += counts["embedding_similarity"]
                        result["shared_entity"] += counts["shared_entity"]
                        if (i + 1) % 50 == 0:
                            click.echo(f"  Progress: {i + 1}/{len(documents)}")

                click.echo(f"  Done: {result['embedding_similarity']} similarity, {result['shared_entity']} shared entity")
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
        else:
            click.echo("\n[3/5] Cross-document Relation Discovery... skipped")

        # Step 4: Topic Clustering
        if not skip_topics:
            click.echo("\n[4/5] Topic Clustering...")
            try:
                from kb.processors.topic_clusterer import TopicClusterer
                clusterer = TopicClusterer.from_config(config)
                result = clusterer.cluster_all()
                click.echo(f"  Done: {result['clusters']} clusters, {result['classified']} classified, {result['noise']} noise")
            except ImportError as e:
                click.echo(f"  Skipped: {e}", err=True)
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
        else:
            click.echo("\n[4/5] Topic Clustering... skipped")

        # Step 5: Wiki Compilation
        if not skip_wiki:
            click.echo("\n[5/5] Wiki Compilation...")
            try:
                from kb.processors.wiki_compiler import WikiCompiler
                compiler = WikiCompiler.from_config(config)
                result = compiler.compile_all()
                click.echo(f"  Done: {result.get('compiled', 0)} articles compiled, {result.get('skipped', 0)} skipped, {result.get('entity_cards', 0)} entity cards")
            except ValueError as e:
                click.echo(f"  Skipped: {e}", err=True)
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
        else:
            click.echo("\n[5/5] Wiki Compilation... skipped")

        click.echo("\n" + "=" * 60)
        click.echo("Knowledge mining pipeline complete!")
        click.echo("Run 'localbrain web' to view results in the browser.")

    finally:
        storage.close()


@mine.command("stats")
def mine_stats():
    """Show knowledge mining statistics."""
    storage = _get_sqlite_storage()
    try:
        cursor = storage.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM entities")
        entities = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entity_relations")
        relations = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entity_mentions")
        mentions = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM document_embeddings")
        embeddings = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM document_relations")
        doc_relations = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM topic_clusters")
        topics = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM knowledge_topics")
        classified = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM reading_history")
        history = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        total_docs = cursor.fetchone()[0]
        cursor.close()

        click.echo("Knowledge Mining Statistics")
        click.echo("=" * 40)
        click.echo(f"  Documents:           {total_docs}")
        click.echo(f"  Entities:            {entities}")
        click.echo(f"  Entity Relations:    {relations}")
        click.echo(f"  Entity Mentions:     {mentions}")
        click.echo(f"  Doc Embeddings:      {embeddings}")
        click.echo(f"  Doc Relations:       {doc_relations}")
        click.echo(f"  Topic Clusters:      {topics}")
        click.echo(f"  Classified Docs:     {classified}")
        click.echo(f"  Reading History:     {history}")
    finally:
        storage.close()
