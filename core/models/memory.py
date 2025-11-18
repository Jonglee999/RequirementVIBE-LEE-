"""
Short-term memory management for ReqVibe.
Handles chat history, requirements storage, and token counting.
"""

import streamlit as st
from typing import List, Dict, Any, Optional

# Try to import tiktoken, but make it optional
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None


class ShortTermMemory:
    """
    Short-term memory class for managing chat history, requirements, and token counting.
    Automatically initializes in Streamlit session_state if not exists.
    """
    
    def __init__(self):
        """
        Initialize ShortTermMemory with empty chat history, requirements, and token count.
        """
        self.chat_history: List[Dict[str, str]] = []
        self.requirements: List[Dict[str, Any]] = []
        self.token_count: int = 0
        self._encoding = None
    
    @staticmethod
    def get_or_create(session_state_key: str = "memory") -> 'ShortTermMemory':
        """
        Get existing memory from session_state or create new one.
        
        Args:
            session_state_key: Key to use in session_state (default: "memory")
        
        Returns:
            ShortTermMemory: Memory instance from session_state
        """
        if session_state_key not in st.session_state:
            st.session_state[session_state_key] = ShortTermMemory()
        return st.session_state[session_state_key]
    
    def _get_encoding(self):
        """Get or create tiktoken encoding for token counting."""
        if not TIKTOKEN_AVAILABLE:
            return None
        if self._encoding is None:
            try:
                # Use cl100k_base encoding (used by GPT-3.5 and GPT-4)
                self._encoding = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                print(f"Warning: Failed to load tiktoken encoding: {e}")
                return None
        return self._encoding
    
    def estimate_tokens(self, messages_list: List[Dict[str, str]]) -> int:
        """
        Estimate the number of tokens in a list of messages.
        
        This function uses tiktoken for accurate token counting if available,
        otherwise falls back to a simple approximation (4 characters per token).
        
        Args:
            messages_list: List of message dictionaries with 'role' and 'content' keys
        
        Returns:
            int: Estimated number of tokens
        """
        if not messages_list:
            return 0
        
        encoding = self._get_encoding()
        if encoding:
            # Use tiktoken for accurate counting
            total_tokens = 0
            for message in messages_list:
                role = message.get("role", "")
                content = message.get("content", "")
                # Count tokens for role and content, plus overhead for message structure
                total_tokens += len(encoding.encode(role))
                total_tokens += len(encoding.encode(content))
                total_tokens += 4  # Overhead for message structure (role, content keys, etc.)
            return total_tokens
        else:
            # Fallback: approximate token count (rough estimate)
            # GPT models typically use ~4 characters per token
            total_chars = sum(len(str(msg.get("role", "")) + str(msg.get("content", ""))) for msg in messages_list)
            return total_chars // 4
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the chat history.
        
        Args:
            role: Message role ('user', 'assistant', 'system')
            content: Message content
        """
        self.chat_history.append({"role": role, "content": content})
        # Update token count
        self.token_count = self.estimate_tokens(self.chat_history)
    
    def get_history_length(self) -> int:
        """
        Get the number of messages in the chat history.
        
        Returns:
            int: Number of messages
        """
        return len(self.chat_history)
    
    def get_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        """
        Get all messages from the chat history.
        
        Args:
            include_system: Whether to include system messages (default: True)
        
        Returns:
            List[Dict[str, str]]: List of message dictionaries
        """
        if include_system:
            return self.chat_history.copy()
        else:
            return [msg for msg in self.chat_history if msg.get("role") != "system"]
    
    def load_messages(self, messages: List[Dict[str, str]], reset: bool = True) -> None:
        """
        Load messages into the chat history.
        
        Args:
            messages: List of message dictionaries to load
            reset: Whether to reset the chat history before loading (default: True)
        """
        if reset:
            self.chat_history = []
            self.requirements = []
            self.token_count = 0
        
        for message in messages:
            self.chat_history.append(message)
        
        # Update token count
        self.token_count = self.estimate_tokens(self.chat_history)
    
    def add_requirement(self, requirement: Dict[str, Any]) -> None:
        """
        Add a requirement to the requirements list.
        
        Args:
            requirement: Requirement dictionary with 'id', 'text', 'volere' keys
        """
        self.requirements.append(requirement)
    
    def get_requirements(self) -> List[Dict[str, Any]]:
        """
        Get all requirements from the requirements list.
        
        Returns:
            List[Dict[str, Any]]: List of requirement dictionaries
        """
        return self.requirements.copy()
    
    def get_context_for_api(self, max_tokens: int = 3500, client=None, model: str = None) -> List[Dict[str, str]]:
        """
        Get conversation context optimized for API calls.
        
        This function:
        1. Retrieves recent messages that fit within the token limit
        2. Ensures we don't exceed API token limits
        
        Args:
            max_tokens: Maximum number of tokens for context (default: 3500)
            client: Optional API client (kept for backward compatibility, not used)
            model: Optional model name (kept for backward compatibility, not used)
        
        Returns:
            List[Dict[str, str]]: List of message dictionaries optimized for API calls
        """
        # Get all messages (excluding system messages for context calculation)
        messages = self.get_messages(include_system=False)
        
        if not messages:
            return []
        
        # Estimate tokens for all messages
        total_tokens = self.estimate_tokens(messages)
        
        # If within token limit, return all messages
        if total_tokens <= max_tokens:
            return messages
        
        # Return recent messages that fit within token limit
        # Start from the end and work backwards
        context_messages = []
        current_tokens = 0
        
        for message in reversed(messages):
            message_tokens = self.estimate_tokens([message])
            if current_tokens + message_tokens <= max_tokens:
                context_messages.insert(0, message)
                current_tokens += message_tokens
            else:
                break
        
        return context_messages
    
