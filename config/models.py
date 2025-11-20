"""
Model Configuration

This module defines the available LLM models organized by provider.
These models are accessible through the centralized API.
Models are fetched from the API on initialization, with fallback to default list.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Default/fallback models organized by provider
# Only includes the newest, most commonly used basic model (1 per provider)
# Used if API fetch fails or during initialization
_DEFAULT_MODELS: Dict[str, List[str]] = {
    "DeepSeek": [
        "deepseek-v3.1",      # Latest DeepSeek v3.1 model
    ],
    "GPT (OpenAI)": [
        "gpt-5.1",            # Latest GPT 5.1 model
    ],
    "Claude (Anthropic)": [
        "claude-sonnet-4-5-20250929",  # Latest Claude Sonnet 4.5 model
    ],
    "Grok (xAI)": [
        "grok-4",             # Latest Grok 4 model
    ],
    "Gemini (Google)": [
        "gemini-2.5-flash",   # Latest Gemini 2.5 Flash model
    ],
}

_CACHE_DIR = Path(__file__).resolve().parent / ".cache"
_CACHE_DIR.mkdir(exist_ok=True)
_CACHE_FILE = _CACHE_DIR / "models.json"
_CACHE_TTL_SECONDS = int(os.getenv("REQVIBE_MODEL_CACHE_TTL", "3600"))


def _load_cached_models(strict_ttl: bool = True) -> Optional[Dict[str, List[str]]]:
    """
    Load cached models from disk.

    Args:
        strict_ttl: If True, enforces TTL check. If False, returns cached data even if stale.
    """
    if not _CACHE_FILE.exists():
        return None

    try:
        if strict_ttl:
            age_seconds = time.time() - _CACHE_FILE.stat().st_mtime
            if age_seconds > _CACHE_TTL_SECONDS:
                return None

        with _CACHE_FILE.open("r", encoding="utf-8") as cache_file:
            data = json.load(cache_file)
            if isinstance(data, dict):
                return {provider: list(models) for provider, models in data.items()}
    except Exception as cache_error:
        print(f"Failed to load cached model list: {cache_error}")

    return None


def _write_model_cache(models: Dict[str, List[str]]) -> None:
    """Write the model list to the local cache for reuse between reruns."""
    try:
        with _CACHE_FILE.open("w", encoding="utf-8") as cache_file:
            json.dump(models, cache_file, indent=2)
    except Exception as cache_error:
        print(f"Failed to write model cache: {cache_error}")


def _fetch_models_from_api() -> Optional[Dict[str, List[str]]]:
    """
    Fetch available models from the API, with local caching to avoid repeated calls.

    Returns:
        Dictionary of models by provider, or None if fetch fails
    """
    cached_models = _load_cached_models(strict_ttl=True)
    if cached_models:
        return cached_models

    try:
        from infrastructure.llm.client import fetch_available_models

        models = fetch_available_models()
        if models:
            _write_model_cache(models)
            return models
    except Exception as exc:
        print(f"Failed to fetch models from API: {exc}")

    # Fall back to stale cache (even if TTL expired) before using defaults
    return _load_cached_models(strict_ttl=False)


def _initialize_models() -> Tuple[Dict[str, List[str]], List[Dict[str, str]]]:
    """
    Initialize the model list, fetching from API if possible.
    
    Returns:
        Tuple of (AVAILABLE_MODELS dict, ALL_MODELS list)
    """
    api_models = _fetch_models_from_api()
    
    if api_models:
        available_models = api_models
    else:
        available_models = _DEFAULT_MODELS.copy()
        _write_model_cache(available_models)
    
    all_models: List[Dict[str, str]] = []
    for provider, models in available_models.items():
        for model in models:
            all_models.append({
                "id": model,
                "name": model,
                "provider": provider
            })
    
    return available_models, all_models


# Initialize models (will try API first, fallback to defaults)
AVAILABLE_MODELS, ALL_MODELS = _initialize_models()

