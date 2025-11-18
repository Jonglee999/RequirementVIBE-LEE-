"""
UI Styles - ChatGPT-like Dark Theme

This module contains custom CSS styling for the Streamlit application.
It provides a dark, modern interface similar to ChatGPT.
"""

import streamlit as st


def get_custom_css() -> str:
    """
    Get custom CSS styles for the application.
    
    Returns:
        str: CSS styles as a string
    """
    return """
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
    
    /* Session management columns - align buttons at the top */
    /* Target columns that contain session buttons specifically */
    section[data-testid="stSidebar"] [data-testid="column"][class*="stColumn"],
    section[data-testid="stSidebar"] [data-baseweb="column"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        vertical-align: top !important;
    }
    
    /* Container for session button row - ensure top alignment */
    section[data-testid="stSidebar"] [data-testid="column"][class*="stColumn"] > div,
    section[data-testid="stSidebar"] [data-baseweb="column"] > div {
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        align-content: flex-start !important;
    }
    
    /* Ensure buttons in columns align at top when text wraps */
    section[data-testid="stSidebar"] [data-testid="column"] .stButton,
    section[data-testid="stSidebar"] [data-baseweb="column"] .stButton {
        align-self: stretch !important;
        display: flex !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    
    /* Base button styling for session buttons - ensure consistent height and alignment */
    section[data-testid="stSidebar"] [data-testid="column"] .stButton > button,
    section[data-testid="stSidebar"] [data-baseweb="column"] .stButton > button {
        width: 100% !important;
        min-height: 38px !important;
        height: auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        padding: 0.5rem 0.75rem !important;
        line-height: 1.4 !important;
        vertical-align: top !important;
        margin: 0 !important;
    }
    
    /* Session button (first column) - left align text, allow wrapping, align at top */
    section[data-testid="stSidebar"] [data-testid="column"]:first-of-type .stButton > button,
    section[data-testid="stSidebar"] [data-baseweb="column"]:first-of-type .stButton > button {
        justify-content: flex-start !important;
        align-items: flex-start !important;
        text-align: left !important;
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    
    /* Delete button - center the X symbol by targeting buttons in the second column, align at top */
    section[data-testid="stSidebar"] [data-testid="column"]:nth-of-type(2) .stButton > button,
    section[data-testid="stSidebar"] [data-baseweb="column"]:nth-of-type(2) .stButton > button {
        text-align: center !important;
        justify-content: center !important;
        align-items: center !important;
        padding: 0.5rem !important;
        font-size: 1rem !important;
        line-height: 1 !important;
        min-height: 38px !important;
        height: auto !important;
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
    
    /* Authentication form styling */
    .auth-container {
        max-width: 400px;
        margin: 4rem auto;
        padding: 2rem;
        background-color: #202123;
        border-radius: 12px;
        border: 1px solid #565869;
    }
    
    .auth-title {
        color: #ececf1;
        font-size: 1.75rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .auth-subtitle {
        color: #8e8ea0;
        font-size: 0.9rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .auth-input {
        background-color: #343541 !important;
        color: #ececf1 !important;
        border: 1px solid #565869 !important;
    }
    
    .auth-button {
        width: 100%;
        background-color: #10a37f !important;
        color: #ececf1 !important;
        border: none !important;
        padding: 0.75rem !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }
    
    .auth-button:hover {
        background-color: #0d8f6e !important;
    }
    
    .auth-link {
        color: #10a37f;
        text-decoration: none;
        cursor: pointer;
    }
    
    .auth-link:hover {
        text-decoration: underline;
    }
    
    .auth-error {
        background-color: #543636;
        color: #f5c6cb;
        padding: 0.75rem;
        border-radius: 6px;
        border-left: 4px solid #ef4444;
        margin-bottom: 1rem;
    }
    
    .auth-success {
        background-color: #2d5016;
        color: #c3e6cb;
        padding: 0.75rem;
        border-radius: 6px;
        border-left: 4px solid #10a37f;
        margin-bottom: 1rem;
    }
</style>
"""


def apply_styles():
    """
    Applies custom CSS styling to the Streamlit application to create a ChatGPT-like dark theme.
    This function should be called once at the beginning of the application.
    """
    st.markdown(get_custom_css(), unsafe_allow_html=True)

