"""
知识挖掘控制台单元测试 + 集成测试

Tests for:
- MiningRunner: JSONL history append/read/rotation, run state tracking
- _estimate_remaining: remaining time calculation
- get_run_state: thread-safe state access
- run_mining: pipeline orchestration, partial/completed/failed status, history writing
- API: POST /api/mining/run validation, GET /api/mining/status, GET /api/mining/history
"""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

import kb.processors.mining_runner as runner_module
from kb.processors.mining_runner import (
    _estimate_remaining,
    get_run_state,
    read_history,
    run_mining,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_INITIAL_STATE = {
    "running": False,
    "run_id": None,
    "mode": None,
    "workers": 3,
    "started_at": None,
    "steps": [],
    "current_step": None,
    "error": None,
}


@pytest.fixture(autouse=True)
def reset_run_state():
    """Reset module-level _run_state before and after each test."""
    runner_module._run_state.update(_INITIAL_STATE)
    runner_module._run_state["steps"] = []
    runner_module._run_state.pop("_start_time", None)
    yield
    runner_module._run_state.update(_INITIAL_STATE)
    runner_module._run_state["steps"] = []
    runner_module._run_state.pop("_start_time", None)


@pytest.fixture
def history_file(tmp_path, monkeypatch):
    """Redirect JSONL history writes/reads to a temp file."""
    history_path = tmp_path / "mining-history.jsonl"
    monkeypatch.setattr(runner_module, "_get_history_path", lambda: history_path)
    return history_path


def _make_mock_storage(documents=None):
    """Return a mock SQLiteStorage whose cursor yields the given document rows."""
    storage = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = documents or []
    storage.conn.cursor.return_value = cursor
    return storage


def _step_result(step, status="completed"):
    """Build a minimal step result dict as returned by _run_* helpers."""
    result = {
        "step": step,
        "status": status,
        "processed": 1,
        "failed": 0,
        "duration_seconds": 0,
    }
    if step == "topics":
        result.update({"clusters": 1, "classified": 1, "noise": 0})
    return result


# ---------------------------------------------------------------------------
# TestMiningRunnerHistory
# ---------------------------------------------------------------------------


class TestMiningRunnerHistory:
    def test_read_history_returns_empty_when_file_absent(self, history_file):
        assert read_history(limit=10) == []

    def test_append_and_read_roundtrip(self, history_file):
        record = {"run_id": "abc123", "mode": "incremental", "status": "completed"}
        runner_module._append_history(record)
        records = read_history(limit=10)
        assert len(records) == 1
        assert records[0]["run_id"] == "abc123"

    def test_read_history_returns_most_recent_n(self, history_file):
        for i in range(5):
            runner_module._append_history({"run_id": f"run{i}", "status": "completed"})
        records = read_history(limit=3)
        assert len(records) == 3
        assert records[0]["run_id"] == "run2"
        assert records[2]["run_id"] == "run4"

    def test_read_history_skips_invalid_json_lines(self, history_file):
        history_file.write_text('{"run_id": "r1"}\nnot-valid-json\n{"run_id": "r2"}\n')
        records = read_history(limit=10)
        assert len(records) == 2
        assert records[0]["run_id"] == "r1"
        assert records[1]["run_id"] == "r2"

    def test_append_rotates_file_when_over_5mb(self, history_file, tmp_path):
        history_file.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
        runner_module._append_history({"run_id": "after_rotation"})
        jsonl_files = list(tmp_path.glob("*.jsonl"))
        assert len(jsonl_files) == 2  # rotated file + new file
        assert '"after_rotation"' in history_file.read_text()


# ---------------------------------------------------------------------------
# TestEstimateRemaining
# ---------------------------------------------------------------------------


class TestEstimateRemaining:
    def test_returns_none_when_no_documents_processed(self):
        steps = [{"step": "entities", "status": "running", "processed": 0, "total": 32}]
        assert _estimate_remaining(steps, elapsed=10.0) is None

    def test_returns_none_when_elapsed_is_zero(self):
        steps = [{"step": "entities", "status": "running", "processed": 16, "total": 32}]
        assert _estimate_remaining(steps, elapsed=0.0) is None

    def test_returns_non_negative_int_during_progress(self):
        steps = [{"step": "entities", "status": "running", "processed": 16, "total": 32}]
        result = _estimate_remaining(steps, elapsed=10.0)
        assert isinstance(result, int)
        assert result >= 0

    def test_completed_steps_count_toward_total_processed(self):
        steps = [
            {"step": "entities", "status": "completed", "processed": 32, "total": 32},
            {"step": "embeddings", "status": "running", "processed": 0, "total": 32},
        ]
        result = _estimate_remaining(steps, elapsed=20.0)
        assert isinstance(result, int)
        assert result >= 0


# ---------------------------------------------------------------------------
# TestGetRunState
# ---------------------------------------------------------------------------


class TestGetRunState:
    def test_idle_state_has_zero_elapsed_and_null_remaining(self):
        state = get_run_state()
        assert state["running"] is False
        assert state["elapsed_seconds"] == 0
        assert state["estimated_remaining_seconds"] is None

    def test_internal_start_time_not_exposed(self):
        runner_module._run_state["_start_time"] = time.time()
        state = get_run_state()
        assert "_start_time" not in state

    def test_running_state_includes_elapsed_seconds(self):
        runner_module._run_state["running"] = True
        runner_module._run_state["started_at"] = "2026-04-09T22:00:00+00:00"
        runner_module._run_state["_start_time"] = time.time() - 5.0
        state = get_run_state()
        assert state["elapsed_seconds"] >= 5


# ---------------------------------------------------------------------------
# TestRunMining
# ---------------------------------------------------------------------------


class TestRunMining:
    def test_no_documents_returns_completed_with_message(self, history_file):
        with patch("kb.config.Config"), \
             patch("kb.commands.utils._get_sqlite_storage",
                   return_value=_make_mock_storage(documents=[])):
            result = run_mining(mode="incremental")
        assert result["status"] == "completed"
        assert "No documents" in result.get("message", "")

    def test_completed_run_writes_jsonl_history_record(self, history_file):
        doc = ("doc1", "Title", "Summary", "file")
        with patch("kb.config.Config"), \
             patch("kb.commands.utils._get_sqlite_storage",
                   return_value=_make_mock_storage(documents=[doc])), \
             patch.object(runner_module, "_run_entities",
                          return_value=_step_result("entities")), \
             patch.object(runner_module, "_run_embeddings",
                          return_value=_step_result("embeddings")), \
             patch.object(runner_module, "_run_relations",
                          return_value=_step_result("relations")), \
             patch.object(runner_module, "_run_topics",
                          return_value=_step_result("topics")), \
             patch.object(runner_module, "_run_wiki",
                          return_value=_step_result("wiki")):
            result = run_mining(mode="incremental", triggered_by="web")

        assert result["status"] == "completed"
        records = read_history(limit=1)
        assert len(records) == 1
        assert records[0]["run_id"] == result["run_id"]
        assert records[0]["mode"] == "incremental"
        assert records[0]["triggered_by"] == "web"
        assert records[0]["status"] == "completed"

    def test_failed_step_yields_partial_overall_status(self, history_file):
        doc = ("doc1", "Title", "Summary", "file")
        with patch("kb.config.Config"), \
             patch("kb.commands.utils._get_sqlite_storage",
                   return_value=_make_mock_storage(documents=[doc])), \
             patch.object(runner_module, "_run_entities",
                          return_value=_step_result("entities", status="failed")), \
             patch.object(runner_module, "_run_embeddings",
                          return_value=_step_result("embeddings")), \
             patch.object(runner_module, "_run_relations",
                          return_value=_step_result("relations")), \
             patch.object(runner_module, "_run_topics",
                          return_value=_step_result("topics")):
            result = run_mining(mode="incremental")

        assert result["status"] == "partial"
        records = read_history(limit=1)
        assert records[0]["status"] == "partial"

    def test_all_entity_extractions_failing_sets_step_status_failed(self, history_file):
        """When 100% of entity extractions fail, step status must be 'failed' not 'completed'."""
        doc = ("doc1", "Title", "Summary", "file")
        storage = _make_mock_storage(documents=[doc])

        # Simulate extractor.extract() raising for every document
        with patch("kb.config.Config"), \
             patch("kb.commands.utils._get_sqlite_storage", return_value=storage), \
             patch("kb.processors.entity_extractor.EntityExtractor.from_config") as mock_extractor_cls:
            mock_extractor = mock_extractor_cls.return_value
            mock_extractor.extract.side_effect = ValueError("LLM not configured")
            # Also patch embeddings/relations/topics to avoid real execution
            with patch.object(runner_module, "_run_embeddings",
                               return_value=_step_result("embeddings")), \
                 patch.object(runner_module, "_run_relations",
                               return_value=_step_result("relations")), \
                 patch.object(runner_module, "_run_topics",
                               return_value=_step_result("topics")):
                result = run_mining(mode="incremental")

        # Overall should be partial (entities failed, others succeeded)
        assert result["status"] == "partial"
        # entities step in history should record the error
        records = read_history(limit=1)
        entity_step = next(s for s in records[0]["steps"] if s["step"] == "entities")
        assert entity_step["status"] == "failed"
        assert entity_step["error"] is not None
        assert "LLM not configured" in entity_step["error"]

    def test_steps_filter_skips_unspecified_steps(self, history_file):
        called = []
        doc = ("doc1", "Title", "Summary", "file")

        def fake_topics(config):
            called.append("topics")
            return _step_result("topics")

        with patch("kb.config.Config"), \
             patch("kb.commands.utils._get_sqlite_storage",
                   return_value=_make_mock_storage(documents=[doc])), \
             patch.object(runner_module, "_run_topics", side_effect=fake_topics):
            run_mining(mode="incremental", steps=["topics"])

        assert called == ["topics"]

    def test_run_state_not_running_after_completion(self, history_file):
        with patch("kb.config.Config"), \
             patch("kb.commands.utils._get_sqlite_storage",
                   return_value=_make_mock_storage(documents=[])):
            run_mining(mode="incremental")
        assert runner_module._run_state["running"] is False

    def test_run_id_is_8_char_hex(self, history_file):
        doc = ("doc1", "Title", "Summary", "file")
        with patch("kb.config.Config"), \
             patch("kb.commands.utils._get_sqlite_storage",
                   return_value=_make_mock_storage(documents=[doc])), \
             patch.object(runner_module, "_run_entities",
                          return_value=_step_result("entities")), \
             patch.object(runner_module, "_run_embeddings",
                          return_value=_step_result("embeddings")), \
             patch.object(runner_module, "_run_relations",
                          return_value=_step_result("relations")), \
             patch.object(runner_module, "_run_topics",
                          return_value=_step_result("topics")):
            result = run_mining(mode="full")

        assert len(result["run_id"]) == 8
        assert result["run_id"].isalnum()


# ---------------------------------------------------------------------------
# TestMiningAPIValidation
# ---------------------------------------------------------------------------


class TestMiningAPIValidation:
    def _make_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from kb.web.routes.mining import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        return TestClient(app)

    def test_invalid_mode_returns_400(self):
        client = self._make_client()
        resp = client.post("/api/mining/run", json={"mode": "rebuild"})
        assert resp.status_code == 400
        assert "mode" in resp.json()["detail"]

    def test_full_mode_without_confirm_returns_422(self):
        client = self._make_client()
        resp = client.post("/api/mining/run", json={"mode": "full", "confirm": False})
        assert resp.status_code == 422

    def test_full_mode_with_confirm_true_not_rejected(self):
        client = self._make_client()
        fake_state = {
            "run_id": "a1b2c3d4", "running": True, "mode": "full",
            "workers": 3, "steps": [], "started_at": None,
            "current_step": None, "error": None,
            "elapsed_seconds": 0, "estimated_remaining_seconds": None,
        }
        with patch("kb.processors.mining_runner.is_running", return_value=False), \
             patch("kb.processors.mining_runner.run_mining", return_value={}), \
             patch("kb.processors.mining_runner.get_run_state", return_value=fake_state):
            resp = client.post("/api/mining/run", json={"mode": "full", "confirm": True})
        assert resp.status_code not in (400, 422)

    def test_workers_below_1_returns_400(self):
        client = self._make_client()
        resp = client.post("/api/mining/run", json={"mode": "incremental", "workers": 0})
        assert resp.status_code == 400

    def test_workers_above_5_returns_400(self):
        client = self._make_client()
        resp = client.post("/api/mining/run", json={"mode": "incremental", "workers": 6})
        assert resp.status_code == 400

    def test_already_running_returns_409(self):
        client = self._make_client()
        with patch("kb.processors.mining_runner.is_running", return_value=True):
            resp = client.post("/api/mining/run", json={"mode": "incremental"})
        assert resp.status_code == 409

    def test_valid_incremental_returns_started_with_run_id(self):
        client = self._make_client()
        fake_state = {
            "run_id": "a1b2c3d4", "running": True, "mode": "incremental",
            "workers": 3, "steps": [], "started_at": "2026-04-09T22:00:00+00:00",
            "current_step": None, "error": None,
            "elapsed_seconds": 0, "estimated_remaining_seconds": None,
        }
        with patch("kb.processors.mining_runner.is_running", return_value=False), \
             patch("kb.processors.mining_runner.run_mining", return_value={}), \
             patch("kb.processors.mining_runner.get_run_state", return_value=fake_state):
            resp = client.post("/api/mining/run", json={"mode": "incremental"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["run_id"] == "a1b2c3d4"

    def test_history_limit_below_1_returns_400(self):
        client = self._make_client()
        assert client.get("/api/mining/history?limit=0").status_code == 400

    def test_history_limit_above_100_returns_400(self):
        client = self._make_client()
        assert client.get("/api/mining/history?limit=101").status_code == 400

    def test_history_valid_limit_returns_records_and_total(self):
        client = self._make_client()
        fake_records = [{"run_id": "r1", "mode": "incremental", "status": "completed"}]
        with patch("kb.processors.mining_runner.read_history", return_value=fake_records):
            resp = client.get("/api/mining/history?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert data["total"] == 1

    def test_status_endpoint_returns_state_dict(self):
        client = self._make_client()
        fake_state = {
            "running": False, "run_id": None, "mode": None, "workers": 3,
            "started_at": None, "steps": [], "current_step": None, "error": None,
            "elapsed_seconds": 0, "estimated_remaining_seconds": None,
        }
        with patch("kb.processors.mining_runner.get_run_state", return_value=fake_state):
            resp = client.get("/api/mining/status")
        assert resp.status_code == 200
        assert resp.json()["running"] is False
