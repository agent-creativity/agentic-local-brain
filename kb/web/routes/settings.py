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

# Valid provider values for the UI (actual provider names)
# These map to litellm internally
VALID_UI_PROVIDERS = {"dashscope", "openai", "anthropic", "ollama", "openai_compatible"}

# Legacy providers that we support for backward compatibility
LEGACY_PROVIDERS = {"dashscope", "openai_compatible", "litellm"}


class LLMConfigRequest(BaseModel):
    """Request model for updating LLM configuration."""
    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None


class EmbeddingConfigRequest(BaseModel):
    """Request model for updating embedding configuration."""
    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None


class BackupConfigRequest(BaseModel):
    """Request model for updating backup configuration."""
    enabled: bool
    schedule: str
    retention_days: int
    backup_dir: str
    include_db: bool
    include_files: bool
    compression: bool


def _parse_litellm_model(model_str: str) -> tuple:
    """
    Parse a litellm model string into (provider, model_name).
    
    Examples:
    - 'dashscope/qwen-plus' -> ('dashscope', 'qwen-plus')
    - 'openai/gpt-4o' -> ('openai', 'gpt-4o')
    - 'qwen-plus' -> (None, 'qwen-plus')  # legacy format without prefix
    """
    if '/' in model_str:
        parts = model_str.split('/', 1)
        return (parts[0], parts[1])
    return (None, model_str)


def _determine_ui_provider(stored_provider: str, stored_model: str, base_url: str = None, is_embedding: bool = False) -> str:
    """
    Determine the UI provider from stored config.
    
    Handles:
    - New format: provider='litellm', model='dashscope/qwen-plus' -> 'dashscope'
    - Legacy format: provider='dashscope', model='qwen-plus' -> 'dashscope'
    - Legacy format: provider='openai_compatible', model='...' -> 'openai_compatible'
    - DashScope embedding via OpenAI-compatible: model='openai/text-embedding-v4', base_url contains 'dashscope.aliyuncs.com' -> 'dashscope'
    """
    # Special case: DashScope embeddings via OpenAI-compatible endpoint
    # Model has 'openai/' prefix but base_url points to DashScope
    if is_embedding and stored_model.startswith('openai/') and base_url and 'dashscope.aliyuncs.com' in base_url:
        return 'dashscope'
    
    # If provider is litellm, extract the actual provider from model string
    if stored_provider == 'litellm':
        parsed_provider, _ = _parse_litellm_model(stored_model)
        if parsed_provider:
            # Map litellm provider names to UI provider names
            # 'openai' in litellm could be actual OpenAI or openai_compatible
            # We default to 'openai' for openai/ prefix
            return parsed_provider
        # If no prefix in model, default to dashscope
        return 'dashscope'
    
    # Legacy format: provider is the actual provider name
    return stored_provider


def _build_litellm_model(ui_provider: str, ui_model: str, is_embedding: bool = False) -> str:
    """
    Build a litellm model string from UI provider and model.
    
    Examples:
    - ('dashscope', 'qwen-plus') -> 'dashscope/qwen-plus'
    - ('openai', 'gpt-4o') -> 'openai/gpt-4o'
    - ('openai_compatible', 'some-model') -> 'openai/some-model'
    - ('ollama', 'llama3') -> 'ollama/llama3'
    
    Special case for DashScope embeddings:
    - ('dashscope', 'text-embedding-v4', True) -> 'openai/text-embedding-v4'
      (DashScope embeddings must use OpenAI-compatible endpoint)
    """
    ui_model = ui_model.strip()
    
    # If model already has a prefix, use it as-is
    if '/' in ui_model:
        return ui_model
    
    # DashScope embeddings must use openai/ prefix for litellm (OpenAI-compatible mode)
    # DashScope LLM uses native dashscope/ prefix
    if is_embedding and ui_provider == 'dashscope':
        return f'openai/{ui_model}'
    
    # openai_compatible uses openai/ prefix for litellm
    if ui_provider == 'openai_compatible':
        return f'openai/{ui_model}'
    
    # All other providers use their name as prefix
    return f'{ui_provider}/{ui_model}'


def _load_raw_config() -> Dict[str, Any]:
    """Load raw config file without expanding environment variables.

    Merges with DEFAULT_CONFIG to ensure all sections are preserved.
    """
    from kb.config import DEFAULT_CONFIG
    import copy

    # Start with a deep copy of default config
    config = copy.deepcopy(DEFAULT_CONFIG)

    # If config file exists, load and merge it
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f)
            if file_config:
                _deep_merge_dict(config, file_config)

    return config


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Deep merge override dict into base dict (modifies base in place)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge_dict(base[key], value)
        else:
            base[key] = value


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


def _is_masked_key(key: str) -> bool:
    """Check if an api_key appears to be masked (contains asterisks)."""
    return "*" in key


@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """
    Get current system settings.

    Returns LLM and embedding configuration with api_key masked for display.
    The raw api_key value (env var name or masked key) is returned
    so the frontend can show what's currently configured.
    
    The provider and model are parsed from litellm format for the UI:
    - If stored model is 'dashscope/qwen-plus', returns provider='dashscope', model='qwen-plus'
    - Legacy configs (provider='dashscope', model='qwen-plus') are handled correctly
    """
    try:
        from kb.config import Config
        config = Config()

        raw = _load_raw_config()
        llm = raw.get("llm", {})
        embedding = raw.get("embedding", {})
        
        # Parse LLM config
        llm_stored_provider = llm.get("provider", "dashscope")
        llm_stored_model = llm.get("model", "qwen-plus")
        llm_ui_provider = _determine_ui_provider(llm_stored_provider, llm_stored_model)
        
        # Parse model name for UI
        if llm_stored_provider == "litellm" or "/" in llm_stored_model:
            _, llm_ui_model = _parse_litellm_model(llm_stored_model)
        else:
            llm_ui_model = llm_stored_model
        
        # Parse Embedding config
        emb_stored_provider = embedding.get("provider", "dashscope")
        emb_stored_model = embedding.get("model", "text-embedding-v4")
        emb_base_url = embedding.get("base_url", "")
        emb_ui_provider = _determine_ui_provider(emb_stored_provider, emb_stored_model, emb_base_url, is_embedding=True)
        
        # Parse model name for UI
        if emb_stored_provider == "litellm" or "/" in emb_stored_model:
            _, emb_ui_model = _parse_litellm_model(emb_stored_model)
        else:
            emb_ui_model = emb_stored_model

        return {
            "llm": {
                "provider": llm_ui_provider,
                "model": llm_ui_model,
                "api_key": _mask_api_key(llm.get("api_key", "")),
                "base_url": llm.get("base_url", ""),
            },
            "embedding": {
                "provider": emb_ui_provider,
                "model": emb_ui_model,
                "api_key": _mask_api_key(embedding.get("api_key", "")),
                "base_url": embedding.get("base_url", ""),
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

    The UI sends actual provider names (dashscope, openai, anthropic, ollama, openai_compatible)
    and plain model names (qwen-plus, gpt-4o). This endpoint converts them to litellm format
    for storage: provider='litellm', model='{provider}/{model}'.

    api_key accepts either:
    - An environment variable name in ${VAR_NAME} format
    - A raw API key value

    Args:
        request: LLMConfigRequest with provider, model, api_key, and optional base_url.

    Returns:
        Updated LLM configuration (api_key masked).
    """
    # Support both new UI providers and legacy providers for backward compatibility
    if request.provider not in VALID_UI_PROVIDERS and request.provider not in LEGACY_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{request.provider}'. Must be one of: {', '.join(sorted(VALID_UI_PROVIDERS))}"
        )

    if not request.model.strip():
        raise HTTPException(status_code=400, detail="model cannot be empty")

    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty")

    # base_url is required for openai_compatible, optional for others
    if request.provider == "openai_compatible" and not request.base_url:
        raise HTTPException(
            status_code=400,
            detail="base_url is required for openai_compatible provider"
        )

    try:
        raw = _load_raw_config()

        # Build litellm model string from UI provider and model
        ui_provider = request.provider
        ui_model = request.model.strip()

        # For legacy providers (dashscope, openai_compatible, litellm),
        # we still convert to the new litellm format
        litellm_model = _build_litellm_model(ui_provider, ui_model)

        # Check if the incoming api_key is masked - if so, preserve the existing key
        incoming_key = request.api_key.strip()
        if _is_masked_key(incoming_key):
            # Keep the existing api_key from config
            existing_llm = raw.get("llm", {})
            api_key_to_save = existing_llm.get("api_key", incoming_key)
        else:
            api_key_to_save = incoming_key

        # Preserve existing llm config and update only the specified fields
        llm_config = raw.get("llm", {})
        llm_config.update({
            "provider": "litellm",
            "model": litellm_model,
            "api_key": api_key_to_save,
        })
        if request.base_url:
            llm_config["base_url"] = request.base_url.strip()

        raw["llm"] = llm_config
        _save_raw_config(raw)

        # Invalidate the cached config so next request reloads
        try:
            from kb.web.dependencies import get_config
            get_config.cache_clear()
        except Exception:
            pass

        # Return the UI format (not the stored litellm format)
        return {
            "llm": {
                "provider": ui_provider,
                "model": ui_model,
                "api_key": _mask_api_key(llm_config["api_key"]),
                "base_url": llm_config.get("base_url", ""),
            },
            "message": "LLM configuration updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")


@router.put("/settings/embedding")
async def update_embedding_settings(request: EmbeddingConfigRequest) -> Dict[str, Any]:
    """
    Update embedding model service configuration.

    The UI sends actual provider names (dashscope, openai, anthropic, ollama, openai_compatible)
    and plain model names (text-embedding-v4, text-embedding-3-small). This endpoint converts
    them to litellm format for storage: provider='litellm', model='{provider}/{model}'.

    api_key accepts either:
    - An environment variable name in ${VAR_NAME} format
    - A raw API key value

    Args:
        request: EmbeddingConfigRequest with provider, model, api_key, and optional base_url.

    Returns:
        Updated embedding configuration (api_key masked).
    """
    # Support both new UI providers and legacy providers for backward compatibility
    if request.provider not in VALID_UI_PROVIDERS and request.provider not in LEGACY_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{request.provider}'. Must be one of: {', '.join(sorted(VALID_UI_PROVIDERS))}"
        )

    if not request.model.strip():
        raise HTTPException(status_code=400, detail="model cannot be empty")

    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty")

    # base_url is required for openai_compatible, optional for others
    if request.provider == "openai_compatible" and not request.base_url:
        raise HTTPException(
            status_code=400,
            detail="base_url is required for openai_compatible provider"
        )

    try:
        raw = _load_raw_config()

        # Build litellm model string from UI provider and model
        ui_provider = request.provider
        ui_model = request.model.strip()

        # For legacy providers (dashscope, openai_compatible, litellm),
        # we still convert to the new litellm format
        # is_embedding=True handles DashScope's special OpenAI-compatible mode
        litellm_model = _build_litellm_model(ui_provider, ui_model, is_embedding=True)

        # Check if the incoming api_key is masked - if so, preserve the existing key
        incoming_key = request.api_key.strip()
        if _is_masked_key(incoming_key):
            # Keep the existing api_key from config
            existing_embedding = raw.get("embedding", {})
            api_key_to_save = existing_embedding.get("api_key", incoming_key)
        else:
            api_key_to_save = incoming_key

        # Determine base_url
        base_url = request.base_url.strip() if request.base_url else None

        # Auto-set base_url for DashScope embeddings (requires OpenAI-compatible endpoint)
        if ui_provider == 'dashscope' and not base_url:
            base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

        # Preserve existing embedding config and update only the specified fields
        embedding_config = raw.get("embedding", {})
        embedding_config.update({
            "provider": "litellm",
            "model": litellm_model,
            "api_key": api_key_to_save,
        })
        if base_url:
            embedding_config["base_url"] = base_url

        raw["embedding"] = embedding_config
        _save_raw_config(raw)

        # Invalidate the cached config so next request reloads
        try:
            from kb.web.dependencies import get_config
            get_config.cache_clear()
        except Exception:
            pass

        # Return the UI format (not the stored litellm format)
        return {
            "embedding": {
                "provider": ui_provider,
                "model": ui_model,
                "api_key": _mask_api_key(embedding_config["api_key"]),
                "base_url": embedding_config.get("base_url", ""),
            },
            "message": "Embedding configuration updated successfully"
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
    provider_name = llm_config.get("provider", "litellm")
    model = llm_config.get("model", "dashscope/qwen-plus")
    api_key = llm_config.get("api_key", "")

    if not api_key:
        return {"success": False, "error": "API key not configured", "latency_ms": 0}

    start = time.time()
    try:
        from kb.processors.tag_extractor import LiteLLMProvider

        # The stored model is always in litellm format (e.g., "dashscope/qwen-plus")
        # If it's legacy format without provider prefix, add dashscope/
        llm_model = model if "/" in model else f"dashscope/{model}"

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


@router.get("/settings/doctor")
async def run_doctor() -> Dict[str, Any]:
    """
    Run system diagnostics and return structured results.

    Returns version info, check results, and any issues found.
    """
    from kb.commands.doctor import run_diagnostics
    return run_diagnostics()


@router.get("/settings/backup")
async def get_backup_settings() -> Dict[str, Any]:
    """
    Get current backup configuration.

    Returns backup settings from config file.
    """
    try:
        raw = _load_raw_config()
        backup = raw.get("backup", {})

        return {
            "backup": {
                "enabled": backup.get("enabled", False),
                "schedule": backup.get("schedule", "0 2 * * *"),
                "retention_days": backup.get("retention_days", 30),
                "backup_dir": backup.get("backup_dir", "~/.knowledge-base/backups"),
                "include_db": backup.get("include_db", True),
                "include_files": backup.get("include_files", True),
                "compression": backup.get("compression", True),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load backup settings: {str(e)}")


@router.put("/settings/backup")
async def update_backup_settings(request: BackupConfigRequest) -> Dict[str, Any]:
    """
    Update backup configuration.

    Args:
        request: BackupConfigRequest with backup settings.

    Returns:
        Updated backup configuration.
    """
    # Validate schedule format (basic cron validation)
    if not request.schedule.strip():
        raise HTTPException(status_code=400, detail="schedule cannot be empty")

    if request.retention_days < 1:
        raise HTTPException(status_code=400, detail="retention_days must be at least 1")

    if not request.backup_dir.strip():
        raise HTTPException(status_code=400, detail="backup_dir cannot be empty")

    try:
        raw = _load_raw_config()

        # Preserve existing backup config and update
        backup_config = raw.get("backup", {})
        backup_config.update({
            "enabled": request.enabled,
            "schedule": request.schedule.strip(),
            "retention_days": request.retention_days,
            "backup_dir": request.backup_dir.strip(),
            "include_db": request.include_db,
            "include_files": request.include_files,
            "compression": request.compression,
        })

        raw["backup"] = backup_config
        _save_raw_config(raw)

        # Invalidate the cached config
        try:
            from kb.web.dependencies import get_config
            get_config.cache_clear()
        except Exception:
            pass

        return {
            "backup": backup_config,
            "message": "Backup configuration updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save backup settings: {str(e)}")
