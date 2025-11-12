"""
ReqVibe - AI Requirements Analyst Application

This Streamlit application provides an AI-powered requirements engineering assistant that:
- Analyzes and refines software requirements using Volere template structure
- Supports multiple LLM models (DeepSeek, GPT, Claude, Grok) via centralized API
- Manages conversation sessions with persistent chat history
- Generates IEEE 830 SRS documents from conversations
- Provides context summarization for long conversations

Main Components:
1. Centralized LLM API Client - Wraps the centralized API to mimic OpenAI interface
2. Session Management - Handles multiple conversation sessions with model persistence
3. Memory Management - Manages chat history, token counting, and context window
4. UI Components - Sidebar for session/model management, main chat area
5. SRS Generation - Converts conversation history to IEEE 830 format documents
"""

import streamlit as st
import os
import requests
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI  # DeepSeek API uses OpenAI-compatible SDK
import uuid
from datetime import datetime
from memory import ShortTermMemory
from long_term_memory import LongTermMemory
from character import decide_and_build_prompt
import re
import copy

# ----------------------------------------------------------------------
# Page Configuration
# ----------------------------------------------------------------------
# Sets up the Streamlit page with title, icon, layout, and initial sidebar state
# The sidebar starts expanded to show session management and model selection
st.set_page_config(
    page_title="Requirement Auto Analysis:UESTC-MBSE Requirement Assistant",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"  # Start with sidebar expanded, but user can collapse it
)

# ----------------------------------------------------------------------
# UI Styling - ChatGPT-like Dark Theme
# ----------------------------------------------------------------------
# Custom CSS to create a dark, modern interface similar to ChatGPT
# Includes styling for:
# - Header and sidebar (dark backgrounds, proper z-indexing)
# - Chat messages (user/assistant avatars, message bubbles)
# - Buttons and inputs (hover effects, consistent styling)
# - Scrollbars and responsive design
# - Menu toggle button positioning
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    footer {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Keep header visible for sidebar toggle */
    header {
        visibility: visible !important;
        display: block !important;
        height: 3.5rem !important;
        background-color: #202123 !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        z-index: 100;
    }
    
    /* Ensure header buttons are visible and styled */
    header button,
    [data-testid="stHeader"] button,
    button[data-testid="baseButton-header"] {
        visibility: visible !important;
        display: inline-block !important;
        background-color: transparent !important;
        border: 1px solid #565869 !important;
        color: #ececf1 !important;
        border-radius: 4px;
        padding: 0.4rem 0.6rem;
        cursor: pointer;
    }
    
    header button:hover,
    [data-testid="stHeader"] button:hover {
        background-color: #343541 !important;
    }
    
    /* Ensure MainMenu is accessible */
    #MainMenu {
        visibility: visible !important;
    }
    
    /* Main app background */
    .stApp {
        background-color: #343541 !important;
    }
    
    /* Main container styling */
    .main .block-container {
        padding-top: 4rem;
        padding-bottom: 6rem;
        padding-left: 1rem;
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* Add space for the menu button */
    @media (min-width: 768px) {
        .main .block-container {
            padding-left: 2rem;
        }
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #202123 !important;
        z-index: 1000 !important;
    }
    
    /* Ensure sidebar is visible when expanded */
    section[data-testid="stSidebar"][aria-expanded="true"],
    section[data-testid="stSidebar"]:not([aria-expanded="false"]) {
        display: flex !important;
        visibility: visible !important;
    }
    
    section[data-testid="stSidebar"] > div {
        background-color: #202123 !important;
        padding-top: 1rem;
    }
    
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #ececf1;
    }
    
    /* Sidebar buttons */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: transparent;
        color: #ececf1;
        border: 1px solid #565869;
        border-radius: 6px;
        padding: 0.5rem;
        width: 100%;
        text-align: left;
        margin-bottom: 0.25rem;
        transition: background-color 0.2s;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #343541;
        border-color: #565869;
    }
    
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background-color: #343541;
        border-color: #565869;
    }
    
    /* Chat message styling */
    .stChatMessage {
        padding: 1.5rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stChatMessage:last-child {
        border-bottom: none;
    }
    
    /* User message styling */
    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"] {
        background-color: #5436da;
    }
    
    /* Assistant message styling */
    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] {
        background-color: #10a37f;
    }
    
    /* Chat input styling */
    [data-testid="stChatInput"] {
        background-color: #40414f;
        border-radius: 12px;
        border: 1px solid #565869;
    }
    
    [data-testid="stChatInput"] textarea {
        background-color: #40414f !important;
        color: #ececf1 !important;
    }
    
    [data-testid="stChatInput"] button {
        background-color: #10a37f !important;
    }
    
    [data-testid="stChatInput"] button:hover {
        background-color: #0d8f6e !important;
    }
    
    /* Markdown content styling */
    .stMarkdown {
        color: #ececf1;
    }
    
    .stMarkdown p {
        color: #ececf1;
        line-height: 1.75;
    }
    
    .stMarkdown code {
        background-color: #40414f;
        color: #ececf1;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
    }
    
    /* Spinner styling */
    .stSpinner > div {
        border-color: #10a37f transparent transparent transparent;
    }
    
    /* Error message styling */
    .stAlert {
        background-color: #40414f;
        border-left: 4px solid #ef4444;
    }
    
    /* Welcome message styling */
    h1 {
        color: #ececf1 !important;
    }
    
    h2, h3 {
        color: #ececf1 !important;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #202123;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #565869;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #6e6f7f;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Centralized LLM API Client Implementation
# ----------------------------------------------------------------------
# This section implements a client that wraps the centralized LLM API (api.ai88n.com)
# to mimic the OpenAI SDK interface. This allows the rest of the code to use
# the same API calls regardless of which provider is being used.
#
# Architecture:
# - CentralizedLLMClient: Main client class that holds API token and base URL
# - _Chat: Wrapper class that provides the 'chat' attribute
# - _Completions: Wrapper class that provides the 'completions' attribute
# - MockResponse/MockChoice/MockMessage: Classes that mimic OpenAI response structure

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

# ----------------------------------------------------------------------
# Model Configuration
# ----------------------------------------------------------------------
# Defines the available LLM models organized by provider.
# These models are accessible through the centralized API.
# Users can select from these models in the sidebar UI.

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

# ----------------------------------------------------------------------
# API Client Initialization Functions
# ----------------------------------------------------------------------
# These functions handle API client creation with proper error handling
# and support for both environment variables and Streamlit secrets.

def get_centralized_client():
    """
    Get centralized LLM API client with automatic credential detection.
    
    This function attempts to retrieve the API token in the following order:
    1. Environment variable (API_TOKEN) - preferred for local development
    2. Streamlit secrets (API_TOKEN) - used for Streamlit Cloud deployment
    
    If no token is found, displays setup instructions and stops the app.
    
    Returns:
        CentralizedLLMClient: Initialized client instance, or None if token not found
    
    Side Effects:
        - May display error messages and setup instructions in the UI
        - Calls st.stop() if token is not found, halting app execution
    """
    # Priority 1: Try to get API token from environment variable
    # This is the most reliable method for local development
    # Environment variables persist across terminal sessions (if set in shell config)
    api_token = os.getenv("API_TOKEN")
    
    # Priority 2: Fall back to Streamlit secrets if environment variable is not set
    # Streamlit secrets are stored in .streamlit/secrets.toml (local) or cloud secrets (deployed)
    # This method is preferred for Streamlit Cloud deployments
    if not api_token:
        api_token = _get_api_token_from_secrets()
    
    # If no API token found from either source, show instructions and stop execution
    # This prevents the app from running without proper authentication
    if not api_token:
        _show_api_token_setup_instructions()
        st.stop()  # Stop Streamlit execution - app cannot continue without API token
        return None
    
    # Create and return the initialized client
    return CentralizedLLMClient(api_token=api_token)

def get_deepseek_client():
    """
    Legacy function for backward compatibility.
    
    This function was originally for DeepSeek API but now uses the centralized API.
    It's kept to maintain compatibility with existing code that calls get_deepseek_client().
    
    Returns:
        CentralizedLLMClient: Same as get_centralized_client()
    """
    return get_centralized_client()

def _get_api_token_from_secrets():
    """
    Safely retrieve API token from Streamlit secrets.
    
    This function handles cases where secrets.toml doesn't exist or is inaccessible.
    It never raises exceptions, returning None instead if secrets are unavailable.
    
    Returns:
        str: API token if found in secrets, None otherwise
    """
    try:
        api_token = st.secrets.get("API_TOKEN", None)
        return api_token if api_token else None
    except Exception:
        return None

def _show_api_token_setup_instructions():
    """
    Display user-friendly instructions for setting up the API token.
    
    Shows error message and detailed setup instructions for both:
    - Local development (environment variables)
    - Streamlit Cloud deployment (secrets.toml)
    
    Side Effects:
        - Displays error and info messages in the Streamlit UI
    """
    st.error("⚠️ API_TOKEN is not set.")
    st.info("""
    **To set the API token, choose one of the following methods:**
    
    1. **Environment Variable (Recommended for local development):**
       ```bash
       # Windows PowerShell
       $env:API_TOKEN="your_api_token_here"
       
       # Windows CMD
       set API_TOKEN=your_api_token_here
       
       # Linux/Mac
       export API_TOKEN=your_api_token_here
       ```
       Then restart your Streamlit app.
    
    2. **Streamlit Secrets (For Streamlit Cloud deployment):**
       Create a `.streamlit/secrets.toml` file in your project directory with:
       ```toml
       API_TOKEN = "your_api_token_here"
       ```
       See `.streamlit/secrets.toml.example` for a template.
    """)

def _get_api_key_from_secrets():
    """
    Safely try to get API key from Streamlit secrets. 
    Returns None if not available or if secrets.toml doesn't exist.
    This function is designed to never raise exceptions.
    IMPORTANT: This function should only be called if environment variable is not set.
    """
    # Use a single comprehensive try-except to catch ANY possible error
    # This includes errors from Streamlit's internal secrets checking
    try:
        # IMPORTANT: Simply accessing st.secrets might trigger Streamlit to check for secrets.toml
        # So we wrap everything in one big try-except block
        api_key = st.secrets.get("DEEPSEEK_API_KEY", None)
        return api_key if api_key else None
    except (FileNotFoundError, AttributeError, KeyError, RuntimeError, OSError, Exception):
        # Any error means secrets are not available - this is expected and fine
        # The app will use environment variables instead
        # We silently return None - no error is raised
        return None

def _show_api_key_setup_instructions():
    """Display instructions for setting up the API key."""
    st.error("⚠️ DEEPSEEK_API_KEY is not set.")
    st.info("""
    **To set the API key, choose one of the following methods:**
    
    1. **Environment Variable (Recommended for local development):**
       ```bash
       # Windows PowerShell
       $env:DEEPSEEK_API_KEY="your_api_key_here"
       
       # Windows CMD
       set DEEPSEEK_API_KEY=your_api_key_here
       
       # Linux/Mac
       export DEEPSEEK_API_KEY=your_api_key_here
       ```
       Then restart your Streamlit app.
    
    2. **Streamlit Secrets (For Streamlit Cloud deployment):**
       Create a `.streamlit/secrets.toml` file in your project directory with:
       ```toml
       DEEPSEEK_API_KEY = "your_api_key_here"
       ```
       See `.streamlit/secrets.toml.example` for a template.
    """)

# ----------------------------------------------------------------------
# Session State Initialization
# ----------------------------------------------------------------------
# Streamlit's session_state persists data across reruns within the same session.
# This section initializes all required state variables with default values.
# These variables maintain:
# - Multiple conversation sessions (users can have multiple chats)
# - Current session tracking
# - Generated SRS documents
# - Selected LLM model
# - UI state (model selector visibility, warnings)

# Session Management State
# sessions: Dictionary mapping session_id -> session data (messages, title, model, created_at)
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
# current_session_id: UUID string identifying the currently active session
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
# session_counter: Incremental counter for generating default session titles
if "session_counter" not in st.session_state:
    st.session_state.session_counter = 0

# SRS Generation State
# generated_srs: Markdown content of the generated IEEE 830 SRS document
if "generated_srs" not in st.session_state:
    st.session_state.generated_srs = None
# srs_generation_error: Error message if SRS generation failed
if "srs_generation_error" not in st.session_state:
    st.session_state.srs_generation_error = None

# Model Selection State
# selected_model: Currently selected LLM model identifier (e.g., "deepseek-chat")
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "deepseek-chat"  # Default model
# model_change_warning: Warning message to display if user tries to change model after session starts
if "model_change_warning" not in st.session_state:
    st.session_state.model_change_warning = None
# show_model_selector: Boolean flag to control visibility of model selection dropdown
if "show_model_selector" not in st.session_state:
    st.session_state.show_model_selector = False

# Memory Management
# memory: ShortTermMemory instance that manages chat history, token counting, and context window
# This is separate from session storage - it's the active working memory for the current session
if "memory" not in st.session_state:
    st.session_state.memory = ShortTermMemory()

# Long-Term Memory
# ltm: LongTermMemory instance that provides persistent vector storage for requirements
# Uses ChromaDB to store requirements with embeddings for semantic search capabilities
if "ltm" not in st.session_state:
    st.session_state.ltm = LongTermMemory()

# Pending Requirement State
# Stores requirement data detected from user input until the assistant response confirms it
if "pending_requirement" not in st.session_state:
    st.session_state.pending_requirement = None

# ----------------------------------------------------------------------
# Session Management Functions
# ----------------------------------------------------------------------
# These functions handle creation, retrieval, and management of conversation sessions.
# Each session maintains its own chat history, model selection, and metadata.

def create_new_session():
    """
    Create a new conversation session with unique ID.
    
    This function:
    1. Saves the current session's messages and model to persistent storage
    2. Generates a new unique session ID using UUID
    3. Creates a new session entry with empty messages
    4. Resets the memory for the new session
    5. Clears any generated SRS documents
    
    The new session uses the currently selected model, which can be changed
    before the first message is sent. After the first message, the model is locked.
    
    Returns:
        str: The newly created session ID (UUID string)
    
    Side Effects:
        - Updates st.session_state.sessions with new session
        - Sets st.session_state.current_session_id to new session
        - Resets st.session_state.memory to empty ShortTermMemory
        - Clears SRS generation state
    """
    # Generate unique session identifier using UUID
    session_id = str(uuid.uuid4())
    
    # Save current session's data before creating new one
    # This ensures no data is lost when switching between sessions
    if st.session_state.current_session_id and st.session_state.current_session_id in st.session_state.sessions:
        # Retrieve previous session and save current memory state
        prev_session = st.session_state.sessions[st.session_state.current_session_id]
        prev_session["messages"] = st.session_state.memory.get_messages()  # Save chat history
        prev_session["model"] = st.session_state.selected_model  # Save model used in this session
        st.session_state.sessions[st.session_state.current_session_id] = prev_session
    
    # Create new session entry with initial state
    st.session_state.sessions[session_id] = {
        "id": session_id,                                    # Unique identifier
        "messages": [],                                      # Empty chat history
        "title": f"New Chat {st.session_state.session_counter + 1}",  # Default title (updated from first message)
        "created_at": datetime.now(),                        # Timestamp for sorting
        "model": st.session_state.selected_model             # Model selected for this session
    }
    st.session_state.session_counter += 1
    st.session_state.current_session_id = session_id
    
    # Reset memory for new session (fresh start)
    st.session_state.memory = ShortTermMemory()
    
    # Clear generated SRS when creating new session (SRS is session-specific)
    st.session_state.generated_srs = None
    st.session_state.srs_generation_error = None
    return session_id

def get_current_session():
    """
    Get the currently active session, creating one if none exists.
    
    This function ensures there's always an active session. If no session exists
    (e.g., on first app load), it automatically creates a new one.
    
    Returns:
        dict: Session dictionary containing:
            - id: Session UUID
            - messages: List of chat messages
            - title: Session title (default or from first message)
            - created_at: Creation timestamp
            - model: Model used in this session
    """
    # Auto-create session if none exists (handles first-time app load)
    if st.session_state.current_session_id is None:
        create_new_session()
    
    # Retrieve and return the current session data
    session = st.session_state.sessions[st.session_state.current_session_id]
    return session

def update_session_title(session_id, first_message):
    """
    Update session title from the first user message.
    
    When a user sends their first message, this function extracts the first
    50 characters to use as a more descriptive session title, replacing
    the default "New Chat N" title.
    
    Args:
        session_id: UUID string identifying the session to update
        first_message: The first user message content (used to generate title)
    
    Side Effects:
        - Updates the session title in st.session_state.sessions if:
          - Session exists
          - Current title is still the default "New Chat" format
    """
    if session_id in st.session_state.sessions:
        # Only update if title is still the default (hasn't been manually changed)
        if st.session_state.sessions[session_id]["title"].startswith("New Chat"):
            # Extract first 50 characters as title
            title = first_message[:50]
            if len(first_message) > 50:
                title += "..."  # Add ellipsis if message was truncated
            st.session_state.sessions[session_id]["title"] = title

# ----------------------------------------------------------------------
# SRS Generation Function
# ----------------------------------------------------------------------
# This function generates IEEE 830 Software Requirements Specification documents
# by analyzing the assistant's responses from the conversation and formatting
# them according to the IEEE 830 standard structure.

def generate_ieee830_srs_from_conversation(client, assistant_messages):
    """
    Generate IEEE 830 SRS document from conversation history using LLM API.
    
    This function takes all assistant messages from a conversation and uses an LLM
    to analyze and format them into a complete IEEE 830 Software Requirements
    Specification document. The LLM extracts requirements, organizes them by category,
    and structures them according to IEEE 830 standards.
    
    Process:
    1. Combines all assistant messages into a formatted context string
    2. Creates a system prompt instructing the LLM to generate IEEE 830 SRS
    3. Sends the context and instructions to the LLM API
    4. Returns the generated Markdown document
    
    Args:
        client: Initialized API client (CentralizedLLMClient or OpenAI-compatible)
        assistant_messages: List of assistant message content strings from the conversation
    
    Returns:
        str: Complete IEEE 830 SRS document in Markdown format, including:
            - Introduction (Purpose, Scope, Definitions, References, Overview)
            - Overall Description (Product Perspective, Functions, User Characteristics)
            - Specific Requirements (Functional, Non-Functional, Interface, Performance)
    
    Note:
        Only assistant messages are used (not user messages) to focus on the
        requirements that were identified and analyzed by the AI.
    """
    # Handle empty conversation case - return template with instructions
    if not assistant_messages:
        return "# Software Requirements Specification (IEEE 830)\n\n## 1. Introduction\n\nNo requirements have been captured yet. Please start a conversation with the AI assistant to analyze and capture requirements."
    
    # Combine all assistant messages into a single formatted context string
    # Each message is numbered and separated by dividers for clarity
    # This context is sent to the LLM for analysis and formatting
    conversation_context = "\n\n---\n\n".join([
        f"**Assistant Response {i+1}:**\n{msg}" 
        for i, msg in enumerate(assistant_messages)
    ])
    
    # Create system prompt that instructs the LLM on how to generate the SRS
    # The prompt specifies the IEEE 830 structure and what information to extract
    system_prompt = """You are a professional requirements engineer. Your task is to analyze the conversation history (specifically the assistant's responses) and generate a complete Software Requirements Specification (SRS) document following the IEEE 830 standard format.

The IEEE 830 SRS structure should include:
1. Introduction
   1.1 Purpose
   1.2 Scope
   1.3 Definitions, Acronyms, and Abbreviations
   1.4 References
   1.5 Overview
2. Overall Description
   2.1 Product Perspective
   2.2 Product Functions
   2.3 User Characteristics
   2.4 Constraints
   2.5 Assumptions and Dependencies
3. Specific Requirements
   3.1 Functional Requirements
   3.2 Non-Functional Requirements
   3.3 Interface Requirements
   3.4 Performance Requirements
   3.5 Design Constraints

Extract all requirements mentioned in the assistant responses. For each requirement, include:
- Requirement ID (REQ-XXX format if available)
- Requirement description
- Priority (if mentioned)
- Dependencies (if mentioned)
- Acceptance criteria (if mentioned)

Format the output as a well-structured Markdown document following IEEE 830 standards. Be comprehensive and organized."""

    # Create user prompt that includes the conversation context and specific instructions
    # The conversation_context variable (created above) is embedded here using f-string formatting
    # This is where conversation_context is actually used - it's inserted into the prompt
    # that gets sent to the LLM API for SRS generation
    user_prompt = f"""Please analyze the following assistant responses from a requirements engineering conversation and generate a complete IEEE 830 SRS document in Markdown format.

**Conversation History (Assistant Responses Only):**

{conversation_context}

**Instructions:**
- Extract all requirements, functional and non-functional
- Organize them according to IEEE 830 SRS structure
- Include all requirement IDs (REQ-XXX) if present
- Include Volere fields (Goal, Context, Stakeholder) if mentioned
- Be comprehensive and well-structured
- Use proper Markdown formatting with headers, lists, and tables where appropriate

Generate the complete SRS document now:"""
    
    try:
        # Call the LLM API to generate the SRS document
        # Uses the currently selected model (can be DeepSeek, GPT, Claude, or Grok)
        # Note: SRS generation can take longer due to large output, so we use extended timeout
        response = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=[
                {"role": "system", "content": system_prompt},  # Instructions for SRS structure
                {"role": "user", "content": user_prompt}       # Conversation context + formatting instructions
            ],
            temperature=0.3,   # Lower temperature for more consistent, structured output (less creative variation)
            max_tokens=12000,  # Allow for comprehensive SRS document (may need adjustment for very long documents)
            timeout=180        # Extended timeout (3 minutes) for large document generation
        )
        
        # Extract the generated SRS content from the API response
        srs_content = response.choices[0].message.content
        
        # Ensure the document starts with a proper Markdown header
        # Some models may omit the main header, so we add it if missing
        if not srs_content.startswith("#"):
            srs_content = "# Software Requirements Specification (IEEE 830)\n\n" + srs_content
        
        return srs_content
    except Exception as e:
        # Re-raise with more context about what operation failed
        raise Exception(f"Failed to generate SRS from API: {str(e)}")

# ----------------------------------------------------------------------
# Sidebar UI - Session and Model Management
# ----------------------------------------------------------------------
# The sidebar provides:
# 1. Model selection (with lock mechanism after session starts)
# 2. Session management (create new, switch between sessions)
# 3. SRS export functionality
# 4. Context summarization
# 5. Chat history display
#
# The sidebar uses a dark theme matching the main chat interface.

with st.sidebar:
    st.markdown("""
    <div style='padding: 1rem 0 1.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1rem;'>
        <h2 style='color: #ececf1; margin: 0; font-size: 1.5rem;'>📋 UESTC-MBSE Requirement Assistant</h2>
        <p style='color: #8e8ea0; margin: 0.25rem 0 0 0; font-size: 0.85rem;'>AI Requirements Analyst</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ----------------------------------------------------------------------
    # Model Selection UI
    # ----------------------------------------------------------------------
    # This section allows users to select which LLM model to use for the conversation.
    # Once a session has messages, the model is locked to maintain consistency.
    
    st.markdown("<div style='margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Model Selection</h3></div>", unsafe_allow_html=True)
    
    # Determine if model can be changed
    # Model is locked once the session has any messages (user or assistant)
    # This ensures conversation consistency - all messages in a session use the same model
    current_session = get_current_session()
    has_messages = len(current_session.get("messages", [])) > 0 or st.session_state.memory.get_history_length() > 0
    model_locked = has_messages
    
    # Display current model
    current_model_info = next((m for m in ALL_MODELS if m["id"] == st.session_state.selected_model), None)
    current_provider = current_model_info["provider"] if current_model_info else "Unknown"
    current_model_name = st.session_state.selected_model
    
    st.markdown(f"""
    <div style='padding: 0.75rem; background-color: #343541; border-radius: 6px; border: 1px solid #565869; margin-bottom: 0.5rem;'>
        <div style='color: #8e8ea0; font-size: 0.75rem; margin-bottom: 0.25rem;'>{current_provider}</div>
        <div style='color: #ececf1; font-size: 0.9rem; font-weight: 500;'>{current_model_name}</div>
        {"<div style='color: #8e8ea0; font-size: 0.7rem; margin-top: 0.25rem;'>🔒 Model locked (session started)</div>" if model_locked else ""}
    </div>
    """, unsafe_allow_html=True)
    
    # Model selector UI - Different behavior based on lock state
    if model_locked:
        # Session has messages - model is locked
        # Show button that displays warning when clicked (model cannot be changed)
        if st.button("🔄 Change Model", use_container_width=True, type="secondary", help="Click to change model (warning: model cannot be changed after session starts)"):
            st.session_state.model_change_warning = "⚠️ Model cannot be changed after the session has started. Please create a new chat to use a different model."
            st.rerun()
    else:
        # Session is empty - model can be changed
        # Show button to open model selector dropdown
        if st.button("🤖 Select Model", use_container_width=True, type="secondary", help="Click to select a different model"):
            st.session_state.show_model_selector = not st.session_state.show_model_selector
            st.rerun()
        
        # Display model selection dropdown when button is clicked
        # The dropdown shows all available models grouped by provider
        if st.session_state.show_model_selector:
            # Build model options list with provider labels for better UX
            # Each model is displayed as "model-name (Provider)" for clarity
            model_options = []        # List of model IDs (for API calls)
            model_display_names = []  # List of display names (for UI)
            
            for provider, models in AVAILABLE_MODELS.items():
                for model in models:
                    model_options.append(model)  # Store model ID
                    display_name = f"{model} ({provider})"  # Create display name with provider
                    model_display_names.append(display_name)
            
            # Find the index of the currently selected model in the options list
            # This ensures the selectbox shows the current selection
            try:
                selected_index = model_options.index(st.session_state.selected_model)
            except ValueError:
                # If current model not found in list, default to first option
                selected_index = 0
            
            # Display the model selection dropdown
            # Streamlit's selectbox automatically triggers rerun when value changes
            selected_display = st.selectbox(
                "Choose a model:",
                options=model_display_names,
                index=selected_index,
                key="model_selector_dropdown",
                help="Select the LLM model to use for this session"
            )
            
            # Extract the actual model ID from the display name
            # The display name format is "model-name (Provider)", we need just "model-name"
            selected_model_id = model_options[model_display_names.index(selected_display)]
            
            # Check if user selected a different model
            # This condition is true when selectbox value changes (triggers rerun)
            if selected_model_id != st.session_state.selected_model:
                # Update the selected model in session state
                st.session_state.selected_model = selected_model_id
                # Also update the current session's model field (for persistence)
                if st.session_state.current_session_id:
                    current_session["model"] = selected_model_id
                    st.session_state.sessions[st.session_state.current_session_id] = current_session
                # Automatically close the selector after selection
                st.session_state.show_model_selector = False
                st.rerun()
            
            # Provide a Cancel button to close the selector without changing model
            if st.button("Cancel", use_container_width=True, type="secondary", key="model_selector_cancel"):
                st.session_state.show_model_selector = False
                st.rerun()
    
    # ----------------------------------------------------------------------
    # Long-Term Memory Auto-Save Toggle
    # ----------------------------------------------------------------------
    # This toggle controls whether requirements are automatically saved to
    # the long-term memory (ChromaDB) when they are extracted. When enabled,
    # requirements are persisted with embeddings for semantic search.
    
    st.markdown("<div style='margin-top: 1.5rem; margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Memory Settings</h3></div>", unsafe_allow_html=True)
    
    # Initialize LTM auto-save setting (default: True)
    if "ltm_auto_save" not in st.session_state:
        st.session_state.ltm_auto_save = True
    
    # Toggle for auto-saving requirements to long-term memory
    ltm_auto_save = st.toggle(
        "💾 Persist to Long-Term Memory",
        value=st.session_state.ltm_auto_save,
        help="When enabled, requirements are automatically saved to long-term memory (ChromaDB) for semantic search. This allows you to search and retrieve requirements across sessions.",
        key="ltm_auto_save_toggle"
    )
    
    # Update session state when toggle changes
    if ltm_auto_save != st.session_state.ltm_auto_save:
        st.session_state.ltm_auto_save = ltm_auto_save
        if ltm_auto_save:
            st.success("✅ Requirements will be automatically saved to long-term memory.")
        else:
            st.info("ℹ️ Requirements will not be automatically saved to long-term memory.")
        st.rerun()
    
    # ----------------------------------------------------------------------
    # Model Change Warning Display
    # ----------------------------------------------------------------------
    # Shows a temporary warning message if user tries to change model after session starts.
    # The warning auto-dismisses after 3 seconds using JavaScript.
    
    if st.session_state.model_change_warning:
        warning_container = st.container()
        with warning_container:
            st.warning(st.session_state.model_change_warning)
        
        # Auto-dismiss after 3 seconds using JavaScript
        st.markdown("""
        <script>
        setTimeout(function() {
            // Find and hide the warning element
            const warningElements = window.parent.document.querySelectorAll('[data-testid="stAlert"]');
            warningElements.forEach(function(el) {
                const text = el.textContent || el.innerText;
                if (text.includes('Model cannot be changed')) {
                    el.style.display = 'none';
                }
            });
        }, 3000);
        </script>
        """, unsafe_allow_html=True)
        
        # Clear warning state after displaying (will be cleared on next interaction)
        # Use a flag to track if we've shown it
        if "warning_shown" not in st.session_state:
            st.session_state.warning_shown = True
        else:
            # Clear on next rerun (after user interaction)
            st.session_state.model_change_warning = None
            st.session_state.warning_shown = None
    
    # ----------------------------------------------------------------------
    # Long-Term Memory Search (RAG)
    # ----------------------------------------------------------------------
    # This section allows users to search past requirements stored in long-term memory
    # and inject relevant requirements into the AI context for better continuity.
    
    st.markdown("<div style='margin-top: 1.5rem; margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Search Past Requirements</h3></div>", unsafe_allow_html=True)
    
    # Initialize search results storage
    if "rag_search_results" not in st.session_state:
        st.session_state.rag_search_results = []
    if "inject_requirement_context" not in st.session_state:
        st.session_state.inject_requirement_context = None
    
    # Search input field
    search_query = st.text_input(
        "🔍 Search past requirements",
        key="rag_search",
        placeholder="Type to search requirements...",
        help="Search for past requirements using semantic search. Results are ranked by relevance."
    )
    
    # Perform search when query is entered
    if search_query and search_query.strip():
        try:
            # Search long-term memory for similar requirements
            results = st.session_state.ltm.search(search_query.strip(), top_k=3)
            st.session_state.rag_search_results = results
            
            # Display search results
            if results:
                st.markdown("<div style='margin-top: 0.5rem; margin-bottom: 0.5rem;'><strong style='color: #ececf1; font-size: 0.85rem;'>Search Results:</strong></div>", unsafe_allow_html=True)
                
                for idx, r in enumerate(results):
                    req_id = r.get('id', 'Unknown')
                    req_text = r.get('text', '')
                    req_project = r.get('metadata', {}).get('project', 'unknown')
                    req_score = r.get('score', 0.0)
                    
                    # Display each result with ID, project, and text
                    st.markdown(f"""
                    <div style='
                        padding: 0.75rem;
                        background-color: #343541;
                        border-radius: 6px;
                        border: 1px solid #565869;
                        margin-bottom: 0.5rem;
                    '>
                        <div style='color: #ececf1; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem;'>
                            <strong>{req_id}</strong> <span style='color: #8e8ea0; font-size: 0.75rem; font-weight: normal;'>(from {req_project})</span>
                        </div>
                        <div style='color: #8e8ea0; font-size: 0.85rem; line-height: 1.4;'>{req_text}</div>
                        <div style='color: #565869; font-size: 0.7rem; margin-top: 0.25rem;'>Relevance: {req_score:.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Button to inject top result into AI context
                if st.button("💉 Inject into AI context", use_container_width=True, type="secondary", help="Add the top search result to the next AI prompt for better context"):
                    # Store the top result to inject into the next API call
                    top_result = results[0]
                    st.session_state.inject_requirement_context = {
                        "id": top_result.get('id', ''),
                        "text": top_result.get('text', ''),
                        "project": top_result.get('metadata', {}).get('project', 'unknown'),
                        "volere": top_result.get('metadata', {}).get('volere', {})
                    }
                    st.success(f"✅ {top_result.get('id', 'Requirement')} will be included in the next AI response.")
                    st.rerun()
            else:
                st.info("ℹ️ No matching requirements found. Try different search terms.")
                st.session_state.rag_search_results = []
        except Exception as e:
            st.error(f"❌ Error searching requirements: {str(e)}")
            st.session_state.rag_search_results = []
    else:
        # Clear results when search is empty
        st.session_state.rag_search_results = []
    
    # Show currently injected requirement if any
    if st.session_state.inject_requirement_context:
        injected = st.session_state.inject_requirement_context
        st.markdown(f"""
        <div style='
            padding: 0.75rem;
            background-color: #2d5016;
            border-radius: 6px;
            border: 1px solid #4a7c2a;
            margin-top: 0.5rem;
        '>
            <div style='color: #8e8ea0; font-size: 0.75rem; margin-bottom: 0.25rem;'>Injected into next prompt:</div>
            <div style='color: #ececf1; font-weight: 600; font-size: 0.9rem;'>{injected.get('id', 'Unknown')}</div>
            <div style='color: #8e8ea0; font-size: 0.8rem; margin-top: 0.25rem;'>{injected.get('text', '')[:100]}...</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Button to clear injected context
        if st.button("🗑️ Clear injected context", use_container_width=True, type="secondary", key="clear_injected_context"):
            st.session_state.inject_requirement_context = None
            st.rerun()
    
    # Divider between model selection and session management
    st.markdown("<div style='margin: 1rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1);'></div>", unsafe_allow_html=True)
    
    # ----------------------------------------------------------------------
    # Session Management UI
    # ----------------------------------------------------------------------
    # This section provides controls for creating and managing conversation sessions.
    
    # New Chat button - Creates a fresh conversation session
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        create_new_session()
        st.rerun()
    
    # Chat History section - Lists all existing sessions
    st.markdown("<div style='margin: 1.5rem 0 0.5rem 0;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Chat History</h3></div>", unsafe_allow_html=True)
    
    # Ensure at least one session exists (create default session on first load)
    if len(st.session_state.sessions) == 0:
        create_new_session()
    
    # Retrieve all sessions and sort by creation time (newest first)
    # This provides a chronological list in the sidebar
    sessions_list = list(st.session_state.sessions.values())
    sessions_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Display each session as a clickable button
    # Active session is highlighted with primary button style
    session_container = st.container()
    with session_container:
        for session in sessions_list:
            session_id = session["id"]
            is_active = st.session_state.current_session_id == session_id
            
            # Create a button for each session with its title
            button_label = session["title"]
            button_type = "primary" if is_active else "secondary"
            if st.button(
                button_label,
                key=f"session_{session_id}",
                use_container_width=True,
                type=button_type
            ):
                # Save current session's state before switching
                # This ensures no data is lost when switching between sessions
                if st.session_state.current_session_id and st.session_state.current_session_id in st.session_state.sessions:
                    prev_session = st.session_state.sessions[st.session_state.current_session_id]
                    prev_session["messages"] = st.session_state.memory.get_messages()  # Save chat history
                    st.session_state.sessions[st.session_state.current_session_id] = prev_session
                
                # Switch to the selected session
                st.session_state.current_session_id = session_id
                
                # Load the selected session's messages into memory
                # This restores the conversation history for display and continuation
                selected_session = st.session_state.sessions[session_id]
                st.session_state.memory.load_messages(selected_session["messages"], reset=True)
                
                # Restore the model that was used in this session
                # Each session remembers which model it was using
                if "model" in selected_session:
                    st.session_state.selected_model = selected_session["model"]
                
                # Clear generated SRS when switching sessions
                # SRS documents are session-specific and shouldn't persist across switches
                st.session_state.generated_srs = None
                st.session_state.srs_generation_error = None
                st.rerun()
    
    # Divider before action buttons (Export SRS, Summarize, Clear)
    st.markdown("<div style='margin-top: 2rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.1);'>", unsafe_allow_html=True)
    
    # ----------------------------------------------------------------------
    # SRS Export Functionality
    # ----------------------------------------------------------------------
    # Allows users to generate and download IEEE 830 SRS documents from conversations.
    # The button is always visible, but only shows status messages after clicking.
    
    if st.button("📄 Export SRS (Markdown)", use_container_width=True, type="secondary", help="Generate and download IEEE 830 SRS document from conversation"):
        # Extract only assistant messages from conversation history
        # User messages are excluded - only the AI's analysis is used for SRS generation
        all_messages = st.session_state.memory.get_messages(include_system=False)
        assistant_messages = [msg["content"] for msg in all_messages if msg.get("role") == "assistant"]
        
        # Validate that we have assistant messages to work with
        if not assistant_messages:
            st.warning("⚠️ No assistant responses found in the conversation. Please start a conversation and receive responses from the AI before exporting SRS.")
            st.session_state.generated_srs = None
            st.session_state.srs_generation_error = "No assistant messages found"
        else:
            # Generate SRS document using LLM API
            # The API analyzes assistant messages and formats them into IEEE 830 structure
            try:
                client = get_deepseek_client()
                if client:
                    with st.spinner("🔄 Generating IEEE 830 SRS document from conversation..."):
                        # Call the SRS generation function with assistant messages
                        srs_content = generate_ieee830_srs_from_conversation(client, assistant_messages)
                        # Store generated SRS for download
                        st.session_state.generated_srs = srs_content
                        st.session_state.srs_generation_error = None
                        st.success("✅ SRS document generated successfully! Use the download button below to save it.")
                else:
                    st.error("❌ Unable to connect to API. Please check your API key configuration.")
                    st.session_state.generated_srs = None
                    st.session_state.srs_generation_error = "API connection failed"
            except Exception as e:
                error_msg = f"❌ Error generating SRS: {str(e)}"
                st.error(error_msg)
                st.session_state.generated_srs = None
                st.session_state.srs_generation_error = str(e)
    
    # Display download button if SRS has been successfully generated
    if st.session_state.generated_srs:
        st.download_button(
            label="💾 Download SRS Document",
            data=st.session_state.generated_srs,
            file_name="srs_ieee830.md",
            mime="text/markdown",
            use_container_width=True,
            type="primary",
            help="Download the generated IEEE 830 SRS document"
        )
    elif st.session_state.srs_generation_error:
        # Show error state - allow retry
        st.info("ℹ️ Click the 'Export SRS (Markdown)' button above to generate the SRS document.")
    
    # ----------------------------------------------------------------------
    # Context Summarization Functionality
    # ----------------------------------------------------------------------
    # Allows users to summarize old conversation messages to reduce token usage.
    # This is useful for very long conversations that approach token limits.
    # The button is always visible, but only shows status messages after clicking.
    
    if st.button("📝 Summarize Context", use_container_width=True, type="secondary", help="Summarize old messages to reduce token usage"):
        # Check conditions after button click
        history_length = st.session_state.memory.get_history_length()
        has_session = st.session_state.current_session_id is not None
        
        # Check if already summarized by checking system messages
        all_messages_with_system = st.session_state.memory.get_messages(include_system=True)
        has_summary = any(
            msg.get("role") == "system" and msg.get("content", "").startswith("SUMMARY:") 
            for msg in all_messages_with_system
        )
        
        if not has_session:
            st.warning("⚠️ No active session found. Please start a conversation first.")
        elif history_length <= 10:
            st.warning(f"⚠️ Summarization requires more than 10 messages in the conversation history. Currently, you have {history_length} message(s). Please continue the conversation to enable this feature.")
        elif has_summary:
            st.info("ℹ️ This conversation has already been summarized. You can continue chatting, and when you have more than 10 new messages, you can summarize again.")
        else:
            # Conditions met, perform summarization
            try:
                client = get_deepseek_client()
                if client:
                    with st.spinner("Summarizing conversation..."):
                        success = st.session_state.memory.summarize_old_messages(client, model=st.session_state.selected_model)
                        if success:
                            # Update session messages from memory (exclude system messages for display)
                            current_session = get_current_session()
                            current_session["messages"] = st.session_state.memory.get_messages(include_system=False)
                            st.session_state.sessions[st.session_state.current_session_id] = current_session
                            st.success("✅ Context summarized successfully! Old messages have been condensed.")
                            st.rerun()
                        else:
                            # Check why it failed
                            if has_summary:
                                st.info("ℹ️ This conversation has already been summarized. Continue chatting to add more messages before summarizing again.")
                            elif history_length <= 10:
                                st.warning(f"⚠️ Summarization requires more than 10 messages. Currently: {history_length} message(s).")
                            else:
                                st.error("❌ Failed to summarize context. Please try again or check your API connection.")
                else:
                    st.error("❌ Unable to connect to API. Please check your API key configuration.")
            except Exception as e:
                st.error(f"❌ Error summarizing context: {str(e)}")
    
    # ----------------------------------------------------------------------
    # Clear Chat Functionality
    # ----------------------------------------------------------------------
    # Allows users to clear the current session's chat history while keeping the session.
    # This is different from creating a new session - it clears messages but keeps the session ID.
    
    # Only show clear button if session exists and has messages
    if st.session_state.current_session_id and len(get_current_session()["messages"]) > 0:
        if st.button("🗑️ Clear Current Chat", use_container_width=True, type="secondary"):
            # Clear messages from session storage
            if st.session_state.current_session_id in st.session_state.sessions:
                st.session_state.sessions[st.session_state.current_session_id]["messages"] = []
            # Clear memory (active chat history)
            st.session_state.memory.clear_chat_history()
            # Clear generated SRS when clearing chat (SRS is based on conversation)
            st.session_state.generated_srs = None
            st.session_state.srs_generation_error = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Sidebar Toggle Button
# ----------------------------------------------------------------------
# Custom JavaScript button in the top-left corner to toggle sidebar visibility.
# This ensures users can always access the sidebar even if it's collapsed.
# The button uses JavaScript to interact with Streamlit's sidebar DOM elements.

st.markdown("""
<div id="sidebarToggleContainer" style='position: fixed; top: 10px; left: 10px; z-index: 9999;'>
    <button id="sidebarToggleBtn" style='
        background-color: #202123;
        color: #ececf1;
        border: 1px solid #565869;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        cursor: pointer;
        font-size: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        transition: all 0.2s;
        font-weight: 500;
    '>
        <span style='font-size: 1.2rem;'>☰</span> <span>Menu</span>
    </button>
</div>

<script>
(function() {
    const btn = document.getElementById('sidebarToggleBtn');
    if (!btn) return;
    
    function findSidebarToggle() {
        // Try multiple selectors to find Streamlit's sidebar toggle button
        const selectors = [
            'button[data-testid="baseButton-header"]',
            '[data-testid="stHeader"] button',
            '[data-testid="stHeader"] button:first-child',
            'button[kind="header"]',
            '.stApp > header button',
            'header button:first-child'
        ];
        
        for (const selector of selectors) {
            const buttons = document.querySelectorAll(selector);
            for (const button of buttons) {
                if (button.offsetWidth > 0 && button.offsetHeight > 0) {
                    return button;
                }
            }
        }
        
        // Fallback: find any button in header area
        const header = document.querySelector('[data-testid="stHeader"]') || 
                       document.querySelector('header') ||
                       document.querySelector('.stApp > div:first-child');
        if (header) {
            const buttons = header.querySelectorAll('button');
            if (buttons.length > 0) {
                return buttons[0];
            }
        }
        
        return null;
    }
    
    function toggleSidebar() {
        console.log('Toggle sidebar clicked');
        
        // Strategy 1: Try to find and click Streamlit's native toggle button
        let toggleBtn = findSidebarToggle();
        if (toggleBtn) {
            console.log('Found native toggle button, clicking...');
            try {
                // Create a proper click event
                const clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    buttons: 1
                });
                toggleBtn.dispatchEvent(clickEvent);
                
                // Also try native click method
                if (typeof toggleBtn.click === 'function') {
                    toggleBtn.click();
                }
                
                // Give it a moment, then check if it worked
                setTimeout(function() {
                    const sidebar = document.querySelector('section[data-testid="stSidebar"]');
                    if (sidebar) {
                        const isExpanded = sidebar.getAttribute('aria-expanded') === 'true' || sidebar.offsetWidth > 100;
                        if (!isExpanded) {
                            console.log('Native click did not work, trying direct manipulation...');
                            expandSidebarDirectly();
                        }
                    }
                }, 200);
                return;
            } catch (e) {
                console.log('Error clicking native toggle:', e);
            }
        }
        
        // Strategy 2: Direct sidebar manipulation
        expandSidebarDirectly();
    }
    
    function expandSidebarDirectly() {
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) {
            console.log('Sidebar not found');
            return;
        }
        
        console.log('Expanding sidebar directly...');
        const currentState = sidebar.getAttribute('aria-expanded');
        const computedStyle = window.getComputedStyle(sidebar);
        const isVisible = computedStyle.display !== 'none' && sidebar.offsetWidth > 50;
        
        if (currentState !== 'true' || !isVisible) {
            // Force expand sidebar
            sidebar.setAttribute('aria-expanded', 'true');
            sidebar.style.setProperty('display', 'flex', 'important');
            sidebar.style.setProperty('visibility', 'visible', 'important');
            sidebar.style.setProperty('transform', 'translateX(0)', 'important');
            sidebar.style.setProperty('opacity', '1', 'important');
            
            // Ensure sidebar content is visible
            const sidebarContent = sidebar.querySelector('[data-testid="stSidebarContent"]');
            if (sidebarContent) {
                sidebarContent.style.setProperty('display', 'block', 'important');
                sidebarContent.style.setProperty('visibility', 'visible', 'important');
            }
            
            // Trigger resize events for Streamlit
            window.dispatchEvent(new Event('resize'));
            setTimeout(function() {
                window.dispatchEvent(new Event('resize'));
            }, 100);
            
            console.log('Sidebar expanded');
        }
    }
    
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        toggleSidebar();
    });
    
    btn.addEventListener('mouseenter', function() {
        this.style.backgroundColor = '#343541';
    });
    
    btn.addEventListener('mouseleave', function() {
        this.style.backgroundColor = '#202123';
    });
    
    // Initialize: Check sidebar state on load
    setTimeout(function() {
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            const isCollapsed = sidebar.getAttribute('aria-expanded') === 'false' || 
                               sidebar.offsetWidth < 50;
            console.log('Sidebar state on load:', isCollapsed ? 'collapsed' : 'expanded');
            
            // If sidebar is collapsed, ensure button is visible
            if (isCollapsed) {
                const btn = document.getElementById('sidebarToggleBtn');
                if (btn) {
                    btn.style.display = 'flex';
                }
            }
        }
    }, 500);
    
    // Retry finding elements after Streamlit finishes loading
    setTimeout(function() {
        // Re-initialize in case DOM changed
        const btn = document.getElementById('sidebarToggleBtn');
        if (btn && !btn.onclick) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                toggleSidebar();
            });
        }
    }, 1000);
})();
</script>

<style>
/* Ensure the toggle button is always visible and on top */
#sidebarToggleContainer {
    position: fixed !important;
    top: 10px !important;
    left: 10px !important;
    z-index: 9999 !important;
    pointer-events: auto !important;
}

#sidebarToggleBtn {
    position: relative !important;
    z-index: 10000 !important;
    pointer-events: auto !important;
}

#sidebarToggleBtn:hover {
    background-color: #343541 !important;
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}

/* Ensure sidebar is accessible */
section[data-testid="stSidebar"] {
    z-index: 1000 !important;
}

/* Make sure main content doesn't overlap the button on small screens */
@media (max-width: 768px) {
    .main .block-container {
        padding-top: 4rem;
    }
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Main Chat Interface
# ----------------------------------------------------------------------
# This section handles the main chat area where users interact with the AI.
# It includes:
# 1. Chat input field
# 2. Message display
# 3. AI response generation
# 4. Session synchronization

# Chat input field - placed at bottom for better UX (Streamlit handles positioning)
# Users type their requirements questions here
user_input = st.chat_input("Ask for requirement analysis...")

# Get the current active session
current_session = get_current_session()

# Synchronize memory with session storage on page load
# This handles the case where the page reloads: session data persists but memory is reset
# We restore the conversation history from session storage into memory
if current_session["messages"] and st.session_state.memory.get_history_length() == 0:
    st.session_state.memory.load_messages(current_session["messages"], reset=True)

# Handle user input when a message is submitted
if user_input:
    # Add user message to memory immediately (for display and context)
    st.session_state.memory.add_message("user", user_input)
    
    # Update session title from first user message
    # This replaces the default "New Chat N" title with something more descriptive
    if st.session_state.memory.get_history_length() == 1:
        update_session_title(st.session_state.current_session_id, user_input)

# Retrieve messages from memory for display
# Memory is the source of truth for the current session's conversation
messages = st.session_state.memory.get_messages()

# Synchronize session storage with memory
# This ensures session data is up-to-date for persistence across page reloads
# Only update if messages have changed (optimization to avoid unnecessary writes)
if current_session["messages"] != messages:
    current_session["messages"] = messages
    st.session_state.sessions[st.session_state.current_session_id] = current_session

# Display welcome message if conversation is empty
# This provides guidance to users on first load
if len(messages) == 0:
    st.markdown("""
    <div style='text-align: center; padding: 4rem 1rem 2rem 1rem; max-width: 700px; margin: 0 auto;'>
        <h1 style='color: #ececf1; font-size: 2.75rem; font-weight: 600; margin-bottom: 1.5rem; line-height: 1.2;'>What are you working on?</h1>
        <p style='color: #8e8ea0; font-size: 1.1rem; line-height: 1.6; margin: 0;'>Ask MBSE ReqViber to help you analyze and refine your software requirements using Volere template structure.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # Display all chat messages including the new user message
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ----------------------------------------------------------------------
# AI Response Generation
# ----------------------------------------------------------------------
# When a user sends a message, this section:
# 1. Prepares the conversation context (with token management)
# 2. Calls the LLM API with the selected model
# 3. Displays the response
# 4. Saves the response to memory

# Process AI response if user just sent a message
if user_input:
    try:
        # Get API client (centralized LLM API)
        client = get_deepseek_client()
        
        # Get current requirements from memory
        current_requirements = st.session_state.memory.get_requirements()
        
        # Get conversation history for prompt building
        history = st.session_state.memory.get_messages(include_system=False)
        
        # Use decide_and_build_prompt to build proper prompt and detect requirements
        # This function:
        # - Detects if user message contains requirement-like phrases
        # - Builds appropriate system prompt (Volere template or base)
        # - Returns new_requirement_data if a requirement is detected
        api_messages, conflict_message, new_requirement_data = decide_and_build_prompt(
            user_message=user_input,
            history=history,
            requirements=current_requirements
        )
        
        # Store pending requirement from user input (will be saved after assistant response)
        if new_requirement_data:
            st.session_state.pending_requirement = copy.deepcopy(new_requirement_data)
        else:
            st.session_state.pending_requirement = None
        
        # Get conversation context from memory with automatic token management
        # This function:
        # - Retrieves recent messages that fit within the token limit
        # - May automatically summarize old messages if history is very long
        # - Ensures we don't exceed API token limits
        # Pass client and model for optional auto-summarization
        context_messages = st.session_state.memory.get_context_for_api(
            max_tokens=3500,  # Maximum tokens for context (leaves room for response)
            client=client,    # For auto-summarization if needed
            model=st.session_state.selected_model  # Model to use for summarization if needed
        )
        
        # Replace history in api_messages with context_messages (which may be truncated/summarized)
        # Keep the system prompt from decide_and_build_prompt, but use optimized context
        if api_messages and api_messages[0].get("role") == "system":
            system_prompt = api_messages[0]["content"]
            api_messages = [{"role": "system", "content": system_prompt}]
            api_messages.extend(context_messages)
            # Add current user message if not already in context_messages
            if not any(msg.get("content") == user_input for msg in context_messages):
                api_messages.append({"role": "user", "content": user_input})
        else:
            # Fallback: use simple system prompt if decide_and_build_prompt didn't work
            system_prompt = "You are ReqViber, a professional requirements engineer. Use Volere template structure."
            api_messages = [{"role": "system", "content": system_prompt}]
            api_messages.extend(context_messages)
        
        # Inject requirement context from RAG search if available
        # This allows the AI to reference past requirements for better continuity
        if st.session_state.inject_requirement_context:
            injected_req = st.session_state.inject_requirement_context
            # Create a context message with the injected requirement
            context_text = f"""Relevant past requirement for context:
ID: {injected_req.get('id', 'Unknown')}
Project: {injected_req.get('project', 'unknown')}
Text: {injected_req.get('text', '')}
"""
            # Add volere fields if available
            volere = injected_req.get('volere', {})
            if volere:
                context_text += f"Goal: {volere.get('goal', 'Not stated')}\n"
                context_text += f"Context: {volere.get('context', 'Not asked')}\n"
                context_text += f"Stakeholder: {volere.get('stakeholder', 'Unknown')}\n"
            
            # Insert the context message before the user's current message
            # This ensures the AI has the context when responding
            api_messages.append({
                "role": "system",
                "content": f"CONTEXT FROM PAST REQUIREMENT:\n{context_text}\nUse this information to provide better continuity with past requirements."
            })
            
            # Clear the injected context after using it (one-time injection)
            st.session_state.inject_requirement_context = None
        
        # Display loading indicator and call the LLM API
        with st.chat_message("assistant"):
            with st.spinner("Analyzing requirement..."):
                # Call the centralized LLM API with selected model
                response = client.chat.completions.create(
                    model=st.session_state.selected_model,  # Use currently selected model
                    messages=api_messages,                   # Full conversation context
                    temperature=0.7,                        # Balance between creativity and consistency
                    max_tokens=2000                         # Maximum response length
                )
                
                # Extract the generated text from API response
                ai_response = response.choices[0].message.content
                # Display the response as Markdown (supports formatting)
                st.markdown(ai_response)
        
        # Save AI response to memory for future context and display
        st.session_state.memory.add_message("assistant", ai_response)
        
        # Extract and save requirements (from assistant response only)
        pending_requirement = st.session_state.pending_requirement
        requirement_saved = False
        
        # 1. Extract requirements from AI response (look for REQ-XXX patterns)
        # The AI may mention requirements in its response with IDs like "REQ-001"
        # Pattern matches REQ- followed by at least 3 digits (e.g., REQ-001, REQ-123)
        req_pattern = r'REQ-\d{3,}'
        found_req_ids = re.findall(req_pattern, ai_response, re.IGNORECASE)
        
        # Debug: Print found requirement IDs for troubleshooting
        if found_req_ids:
            print(f"DEBUG: Found requirement IDs in AI response: {found_req_ids}")
        
        # If AI mentions a requirement ID, try to extract the requirement text
        if found_req_ids:
            # Get unique requirement IDs
            unique_req_ids = list(set([req_id.upper() for req_id in found_req_ids]))
            
            # Check if these requirements are already saved
            existing_reqs = {req.get("id", "").upper() for req in st.session_state.memory.get_requirements()}
            
            # For each mentioned requirement ID, try to extract the requirement text from AI response
            for req_id in unique_req_ids:
                if req_id not in existing_reqs:
                    # Try multiple patterns to extract requirement text
                    req_text = ""
                    
                    # Pattern 1: Look for "Description:" section after REQ-ID
                    # This handles structured responses like:
                    # REQ-001: Title
                    # Description: The actual requirement text...
                    # Try multiple variations of the Description pattern
                    desc_patterns = [
                        # Pattern 1a: REQ-001: Title\nDescription: text
                        rf'{re.escape(req_id)}[:\-\s]*[^\n]*(?:\n[^\n]*)*?\n\s*\*\*?Description\*\*?[:\s]+([^\n]+(?:\n(?!\*\*|REQ-|Goal|Context|Stakeholder|Rationale|Description)[^\n]+)*)',
                        # Pattern 1b: REQ-001: Title\n**Description:** text
                        rf'{re.escape(req_id)}[:\-\s]*[^\n]*(?:\n[^\n]*)*?\n.*?Description[:\s]+([^\n]+(?:\n(?!\*\*|REQ-|Goal|Context|Stakeholder|Rationale|Description)[^\n]+)*)',
                        # Pattern 1c: Simple Description: text after REQ-ID
                        rf'{re.escape(req_id)}[:\-\s]*[^\n]*(?:\n.*?)?Description[:\s]+([^\n]+(?:\n(?!\*\*|REQ-|Goal|Context|Stakeholder|Rationale|Description)[^\n]+)*)'
                    ]
                    for desc_pattern in desc_patterns:
                        desc_match = re.search(desc_pattern, ai_response, re.IGNORECASE | re.DOTALL)
                        if desc_match:
                            req_text = desc_match.group(1).strip()
                            print(f"DEBUG: Extracted requirement text for {req_id} using Description pattern: {req_text[:100]}...")
                            break
                    
                    # Pattern 2: If no Description section, try to get text after REQ-ID until next section
                    if not req_text:
                        # Look for text after REQ-ID until next markdown header, REQ-ID, or section
                        pattern = rf'{re.escape(req_id)}[:\-\s]+([^\n]+(?:\n(?!\*\*|REQ-|Goal|Context|Stakeholder|Rationale|Description)[^\n]+)*)'
                        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
                        if match:
                            req_text = match.group(1).strip()
                            # Clean up: remove markdown formatting and limit to reasonable length
                            req_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', req_text)  # Remove bold
                            req_text = re.sub(r'`([^`]+)`', r'\1', req_text)  # Remove code blocks
                            # Take first 500 characters or until next major section
                            if len(req_text) > 500:
                                req_text = req_text[:500].rsplit('\n', 1)[0]
                    
                    # Pattern 3: Fallback - just get the first line after REQ-ID
                    if not req_text:
                        pattern = rf'{re.escape(req_id)}[:\-\s]+([^\n]+)'
                        match = re.search(pattern, ai_response, re.IGNORECASE)
                        if match:
                            req_text = match.group(1).strip()
                    
                    # Extract volere fields from AI response if available
                    volere = {}
                    goal_match = re.search(r'Goal[:\s]+([^\n]+)', ai_response, re.IGNORECASE)
                    if goal_match:
                        volere["goal"] = goal_match.group(1).strip()
                    context_match = re.search(r'Context[:\s]+([^\n]+)', ai_response, re.IGNORECASE)
                    if context_match:
                        volere["context"] = context_match.group(1).strip()
                    stakeholder_match = re.search(r'Stakeholder[:\s]+([^\n]+)', ai_response, re.IGNORECASE)
                    if stakeholder_match:
                        volere["stakeholder"] = stakeholder_match.group(1).strip()
                    
                    # Only save if we found requirement text
                    if not req_text:
                        continue  # Skip if we couldn't extract requirement text
                    
                    requirement_data = None
                    pending_matched = False
                    
                    if pending_requirement and pending_requirement.get("id", "").upper() == req_id:
                        # Use pending requirement metadata but replace text with assistant response
                        requirement_data = copy.deepcopy(pending_requirement)
                        requirement_data["text"] = req_text  # Use extracted text from AI response
                        # Merge volere fields from assistant response (if present)
                        if volere:
                            requirement_data.setdefault("volere", {})
                            requirement_data["volere"].update(volere)
                        pending_matched = True
                    else:
                        if req_text:
                            requirement_data = {
                                "id": req_id,
                                "text": req_text,
                                "volere": volere if volere else {
                                    "goal": "Not stated",
                                    "context": "Not asked",
                                    "stakeholder": "Unknown"
                                }
                            }
                        elif pending_requirement and pending_requirement.get("id", "").upper() == req_id:
                            # Fallback: no text found but pending requirement matches
                            requirement_data = copy.deepcopy(pending_requirement)
                            pending_matched = True
                    
                    if requirement_data and requirement_data.get("text"):
                        # Ensure volere fields exist
                        requirement_data.setdefault("volere", {
                            "goal": "Not stated",
                            "context": "Not asked",
                            "stakeholder": "Unknown"
                        })
                        try:
                            st.session_state.memory.add_requirement(requirement_data)
                            existing_reqs.add(req_id)
                            requirement_saved = True
                            print(f"DEBUG: Successfully saved requirement {req_id} to memory")
                            print(f"DEBUG: Requirement text: {requirement_data.get('text', '')[:100]}...")
                            if pending_matched:
                                st.session_state.pending_requirement = None
                        except Exception as e:
                            print(f"ERROR: Failed to save requirement {req_id}: {str(e)}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"DEBUG: Skipping {req_id} - no requirement text extracted or requirement_data is None")
                        if requirement_data:
                            print(f"DEBUG: requirement_data keys: {requirement_data.keys()}")
                            print(f"DEBUG: requirement_data text: {requirement_data.get('text', 'N/A')}")
                        else:
                            print(f"DEBUG: requirement_data is None, req_text was: {req_text[:100] if req_text else 'empty'}")
            
        # If no requirement IDs were found but we have a pending requirement, keep it for next assistant response
        
        st.rerun()  # Refresh UI to show the new message
        
    except Exception as e:
        # Handle errors gracefully - display error message to user
        error_msg = f"Sorry, an error occurred: {str(e)}"
        with st.chat_message("assistant"):
            st.error(error_msg)
        
        # Save error message to memory so it appears in conversation history
        # This helps users understand what went wrong
        st.session_state.memory.add_message("assistant", error_msg)
        st.rerun()

