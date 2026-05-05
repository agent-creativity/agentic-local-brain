"""
Unified mining pipeline runner with progress tracking and JSONL history logging.

Runs the four-stage mining pipeline (entities, embeddings, relations, topics)
with real-time progress updates and persistent history in JSONL format.

Used by both the Web API (/api/mining/run) and can be called from CLI.
"""

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Module-level run state for progress tracking (single-machine, single-process)
_run_state: Dict[str, Any] = {
    "running": False,
    "run_id": None,
    "mode": None,
    "workers": 3,
    "started_at": None,
    "steps": [],
    "current_step": None,
    "error": None,
}
_run_lock = threading.Lock()


def get_run_state() -> Dict[str, Any]:
    """Get current mining run state (thread-safe read)."""
    with _run_lock:
        state = dict(_run_state)
        state["steps"] = [dict(s) for s in _run_state["steps"]]
        if state["started_at"]:
            elapsed = time.time() - state["_start_time"]
            state["elapsed_seconds"] = int(elapsed)
            # Estimate remaining time based on current step progress
            state["estimated_remaining_seconds"] = _estimate_remaining(
                state["steps"], elapsed
            )
        else:
            state["elapsed_seconds"] = 0
            state["estimated_remaining_seconds"] = None
        # Remove internal fields
        state.pop("_start_time", None)
        return state


def is_running() -> bool:
    """Check if a mining run is in progress."""
    return _run_state["running"]


def _estimate_remaining(steps: List[Dict], elapsed: float) -> Optional[int]:
    """Estimate remaining seconds based on current progress."""
    total_processed = 0
    total_expected = 0
    for s in steps:
        if s["status"] == "completed":
            total_processed += s.get("total", s.get("processed", 0))
            total_expected += s.get("total", s.get("processed", 0))
        elif s["status"] == "running":
            total_processed += s.get("processed", 0)
            total_expected += s.get("total", 0)
        else:
            total_expected += s.get("total", 0)

    if total_processed <= 0 or total_expected <= 0:
        return None

    rate = total_processed / elapsed if elapsed > 0 else 0
    if rate <= 0:
        return None
    remaining = (total_expected - total_processed) / rate
    return max(0, int(remaining))


def _update_step(step_name: str, **kwargs) -> None:
    """Update a step's state (thread-safe)."""
    with _run_lock:
        for s in _run_state["steps"]:
            if s["step"] == step_name:
                s.update(kwargs)
                break


def _init_steps(step_names: List[str]) -> None:
    """Initialize step tracking."""
    _run_state["steps"] = [
        {"step": name, "status": "pending", "processed": 0, "total": 0, "failed": 0}
        for name in step_names
    ]


def _get_history_path() -> Path:
    """Get the JSONL history log file path."""
    from kb.config import Config

    config = Config()
    log_dir = config.get_log_dir()
    return log_dir / "mining-history.jsonl"


def _append_history(record: Dict[str, Any]) -> None:
    """Append a mining run record to the JSONL history file."""
    try:
        path = _get_history_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        # Rotate if file exceeds 5MB
        if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
            rotated = path.with_suffix(f".{datetime.now().strftime('%Y%m%d%H%M%S')}.jsonl")
            path.rename(rotated)

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        logger.error(f"[mining] Failed to write history: {e}")


def read_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Read recent mining history records from JSONL file."""
    path = _get_history_path()
    if not path.exists():
        return []

    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"[mining] Failed to read history: {e}")
        return []

    # Return most recent records
    return records[-limit:]


def run_mining(
    mode: str = "incremental",
    workers: int = 3,
    steps: Optional[List[str]] = None,
    skip_wiki: bool = False,
    triggered_by: str = "web",
) -> Dict[str, Any]:
    """
    Run the mining pipeline (blocking). Call from a background thread.

    Args:
        mode: 'incremental' or 'full'.
        workers: Number of concurrent workers for entity extraction (1-5).
        steps: List of steps to run. Default: all five steps.
        skip_wiki: If True, skip wiki compilation step.
        triggered_by: 'web', 'cli', or 'auto'.

    Returns:
        Dict with run results.
    """
    all_steps = ["entities", "embeddings", "relations", "topics", "wiki"]
    if steps is None:
        steps = all_steps
    else:
        steps = [s for s in steps if s in all_steps]
        if not steps:
            steps = all_steps

    # Apply skip_wiki filter
    if skip_wiki and "wiki" in steps:
        steps = [s for s in steps if s != "wiki"]

    workers = max(1, min(workers, 5))
    run_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(timezone.utc).isoformat()
    start_time = time.time()

    # Initialize run state
    with _run_lock:
        _run_state["running"] = True
        _run_state["run_id"] = run_id
        _run_state["mode"] = mode
        _run_state["workers"] = workers
        _run_state["started_at"] = started_at
        _run_state["current_step"] = None
        _run_state["error"] = None
        _run_state["_start_time"] = start_time
        _init_steps(steps)

    history_record = {
        "run_id": run_id,
        "mode": mode,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": None,
        "status": "running",
        "steps": [],
        "total_duration_seconds": 0,
        "error": None,
    }

    overall_status = "completed"

    try:
        from kb.config import Config
        from kb.commands.utils import _get_sqlite_storage

        config = Config()
        storage = _get_sqlite_storage()

        try:
            cursor = storage.conn.cursor()
            cursor.execute(
                "SELECT id, title, summary, content_type FROM knowledge ORDER BY collected_at DESC"
            )
            documents = cursor.fetchall()
            cursor.close()

            if not documents:
                logger.info("[mining] No documents found.")
                with _run_lock:
                    _run_state["running"] = False
                history_record["status"] = "completed"
                history_record["finished_at"] = datetime.now(timezone.utc).isoformat()
                _append_history(history_record)
                return {"run_id": run_id, "status": "completed", "message": "No documents"}

            total_docs = len(documents)

            # Update totals for all steps
            for step_name in steps:
                if step_name in ("topics", "wiki"):
                    _update_step(step_name, total=1)
                else:
                    _update_step(step_name, total=total_docs)

            # Step 1: Entity Extraction
            if "entities" in steps:
                step_result = _run_entities(config, storage, documents, workers, mode)
                history_record["steps"].append(step_result)
                if step_result["status"] == "failed" or step_result.get("failed", 0) > 0:
                    overall_status = "partial"

            # Step 2: Document Embeddings
            if "embeddings" in steps:
                step_result = _run_embeddings(config, mode)
                history_record["steps"].append(step_result)
                if step_result["status"] == "failed" or step_result.get("failed", 0) > 0:
                    overall_status = "partial"

            # Step 3: Cross-document Relations
            if "relations" in steps:
                step_result = _run_relations(config, storage, documents, mode)
                history_record["steps"].append(step_result)
                if step_result["status"] == "failed" or step_result.get("failed", 0) > 0:
                    overall_status = "partial"

            # Step 4: Topic Clustering
            if "topics" in steps:
                step_result = _run_topics(config)
                history_record["steps"].append(step_result)
                if step_result["status"] == "failed":
                    overall_status = "partial"

            # Step 5: Wiki Compilation
            if "wiki" in steps:
                step_result = _run_wiki(config)
                history_record["steps"].append(step_result)
                if step_result["status"] == "failed":
                    overall_status = "partial"

        finally:
            storage.close()

    except Exception as e:
        logger.error(f"[mining] Pipeline error: {e}")
        overall_status = "failed"
        history_record["error"] = str(e)
        with _run_lock:
            _run_state["error"] = str(e)

    # Finalize
    finished_at = datetime.now(timezone.utc).isoformat()
    total_duration = int(time.time() - start_time)

    history_record["status"] = overall_status
    history_record["finished_at"] = finished_at
    history_record["total_duration_seconds"] = total_duration

    _append_history(history_record)

    # Invalidate graph query cache since data has changed
    try:
        from kb.query.graph_query import invalidate_graph_cache
        invalidate_graph_cache()
    except Exception:
        pass

    # Invalidate pipeline result cache since underlying data has changed
    try:
        from kb.query.retrieval_pipeline import invalidate_pipeline_cache
        invalidate_pipeline_cache()
    except Exception:
        pass

    with _run_lock:
        _run_state["running"] = False
        _run_state["current_step"] = None

    logger.info(
        f"[mining] Pipeline {overall_status} in {total_duration}s (run_id={run_id})"
    )

    return {
        "run_id": run_id,
        "status": overall_status,
        "duration_seconds": total_duration,
        "steps": history_record["steps"],
    }


def _run_entities(config, storage, documents, workers, mode) -> Dict[str, Any]:
    """Run entity extraction step."""
    step_name = "entities"
    step_start = time.time()

    with _run_lock:
        _run_state["current_step"] = step_name
    _update_step(step_name, status="running", total=len(documents))

    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from pathlib import Path
        from kb.processors.entity_extractor import EntityExtractor

        extractor = EntityExtractor.from_config(config)

        # Pre-load document content
        doc_items = []
        for doc in documents:
            doc_id, title, summary = doc[0], doc[1], doc[2]
            content = summary or ""
            cursor = storage.conn.cursor()
            cursor.execute("SELECT file_path FROM knowledge WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            cursor.close()
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

        # Parallel LLM extraction
        actual_workers = max(1, min(workers, 5))
        extract_results = {}
        first_error: Optional[str] = None

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
                    if first_error is None:
                        first_error = str(e)
                _update_step(step_name, processed=done_count)

        # Sequential saves
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
                if first_error is None:
                    first_error = str(e)

        duration = int(time.time() - step_start)
        all_failed = success == 0 and len(doc_items) > 0
        step_status = "failed" if all_failed else "completed"
        _update_step(step_name, status=step_status, processed=len(documents), failed=failed)

        return {
            "step": step_name,
            "status": step_status,
            "processed": success,
            "failed": failed,
            "duration_seconds": duration,
            "error": first_error,
        }

    except Exception as e:
        duration = int(time.time() - step_start)
        _update_step(step_name, status="failed")
        logger.error(f"[mining] Entity extraction failed: {e}")
        return {
            "step": step_name,
            "status": "failed",
            "processed": 0,
            "failed": 0,
            "duration_seconds": duration,
            "error": str(e),
        }


def _run_embeddings(config, mode) -> Dict[str, Any]:
    """Run document embedding step."""
    step_name = "embeddings"
    step_start = time.time()

    with _run_lock:
        _run_state["current_step"] = step_name
    _update_step(step_name, status="running")

    try:
        from kb.processors.doc_embedding import DocEmbeddingService

        embedding_svc = DocEmbeddingService.from_config(config)

        if mode == "full":
            result = embedding_svc.generate_all()
        else:
            result = embedding_svc.generate_incremental()

        processed = result.get("processed", 0)
        failed = result.get("failed", 0)
        duration = int(time.time() - step_start)

        _update_step(
            step_name, status="completed", processed=processed, failed=failed,
            total=processed + result.get("skipped", 0) + failed
        )

        return {
            "step": step_name,
            "status": "completed",
            "processed": processed,
            "failed": failed,
            "duration_seconds": duration,
        }

    except Exception as e:
        duration = int(time.time() - step_start)
        _update_step(step_name, status="failed")
        logger.error(f"[mining] Embedding generation failed: {e}")
        return {
            "step": step_name,
            "status": "failed",
            "processed": 0,
            "failed": 0,
            "duration_seconds": duration,
            "error": str(e),
        }


def _run_relations(config, storage, documents, mode) -> Dict[str, Any]:
    """Run cross-document relation discovery step."""
    step_name = "relations"
    step_start = time.time()

    with _run_lock:
        _run_state["current_step"] = step_name
    _update_step(step_name, status="running", total=len(documents))

    try:
        from kb.processors.doc_relation_builder import DocRelationBuilder

        builder = DocRelationBuilder(storage=storage, config=config)

        if mode == "full":
            result = builder.rebuild_all_relations()
            _update_step(step_name, processed=len(documents))
        else:
            result = {"embedding_similarity": 0, "shared_entity": 0}
            for i, doc in enumerate(documents):
                counts = builder.build_relations_for_document(doc[0])
                result["embedding_similarity"] += counts["embedding_similarity"]
                result["shared_entity"] += counts["shared_entity"]
                _update_step(step_name, processed=i + 1)

        duration = int(time.time() - step_start)
        _update_step(step_name, status="completed", processed=len(documents))

        return {
            "step": step_name,
            "status": "completed",
            "processed": len(documents),
            "failed": 0,
            "duration_seconds": duration,
            "embedding_similarity": result["embedding_similarity"],
            "shared_entity": result["shared_entity"],
        }

    except Exception as e:
        duration = int(time.time() - step_start)
        _update_step(step_name, status="failed")
        logger.error(f"[mining] Relation building failed: {e}")
        return {
            "step": step_name,
            "status": "failed",
            "processed": 0,
            "failed": 0,
            "duration_seconds": duration,
            "error": str(e),
        }


def _run_topics(config) -> Dict[str, Any]:
    """Run topic clustering step."""
    step_name = "topics"
    step_start = time.time()

    with _run_lock:
        _run_state["current_step"] = step_name
    _update_step(step_name, status="running", total=1)

    try:
        from kb.processors.topic_clusterer import TopicClusterer

        clusterer = TopicClusterer.from_config(config)
        result = clusterer.cluster_all()

        duration = int(time.time() - step_start)
        _update_step(step_name, status="completed", processed=1)

        return {
            "step": step_name,
            "status": "completed",
            "clusters": result.get("clusters", 0),
            "classified": result.get("classified", 0),
            "noise": result.get("noise", 0),
            "duration_seconds": duration,
        }

    except Exception as e:
        duration = int(time.time() - step_start)
        _update_step(step_name, status="failed")
        logger.error(f"[mining] Topic clustering failed: {e}")
        return {
            "step": step_name,
            "status": "failed",
            "processed": 0,
            "failed": 0,
            "duration_seconds": duration,
            "error": str(e),
        }


def _run_wiki(config) -> Dict[str, Any]:
    """Run wiki compilation step."""
    step_name = "wiki"
    step_start = time.time()

    with _run_lock:
        _run_state["current_step"] = step_name
    _update_step(step_name, status="running", total=1)

    try:
        from kb.processors.wiki_compiler import WikiCompiler

        compiler = WikiCompiler.from_config(config)
        result = compiler.compile_all()

        duration = int(time.time() - step_start)
        _update_step(step_name, status="completed", processed=1)

        return {
            "step": step_name,
            "status": "completed",
            "compiled": result.get("compiled", 0),
            "skipped": result.get("skipped", 0),
            "entity_cards": result.get("entity_cards", 0),
            "errors": result.get("errors", 0),
            "duration_seconds": duration,
        }

    except Exception as e:
        duration = int(time.time() - step_start)
        _update_step(step_name, status="failed")
        logger.error(f"[mining] Wiki compilation failed: {e}")
        return {
            "step": step_name,
            "status": "failed",
            "processed": 0,
            "failed": 0,
            "duration_seconds": duration,
            "error": str(e),
        }




