"""
Model Configuration

This module defines the available LLM models organized by provider.
These models are accessible through the centralized API.
Models are fetched from the API on initialization, with fallback to default list.
"""

# Default/fallback models organized by provider
# Only includes the newest, most commonly used basic model (1 per provider)
# Used if API fetch fails or during initialization
_DEFAULT_MODELS = {
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


def _fetch_models_from_api():
    """
    Fetch available models from the API.
    
    Returns:
        Dictionary of models by provider, or None if fetch fails
    """
    try:
        from infrastructure.llm.client import fetch_available_models
        return fetch_available_models()
    except Exception as e:
        print(f"Failed to fetch models from API: {e}")
        return None


def _initialize_models():
    """
    Initialize the model list, fetching from API if possible.
    
    Returns:
        Tuple of (AVAILABLE_MODELS dict, ALL_MODELS list)
    """
    # Try to fetch models from API
    api_models = _fetch_models_from_api()
    
    if api_models:
        # Use API models, but ensure we have at least the default structure
        available_models = api_models
    else:
        # Fallback to default models
        available_models = _DEFAULT_MODELS.copy()
    
    # Flatten the nested model dictionary into a flat list for easier iteration
    # Each entry contains model ID, name, and provider information
    all_models = []
    for provider, models in available_models.items():
        for model in models:
            all_models.append({
                "id": model,           # Model identifier used in API calls
                "name": model,         # Display name (same as ID in this case)
                "provider": provider   # Provider name for grouping in UI
            })
    
    return available_models, all_models


# Initialize models (will try API first, fallback to defaults)
AVAILABLE_MODELS, ALL_MODELS = _initialize_models()

