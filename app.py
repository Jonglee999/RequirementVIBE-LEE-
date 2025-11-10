import streamlit as st
import os
from openai import OpenAI  # DeepSeek API uses OpenAI-compatible SDK

# Set page title and configuration
st.set_page_config(
    page_title="ReqVibe - AI Requirements Analyst",
    page_icon="📋",
    layout="wide"
)

# Title
st.title("ReqVibe - AI Requirements Analyst")

# Initialize DeepSeek API client
@st.cache_resource
def get_deepseek_client():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("⚠️ DEEPSEEK_API_KEY environment variable is not set. Please set it before running the app.")
        st.stop()
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation history
if st.session_state.messages:
    st.subheader("Conversation History")
    # Create a container for chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    st.divider()

# Text input box
user_input = st.text_area(
    "Enter your requirement or question:",
    height=150,
    placeholder="Type your requirement here...",
    key="user_input"
)

# Ask button
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    ask_button = st.button("Ask", type="primary", use_container_width=True)

# Handle button click
if ask_button and user_input.strip():
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    try:
        # Get DeepSeek API client
        client = get_deepseek_client()
        
        # Prepare messages with system prompt and full conversation history
        system_prompt = "You are ReqVibe, a professional requirements engineer. Use Volere template structure."
        api_messages = [{"role": "system", "content": system_prompt}]
        # Add all conversation history
        api_messages.extend(st.session_state.messages)
        
        # Show loading indicator
        with st.spinner("Analyzing requirement..."):
            # Call DeepSeek API with full conversation history
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=api_messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            # Get AI response
            ai_response = response.choices[0].message.content
            
            # Add AI response to session state
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.session_state.messages.append({"role": "assistant", "content": f"Sorry, an error occurred: {str(e)}"})
    
    # Clear the input box by rerunning
    st.rerun()

# Clear conversation button (shown only if there are messages)
if st.session_state.messages:
    st.divider()
    if st.button("Clear Conversation", type="secondary"):
        st.session_state.messages = []
        st.rerun()

