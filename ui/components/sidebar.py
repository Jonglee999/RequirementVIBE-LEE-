"""
Sidebar UI Component for ReqVibe

This module contains the sidebar UI components including:
- Model selection
- Session management
- SRS export
- Context summarization
- Conversation persistence settings
"""

import streamlit as st
from services.session_service import create_new_session, get_current_session, update_session_title
from services.conversation_service import ConversationStorage
from config.models import ALL_MODELS, AVAILABLE_MODELS
from models.memory import ShortTermMemory
from services.srs_service import generate_ieee830_srs_from_conversation
from clients.llm_client import get_centralized_client
from ui.components.file_upload import render_file_upload
from services.prompt_service import load_role


def render_sidebar():
    """
    Render the sidebar with all UI components.
    
    This function renders:
    1. Header with app title
    2. User info and logout button (if authenticated)
    3. Model selection UI
    4. Session management UI
    5. SRS export button
    6. Context summarization button
    7. Conversation persistence settings
    """
    with st.sidebar:
        # Header
        st.markdown("""
        <div style='padding: 1rem 0 1.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1rem;'>
            <h2 style='color: #ececf1; margin: 0; font-size: 1.5rem;'>UESTC-MBSE Requirement Assistant</h2>
            <p style='color: #8e8ea0; margin: 0.25rem 0 0 0; font-size: 0.85rem;'>AI Requirements Analyst</p>
        </div>
        """, unsafe_allow_html=True)
        
        # User info and logout
        _render_user_info()
        
        # Role selection
        _render_role_selection()
        
        # Model selection
        _render_model_selection()
        
        # Session management
        _render_session_management()
        
        # SRS export
        _render_srs_export()
        
        # Context summarization
        _render_context_summarization()
        
        # File upload
        _render_file_upload()
        
        # Conversation persistence
        _render_conversation_persistence()


def _render_user_info():
    """Render user info and logout button if authenticated."""
    if st.session_state.authenticated and st.session_state.current_user:
        st.markdown(f"""
        <div style='padding: 0.75rem; background-color: #343541; border-radius: 6px; border: 1px solid #565869; margin-bottom: 1rem;'>
            <div style='color: #8e8ea0; font-size: 0.75rem; margin-bottom: 0.25rem;'>Logged in as</div>
            <div style='color: #ececf1; font-size: 0.9rem; font-weight: 500;'>{st.session_state.current_user['username']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Logout", use_container_width=True, key="logout_button"):
            # Save conversations before logout if persistence is enabled
            if st.session_state.conversation_persistence_enabled and st.session_state.conversation_storage:
                # Save current session before logout
                if st.session_state.current_session_id and st.session_state.current_session_id in st.session_state.sessions:
                    current_session = st.session_state.sessions[st.session_state.current_session_id]
                    current_session["messages"] = st.session_state.memory.get_messages()
                    current_session["model"] = st.session_state.selected_model
                    st.session_state.sessions[st.session_state.current_session_id] = current_session
                # Save all sessions to disk
                st.session_state.conversation_storage.save_sessions(st.session_state.sessions)
            
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.conversation_storage = None
            st.session_state.memory = ShortTermMemory()
            st.session_state.sessions = {}
            st.session_state.current_session_id = None
            st.session_state.conversation_persistence_enabled = False
            st.rerun()


def _render_role_selection():
    """Render role selection UI."""
    st.markdown("<div style='margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Role Selection</h3></div>", unsafe_allow_html=True)
    
    # Available roles
    available_roles = {
        "analyst": "Requirements Analyst",
        "architect": "System Architect",
        "developer": "Full Stack Developer",
        "tester": "Software Test Engineer"
    }
    
    # Get current role
    current_role = st.session_state.get("selected_role", "analyst")
    
    # Load initial role if not already loaded
    if st.session_state.get("role_data") is None:
        try:
            role_data = load_role(current_role)
            st.session_state.role_data = role_data.model_dump()
        except Exception as e:
            st.error(f"Failed to load initial role '{current_role}': {str(e)}")
    
    # Role selection selectbox
    selected_role = st.selectbox(
        "Select Role",
        options=list(available_roles.keys()),
        format_func=lambda x: available_roles[x],
        index=list(available_roles.keys()).index(current_role) if current_role in available_roles else 0,
        key="role_selectbox"
    )
    
    # Check if role changed
    if selected_role != current_role:
        # Load the new role and store in session state
        try:
            role_data = load_role(selected_role)
            st.session_state.selected_role = selected_role
            st.session_state.role_data = role_data.model_dump()
            st.rerun()
        except Exception as e:
            st.error(f"Failed to load role '{selected_role}': {str(e)}")
    
    # Display current role info (use selected_role which may have been updated)
    active_role = st.session_state.get("selected_role", "analyst")
    if active_role in available_roles:
        role_name = available_roles[active_role]
        st.markdown(f"""
        <div style='padding: 0.75rem; background-color: #343541; border-radius: 6px; border: 1px solid #565869; margin-top: 0.5rem;'>
            <div style='color: #8e8ea0; font-size: 0.75rem; margin-bottom: 0.25rem;'>Active Role</div>
            <div style='color: #ececf1; font-size: 0.9rem; font-weight: 500;'>{role_name}</div>
        </div>
        """, unsafe_allow_html=True)


def _render_model_selection():
    """Render model selection UI with lock mechanism."""
    st.markdown("<div style='margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Model Selection</h3></div>", unsafe_allow_html=True)
    
    # Check authentication first
    if not st.session_state.authenticated:
        st.info("Please log in to select a model")
        return
    
    # Determine if model can be changed
    current_session = get_current_session()
    has_messages = len(current_session.get("messages", [])) > 0 or st.session_state.memory.get_history_length() > 0
    model_locked = has_messages
    
    # Display current model
    current_model_info = next((m for m in ALL_MODELS if m["id"] == st.session_state.selected_model), None)
    if current_model_info:
        st.markdown(f"""
        <div style='padding: 0.75rem; background-color: #343541; border-radius: 6px; border: 1px solid #565869; margin-bottom: 1rem;'>
            <div style='color: #8e8ea0; font-size: 0.75rem; margin-bottom: 0.25rem;'>Current Model</div>
            <div style='color: #ececf1; font-size: 0.9rem; font-weight: 500;'>{current_model_info['name']}</div>
            {f"<div style='color: #8e8ea0; font-size: 0.7rem; margin-top: 0.25rem;'>Model locked (session started)</div>" if model_locked else ""}
        </div>
        """, unsafe_allow_html=True)
    
    # Model selection button
    if not model_locked:
        if st.button("Change Model", use_container_width=True, key="change_model_button"):
            st.session_state.show_model_selector = not st.session_state.show_model_selector
            st.rerun()
        
        # Model selector dropdown
        if st.session_state.show_model_selector:
            # Group models by provider
            for provider in AVAILABLE_MODELS:
                st.markdown(f"**{provider}**")
                for model_id in AVAILABLE_MODELS[provider]:
                    # Find the model info from ALL_MODELS
                    model_info = next((m for m in ALL_MODELS if m["id"] == model_id), None)
                    if model_info:
                        if st.button(f"  {model_info['name']}", key=f"model_{model_info['id']}", use_container_width=True):
                            st.session_state.selected_model = model_info["id"]
                            st.session_state.show_model_selector = False
                            st.rerun()
    else:
        # Show warning if user tries to change model after session started
        if st.button("Change Model", use_container_width=True, key="change_model_button_locked"):
            st.session_state.model_change_warning = "Model cannot be changed after the session has started. Please create a new session to use a different model."
            st.rerun()
    
    # Display warning if set
    if st.session_state.model_change_warning:
        st.warning(st.session_state.model_change_warning)
        # Auto-dismiss warning after 3 seconds
        import time
        time.sleep(3)
        st.session_state.model_change_warning = None
        st.rerun()


def _render_session_management():
    """Render session management UI (create new, switch sessions)."""
    st.markdown("<div style='margin-top: 1.5rem; margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Sessions</h3></div>", unsafe_allow_html=True)
    
    # Check authentication first
    if not st.session_state.authenticated:
        st.info("Please log in to manage sessions")
        return
    
    # Create new session button
    if st.button("Add New Session", use_container_width=True, key="new_session_button"):
        create_new_session()
        st.rerun()
    
    # List existing sessions
    if st.session_state.sessions:
        st.markdown("<div style='margin-top: 0.5rem; margin-bottom: 0.5rem;'><div style='color: #8e8ea0; font-size: 0.75rem;'>Recent Sessions</div></div>", unsafe_allow_html=True)
        for session_id, session in list(st.session_state.sessions.items())[:5]:  # Show last 5 sessions
            is_current = session_id == st.session_state.current_session_id
            
            # Create columns for session button and delete button
            col1, col2 = st.columns([4, 1])
            
            with col1:
                button_label = f"{'▶ ' if is_current else ''}{session['title']}"
                if st.button(button_label, key=f"session_{session_id}", use_container_width=True):
                    if not is_current:
                        # Save current session before switching
                        if st.session_state.current_session_id and st.session_state.current_session_id in st.session_state.sessions:
                            prev_session = st.session_state.sessions[st.session_state.current_session_id]
                            prev_session["messages"] = st.session_state.memory.get_messages()
                            prev_session["model"] = st.session_state.selected_model
                            st.session_state.sessions[st.session_state.current_session_id] = prev_session
                        
                        # Load new session
                        st.session_state.current_session_id = session_id
                        session = st.session_state.sessions[session_id]
                        st.session_state.memory.load_messages(session.get("messages", []), reset=True)
                        if session.get("model"):
                            st.session_state.selected_model = session["model"]
                        
                        # Save conversations if persistence is enabled
                        if st.session_state.conversation_persistence_enabled and st.session_state.conversation_storage:
                            st.session_state.conversation_storage.save_sessions(st.session_state.sessions)
                        
                        st.rerun()
            
            with col2:
                # Delete button with centered X symbol
                if st.button("✖", key=f"delete_session_{session_id}", help="Delete this conversation", use_container_width=True):
                    # Delete the session
                    if session_id in st.session_state.sessions:
                        # If deleting current session, switch to another or create new
                        if session_id == st.session_state.current_session_id:
                            # Remove current session
                            del st.session_state.sessions[session_id]
                            # Switch to another session or create new
                            if st.session_state.sessions:
                                # Switch to the most recent session
                                sorted_sessions = sorted(
                                    st.session_state.sessions.values(),
                                    key=lambda x: x.get("created_at", ""),
                                    reverse=True
                                )
                                if sorted_sessions:
                                    new_session = sorted_sessions[0]
                                    st.session_state.current_session_id = new_session["id"]
                                    st.session_state.memory.load_messages(new_session.get("messages", []), reset=True)
                                    if new_session.get("model"):
                                        st.session_state.selected_model = new_session["model"]
                            else:
                                # No sessions left, create new one
                                create_new_session()
                        else:
                            # Just delete the session
                            del st.session_state.sessions[session_id]
                        
                        # Save conversations if persistence is enabled
                        if st.session_state.conversation_persistence_enabled and st.session_state.conversation_storage:
                            st.session_state.conversation_storage.save_sessions(st.session_state.sessions)
                        
                        st.success(f"Conversation '{session['title']}' deleted")
                        st.rerun()


def _render_srs_export():
    """Render SRS export button."""
    st.markdown("<div style='margin-top: 1.5rem; margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Export</h3></div>", unsafe_allow_html=True)
    
    if st.button("Export SRS (Markdown)", use_container_width=True, key="export_srs_button"):
        # Check authentication first
        if not st.session_state.authenticated:
            st.warning("Please log in first to export SRS")
            st.rerun()
            return
        
        # Check if there are assistant messages to generate SRS from
        messages = st.session_state.memory.get_messages(include_system=False)
        assistant_messages = [msg.get("content", "") for msg in messages if msg.get("role") == "assistant"]
        
        if not assistant_messages:
            st.warning("No assistant messages found. Please have a conversation with the AI first.")
        else:
            # Generate SRS from conversation
            try:
                with st.spinner("Generating SRS document..."):
                    client = get_centralized_client()
                    
                    srs_content = generate_ieee830_srs_from_conversation(
                        client,
                        assistant_messages,
                        model=st.session_state.selected_model
                    )
                    st.session_state.generated_srs = srs_content
                    st.session_state.srs_generation_error = None
                    st.success("SRS document generated successfully!")
            except Exception as e:
                st.session_state.srs_generation_error = str(e)
                st.error(f"Error generating SRS: {str(e)}")
    
    # Display generated SRS if available
    if st.session_state.generated_srs:
        st.download_button(
            label="Download SRS",
            data=st.session_state.generated_srs,
            file_name="srs_document.md",
            mime="text/markdown",
            use_container_width=True,
            key="download_srs_button"
        )


def _render_context_summarization():
    """Render context summarization button."""
    st.markdown("<div style='margin-top: 1.5rem; margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Context</h3></div>", unsafe_allow_html=True)
    
    if st.button("Summarize Context", use_container_width=True, key="summarize_context_button"):
        # Check authentication first
        if not st.session_state.authenticated:
            st.warning("🔒 Please log in first to summarize context")
            st.rerun()
            return
        
        # Check if there are enough messages to summarize
        history_length = st.session_state.memory.get_history_length()
        if history_length <= 10:
            st.warning("Not enough messages to summarize. Please have more than 10 messages in the conversation.")
        else:
            # Summarize old messages
            try:
                with st.spinner("Summarizing conversation..."):
                    client = get_centralized_client()
                    success = st.session_state.memory.summarize_old_messages(
                        client,
                        model=st.session_state.selected_model
                    )
                    if success:
                        st.success("Conversation summarized successfully!")
                        st.rerun()
                    else:
                        st.warning("Summarization was not performed. This may be because there are not enough messages or a summary already exists.")
            except Exception as e:
                st.error(f"Error summarizing conversation: {str(e)}")


def _render_conversation_persistence():
    """Render conversation persistence settings."""
    st.markdown("<div style='margin-top: 1.5rem; margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Storage</h3></div>", unsafe_allow_html=True)
    
    # Check authentication first
    if not st.session_state.authenticated:
        st.info("🔒 Please log in to manage conversation storage")
        return
    
    # Conversation persistence toggle
    persistence_enabled = st.toggle(
        "Persist Conversations",
        value=st.session_state.conversation_persistence_enabled,
        key="persistence_toggle",
        help="Save conversations to disk (disabled by default)"
    )
    
    # Update persistence state
    if persistence_enabled != st.session_state.conversation_persistence_enabled:
        st.session_state.conversation_persistence_enabled = persistence_enabled
        
        # If enabling persistence, ensure conversation_storage is initialized
        if persistence_enabled and st.session_state.authenticated and st.session_state.current_user:
            if not st.session_state.conversation_storage:
                st.session_state.conversation_storage = ConversationStorage(st.session_state.current_user["username"])
            
            # Save current sessions
            if st.session_state.sessions:
                st.session_state.conversation_storage.save_sessions(st.session_state.sessions)
                st.success("Conversations saved successfully!")
        elif not persistence_enabled:
            st.info("Conversation persistence disabled. Conversations will not be saved.")
        st.rerun()
    
    # Display storage info if persistence is enabled
    if persistence_enabled and st.session_state.conversation_storage:
        storage_info = st.session_state.conversation_storage.get_storage_info()
        st.markdown(f"""
        <div style='padding: 0.5rem; background-color: #343541; border-radius: 6px; border: 1px solid #565869; margin-top: 0.5rem;'>
            <div style='color: #8e8ea0; font-size: 0.7rem; margin-bottom: 0.25rem;'>Storage Usage</div>
            <div style='color: #ececf1; font-size: 0.8rem;'>{storage_info['session_count']} conversations</div>
            <div style='color: #8e8ea0; font-size: 0.7rem; margin-top: 0.25rem;'>{storage_info['storage_size'] / 1024:.1f} KB / {storage_info['max_storage_size'] / 1024:.0f} KB</div>
        </div>
        """, unsafe_allow_html=True)


def _render_file_upload():
    """Render file upload component."""
    render_file_upload()

