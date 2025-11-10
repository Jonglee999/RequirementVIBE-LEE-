import streamlit as st
import os
from openai import OpenAI  # DeepSeek API uses OpenAI-compatible SDK
import uuid
from datetime import datetime

# Set page title and configuration
st.set_page_config(
    page_title="ReqVibe - AI Requirements Analyst",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for ChatGPT-like dark theme
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Main app background */
    .stApp {
        background-color: #343541 !important;
    }
    
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 6rem;
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #202123 !important;
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

# Initialize DeepSeek API client
def get_deepseek_client():
    """
    Get DeepSeek API client. Tries environment variable first, then Streamlit secrets.
    This function handles cases where secrets.toml doesn't exist gracefully.
    """
    # Priority 1: Try to get API key from environment variable (most reliable for local dev)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # Priority 2: Only try Streamlit secrets if environment variable is not set
    # This prevents unnecessary access to secrets.toml when using environment variables
    if not api_key:
        api_key = _get_api_key_from_secrets()
        # If secrets access failed, api_key will be None, which is fine
    
    # If no API key found from either source, show instructions and stop
    if not api_key:
        _show_api_key_setup_instructions()
        # Use st.stop() to prevent further execution
        # This will stop the app from continuing, but won't raise an exception
        st.stop()
        # This return will never be reached due to st.stop(), but included for clarity
        return None
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

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

# Create new session
def create_new_session():
    session_id = str(uuid.uuid4())
    st.session_state.sessions[session_id] = {
        "id": session_id,
        "messages": [],
        "title": f"New Chat {st.session_state.session_counter + 1}",
        "created_at": datetime.now()
    }
    st.session_state.session_counter += 1
    st.session_state.current_session_id = session_id
    return session_id

# Get current session
def get_current_session():
    if st.session_state.current_session_id is None:
        create_new_session()
    return st.session_state.sessions[st.session_state.current_session_id]

# Update session title from first user message
def update_session_title(session_id, first_message):
    if session_id in st.session_state.sessions:
        if st.session_state.sessions[session_id]["title"].startswith("New Chat"):
            # Use first 50 characters of first message as title
            title = first_message[:50]
            if len(first_message) > 50:
                title += "..."
            st.session_state.sessions[session_id]["title"] = title

# Sidebar - Session Management
with st.sidebar:
    st.markdown("""
    <div style='padding: 1rem 0 1.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1rem;'>
        <h2 style='color: #ececf1; margin: 0; font-size: 1.5rem;'>📋 UESTC-MBSE Requirement Assistant</h2>
        <p style='color: #8e8ea0; margin: 0.25rem 0 0 0; font-size: 0.85rem;'>AI Requirements Analyst</p>
    </div>
    """, unsafe_allow_html=True)
    
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
                st.session_state.current_session_id = session_id
                st.rerun()
    
    st.markdown("<div style='margin-top: 2rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.1);'>", unsafe_allow_html=True)
    
    # Clear current session button
    if st.session_state.current_session_id and len(get_current_session()["messages"]) > 0:
        if st.button("🗑️ Clear Current Chat", use_container_width=True, type="secondary"):
            if st.session_state.current_session_id in st.session_state.sessions:
                st.session_state.sessions[st.session_state.current_session_id]["messages"] = []
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# Input area at bottom - placed before message display for better UX
user_input = st.chat_input("Ask for requirement analysis...")

# Main Chat Area
current_session = get_current_session()

# Handle user input
if user_input:
    # Add user message to current session
    current_session["messages"].append({"role": "user", "content": user_input})
    
    # Update session title if it's the first message
    if len(current_session["messages"]) == 1:
        update_session_title(st.session_state.current_session_id, user_input)
    
    # Update session in state
    st.session_state.sessions[st.session_state.current_session_id] = current_session

# Get updated messages
messages = current_session["messages"]

# Display welcome message if no messages
if len(messages) == 0:
    st.markdown("""
    <div style='text-align: center; padding: 4rem 1rem 2rem 1rem; max-width: 700px; margin: 0 auto;'>
        <h1 style='color: #ececf1; font-size: 2.75rem; font-weight: 600; margin-bottom: 1.5rem; line-height: 1.2;'>What are you working on?</h1>
        <p style='color: #8e8ea0; font-size: 1.1rem; line-height: 1.6; margin: 0;'>Ask ReqVibe to help you analyze and refine your software requirements using Volere template structure.</p>
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
        
        # Prepare messages with system prompt and full conversation history
        system_prompt = "You are ReqVibe, a professional requirements engineer. Use Volere template structure."
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(current_session["messages"])
        
        # Show loading indicator and get AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing requirement..."):
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=api_messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                ai_response = response.choices[0].message.content
                st.markdown(ai_response)
        
        # Add AI response to session
        current_session["messages"].append({"role": "assistant", "content": ai_response})
        
        # Update session in state
        st.session_state.sessions[st.session_state.current_session_id] = current_session
        st.rerun()
        
    except Exception as e:
        error_msg = f"Sorry, an error occurred: {str(e)}"
        with st.chat_message("assistant"):
            st.error(error_msg)
        current_session["messages"].append({"role": "assistant", "content": error_msg})
        st.session_state.sessions[st.session_state.current_session_id] = current_session
        st.rerun()

