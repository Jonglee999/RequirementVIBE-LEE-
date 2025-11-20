"""
Centralized LLM API Client

This module provides a client that wraps the centralized LLM API (api.ai88n.com)
to mimic the OpenAI SDK interface. This allows the application to use multiple
LLM providers (DeepSeek, GPT, Claude, Grok) through a single API endpoint.

Architecture:
- CentralizedLLMClient: Main client class that holds API token and base URL
- _Chat: Wrapper class that provides the 'chat' attribute
- _Completions: Wrapper class that provides the 'completions' attribute
- MockResponse/MockChoice/MockMessage: Classes that mimic OpenAI response structure
"""

import json
import re
import requests
from typing import List, Dict, Any, Generator


class _Completions:
    """
    Internal class that mimics OpenAI's chat.completions interface.
    
    This class handles the actual HTTP request to the centralized API endpoint.
    It converts the OpenAI-style method call into a REST API request and
    transforms the response back into an OpenAI-compatible format.
    
    Attributes:
        client: Reference to the parent CentralizedLLMClient instance
    """
    
    def __init__(self, client):
        """Initialize with reference to parent client for API configuration."""
        self.client = client
    
    def create(self, model: str, messages: List[Dict[str, str]], **kwargs):
        """
        Create a chat completion by sending request to centralized API.
        
        This method:
        1. Builds the API request payload with model, messages, and optional parameters
        2. Sends POST request to the centralized API endpoint
        3. Parses the JSON response
        4. Wraps the response in mock objects that match OpenAI's response structure
        5. Handles errors and provides meaningful error messages
        
        Args:
            model: Model identifier (e.g., "deepseek-chat", "gpt-4o")
            messages: List of message dictionaries with "role" and "content" keys
            **kwargs: Optional parameters (temperature, max_tokens, stream, timeout)
        
        Returns:
            MockResponse object with OpenAI-compatible structure:
            - response.choices[0].message.content (the generated text)
            - response.choices[0].message.role
        
        Raises:
            Exception: If API request fails or returns an error
        """
        # Build the API endpoint URL using the client's base URL
        url = f"{self.client.base_url}/v1/chat/completions"
        
        # Determine if streaming is requested
        streaming = kwargs.pop("stream", False)
        
        # Construct the request payload with required fields
        payload = {
            "model": model,
            "messages": messages,
        }
        
        # Add optional parameters if provided (temperature, max_tokens, stream)
        # These control the model's behavior and output length
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if streaming:
            payload["stream"] = True
        
        # Determine timeout: use custom timeout if provided, otherwise default
        # Longer operations (like SRS generation) should use longer timeouts
        timeout = kwargs.get("timeout", 60)  # Default 60 seconds, can be overridden
        
        # For large max_tokens, increase timeout proportionally
        max_tokens = kwargs.get("max_tokens", 2000)
        if max_tokens > 8000:
            # For very long outputs, use longer timeout (3 minutes)
            timeout = max(timeout, 180)
        elif max_tokens > 4000:
            # For medium outputs, use 2 minutes
            timeout = max(timeout, 120)
        
        def _format_request_exception(exc):
            error_msg = f"API request failed: {str(exc)}"
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    error_data = exc.response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except Exception:
                    error_msg = f"API request failed with status {exc.response.status_code}: {str(exc)}"
            return error_msg
        
        if streaming:
            def stream_generator() -> Generator[Dict[str, Any], None, None]:
                try:
                    with self.client.session.post(
                        url,
                        headers=self.client.headers,
                        json=payload,
                        timeout=timeout,
                        stream=True
                    ) as response:
                        response.raise_for_status()
                        # Ensure proper UTF-8 encoding for streaming
                        response.encoding = 'utf-8'
                        for line in response.iter_lines(decode_unicode=False):
                            if not line:
                                continue
                            # Decode bytes to string with UTF-8, handling errors gracefully
                            try:
                                line = line.decode('utf-8').strip()
                            except UnicodeDecodeError:
                                # Try to decode with error handling
                                line = line.decode('utf-8', errors='replace').strip()
                            
                            if not line:
                                continue
                            if line.startswith("data:"):
                                line = line[5:].strip()
                            if not line or line == "[DONE]":
                                if line == "[DONE]":
                                    yield {
                                        "choices": [
                                            {
                                                "delta": {},
                                                "finish_reason": "stop"
                                            }
                                        ]
                                    }
                                continue
                            try:
                                chunk = json.loads(line)
                                yield chunk
                            except json.JSONDecodeError:
                                # Ignore malformed chunks
                                continue
                except requests.exceptions.Timeout:
                    timeout_seconds = timeout if "timeout" in locals() else 60
                    error_msg = f"API request timed out after {timeout_seconds} seconds. The request may be too large or the server is slow. Try reducing the conversation history or try again later."
                    raise Exception(error_msg)
                except requests.exceptions.RequestException as exc:
                    raise Exception(_format_request_exception(exc))
                except Exception as exc:
                    raise Exception(f"API call failed: {str(exc)}")
            
            return stream_generator()
        
        try:
            response = self.client.session.post(
                url, 
                headers=self.client.headers, 
                json=payload, 
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            
            class MockResponse:
                def __init__(self, data):
                    self.data = data
                    choices_data = data.get("choices", [])
                    if choices_data:
                        self.choices = [MockChoice(choices_data[0])]
                    else:
                        self.choices = [MockChoice({})]
            
            class MockChoice:
                def __init__(self, choice_data):
                    message_data = choice_data.get("message", {}) if choice_data else {}
                    self.message = MockMessage(message_data)
            
            class MockMessage:
                def __init__(self, message_data):
                    self.content = message_data.get("content", "") if message_data else ""
                    self.role = message_data.get("role", "assistant") if message_data else "assistant"
            
            return MockResponse(result)
        except requests.exceptions.Timeout:
            timeout_seconds = timeout if "timeout" in locals() else 60
            error_msg = f"API request timed out after {timeout_seconds} seconds. The request may be too large or the server is slow. Try reducing the conversation history or try again later."
            raise Exception(error_msg)
        except requests.exceptions.RequestException as exc:
            raise Exception(_format_request_exception(exc))
        except Exception as exc:
            raise Exception(f"API call failed: {str(exc)}")


class _Chat:
    """
    Internal class that mimics OpenAI's chat interface.
    
    This class provides the 'chat' attribute on the client, which in turn
    provides the 'completions' attribute. This matches the OpenAI SDK structure:
    client.chat.completions.create()
    
    Attributes:
        client: Reference to the parent CentralizedLLMClient instance
        completions: Instance of _Completions class for making API calls
    """
    
    def __init__(self, client):
        """Initialize with reference to parent client and create completions instance."""
        self.client = client
        self.completions = _Completions(client)


class CentralizedLLMClient:
    """
    Main client class for the centralized LLM API.
    
    This class wraps the centralized API (api.ai88n.com) and provides an interface
    that is compatible with the OpenAI SDK. This allows the application to use
    multiple LLM providers (DeepSeek, GPT, Claude, Grok) through a single API.
    
    The client handles:
    - API authentication via Bearer token
    - Request formatting and response parsing
    - Error handling and reporting
    
    Usage:
        client = CentralizedLLMClient(api_token="your_token")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello"}]
        )
        print(response.choices[0].message.content)
    
    Attributes:
        api_token: Bearer token for API authentication
        base_url: Base URL of the centralized API (default: https://api.ai88n.com)
        headers: HTTP headers including Authorization and Content-Type
        chat: _Chat instance that provides the chat.completions interface
    """
    
    def __init__(self, api_token: str, base_url: str = "https://api.ai88n.com"):
        """
        Initialize the centralized LLM client.
        
        Args:
            api_token: Bearer token for API authentication
            base_url: Base URL of the centralized API endpoint
        """
        self.api_token = api_token
        self.base_url = base_url
        # Set up HTTP headers for API requests
        # Authorization uses Bearer token format
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # Initialize the chat interface (provides client.chat.completions.create())
        self.chat = _Chat(self)


def get_centralized_client() -> CentralizedLLMClient:
    """
    Factory function to create and return a CentralizedLLMClient instance.
    
    Reads the API token from the CENTRALIZED_LLM_API_KEY environment variable.
    If the environment variable is not set, raises an error.
    
    Returns:
        CentralizedLLMClient: Initialized client instance
    
    Raises:
        ValueError: If CENTRALIZED_LLM_API_KEY environment variable is not set
    """
    import os
    api_token = os.getenv("CENTRALIZED_LLM_API_KEY")
    if not api_token:
        raise ValueError(
            "CENTRALIZED_LLM_API_KEY environment variable is not set. "
            "Please set it to your API token."
        )
    return CentralizedLLMClient(api_token=api_token)


def get_deepseek_client() -> CentralizedLLMClient:
    """
    Legacy function for backward compatibility.
    
    This function was originally for DeepSeek API but now uses the centralized API.
    It's kept to maintain compatibility with existing code that calls get_deepseek_client().
    
    Returns:
        CentralizedLLMClient: Same as get_centralized_client()
    """
    return get_centralized_client()


def fetch_available_models(client: CentralizedLLMClient = None) -> Dict[str, List[str]]:
    """
    Fetch available models from the centralized LLM API.
    
    This function queries the API's models endpoint to get the latest list of available models.
    It organizes them by provider (GPT, DeepSeek, Claude, Grok, Gemini).
    
    Args:
        client: Optional CentralizedLLMClient instance. If not provided, creates a new one.
        
    Returns:
        Dictionary mapping provider names to lists of model IDs, or None if fetch fails
        
    Raises:
        Exception: If the API request fails
    """
    if client is None:
        client = get_centralized_client()
    
    try:
        # Try to fetch models from /v1/models endpoint
        url = f"{client.base_url}/v1/models"
        # Use longer timeout (30 seconds) to handle slow API responses
        response = client.session.get(url, headers=client.headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Check for error responses first
        if isinstance(result, dict):
            # Some APIs return error in format: {"code": 400, "message": "..."}
            if "code" in result and result.get("code") != 200:
                error_msg = result.get("message", f"API returned error code {result.get('code')}")
                print(f"API returned error: {error_msg}")
                return None
        
        # Parse the response - handle different possible formats:
        # Format 1: {"data": [...], "success": true}
        # Format 2: {"code": 200, "data": [...]}
        # Format 3: {"data": [...]} (OpenAI-compatible)
        # Format 4: [...] (direct list)
        models_data = []
        if isinstance(result, dict):
            # Check if data is directly in result
            if "data" in result:
                data = result["data"]
                # If data is a list, use it directly
                if isinstance(data, list):
                    models_data = data
                # If data is a dict (unlikely but possible), try to extract models
                elif isinstance(data, dict):
                    # Some APIs might wrap the list in another structure
                    if "models" in data:
                        models_data = data["models"]
                    elif isinstance(data.get("data"), list):
                        models_data = data["data"]
        elif isinstance(result, list):
            # Result is directly a list of models
            models_data = result
        
        # Validate that we got model data
        if not models_data or not isinstance(models_data, list):
            print(f"Warning: Unexpected API response format. Result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            return None
        
        # Organize models by provider
        organized_models = {
            "DeepSeek": [],
            "GPT (OpenAI)": [],
            "Claude (Anthropic)": [],
            "Grok (xAI)": [],
            "Gemini (Google)": [],
        }
        
        for model_info in models_data:
            model_id = model_info.get("id", "")
            if not model_id:
                continue
            
            # Categorize models by ID prefix/pattern
            model_lower = model_id.lower()
            
            if "deepseek" in model_lower:
                # Include v3.1 model or basic chat models
                # Exclude specialized variants (coder, reasoner, v2, etc.)
                if "v3.1" in model_lower or ("chat" in model_lower and "coder" not in model_lower and "reasoner" not in model_lower):
                    organized_models["DeepSeek"].append(model_id)
            elif "gpt" in model_lower:
                # Include GPT-5 models (including gpt-5.1)
                # Filter out older versions (gpt-3, gpt-4, etc.)
                if "gpt-5" in model_lower or "gpt5" in model_lower or model_lower.startswith("gpt-5") or model_lower.startswith("gpt5"):
                    # Include all GPT-5 variants (turbo, base, etc.)
                    # Exclude specialized variants: mini, max, vision, o1, o3, etc.
                    if "mini" not in model_lower and "max" not in model_lower and "vision" not in model_lower and "o1" not in model_lower and "o3" not in model_lower:
                        organized_models["GPT (OpenAI)"].append(model_id)
            elif "claude" in model_lower:
                # Include Sonnet models (including sonnet-4-5)
                # Exclude Opus (older) and Haiku (less capable)
                if "sonnet" in model_lower:
                    organized_models["Claude (Anthropic)"].append(model_id)
            elif "grok" in model_lower:
                # Include grok-4 and other basic grok models
                # Exclude specialized variants: vision, beta, etc.
                if "vision" not in model_lower and "beta" not in model_lower:
                    organized_models["Grok (xAI)"].append(model_id)
            elif "gemini" in model_lower:
                # Include gemini-2.5-flash and Pro models
                # Allow flash models (gemini-2.5-flash) and Pro models
                if "2.5-flash" in model_lower or ("pro" in model_lower and "exp" not in model_lower and "experimental" not in model_lower):
                    organized_models["Gemini (Google)"].append(model_id)
        
        # Sort each provider's models to prioritize latest versions
        # Sort by version numbers if present, otherwise alphabetically (reverse for latest first)
        def sort_key(model_id):
            """Extract version numbers for sorting, prioritizing higher versions and common variants."""
            model_lower = model_id.lower()
            
            # Priority boost for common model variants (higher priority = sorted first)
            priority_boost = 0
            # Prioritize specific models used in the project
            if "v3.1" in model_lower and "deepseek" in model_lower:  # DeepSeek v3.1
                priority_boost = 1100
            elif "gpt-5.1" in model_lower or "gpt5.1" in model_lower:  # GPT 5.1
                priority_boost = 1100
            elif "sonnet-4-5" in model_lower and "claude" in model_lower:  # Claude Sonnet 4.5
                priority_boost = 1100
            elif "grok-4" in model_lower:  # Grok 4
                priority_boost = 1100
            elif "2.5-flash" in model_lower and "gemini" in model_lower:  # Gemini 2.5 Flash
                priority_boost = 1100
            elif "turbo" in model_lower:  # GPT turbo models
                priority_boost = 1000
            elif "latest" in model_lower or "newest" in model_lower:
                priority_boost = 900
            elif "chat" in model_lower and "deepseek" in model_lower:  # DeepSeek chat
                priority_boost = 800
            elif "sonnet" in model_lower:  # Claude Sonnet
                priority_boost = 800
            elif "pro" in model_lower and "gemini" in model_lower:  # Gemini Pro
                priority_boost = 800
            
            # Try to extract version numbers (e.g., "3.5", "2.0", "1.5")
            version_match = re.search(r'(\d+)\.(\d+)', model_id)
            if version_match:
                major, minor = int(version_match.group(1)), int(version_match.group(2))
                return (priority_boost, major, minor, 0)
            
            # For models with single version numbers (e.g., "gpt-4", "grok-2")
            single_version = re.search(r'[^0-9](\d+)(?:[^0-9]|$)', model_id)
            if single_version:
                version = int(single_version.group(1))
                return (priority_boost, version, 0, 0)
            
            # For models with date suffixes (e.g., "claude-3-5-sonnet-20241022")
            date_match = re.search(r'(\d{8})$', model_id)
            if date_match:
                date = int(date_match.group(1))
                return (priority_boost, date, 0, 0)
            
            # For models without clear version numbers, use string comparison
            # Prefer shorter names (usually newer) and alphabetical order
            return (priority_boost, 0, 0, len(model_id))
        
        # Filter to keep only the newest, most commonly used basic model for each provider
        # Keep only 1 model per provider (the latest basic model)
        filtered_models = {}
        for provider, models in organized_models.items():
            if not models:
                continue
            
            # Sort by version (newest first)
            sorted_models = sorted(models, key=sort_key, reverse=True)
            
            # Keep only the newest model (the first one after sorting)
            filtered_models[provider] = [sorted_models[0]] if sorted_models else []
        
        return filtered_models
        
    except requests.exceptions.Timeout as e:
        # Handle timeout specifically
        print(f"Could not fetch models from API: Request timed out after 30 seconds. Using fallback models.")
        return None
    except requests.exceptions.RequestException as e:
        # If models endpoint doesn't exist or fails, return None to use fallback
        print(f"Could not fetch models from API: {e}")
        return None
    except Exception as e:
        print(f"Error fetching models: {e}")
        return None

