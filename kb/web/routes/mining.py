"""
Mining routes for Knowledge Base Web API.

Provides endpoints to trigger mining runs, check progress,
and query mining history from JSONL logs.
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class MiningRunRequest(BaseModel):
    mode: str = "incremental"
    workers: int = 3
    steps: Optional[List[str]] = None
    confirm: bool = False


@router.post("/mining/run")
async def start_mining_run(request: MiningRunRequest) -> Dict[str, Any]:
    """
    Trigger a mining pipeline run.

    Args:
        mode: 'incremental' or 'full'.
        workers: Concurrent workers for entity extraction (1-5, default 3).
        steps: Subset of steps to run (default: all four).
        confirm: Must be true for full mode (safety gate).

    Returns:
        Dict with run_id and status.
    """
    from kb.processors.mining_runner import is_running, run_mining

    if request.mode not in ("incremental", "full"):
        raise HTTPException(status_code=400, detail="mode must be 'incremental' or 'full'")

    if request.mode == "full" and not request.confirm:
        raise HTTPException(
            status_code=422,
            detail="Full rebuild requires confirm=true. This will clear and rebuild all mining data.",
        )

    if request.workers < 1 or request.workers > 5:
        raise HTTPException(status_code=400, detail="workers must be between 1 and 5")

    if is_running():
        raise HTTPException(
            status_code=409,
            detail="A mining run is already in progress.",
        )

    # Run in background thread (non-blocking)
    loop = asyncio.get_running_loop()
    loop.run_in_executor(
        None,
        lambda: run_mining(
            mode=request.mode,
            workers=request.workers,
            steps=request.steps,
            triggered_by="web",
        ),
    )

    # Return immediately — client polls /api/mining/status
    # Small delay to let the runner initialize state
    await asyncio.sleep(0.2)

    from kb.processors.mining_runner import get_run_state

    state = get_run_state()
    return {
        "status": "started",
        "run_id": state.get("run_id"),
        "mode": request.mode,
        "message": f"Mining pipeline started ({request.mode} mode).",
    }


@router.get("/mining/status")
async def get_mining_status() -> Dict[str, Any]:
    """
    Get current mining run progress.

    Returns real-time step-by-step progress for the active run,
    or last run summary if idle.
    """
    from kb.processors.mining_runner import get_run_state

    return get_run_state()


@router.get("/mining/history")
async def get_mining_history(limit: int = 20) -> Dict[str, Any]:
    """
    Get recent mining run history from JSONL log.

    Args:
        limit: Number of recent records to return (default 20, max 100).

    Returns:
        Dict with list of history records (most recent last).
    """
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")

    from kb.processors.mining_runner import read_history

    records = read_history(limit=limit)
    return {"records": records, "total": len(records)}
