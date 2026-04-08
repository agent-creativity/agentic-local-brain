"""
Settings routes for Knowledge Base Web API.

Provides endpoints for reading and updating system configuration,
including LLM model service settings and model connectivity testing.
"""
import asyncio
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CONFIG_FILE = Path.home() / ".localbrain" / "config.yaml"

# Valid provider values
VALID_PROVIDERS = {"dashscope", "openai_compatible", "litellm"}


class LLMConfigRequest(BaseModel):
    """Request model for updating LLM configuration."""
    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None


def _load_raw_config() -> Dict[str, Any]:
    """Load raw config file without expanding environment variables."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_raw_config(config: Dict[str, Any]) -> None:
    """Save config dict to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def _mask_api_key(key: str) -> str:
    """Return masked version of api_key for display, preserving env var format."""
    if not key:
        return ""
    # Preserve ${VAR_NAME} format as-is — it's a variable reference, not a secret
    if re.match(r"^\$\{\w+\}$", key):
        return key
    # Mask actual key values
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """
    Get current system settings.

    Returns LLM configuration with api_key masked for display.
    The raw api_key value (env var name or masked key) is returned
    so the frontend can show what's currently configured.
    """
    try:
        from kb.config import Config
        config = Config()

        raw = _load_raw_config()
        llm = raw.get("llm", {})

        return {
            "llm": {
                "provider": llm.get("provider", "dashscope"),
                "model": llm.get("model", "qwen-plus"),
                "api_key": _mask_api_key(llm.get("api_key", "")),
                "base_url": llm.get("base_url", ""),
            },
            "paths": {
                "data_dir": str(config.data_dir),
                "install_dir": str(config.install_dir),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")


@router.put("/settings/llm")
async def update_llm_settings(request: LLMConfigRequest) -> Dict[str, Any]:
    """
    Update LLM model service configuration.

    Supports both old and new provider formats:
    - Old: provider=dashscope, model=qwen-plus
    - Old: provider=openai_compatible, model=qwen-plus, base_url=...
    - New: provider=litellm, model=dashscope/qwen-plus

    api_key accepts either:
    - An environment variable name in ${VAR_NAME} format
    - A raw API key value

    Args:
        request: LLMConfigRequest with provider, model, api_key, and optional base_url.

    Returns:
        Updated LLM configuration (api_key masked).
    """
    if request.provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{request.provider}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
        )

    if not request.model.strip():
        raise HTTPException(status_code=400, detail="model cannot be empty")

    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty")

    if request.provider == "openai_compatible" and not request.base_url:
        raise HTTPException(
            status_code=400,
            detail="base_url is required for openai_compatible provider"
        )

    try:
        raw = _load_raw_config()

        llm_config: Dict[str, Any] = {
            "provider": request.provider,
            "model": request.model.strip(),
            "api_key": request.api_key.strip(),
        }
        if request.base_url:
            llm_config["base_url"] = request.base_url.strip()
        elif "base_url" in raw.get("llm", {}):
            # Remove base_url if it was previously set but not provided now
            pass

        raw["llm"] = llm_config
        _save_raw_config(raw)

        # Invalidate the cached config so next request reloads
        try:
            from kb.web.dependencies import get_config
            get_config.cache_clear()
        except Exception:
            pass

        return {
            "llm": {
                "provider": llm_config["provider"],
                "model": llm_config["model"],
                "api_key": _mask_api_key(llm_config["api_key"]),
                "base_url": llm_config.get("base_url", ""),
            },
            "message": "LLM configuration updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")


@router.post("/settings/test-llm")
async def test_llm() -> Dict[str, Any]:
    """
    Test LLM model connectivity using current config.

    Sends a simple prompt and returns the response with latency.
    """
    try:
        result = await asyncio.to_thread(_test_llm_sync)
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": 0}


def _test_llm_sync() -> Dict[str, Any]:
    """Run LLM test synchronously (called in thread)."""
    from kb.config import Config

    config = Config()
    llm_config = config.get("llm", {})
    provider_name = llm_config.get("provider", "dashscope")
    model = llm_config.get("model", "qwen-plus")
    api_key = llm_config.get("api_key", "")

    if not api_key:
        return {"success": False, "error": "API key not configured", "latency_ms": 0}

    start = time.time()
    try:
        from kb.processors.tag_extractor import LiteLLMProvider

        if provider_name == "litellm":
            llm_model = model
        elif provider_name == "dashscope":
            llm_model = model if "/" in model else f"dashscope/{model}"
        elif provider_name == "openai_compatible":
            llm_model = model if "/" in model else f"openai/{model}"
        else:
            llm_model = model

        base_url = llm_config.get("base_url", None)
        provider = LiteLLMProvider(api_key=api_key, model=llm_model, api_base=base_url)
        response = provider.generate(
            prompt="Reply with exactly: OK",
            temperature=0.0,
            max_retries=1,
        )
        latency = int((time.time() - start) * 1000)
        return {
            "success": True,
            "model": llm_model,
            "response": response.strip()[:200],
            "latency_ms": latency,
        }
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return {"success": False, "error": str(e), "latency_ms": latency}


@router.post("/settings/test-embedding")
async def test_embedding() -> Dict[str, Any]:
    """
    Test embedding model connectivity using current config.

    Generates an embedding for a test sentence and returns dimension info with latency.
    """
    try:
        result = await asyncio.to_thread(_test_embedding_sync)
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": 0}


def _test_embedding_sync() -> Dict[str, Any]:
    """Run embedding test synchronously (called in thread)."""
    from kb.config import Config
    from kb.processors.embedder import Embedder

    config = Config()
    embedding_config = config.get("embedding", {})

    start = time.time()
    try:
        embedder = Embedder.from_config(config)
        result = embedder.embed(["This is a test sentence for embedding."])
        latency = int((time.time() - start) * 1000)

        if result and len(result) > 0:
            dim = len(result[0])
            return {
                "success": True,
                "model": embedding_config.get("model", "") or embedding_config.get("dashscope", {}).get("model", ""),
                "dimensions": dim,
                "latency_ms": latency,
            }
        else:
            return {"success": False, "error": "Empty embedding result", "latency_ms": latency}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return {"success": False, "error": str(e), "latency_ms": latency}
