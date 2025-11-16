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
import copy

# UI Components
from ui.styles import apply_styles
from ui.pages.auth import show_login_page, show_register_page, show_password_reset_page
from ui.components.sidebar import render_sidebar

# Services
from services.session_service import create_new_session, get_current_session, update_session_title
from services.requirement_service import extract_requirements_from_response, merge_requirement_with_pending
from services.prompt_service import decide_and_build_prompt
from services.conversation_service import ConversationStorage

# Clients
from clients.llm_client import get_deepseek_client

# Models
from models.memory import ShortTermMemory

# Utils
from utils.state_manager import initialize_session_state

# Config (models are used in sidebar component, not directly in app.py)

# ----------------------------------------------------------------------
# Page Configuration
# ----------------------------------------------------------------------
# Sets up the Streamlit page with title, icon, layout, and initial sidebar state
# The sidebar starts expanded to show session management and model selection
st.set_page_config(
    page_title="Requirement Auto Analysis:UESTC-MBSE Requirement Assistant",
    page_icon="RequirementVIBEICON.png",
    layout="wide",
    initial_sidebar_state="expanded"  # Start with sidebar expanded, but user can collapse it
)

# ----------------------------------------------------------------------
# UI Styling - ChatGPT-like Dark Theme
# ----------------------------------------------------------------------
# Apply custom CSS styling for dark theme
apply_styles()

# ----------------------------------------------------------------------
# Session State Initialization
# ----------------------------------------------------------------------
# Initialize all session state variables with default values
initialize_session_state()

# Note: Authentication and session management functions have been moved to:
# - ui/pages/auth.py: show_login_page(), show_register_page()
# - services/session_service.py: create_new_session(), get_current_session(), update_session_title()

# ----------------------------------------------------------------------
# SRS Generation Function
# ----------------------------------------------------------------------
# This function generates IEEE 830 Software Requirements Specification documents
# by analyzing the assistant's responses from the conversation and formatting
# them according to the IEEE 830 standard structure.

# Note: SRS generation function has been moved to services/srs_service.py
# Use generate_ieee830_srs_from_conversation() from services.srs_service module

# ----------------------------------------------------------------------
# Sidebar UI - Session and Model Management
# ----------------------------------------------------------------------
# Render sidebar with all UI components
# The sidebar component handles:
# 1. Model selection (with lock mechanism after session starts)
# 2. Session management (create new, switch between sessions)
# 3. SRS export functionality
# 4. Context summarization
# 5. Conversation persistence settings

render_sidebar()

# ----------------------------------------------------------------------
# Sidebar Toggle Button (Custom JavaScript)
# ----------------------------------------------------------------------
# Custom JavaScript button in the top-left corner to toggle sidebar visibility
# This ensures users can always access the sidebar even if it's collapsed
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
        let toggleBtn = findSidebarToggle();
        if (toggleBtn) {
            try {
                const clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    buttons: 1
                });
                toggleBtn.dispatchEvent(clickEvent);
                
                if (typeof toggleBtn.click === 'function') {
                    toggleBtn.click();
                }
                
                setTimeout(function() {
                    const sidebar = document.querySelector('section[data-testid="stSidebar"]');
                    if (sidebar) {
                        const isExpanded = sidebar.getAttribute('aria-expanded') === 'true' || sidebar.offsetWidth > 100;
                        if (!isExpanded) {
                            expandSidebarDirectly();
                        }
                    }
                }, 200);
                return;
            } catch (e) {
                console.log('Error clicking native toggle:', e);
            }
        }
        
        expandSidebarDirectly();
    }
    
    function expandSidebarDirectly() {
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) return;
        
        const currentState = sidebar.getAttribute('aria-expanded');
        const computedStyle = window.getComputedStyle(sidebar);
        const isVisible = computedStyle.display !== 'none' && sidebar.offsetWidth > 50;
        
        if (currentState !== 'true' || !isVisible) {
            sidebar.setAttribute('aria-expanded', 'true');
            sidebar.style.setProperty('display', 'flex', 'important');
            sidebar.style.setProperty('visibility', 'visible', 'important');
            sidebar.style.setProperty('transform', 'translateX(0)', 'important');
            sidebar.style.setProperty('opacity', '1', 'important');
            
            const sidebarContent = sidebar.querySelector('[data-testid="stSidebarContent"]');
            if (sidebarContent) {
                sidebarContent.style.setProperty('display', 'block', 'important');
                sidebarContent.style.setProperty('visibility', 'visible', 'important');
            }
            
            window.dispatchEvent(new Event('resize'));
            setTimeout(function() {
                window.dispatchEvent(new Event('resize'));
            }, 100);
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
})();
</script>

<style>
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

section[data-testid="stSidebar"] {
    z-index: 1000 !important;
}

@media (max-width: 768px) {
    .main .block-container {
        padding-top: 4rem;
    }
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Authentication Check
# ----------------------------------------------------------------------
# Check if user is authenticated before showing the main application
# If not authenticated, show login/registration page

if not st.session_state.authenticated:
    # Show registration, password reset, or login page based on state
    if st.session_state.get("show_password_reset", False):
        show_password_reset_page()
    elif st.session_state.get("show_register", False):
        show_register_page()
    else:
        show_login_page()
    st.stop()  # Stop execution here - don't show main app

# Ensure conversation storage is initialized for authenticated user
if st.session_state.authenticated and st.session_state.current_user and st.session_state.conversation_storage is None:
    st.session_state.conversation_storage = ConversationStorage(st.session_state.current_user["username"])
    # Load previous conversations if they exist (always load on initialization)
    loaded_sessions = st.session_state.conversation_storage.load_sessions()
    if loaded_sessions:
        # Merge with existing sessions (don't overwrite current sessions)
        for session_id, session_data in loaded_sessions.items():
            if session_id not in st.session_state.sessions:
                st.session_state.sessions[session_id] = session_data
        # Update session counter
        if st.session_state.sessions:
            st.session_state.session_counter = len(st.session_state.sessions)
        # Restore current session if available and no current session is set
        if st.session_state.sessions and not st.session_state.current_session_id:
            # Get the most recent session
            sorted_sessions = sorted(
                st.session_state.sessions.values(),
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )
            if sorted_sessions:
                most_recent_session = sorted_sessions[0]
                st.session_state.current_session_id = most_recent_session["id"]
                # Load messages into memory
                if most_recent_session.get("messages"):
                    st.session_state.memory.load_messages(most_recent_session["messages"], reset=True)
                # Restore model
                if most_recent_session.get("model"):
                    st.session_state.selected_model = most_recent_session["model"]

# ----------------------------------------------------------------------
# Main Chat Interface
# ----------------------------------------------------------------------
# This section handles the main chat area where users interact with the AI
# It includes:
# 1. Chat input field
# 2. Message display
# 3. AI response generation
# 4. Session synchronization

# Chat input field - placed at bottom for better UX (Streamlit handles positioning)
user_input = st.chat_input("Ask for requirement analysis...")

# Get the current active session
current_session = get_current_session()

# Synchronize memory with session storage on page load
if current_session["messages"] and st.session_state.memory.get_history_length() == 0:
    st.session_state.memory.load_messages(current_session["messages"], reset=True)

# Handle pending file upload message (from file upload component)
if st.session_state.get("pending_file_upload_message") and not user_input:
    # Use the pending message as user input
    user_input = st.session_state.pending_file_upload_message
    st.session_state.pending_file_upload_message = None  # Clear after use

# Handle user input when a message is submitted
if user_input:
    # Add user message to memory immediately (for display and context)
    st.session_state.memory.add_message("user", user_input)
    
    # Update session title from first user message
    if st.session_state.memory.get_history_length() == 1:
        update_session_title(st.session_state.current_session_id, user_input)

# Retrieve messages from memory for display
messages = st.session_state.memory.get_messages()

# Synchronize session storage with memory
if current_session["messages"] != messages:
    current_session["messages"] = messages
    current_session["model"] = st.session_state.selected_model
    st.session_state.sessions[st.session_state.current_session_id] = current_session
    
    # Save conversations to disk if persistence is enabled
    if st.session_state.conversation_persistence_enabled and st.session_state.conversation_storage and messages:
        st.session_state.conversation_storage.save_sessions(st.session_state.sessions)

# Display welcome message if conversation is empty
if len(messages) == 0:
    st.markdown("""
    <div style='text-align: center; padding: 4rem 1rem 2rem 1rem; max-width: 700px; margin: 0 auto;'>
        <h1 style='color: #ececf1; font-size: 2.75rem; font-weight: 600; margin-bottom: 1.5rem; line-height: 1.2;'>What are you working on?</h1>
        <p style='color: #8e8ea0; font-size: 1.1rem; line-height: 1.6; margin: 0;'>Ask MBSE ReqViber to help you analyze and refine your software requirements using IEEE 830 SRS or Volere template structure.</p>
        <p style='color: #8e8ea0; font-size: 1.1rem; line-height: 1.6; margin: 0;'>If you have any questions about using the website or about the project requirements, please feel free to contact me at wee235929@gmail.com.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # Display all chat messages including the new user message
    for message in messages:
        with st.chat_message(message["role"]):
            # Use Mermaid renderer for assistant messages to detect and render diagrams
            if message["role"] == "assistant":
                from utils.mermaid_renderer import render_message_with_mermaid
                render_message_with_mermaid(message["content"])
            else:
                st.markdown(message["content"])

# ----------------------------------------------------------------------
# AI Response Generation
# ----------------------------------------------------------------------
# When a user sends a message, this section:
# 1. Prepares the conversation context (with token management)
# 2. Calls the LLM API with the selected model
# 3. Displays the response
# 4. Saves the response to memory
# 5. Extracts and saves requirements from the response

# Process AI response if user just sent a message
if user_input:
    try:
        # Get API client (centralized LLM API)
        client = get_deepseek_client()
        
        # Check if GraphRAG should be used for this query
        use_graphrag = False
        graphrag_answer = None
        
        if st.session_state.get("graphrag_index_built") and st.session_state.get("graphrag_index"):
            from services.graphrag_service import (
                is_document_related_query,
                GraphRAGIndex,
                answer_question_with_graphrag
            )
            
            # Check if query is document-related
            if is_document_related_query(user_input):
                try:
                    # Reconstruct GraphRAG index from serialized data
                    index_data = st.session_state.graphrag_index
                    graphrag_index = GraphRAGIndex.from_dict(index_data)
                    
                    # Rebuild graph and embeddings (they weren't serialized)
                    from services.graphrag_service import build_graphrag_index
                    if st.session_state.get("document_processing_results"):
                        graphrag_index = build_graphrag_index(
                            st.session_state.document_processing_results
                        )
                    
                    # Try to answer using GraphRAG
                    with st.chat_message("assistant"):
                        with st.spinner("Searching documents..."):
                            graphrag_answer = answer_question_with_graphrag(
                                query=user_input,
                                index=graphrag_index,
                                llm_client=client,
                                model=st.session_state.selected_model
                            )
                            # Display the GraphRAG answer with Mermaid support
                            from utils.mermaid_renderer import render_message_with_mermaid
                            render_message_with_mermaid(graphrag_answer)
                            use_graphrag = True
                except Exception as e:
                    # If GraphRAG fails, fall back to normal chat
                    print(f"GraphRAG error: {str(e)}. Falling back to normal chat.")
                    use_graphrag = False
        
        # If not using GraphRAG, use normal chat flow
        if not use_graphrag:
            # Get current requirements from memory (short-term)
            current_requirements = st.session_state.memory.get_requirements()
            
            # Get conversation history for prompt building
            history = st.session_state.memory.get_messages(include_system=False)
            
            # Use decide_and_build_prompt to build proper prompt and detect requirements
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
            context_messages = st.session_state.memory.get_context_for_api(
                max_tokens=3500,
                client=client,
                model=st.session_state.selected_model
            )
            
            # Replace history in api_messages with context_messages (which may be truncated/summarized)
            if api_messages and api_messages[0].get("role") == "system":
                system_prompt = api_messages[0]["content"]
                api_messages = [{"role": "system", "content": system_prompt}]
                api_messages.extend(context_messages)
                # Add current user message if not already in context_messages
                if not any(msg.get("content") == user_input for msg in context_messages):
                    api_messages.append({"role": "user", "content": user_input})
            else:
                # Fallback: use simple system prompt
                system_prompt = "You are ReqViber, a professional requirements engineer. Use Volere template structure."
                api_messages = [{"role": "system", "content": system_prompt}]
                api_messages.extend(context_messages)
            
            # Display loading indicator and call the LLM API
            with st.chat_message("assistant"):
                with st.spinner("Analyzing requirement..."):
                    # Call the centralized LLM API with selected model
                    response = client.chat.completions.create(
                        model=st.session_state.selected_model,
                        messages=api_messages,
                        temperature=0.7,
                        max_tokens=2000
                    )
                    
                    # Extract the generated text from API response
                    ai_response = response.choices[0].message.content
                    # Display the response with Mermaid diagram support
                    from utils.mermaid_renderer import render_message_with_mermaid
                    render_message_with_mermaid(ai_response)
        else:
            # Using GraphRAG answer
            ai_response = graphrag_answer
        
        # Save AI response to memory for future context and display
        st.session_state.memory.add_message("assistant", ai_response)
        
        # Only extract requirements if not using GraphRAG (GraphRAG answers are document-focused)
        if not use_graphrag:
            # Extract and save requirements from AI response using requirement service
            pending_requirement = st.session_state.pending_requirement
            existing_requirements = st.session_state.memory.get_requirements()
            
            # Extract requirements from AI response
            extracted_requirements = extract_requirements_from_response(
                ai_response,
                existing_requirements=existing_requirements
            )
            
            # Save each extracted requirement
            for requirement_data in extracted_requirements:
                # Merge with pending requirement if it matches
                original_req_id = requirement_data.get("id", "").upper()
                if pending_requirement and pending_requirement.get("id", "").upper() == original_req_id:
                    requirement_data = merge_requirement_with_pending(
                        requirement_data,
                        pending_requirement,
                        original_req_id
                    )
                    st.session_state.pending_requirement = None
                
                # Save to memory
                try:
                    st.session_state.memory.add_requirement(requirement_data)
                    print(f"DEBUG: Successfully saved requirement {requirement_data.get('id')} to memory")
                except Exception as e:
                    print(f"ERROR: Failed to save requirement {requirement_data.get('id')}: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        st.rerun()  # Refresh UI to show the new message
        
    except Exception as e:
        # Handle errors gracefully - display error message to user
        error_msg = f"Sorry, an error occurred: {str(e)}"
        with st.chat_message("assistant"):
            st.error(error_msg)
        
        # Save error message to memory so it appears in conversation history
        st.session_state.memory.add_message("assistant", error_msg)
        st.rerun()

