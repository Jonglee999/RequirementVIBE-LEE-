"""
Sidebar UI Component for ReqVibe

This module contains the sidebar UI components including:
- Model selection
- Session management
- SRS export
- Conversation persistence settings
"""

# Add project root to Python path for Streamlit Cloud compatibility
import sys
import os

# Get the project root (parent of presentation/components)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
from domain.sessions.service import create_new_session, get_current_session, update_session_title
from domain.conversations.service import ConversationStorage
from config.models import ALL_MODELS, AVAILABLE_MODELS
from core.models.memory import ShortTermMemory
from domain.documents.srs import generate_ieee830_srs_from_conversation
from infrastructure.llm.client import get_centralized_client
from presentation.components.file_upload import render_file_upload
from domain.prompts.service import load_role


def render_sidebar():
    """
    Render the sidebar with all UI components.
    
    This function renders:
    1. Header with app title
    2. User info and logout button (if authenticated)
    3. Model selection UI
    4. Session management UI
    5. SRS export button
    6. Conversation persistence settings
    """
    with st.sidebar:
        # Header with icon
        import os
        
        # Try to find and display the icon
        # Get the project root directory (two levels up from this file)
        current_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(current_dir))
        icon_path = os.path.join(project_root, "RequirementVIBEICON.png")
        
        # Check if icon exists and display it
        if os.path.exists(icon_path):
            try:
                # Read and encode the image as base64 for embedding in HTML
                import base64
                with open(icon_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode()
                
                # Display icon centered above text using HTML with base64 encoding
                st.markdown(f"""
                <div style='text-align: center; padding: 1rem 0 0.75rem 0; width: 100%;'>
                    <img src="data:image/png;base64,{img_data}" style='width: 60px; height: 60px; display: block; margin: 0 auto;' />
                </div>
                """, unsafe_allow_html=True)
                
                # Display title below icon, centered
                st.markdown("""
                <div style='text-align: center; padding: 0.5rem 0 1.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1rem;'>
                    <h2 style='color: #ececf1; margin: 0; font-size: 1.5rem;'>UESTC-MBSE Requirement Assistant</h2>
                    <p style='color: #8e8ea0; margin: 0.25rem 0 0 0; font-size: 0.85rem;'>AI Requirements Analyst</p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                # Fallback if icon can't be loaded
                st.markdown("""
                <div style='padding: 1rem 0 1.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1rem; text-align: center;'>
                    <h2 style='color: #ececf1; margin: 0; font-size: 1.5rem;'>UESTC-MBSE Requirement Assistant</h2>
                    <p style='color: #8e8ea0; margin: 0.25rem 0 0 0; font-size: 0.85rem;'>AI Requirements Analyst</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Fallback if icon file doesn't exist
            st.markdown("""
            <div style='padding: 1rem 0 1.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1rem; text-align: center;'>
                <h2 style='color: #ececf1; margin: 0; font-size: 1.5rem;'>UESTC-MBSE Requirement Assistant</h2>
                <p style='color: #8e8ea0; margin: 0.25rem 0 0 0; font-size: 0.85rem;'>AI Requirements Analyst</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        
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
    """Render model selection UI with dropdown similar to role selection."""
    st.markdown("<div style='margin-bottom: 1rem;'><h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;'>Model Selection</h3></div>", unsafe_allow_html=True)
    
    # Check authentication first
    if not st.session_state.authenticated:
        st.info("Please log in to select a model")
        return
    
    # Determine if model can be changed
    current_session = get_current_session()
    has_messages = len(current_session.get("messages", [])) > 0 or st.session_state.memory.get_history_length() > 0
    model_locked = has_messages
    
    # Get current model
    current_model = st.session_state.get("selected_model", ALL_MODELS[0]["id"] if ALL_MODELS else None)
    
    # Create model options with display names (provider - model name)
    model_options = []
    model_display_map = {}
    
    for model_info in ALL_MODELS:
        # Create display name: "Provider - Model Name"
        display_name = f"{model_info['provider']} - {model_info['name']}"
        model_options.append(model_info['id'])
        model_display_map[model_info['id']] = display_name
    
    # Find current index
    current_index = 0
    if current_model and current_model in model_options:
        current_index = model_options.index(current_model)
    
    # Model selection dropdown (similar to role selection)
    if not model_locked:
        selected_model_id = st.selectbox(
            "Select Model",
            options=model_options,
            format_func=lambda x: model_display_map.get(x, x),
            index=current_index,
            key="model_selectbox"
        )
        
        # Check if model changed
        if selected_model_id != current_model:
            st.session_state.selected_model = selected_model_id
            st.rerun()
    else:
        # Show disabled selectbox when locked
        current_model_info = next((m for m in ALL_MODELS if m["id"] == current_model), None)
        if current_model_info:
            display_name = f"{current_model_info['provider']} - {current_model_info['name']}"
            st.selectbox(
                "Select Model",
                options=[current_model] if current_model else [],
                format_func=lambda x: display_name,
                index=0,
                key="model_selectbox_locked",
                disabled=True
            )
            st.caption("Model locked (session started). Create a new session to change model.")
    
    # Display current model info
    current_model_info = next((m for m in ALL_MODELS if m["id"] == current_model), None)
    if current_model_info:
        st.markdown(f"""
        <div style='padding: 0.75rem; background-color: #343541; border-radius: 6px; border: 1px solid #565869; margin-top: 0.5rem;'>
            <div style='color: #8e8ea0; font-size: 0.75rem; margin-bottom: 0.25rem;'>Active Model</div>
            <div style='color: #ececf1; font-size: 0.9rem; font-weight: 500;'>{current_model_info['name']}</div>
            <div style='color: #8e8ea0; font-size: 0.7rem; margin-top: 0.25rem;'>{current_model_info['provider']}</div>
        </div>
        """, unsafe_allow_html=True)


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
    
    # Check authentication first - only show export functionality if logged in
    if not st.session_state.authenticated:
        st.info("🔒 Please log in to export SRS")
        return
    
    if st.button("Export SRS (Markdown)", use_container_width=True, key="export_srs_button"):
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
    
    # Display generated SRS if available (only when authenticated)
    if st.session_state.authenticated and st.session_state.generated_srs:
        st.download_button(
            label="Download SRS",
            data=st.session_state.generated_srs,
            file_name="srs_document.md",
            mime="text/markdown",
            use_container_width=True,
            key="download_srs_button"
        )


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

