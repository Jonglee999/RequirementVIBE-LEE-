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

import requests
from typing import List, Dict, Any


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
        if "stream" in kwargs:
            payload["stream"] = kwargs["stream"]
        
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
        
        try:
            # Send HTTP POST request to the centralized API
            # Uses Bearer token authentication from client headers
            response = requests.post(
                url, 
                headers=self.client.headers, 
                json=payload, 
                timeout=timeout  # Configurable timeout based on operation type
            )
            # Raise exception if HTTP status code indicates an error
            response.raise_for_status()
            # Parse JSON response from API
            result = response.json()
            
            # Create mock response objects that match OpenAI SDK structure
            # This allows the rest of the code to use the same interface
            class MockResponse:
                def __init__(self, data):
                    self.data = data
                    choices_data = data.get("choices", [])
                    if choices_data:
                        self.choices = [MockChoice(choices_data[0])]
                    else:
                        # Return empty choice if no choices
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
        except requests.exceptions.Timeout as e:
            # Handle timeout errors with helpful message
            timeout_seconds = timeout if 'timeout' in locals() else 60
            error_msg = f"API request timed out after {timeout_seconds} seconds. The request may be too large or the server is slow. Try reducing the conversation history or try again later."
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = f"API request failed with status {e.response.status_code}: {str(e)}"
            raise Exception(error_msg)
        except Exception as e:
            raise Exception(f"API call failed: {str(e)}")


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

