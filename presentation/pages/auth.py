"""
Authentication Pages

This module contains the login, registration, and password reset page components for the Streamlit application.
"""

# Add project root to Python path for Streamlit Cloud compatibility
# This MUST be done before any other imports
import sys
import os

def _find_project_root():
    """Find the project root by looking for app.py or requirements.txt."""
    # Start from this file's directory
    current = os.path.abspath(__file__)
    checked_paths = []
    
    # Go up the directory tree looking for project root markers
    for _ in range(6):  # Max 6 levels up (to handle /mount/src/requirementvibe structure)
        current = os.path.dirname(current)
        checked_paths.append(current)
        
        # Check for project root markers
        has_app = os.path.exists(os.path.join(current, 'app.py'))
        has_requirements = os.path.exists(os.path.join(current, 'requirements.txt'))
        has_domain = os.path.exists(os.path.join(current, 'domain'))
        
        if (has_app or has_requirements) and has_domain:
            # Double-check: verify domain/conversations exists
            if os.path.exists(os.path.join(current, 'domain', 'conversations')):
                return current
    
    # Fallback: calculate from file path (presentation/pages/auth.py -> project_root)
    fallback = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return fallback

# Find and add project root to sys.path
_project_root = _find_project_root()

# Add project root and all possible parent directories to sys.path
_paths_to_add = []
if _project_root:
    _paths_to_add.append(_project_root)
    # Also try parent directories (for /mount/src/requirementvibe cases)
    _current = _project_root
    for _ in range(3):  # Check up to 3 levels up
        _current = os.path.dirname(_current)
        if _current and os.path.exists(os.path.join(_current, 'domain')):
            _paths_to_add.append(_current)

# Add all valid paths to sys.path
for path in _paths_to_add:
    if path and path not in sys.path:
        sys.path.insert(0, path)

# Also check current working directory and common Streamlit Cloud paths
_cwd = os.getcwd()
if _cwd and _cwd not in sys.path:
    if os.path.exists(os.path.join(_cwd, 'domain')):
        sys.path.insert(0, _cwd)

import streamlit as st

# Import with multiple fallback attempts
try:
    from domain.conversations.service import ConversationStorage
except ModuleNotFoundError as e:
    # Try to find domain package in sys.path
    _found = False
    for path in sys.path:
        if not path:
            continue
        domain_path = os.path.join(path, 'domain', 'conversations')
        if os.path.exists(domain_path):
            # Try importing again
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "domain.conversations.service",
                    os.path.join(path, 'domain', 'conversations', 'service.py')
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    ConversationStorage = module.ConversationStorage
                    _found = True
                    break
            except Exception:
                continue
    
    if not _found:
        # If all attempts fail, raise a more informative error
        _relevant_paths = [p for p in sys.path[:10] if p and ('requirement' in p.lower() or 'mount' in p.lower() or 'src' in p.lower())]
        raise ModuleNotFoundError(
            f"Could not find 'domain.conversations' module. "
            f"Project root found: {_project_root}. "
            f"Relevant paths checked: {_relevant_paths}. "
            f"Current file: {__file__}"
        ) from e

from application.email.service import get_email_service


def show_login_page():
    """
    Display the login page with username and password fields.
    
    This function:
    1. Displays a styled login form matching the app's dark theme
    2. Handles user login attempts
    3. Shows error messages for failed login attempts
    4. Provides links to registration and password reset
    5. Loads previous conversations on successful login
    """
    st.markdown("""
    <div style='text-align: center; padding: 4rem 1rem 2rem 1rem; max-width: 500px; margin: 0 auto;'>
        <h1 style='color: #ececf1; font-size: 2.5rem; font-weight: 600; margin-bottom: 0.5rem;'>Welcome to UESTC MBSE RequirementVIBE, Log in to explore endless possibilities</h1>
        <p style='color: #8e8ea0; font-size: 1rem; margin-bottom: 2rem;'>Sign in to access your requirements</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Login form
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username", help="Enter your username")
                password = st.text_input("Password", type="password", key="login_password", help="Enter your password")
                submit_button = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                
                if submit_button:
                    if username and password:
                        success, message, user_data = st.session_state.auth_manager.login_user(username, password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.current_user = user_data
                            # Initialize user-specific conversation storage
                            st.session_state.conversation_storage = ConversationStorage(user_data["username"])
                            # Load previous conversations if they exist (always load on login)
                            # Note: Persistence toggle controls saving, not loading
                            loaded_sessions = st.session_state.conversation_storage.load_sessions()
                            if loaded_sessions:
                                st.session_state.sessions = loaded_sessions
                                # Restore session counter
                                if st.session_state.sessions:
                                    st.session_state.session_counter = len(st.session_state.sessions)
                                # Restore current session if available
                                if st.session_state.sessions:
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
                                st.info(f"✅ Loaded {len(loaded_sessions)} previous conversations")
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please enter both username and password")
            
            # Links to registration and password reset
            st.markdown("""
            <div style='text-align: center; margin-top: 1.5rem;'>
                <p style='color: #8e8ea0; font-size: 0.9rem;'>
                    Don't have an account? 
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                # Toggle to registration
                if st.button("Switch to Registration", use_container_width=True, type="secondary"):
                    st.session_state.show_register = True
                    st.session_state.show_password_reset = False
                    st.rerun()
            
            with col_btn2:
                # Toggle to password reset
                if st.button("Forgot Password?", use_container_width=True, type="secondary"):
                    st.session_state.show_password_reset = True
                    st.session_state.show_register = False
                    st.rerun()


def show_register_page():
    """
    Display the registration page with email verification.
    
    This function:
    1. Displays a styled registration form matching the app's dark theme
    2. Validates email format
    3. Sends verification code to email
    4. Verifies code before registration
    5. Handles user registration
    6. Provides a link to the login page
    """
    st.markdown("""
    <div style='text-align: center; padding: 4rem 1rem 2rem 1rem; max-width: 500px; margin: 0 auto;'>
        <h1 style='color: #ececf1; font-size: 2.5rem; font-weight: 600; margin-bottom: 0.5rem;'>Create Account</h1>
        <p style='color: #8e8ea0; font-size: 1rem; margin-bottom: 2rem;'>Register to start managing your requirements</p>
    </div>
    """, unsafe_allow_html=True)
    
    email_service = get_email_service()
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Initialize verification state
            if "verification_code_sent" not in st.session_state:
                st.session_state.verification_code_sent = False
            if "email_verified" not in st.session_state:
                st.session_state.email_verified = False
            if "registration_email" not in st.session_state:
                st.session_state.registration_email = ""

            # Step 1: Email input (verification disabled)
            if not st.session_state.email_verified:
                st.markdown("### Step 1: Provide Email")
                with st.form("email_input_form"):
                    email = st.text_input("Email Address", key="register_email", help="Enter your email address (required)")
                    proceed_button = st.form_submit_button("Continue", use_container_width=True, type="primary")
                    if proceed_button:
                        if email:
                            # Basic validation only
                            is_valid, error_msg = email_service.validate_email(email)
                            if is_valid:
                                st.session_state.registration_email = email.strip()
                                st.session_state.email_verified = True
                                st.success("Email format validated. You can proceed with registration.")
                                st.rerun()
                            else:
                                st.error(error_msg)
                        else:
                            st.error("Please enter your email address")

            # Step 2: Registration form (after basic email validation)
            if st.session_state.email_verified:
                st.markdown("### Step 2: Complete Registration")
                with st.form("register_form"):
                    username = st.text_input("Username", key="register_username", help="Choose a unique username")
                    password = st.text_input("Password", type="password", key="register_password", help="At least 6 characters")
                    confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password", help="Re-enter your password")
                    submit_button = st.form_submit_button("Sign Up", use_container_width=True, type="primary")

                    if submit_button:
                        if not username:
                            st.error("Username is required")
                        elif not password:
                            st.error("Password is required")
                        elif len(password) < 6:
                            st.error("Password must be at least 6 characters long")
                        elif password != confirm_password:
                            st.error("Passwords do not match")
                        else:
                            success, message = st.session_state.auth_manager.register_user(
                                username,
                                password,
                                st.session_state.registration_email
                            )
                            if success:
                                st.success(message)
                                st.info("You can now sign in with your credentials")
                                # Reset state
                                st.session_state.email_verified = False
                                st.session_state.registration_email = ""
                                st.session_state.show_register = False
                                st.rerun()
                            else:
                                st.error(message)

            # Link to login
            st.markdown("""
            <div style='text-align: center; margin-top: 1.5rem;'>
                <p style='color: #8e8ea0; font-size: 0.9rem;'>
                    Already have an account? 
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Toggle to login
            if st.button("Switch to Login", use_container_width=True, type="secondary"):
                st.session_state.show_register = False
                st.session_state.show_password_reset = False
                st.session_state.verification_code_sent = False
                st.session_state.email_verified = False
                st.session_state.registration_email = ""
                st.rerun()


def show_password_reset_page():
    """
    Display the password reset page with email verification.
    
    This function:
    1. Displays a styled password reset form matching the app's dark theme
    2. Validates email and checks if user exists
    3. Sends verification code to email
    4. Verifies code
    5. Allows password reset with confirmation
    6. Provides a link to the login page
    """
    st.markdown("""
    <div style='text-align: center; padding: 4rem 1rem 2rem 1rem; max-width: 500px; margin: 0 auto;'>
        <h1 style='color: #ececf1; font-size: 2.5rem; font-weight: 600; margin-bottom: 0.5rem;'>🔐 Reset Password</h1>
        <p style='color: #8e8ea0; font-size: 1rem; margin-bottom: 2rem;'>Reset your password using email verification</p>
    </div>
    """, unsafe_allow_html=True)
    
    email_service = get_email_service()
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Password Reset")
            st.markdown(
                """
                Email-based password reset is temporarily disabled.\
                If you need to change your password, please contact \
                **wee235929@gmail.com** with your account details.
                """
            )
            
            if st.button("Back to Login", use_container_width=True, type="primary"):
                st.session_state.show_password_reset = False
                st.rerun()
