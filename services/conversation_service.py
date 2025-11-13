"""
Conversation Storage Service for ReqVibe

This module provides persistent storage for conversation sessions including:
- User-specific conversation storage
- Storage size limits (1MB per user)
- Limiting to 10 most recent conversations
- Loading and saving conversations to disk

Storage Features:
- Conversations are stored in JSON files per user
- Maximum 1MB storage per user
- Only 10 most recent conversations are kept
- Conversations are loaded on login and saved on logout or periodically
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Constants for conversation storage limits
MAX_CONVERSATIONS = 10  # Maximum number of conversations to store per user
MAX_STORAGE_SIZE = 1 * 1024 * 1024  # 1MB maximum storage size per user (in bytes)

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
_default_storage_dir = os.path.join(_project_root, "conversations")


class ConversationStorage:
    """
    Manages persistent storage of user conversation sessions.

    Each user has their own conversation file (sessions.json) within a dedicated
    directory (conversations/{username}/). This ensures data isolation.

    The storage enforces limits:
    - MAX_CONVERSATIONS: Only the most recent N conversations are kept.
    - MAX_STORAGE_SIZE: Total size of conversations for a user cannot exceed this limit.
                        If exceeded, messages from older conversations are truncated.
    """

    def __init__(self, username: str, storage_dir: str = _default_storage_dir):
        """
        Initialize the ConversationStorage for a specific user.

        Args:
            username: Username for user-specific storage
            storage_dir: Directory to store conversation files (default: "conversations")
        """
        self.username = username
        self.storage_dir = storage_dir
        self.user_dir = os.path.join(storage_dir, username)
        self.sessions_file = os.path.join(self.user_dir, "sessions.json")

        # Create user directory if it doesn't exist
        os.makedirs(self.user_dir, exist_ok=True)

    def _get_storage_size(self, data: Dict[str, Any]) -> int:
        """
        Calculate the size of data in bytes when serialized to JSON.

        Args:
            data: Dictionary to calculate size for

        Returns:
            int: Size in bytes
        """
        try:
            json_str = json.dumps(data, default=str)
            return len(json_str.encode('utf-8'))
        except Exception as e:
            print(f"Error calculating storage size: {str(e)}")
            return 0

    def _truncate_to_limit(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Truncate sessions to MAX_CONVERSATIONS and ensure storage size is under limit.

        This method:
        1. Sorts sessions by created_at (newest first)
        2. Keeps only the MAX_CONVERSATIONS most recent
        3. Truncates messages if needed to stay under MAX_STORAGE_SIZE

        Args:
            sessions: List of session dictionaries

        Returns:
            List[Dict[str, Any]]: Truncated list of sessions
        """
        if not sessions:
            return []

        # Sort by created_at (newest first)
        # Handle both ISO format strings and datetime objects
        def get_sort_key(session):
            created_at = session.get("created_at", "")
            if isinstance(created_at, str):
                # ISO format string - can be sorted directly
                return created_at
            elif hasattr(created_at, 'isoformat'):
                # datetime object - convert to ISO format
                return created_at.isoformat()
            else:
                # Fallback to empty string
                return ""

        sorted_sessions = sorted(
            sessions,
            key=get_sort_key,
            reverse=True
        )

        # Keep only the MAX_CONVERSATIONS most recent
        truncated_sessions = sorted_sessions[:MAX_CONVERSATIONS]

        # Calculate total size and truncate if needed
        total_size = self._get_storage_size({"sessions": truncated_sessions})

        # If over limit, remove messages from oldest sessions until under limit
        if total_size > MAX_STORAGE_SIZE:
            # Start with oldest sessions and remove messages until under limit
            for i in range(len(truncated_sessions) - 1, -1, -1):
                session = truncated_sessions[i]
                # Remove messages from oldest sessions first
                session["messages"] = []
                total_size = self._get_storage_size({"sessions": truncated_sessions})
                if total_size <= MAX_STORAGE_SIZE:
                    break

        return truncated_sessions

    def save_sessions(self, sessions: Dict[str, Dict[str, Any]]) -> bool:
        """
        Save conversations to disk.

        This method:
        1. Converts sessions dictionary to list
        2. Truncates sessions based on MAX_CONVERSATIONS and MAX_STORAGE_SIZE
        3. Serializes to JSON and writes to user-specific file

        Args:
            sessions: Dictionary of session data (session_id -> session_dict)

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            sessions_list = list(sessions.values())
            truncated_sessions = self._truncate_to_limit(sessions_list)

            # Convert datetime objects to ISO format strings for JSON serialization
            for session in truncated_sessions:
                if isinstance(session.get("created_at"), datetime):
                    session["created_at"] = session["created_at"].isoformat()

            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump({"sessions": truncated_sessions}, f, indent=4, default=str)
            return True
        except Exception as e:
            print(f"ERROR: Failed to save sessions for user {self.username}: {str(e)}")
            return False

    def load_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Load conversations from disk for the current user.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of loaded session data,
                                      or empty dict if file not found or error.
        """
        if not os.path.exists(self.sessions_file):
            return {}

        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sessions_list = data.get("sessions", [])
                
                # Convert ISO format strings back to datetime objects
                for session in sessions_list:
                    if isinstance(session.get("created_at"), str):
                        try:
                            session["created_at"] = datetime.fromisoformat(session["created_at"])
                        except ValueError:
                            # Fallback if format is unexpected
                            session["created_at"] = datetime.now() 
                
                # Convert list back to dictionary keyed by session_id
                return {session["id"]: session for session in sessions_list}
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to decode sessions JSON for user {self.username}: {str(e)}")
            # Optionally, backup corrupted file and start fresh
            return {}
        except Exception as e:
            print(f"ERROR: Failed to load sessions for user {self.username}: {str(e)}")
            return {}

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get current storage information for the user.

        Returns:
            Dict[str, Any]: Dictionary with 'session_count', 'storage_size',
                           'max_conversations', 'max_storage_size'.
        """
        sessions = self.load_sessions()
        current_sessions_list = list(sessions.values())
        
        # Ensure created_at is datetime for sorting if not already
        for session in current_sessions_list:
            if isinstance(session.get("created_at"), str):
                try:
                    session["created_at"] = datetime.fromisoformat(session["created_at"])
                except ValueError:
                    session["created_at"] = datetime.now() # Fallback
        
        # Sort to get the most recent ones for accurate count
        sorted_sessions = sorted(current_sessions_list, key=lambda x: x.get("created_at", datetime.min), reverse=True)
        
        # Apply truncation logic to get the actual number of stored sessions and their size
        truncated_sessions = self._truncate_to_limit(sorted_sessions)
        
        return {
            "session_count": len(truncated_sessions),
            "storage_size": self._get_storage_size({"sessions": truncated_sessions}),
            "max_conversations": MAX_CONVERSATIONS,
            "max_storage_size": MAX_STORAGE_SIZE
        }

