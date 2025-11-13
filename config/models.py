"""
Model Configuration

This module defines the available LLM models organized by provider.
These models are accessible through the centralized API.
"""

# Available models organized by provider for easy selection
# Each provider has multiple model variants with different capabilities
AVAILABLE_MODELS = {
    "DeepSeek": [
        "deepseek-chat",
        "deepseek-coder",
        "deepseek-reasoner",
    ],
    "GPT (OpenAI)": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ],
    "Claude (Anthropic)": [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ],
    "Grok (xAI)": [
        "grok-beta",
        "grok-2",
    ],
}

# Flatten the nested model dictionary into a flat list for easier iteration
# Each entry contains model ID, name, and provider information
# This structure is used by the model selector UI to display and filter models
ALL_MODELS = []
for provider, models in AVAILABLE_MODELS.items():
    for model in models:
        ALL_MODELS.append({
            "id": model,           # Model identifier used in API calls
            "name": model,         # Display name (same as ID in this case)
            "provider": provider   # Provider name for grouping in UI
        })

