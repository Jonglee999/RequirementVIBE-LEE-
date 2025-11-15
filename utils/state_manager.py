"""
State Manager for ReqVibe

This module handles initialization and management of Streamlit session state.
It centralizes all session state initialization to ensure consistency.
"""

import streamlit as st
from models.memory import ShortTermMemory
from services.auth_service import AuthManager


def initialize_session_state():
    """
    Initialize all required session state variables with default values.
    
    This function ensures all session state variables are properly initialized
    before the application starts. It should be called at the beginning of app.py.
    
    Initialized state includes:
    - Session management (sessions, current_session_id, session_counter)
    - SRS generation (generated_srs, srs_generation_error)
    - Model selection (selected_model, model_change_warning, show_model_selector)
    - Memory management (memory)
    - Authentication (authenticated, current_user, auth_manager)
    - Conversation storage (conversation_storage, conversation_persistence_enabled)
    - UI state (pending_requirement, show_register)
    """
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
    
    # Authentication State
    # authenticated: Boolean flag indicating if user is logged in
    # current_user: Dictionary containing logged-in user information (username, email, etc.)
    # auth_manager: AuthManager instance for handling authentication operations
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = AuthManager()
    
    # Conversation Storage
    # conversation_storage: ConversationStorage instance for persistent conversation storage
    # conversation_persistence_enabled: Boolean flag indicating if conversation persistence is enabled (default: False)
    if "conversation_storage" not in st.session_state:
        st.session_state.conversation_storage = None
    if "conversation_persistence_enabled" not in st.session_state:
        st.session_state.conversation_persistence_enabled = False
    
    # UI State
    # pending_requirement: Optional requirement data waiting to be saved after AI response
    if "pending_requirement" not in st.session_state:
        st.session_state.pending_requirement = None
    # show_register: Boolean flag to toggle between login and registration pages
    if "show_register" not in st.session_state:
        st.session_state.show_register = False
    # show_password_reset: Boolean flag to toggle password reset page
    if "show_password_reset" not in st.session_state:
        st.session_state.show_password_reset = False
    
    # File Upload State
    # document_processing_results: Results from processing uploaded documents
    if "document_processing_results" not in st.session_state:
        st.session_state.document_processing_results = None
    # document_processing_error: Error message if document processing failed
    if "document_processing_error" not in st.session_state:
        st.session_state.document_processing_error = None
    # document_processing_formatted: Formatted text output from document processing
    if "document_processing_formatted" not in st.session_state:
        st.session_state.document_processing_formatted = None
    # pending_file_upload_message: Message to be added to chat from file upload
    if "pending_file_upload_message" not in st.session_state:
        st.session_state.pending_file_upload_message = None
    
    # GraphRAG State
    # graphrag_index: Serialized GraphRAG index dictionary
    if "graphrag_index" not in st.session_state:
        st.session_state.graphrag_index = None
    # graphrag_index_built: Boolean flag indicating if GraphRAG index has been built
    if "graphrag_index_built" not in st.session_state:
        st.session_state.graphrag_index_built = False

