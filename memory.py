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
            # Use cl100k_base encoding (used by GPT-4 and DeepSeek)
            try:
                self._encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Fallback to o200k_base if cl100k_base is not available
                try:
                    self._encoding = tiktoken.get_encoding("o200k_base")
                except Exception:
                    # Last resort: use approximate counting
                    self._encoding = None
        return self._encoding
    
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: Text to count tokens for
        
        Returns:
            int: Number of tokens
        """
        encoding = self._get_encoding()
        if encoding:
            try:
                return len(encoding.encode(text))
            except Exception:
                # Fallback: approximate token count (1 token ≈ 4 characters)
                return len(text) // 4
        else:
            # Fallback: approximate token count (1 token ≈ 4 characters)
            return len(text) // 4
    
    def add_message(self, role: str, content: str, count_tokens: bool = True) -> None:
        """
        Add a message to chat history and update token count.
        
        Args:
            role: Message role ("user", "assistant", or "system")
            content: Message content
            count_tokens: Whether to count tokens for this message (default: True)
        """
        if not content or not content.strip():
            return
        
        message = {
            "role": role,
            "content": content.strip()
        }
        
        self.chat_history.append(message)
        
        # Update token count if requested
        if count_tokens:
            message_tokens = self._count_tokens(content)
            self.token_count += message_tokens
    
    def load_messages(self, messages: List[Dict[str, str]], reset: bool = True) -> None:
        """
        Load messages into memory (useful for syncing from session).
        Resets chat history and recalculates token count from all messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            reset: Whether to reset before loading (default: True)
        """
        if reset:
            self.chat_history = []
            self.token_count = 0
        
        # Load all messages and recalculate token count
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if content:
                message = {
                    "role": role,
                    "content": content.strip()
                }
                self.chat_history.append(message)
                # Count tokens for this message
                self.token_count += self._count_tokens(content)
    
    def get_messages(self, include_system: bool = False) -> List[Dict[str, str]]:
        """
        Get messages in format ready for OpenAI API.
        
        Args:
            include_system: Whether to include system messages (default: False)
        
        Returns:
            List[Dict[str, str]]: List of messages with 'role' and 'content' keys
        """
        if include_system:
            return self.chat_history.copy()
        else:
            # Filter out system messages
            return [msg for msg in self.chat_history if msg["role"] != "system"]
    
    def add_requirement(self, requirement: Dict[str, Any]) -> None:
        """
        Add a requirement to the requirements list.
        Also saves to long-term memory (LTM) if auto-save is enabled.
        
        Args:
            requirement: Requirement dictionary with 'id', 'text', 'volere' keys
        """
        self.requirements.append(requirement)
        
        # Auto-save to long-term memory if enabled
        # Check if LTM auto-save is enabled in session state (default: True)
        auto_save_enabled = st.session_state.get("ltm_auto_save", True)
        
        if auto_save_enabled and "ltm" in st.session_state:
            try:
                # Extract requirement data for LTM storage
                req_id = requirement.get("id", "")
                req_text = requirement.get("text", "")
                req_volere = requirement.get("volere", {})
                
                # Get current project name from session state (default: "default")
                current_project = st.session_state.get("current_project", "default")
                
                # Save to long-term memory with metadata
                st.session_state.ltm.save(
                    req_id=req_id,
                    text=req_text,
                    metadata={
                        "project": current_project,
                        "volere": req_volere
                    }
                )
            except Exception as e:
                # Silently fail if LTM save fails (don't interrupt requirement storage)
                # In production, you might want to log this error
                pass
    
    def get_requirements(self) -> List[Dict[str, Any]]:
        """
        Get all stored requirements.
        
        Returns:
            List[Dict[str, Any]]: List of requirement dictionaries
        """
        return self.requirements.copy()
    
    def clear_chat_history(self) -> None:
        """Clear chat history and reset token count."""
        self.chat_history = []
        self.token_count = 0
    
    def clear_requirements(self) -> None:
        """Clear all stored requirements."""
        self.requirements = []
    
    def clear_all(self) -> None:
        """Clear both chat history and requirements."""
        self.clear_chat_history()
        self.clear_requirements()
    
    def get_token_count(self) -> int:
        """
        Get current token count.
        
        Returns:
            int: Total token count
        """
        return self.token_count
    
    def get_history_length(self) -> int:
        """
        Get number of messages in chat history.
        
        Returns:
            int: Number of messages
        """
        return len(self.chat_history)
    
    def get_requirements_count(self) -> int:
        """
        Get number of stored requirements.
        
        Returns:
            int: Number of requirements
        """
        return len(self.requirements)
    
    def estimate_tokens(self, messages_list: List[Dict[str, str]]) -> int:
        """
        Estimate token count for a list of messages using tiktoken.
        
        Accounts for API message format overhead (role, JSON structure, etc.).
        Uses tiktoken for accurate token counting compatible with DeepSeek API.
        
        Args:
            messages_list: List of message dictionaries with 'role' and 'content' keys
        
        Returns:
            int: Estimated token count
        """
        if not messages_list:
            return 0
        
        total_tokens = 0
        encoding = self._get_encoding()
        
        for message in messages_list:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if encoding:
                try:
                    # Count tokens for content (main text)
                    content_tokens = len(encoding.encode(content)) if content else 0
                    
                    # Count tokens for role name
                    role_tokens = len(encoding.encode(role)) if role else 0
                    
                    # Add overhead for JSON structure and message formatting
                    # Each message in API format adds approximately:
                    # - Role name: ~1-2 tokens (user, assistant, system)
                    # - JSON structure: ~4-6 tokens ({"role": "...", "content": "..."})
                    # Total overhead: ~6-8 tokens per message
                    message_overhead = 6
                    
                    message_tokens = content_tokens + role_tokens + message_overhead
                    total_tokens += message_tokens
                except Exception:
                    # Fallback: approximate counting
                    # Approximate: content tokens + overhead
                    total_tokens += (len(content) // 4) + 8
            else:
                # Fallback: approximate token count (1 token ≈ 4 characters)
                # Add overhead for message structure
                total_tokens += (len(content) // 4) + 8
        
        return total_tokens
    
    def get_context_for_api(self, max_tokens: int = 3500, client=None, model: str = "deepseek-chat") -> List[Dict[str, str]]:
        """
        Get context for API call with token limit management.
        
        If chat history tokens exceed max_tokens, returns recent messages that fit within the limit.
        Always ensures at least the last 5 messages are included (if available).
        Otherwise returns full history.
        
        Optionally attempts summarization if history is long and client is provided.
        
        Args:
            max_tokens: Maximum tokens to return (default: 3500)
            client: Optional OpenAI-compatible client for auto-summarization (default: None)
        
        Returns:
            List[Dict[str, str]]: List of messages ready for API call
        """
        # Get all messages (excluding system messages for token estimation)
        all_messages = self.get_messages(include_system=False)
        
        if not all_messages:
            return []
        
        # Estimate tokens for full history
        total_tokens = self.estimate_tokens(all_messages)
        
        # If over limit and we have many messages, optionally try summarization
        # Only if client is provided and we have more than 10 messages
        summarization_performed = False
        if total_tokens > max_tokens and client is not None and len(self.chat_history) > 10:
            # Try to summarize old messages to reduce token count
            if self.summarize_old_messages(client, model=model):
                summarization_performed = True
                # After summarization, recalculate with system messages included
                # (summary is stored as a system message)
                all_messages_with_system = self.get_messages(include_system=True)
                total_tokens = self.estimate_tokens(all_messages_with_system)
        
        # After summarization or if under limit, check if we're still over
        if total_tokens <= max_tokens:
            # Return messages including system messages (for summary context)
            return self.get_messages(include_system=True)
        
        # If still over limit after summarization (or no summarization was performed),
        # return recent messages that fit
        # Include system messages (like summaries) in the context
        all_messages_with_system = self.get_messages(include_system=True)
        
        # Separate system and non-system messages
        system_messages = [msg for msg in all_messages_with_system if msg.get("role") == "system"]
        non_system_messages = [msg for msg in all_messages_with_system if msg.get("role") != "system"]
        
        # Estimate tokens for system messages (summaries, etc.)
        system_tokens = self.estimate_tokens(system_messages)
        remaining_tokens = max_tokens - system_tokens
        
        # If system messages alone exceed the limit, return at least system messages + last 5
        if remaining_tokens <= 0:
            # Return system messages + last 5 non-system messages
            min_messages = min(5, len(non_system_messages))
            return system_messages + non_system_messages[-min_messages:] if non_system_messages else system_messages
        
        # Work backwards from non-system messages to fit within remaining token budget
        min_messages = min(5, len(non_system_messages))
        recent_messages = []
        accumulated_tokens = 0
        
        # Start from the most recent non-system message and work backwards
        for i in range(len(non_system_messages) - 1, -1, -1):
            message = non_system_messages[i]
            message_tokens = self.estimate_tokens([message])
            
            # Always include the last message (current user input)
            if not recent_messages:
                recent_messages.insert(0, message)
                accumulated_tokens += message_tokens
                continue
            
            # Check if adding this message would exceed the remaining token budget
            if accumulated_tokens + message_tokens > remaining_tokens:
                # If we have less than min_messages, add it anyway to ensure minimum context
                if len(recent_messages) < min_messages:
                    recent_messages.insert(0, message)
                    accumulated_tokens += message_tokens
                    continue
                else:
                    # We've reached the limit and have minimum messages, stop
                    break
            
            # Add message to the beginning (maintain chronological order)
            recent_messages.insert(0, message)
            accumulated_tokens += message_tokens
        
        # Ensure we have at least the last 5 non-system messages if available
        if len(recent_messages) < min_messages and len(non_system_messages) >= min_messages:
            recent_messages = non_system_messages[-min_messages:]
        
        # Return system messages + recent non-system messages
        return system_messages + recent_messages
    
    def summarize_old_messages(self, client, model: str = "deepseek-chat") -> bool:
        """
        Summarize old messages if chat history has more than 10 messages.
        
        Takes messages[0:len-5] (all but last 5), sends to OpenAI for summarization,
        replaces old messages with a system message containing the summary,
        and keeps the last 5 messages.
        
        Args:
            client: OpenAI-compatible client (for DeepSeek API)
        
        Returns:
            bool: True if summarization was performed, False otherwise
        """
        # Check if we have more than 10 messages
        if len(self.chat_history) <= 10:
            return False
        
        # Check if we already have a summary (to avoid re-summarizing)
        has_summary = any(msg.get("role") == "system" and msg.get("content", "").startswith("SUMMARY:") 
                         for msg in self.chat_history)
        if has_summary:
            # If we already have a summary, don't summarize again
            # (This prevents infinite summarization loops)
            return False
        
        # Get old messages (all but last 5)
        old_messages = self.chat_history[:-5]
        last_5_messages = self.chat_history[-5:]
        
        # Prepare messages for summarization API call
        # Format the conversation for summarization
        conversation_text = ""
        for msg in old_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if content:
                # Skip system messages in the summary request
                if role != "system":
                    conversation_text += f"{role.upper()}: {content}\n\n"
        
        if not conversation_text.strip():
            return False
        
        try:
            # Send to OpenAI/DeepSeek for summarization
            summarization_prompt = """Summarize this requirements interview conversation in 3 bullet points. 
Keep all REQ-XXX IDs mentioned. Focus on key requirements, decisions, and important context.

Conversation:
""" + conversation_text
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a requirements engineering assistant. Summarize conversations concisely while preserving all requirement IDs and key information."},
                    {"role": "user", "content": summarization_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent summaries
                max_tokens=500
            )
            
            summary = response.choices[0].message.content
            
            # Create summary system message
            summary_message = {
                "role": "system",
                "content": f"SUMMARY: {summary}"
            }
            
            # Replace old messages with summary
            # Keep only system messages that are not summaries (preserve original system messages if any)
            existing_system_messages = [msg for msg in old_messages if msg.get("role") == "system" 
                                       and not msg.get("content", "").startswith("SUMMARY:")]
            
            # Build new chat history: existing system messages + summary + last 5 messages
            self.chat_history = existing_system_messages + [summary_message] + last_5_messages
            
            # Reset token count by recalculating
            self.token_count = 0
            for msg in self.chat_history:
                content = msg.get("content", "")
                if content:
                    self.token_count += self._count_tokens(content)
            
            return True
            
        except Exception as e:
            # If summarization fails, return False and keep original history
            # In a production app, you might want to log this error
            return False

