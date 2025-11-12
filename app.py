import streamlit as st
import os
import requests
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI  # DeepSeek API uses OpenAI-compatible SDK
import uuid
from datetime import datetime
from memory import ShortTermMemory

# Set page title and configuration
st.set_page_config(
    page_title="Requirement Auto Analysis:UESTC-MBSE Requirement Assistant",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"  # Start with sidebar expanded, but user can collapse it
)

# Custom CSS for ChatGPT-like dark theme
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
# Centralized LLM API Client (mimics OpenAI client interface)
# ----------------------------------------------------------------------

# Define Completions class first (outside, or as inner class)
class _Completions:
    """Mimics OpenAI's chat.completions interface."""
    
    def __init__(self, client):
        self.client = client
    
    def create(self, model: str, messages: List[Dict[str, str]], **kwargs):
        """Create a chat completion."""
        url = f"{self.client.base_url}/v1/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
        }
        
        # Add optional parameters
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "stream" in kwargs:
            payload["stream"] = kwargs["stream"]
        
        try:
            response = requests.post(
                url, 
                headers=self.client.headers, 
                json=payload, 
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # Return object that mimics OpenAI response structure
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
    """Mimics OpenAI's chat interface."""
    
    def __init__(self, client):
        self.client = client
        self.completions = _Completions(client)

class CentralizedLLMClient:
    """Client for centralized LLM API that mimics OpenAI client interface."""
    
    def __init__(self, api_token: str, base_url: str = "https://api.ai88n.com"):
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Initialize chat attribute
        self.chat = _Chat(self)

# Available models organized by provider
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

# Flatten model list for easier access
ALL_MODELS = []
for provider, models in AVAILABLE_MODELS.items():
    for model in models:
        ALL_MODELS.append({
            "id": model,
            "name": model,
            "provider": provider
        })

# Initialize Centralized LLM API client
def get_centralized_client():
    """
    Get centralized LLM API client. Tries environment variable first, then Streamlit secrets.
    This function handles cases where secrets.toml doesn't exist gracefully.
    """
    # Priority 1: Try to get API token from environment variable (most reliable for local dev)
    api_token = os.getenv("API_TOKEN")
    
    # Priority 2: Only try Streamlit secrets if environment variable is not set
    if not api_token:
        api_token = _get_api_token_from_secrets()
    
    # If no API token found from either source, show instructions and stop
    if not api_token:
        _show_api_token_setup_instructions()
        st.stop()
        return None
    
    return CentralizedLLMClient(api_token=api_token)

# Legacy function for backward compatibility (uses centralized API)
def get_deepseek_client():
    """
    Get API client (now uses centralized API).
    This function is kept for backward compatibility.
    """
    return get_centralized_client()

def _get_api_token_from_secrets():
    """Safely get API token from Streamlit secrets."""
    try:
        api_token = st.secrets.get("API_TOKEN", None)
        return api_token if api_token else None
    except Exception:
        return None

def _show_api_token_setup_instructions():
    """Display instructions for setting up the API token."""
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

# Initialize session state
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "session_counter" not in st.session_state:
    st.session_state.session_counter = 0
if "generated_srs" not in st.session_state:
    st.session_state.generated_srs = None
if "srs_generation_error" not in st.session_state:
    st.session_state.srs_generation_error = None
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "deepseek-chat"  # Default model
if "model_change_warning" not in st.session_state:
    st.session_state.model_change_warning = None
if "show_model_selector" not in st.session_state:
    st.session_state.show_model_selector = False

# Initialize memory (per session)
if "memory" not in st.session_state:
    st.session_state.memory = ShortTermMemory()

# Create new session
def create_new_session():
    session_id = str(uuid.uuid4())
    # Save current memory to previous session if it exists
    if st.session_state.current_session_id and st.session_state.current_session_id in st.session_state.sessions:
        # Save memory messages to previous session before switching
        prev_session = st.session_state.sessions[st.session_state.current_session_id]
        prev_session["messages"] = st.session_state.memory.get_messages()
        prev_session["model"] = st.session_state.selected_model  # Save model to session
        st.session_state.sessions[st.session_state.current_session_id] = prev_session
    
    # Create new session
    st.session_state.sessions[session_id] = {
        "id": session_id,
        "messages": [],
        "title": f"New Chat {st.session_state.session_counter + 1}",
        "created_at": datetime.now(),
        "model": st.session_state.selected_model  # Store model with session
    }
    st.session_state.session_counter += 1
    st.session_state.current_session_id = session_id
    # Reset memory for new session
    st.session_state.memory = ShortTermMemory()
    # Clear generated SRS when creating new session
    st.session_state.generated_srs = None
    st.session_state.srs_generation_error = None
    return session_id

# Get current session
def get_current_session():
    if st.session_state.current_session_id is None:
        create_new_session()
    
    session = st.session_state.sessions[st.session_state.current_session_id]
    return session

# Update session title from first user message
def update_session_title(session_id, first_message):
    if session_id in st.session_state.sessions:
        if st.session_state.sessions[session_id]["title"].startswith("New Chat"):
            # Use first 50 characters of first message as title
            title = first_message[:50]
            if len(first_message) > 50:
                title += "..."
            st.session_state.sessions[session_id]["title"] = title

# Generate IEEE 830 SRS from assistant messages using API
def generate_ieee830_srs_from_conversation(client, assistant_messages):
    """
    Generate IEEE 830 SRS format from all assistant messages using API.
    
    Args:
        client: OpenAI-compatible API client (DeepSeek)
        assistant_messages: List of assistant message strings
    
    Returns:
        str: IEEE 830 formatted SRS document in Markdown
    """
    if not assistant_messages:
        return "# Software Requirements Specification (IEEE 830)\n\n## 1. Introduction\n\nNo requirements have been captured yet. Please start a conversation with the AI assistant to analyze and capture requirements."
    
    # Combine all assistant messages into a single context
    conversation_context = "\n\n---\n\n".join([
        f"**Assistant Response {i+1}:**\n{msg}" 
        for i, msg in enumerate(assistant_messages)
    ])
    
    # Create prompt for API to format into IEEE 830 SRS
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
        response = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent, structured output
            max_tokens=4000  # Allow for comprehensive SRS document
        )
        
        srs_content = response.choices[0].message.content
        
        # Ensure it starts with a proper header if not already present
        if not srs_content.startswith("#"):
            srs_content = "# Software Requirements Specification (IEEE 830)\n\n" + srs_content
        
        return srs_content
    except Exception as e:
        raise Exception(f"Failed to generate SRS from API: {str(e)}")

# Sidebar - Session Management
with st.sidebar:
    st.markdown("""
    <div style='padding: 1rem 0 1.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1rem;'>
        <h2 style='color: #ececf1; margin: 0; font-size: 1.5rem;'>📋 UESTC-MBSE Requirement Assistant</h2>
        <p style='color: #8e8ea0; margin: 0.25rem 0 0 0; font-size: 0.85rem;'>AI Requirements Analyst</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Model Selector Section
    st.markdown("<div style='margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Model Selection</h3></div>", unsafe_allow_html=True)
    
    # Check if current session has messages (model cannot be changed if it does)
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
    
    # Model selector - Single button with dropdown
    if model_locked:
        # If session has messages, show a button that triggers warning
        if st.button("🔄 Change Model", use_container_width=True, type="secondary", help="Click to change model (warning: model cannot be changed after session starts)"):
            st.session_state.model_change_warning = "⚠️ Model cannot be changed after the session has started. Please create a new chat to use a different model."
            st.rerun()
    else:
        # Show "Select Model" button
        if st.button("🤖 Select Model", use_container_width=True, type="secondary", help="Click to select a different model"):
            st.session_state.show_model_selector = not st.session_state.show_model_selector
            st.rerun()
        
        # Show model selector dropdown if button was clicked
        if st.session_state.show_model_selector:
            # Build model options with provider labels for better organization
            model_options = []
            model_display_names = []
            
            for provider, models in AVAILABLE_MODELS.items():
                for model in models:
                    model_options.append(model)
                    display_name = f"{model} ({provider})"
                    model_display_names.append(display_name)
            
            # Find current selection index
            try:
                selected_index = model_options.index(st.session_state.selected_model)
            except ValueError:
                selected_index = 0
            
            # Display selectbox
            # Use a unique key to track changes
            selectbox_key = "model_selector_dropdown"
            selected_display = st.selectbox(
                "Choose a model:",
                options=model_display_names,
                index=selected_index,
                key=selectbox_key,
                help="Select the LLM model to use for this session"
            )
            
            # Extract model ID from display name
            selected_model_id = model_options[model_display_names.index(selected_display)]
            
            # Check if model was changed (this will be true on rerun when selectbox value changes)
            if selected_model_id != st.session_state.selected_model:
                # Update selected model
                st.session_state.selected_model = selected_model_id
                # Update current session's model
                if st.session_state.current_session_id:
                    current_session["model"] = selected_model_id
                    st.session_state.sessions[st.session_state.current_session_id] = current_session
                # Close the selector after selection
                st.session_state.show_model_selector = False
                st.rerun()
            
            # Add a "Cancel" button to close the selector without changing
            if st.button("Cancel", use_container_width=True, type="secondary", key="model_selector_cancel"):
                st.session_state.show_model_selector = False
                st.rerun()
    
    # Show auto-dismissing warning if user tried to change model after session started
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
    
    st.markdown("<div style='margin: 1rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1);'></div>", unsafe_allow_html=True)
    
    # New Chat button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        create_new_session()
        st.rerun()
    
    st.markdown("<div style='margin: 1.5rem 0 0.5rem 0;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Chat History</h3></div>", unsafe_allow_html=True)
    
    if len(st.session_state.sessions) == 0:
        create_new_session()
    
    # Display sessions
    sessions_list = list(st.session_state.sessions.values())
    sessions_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Create a container for session buttons
    session_container = st.container()
    with session_container:
        for session in sessions_list:
            session_id = session["id"]
            is_active = st.session_state.current_session_id == session_id
            
            # Create a button for each session
            button_label = session["title"]
            button_type = "primary" if is_active else "secondary"
            if st.button(
                button_label,
                key=f"session_{session_id}",
                use_container_width=True,
                type=button_type
            ):
                # Save current memory to previous session before switching
                if st.session_state.current_session_id and st.session_state.current_session_id in st.session_state.sessions:
                    prev_session = st.session_state.sessions[st.session_state.current_session_id]
                    prev_session["messages"] = st.session_state.memory.get_messages()
                    st.session_state.sessions[st.session_state.current_session_id] = prev_session
                
                # Switch to selected session
                st.session_state.current_session_id = session_id
                # Load selected session's messages into memory
                selected_session = st.session_state.sessions[session_id]
                st.session_state.memory.load_messages(selected_session["messages"], reset=True)
                # Load the model used in this session (if stored)
                if "model" in selected_session:
                    st.session_state.selected_model = selected_session["model"]
                # Clear generated SRS when switching sessions (since it's session-specific)
                st.session_state.generated_srs = None
                st.session_state.srs_generation_error = None
                st.rerun()
    
    st.markdown("<div style='margin-top: 2rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.1);'>", unsafe_allow_html=True)
    
    # Export SRS section (always visible button, no status message before click)
    if st.button("📄 Export SRS (Markdown)", use_container_width=True, type="secondary", help="Generate and download IEEE 830 SRS document from conversation"):
        # Check if we have assistant messages
        all_messages = st.session_state.memory.get_messages(include_system=False)
        assistant_messages = [msg["content"] for msg in all_messages if msg.get("role") == "assistant"]
        
        if not assistant_messages:
            st.warning("⚠️ No assistant responses found in the conversation. Please start a conversation and receive responses from the AI before exporting SRS.")
            st.session_state.generated_srs = None
            st.session_state.srs_generation_error = "No assistant messages found"
        else:
            # Generate SRS using API
            try:
                client = get_deepseek_client()
                if client:
                    with st.spinner("🔄 Generating IEEE 830 SRS document from conversation..."):
                        srs_content = generate_ieee830_srs_from_conversation(client, assistant_messages)
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
    
    # Show download button if SRS has been generated
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
    
    # Summarize Context button (always visible, no status message before click)
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
    
    # Clear current session button
    if st.session_state.current_session_id and len(get_current_session()["messages"]) > 0:
        if st.button("🗑️ Clear Current Chat", use_container_width=True, type="secondary"):
            if st.session_state.current_session_id in st.session_state.sessions:
                st.session_state.sessions[st.session_state.current_session_id]["messages"] = []
            # Clear memory
            st.session_state.memory.clear_chat_history()
            # Clear generated SRS when clearing chat
            st.session_state.generated_srs = None
            st.session_state.srs_generation_error = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# Add sidebar toggle button in top left corner (fixed position)
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

# Input area at bottom - placed before message display for better UX
user_input = st.chat_input("Ask for requirement analysis...")

# Main Chat Area
current_session = get_current_session()

# On first load, if session has messages but memory is empty, load them
# (This handles the case where the page reloads and memory is reset but session persists)
if current_session["messages"] and st.session_state.memory.get_history_length() == 0:
    st.session_state.memory.load_messages(current_session["messages"], reset=True)

# Handle user input
if user_input:
    # Add user message to memory
    st.session_state.memory.add_message("user", user_input)
    
    # Update session title if it's the first message
    if st.session_state.memory.get_history_length() == 1:
        update_session_title(st.session_state.current_session_id, user_input)

# Get messages from memory for display (memory is source of truth)
messages = st.session_state.memory.get_messages()
# Sync session messages from memory (only update if changed)
if current_session["messages"] != messages:
    current_session["messages"] = messages
    st.session_state.sessions[st.session_state.current_session_id] = current_session

# Display welcome message if no messages
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

# Process AI response if user just sent a message
if user_input:
    try:
        client = get_deepseek_client()
        
        # Prepare messages with system prompt and context from memory (with token management)
        system_prompt = "You are ReqViber, a professional requirements engineer. Use Volere template structure."
        
        # Get context from memory (automatically manages token limit, may trigger summarization)
        # Pass client for optional auto-summarization when tokens are high
        context_messages = st.session_state.memory.get_context_for_api(max_tokens=3500, client=client, model=st.session_state.selected_model)
        
        # Build API messages: system prompt + context
        # Context messages may include system messages (like summaries) and conversation messages
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(context_messages)
        
        # Show loading indicator and get AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing requirement..."):
                response = client.chat.completions.create(
                    model=st.session_state.selected_model,
                    messages=api_messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                ai_response = response.choices[0].message.content
                st.markdown(ai_response)
        
        # Add AI response to memory
        st.session_state.memory.add_message("assistant", ai_response)
        st.rerun()
        
    except Exception as e:
        error_msg = f"Sorry, an error occurred: {str(e)}"
        with st.chat_message("assistant"):
            st.error(error_msg)
        
        # Add error message to memory
        st.session_state.memory.add_message("assistant", error_msg)
        st.rerun()

