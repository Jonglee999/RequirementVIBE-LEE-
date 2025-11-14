"""
Conversation Storage Module for ReqVibe

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
import sys

# Maximum storage size per user (1MB in bytes)
MAX_STORAGE_SIZE = 1 * 1024 * 1024  # 1MB

# Maximum number of conversations to keep
MAX_CONVERSATIONS = 10

class ConversationStorage:
    """
    Manages persistent storage for conversation sessions.
    
    This class handles:
    - Saving conversations to disk (JSON files)
    - Loading conversations from disk
    - Enforcing storage size limits (1MB per user)
    - Keeping only the 10 most recent conversations
    - User-specific storage isolation
    
    Storage Structure:
    - Conversations are stored in `conversations/{username}/sessions.json`
    - Each conversation includes: id, messages, title, created_at, model
    - Conversations are sorted by created_at (newest first)
    - Only the 10 most recent are kept
    """
    
    def __init__(self, username: str, storage_dir: str = "conversations"):
        """
        Initialize conversation storage for a user.
        
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
        2. Truncates to MAX_CONVERSATIONS and MAX_STORAGE_SIZE
        3. Saves to JSON file
        
        Args:
            sessions: Dictionary mapping session_id -> session data
        
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Convert sessions dictionary to list
            sessions_list = list(sessions.values())
            
            # Truncate to limits
            truncated_sessions = self._truncate_to_limit(sessions_list)
            
            # Check final size
            total_size = self._get_storage_size({"sessions": truncated_sessions})
            if total_size > MAX_STORAGE_SIZE:
                print(f"WARNING: Storage size ({total_size} bytes) exceeds limit ({MAX_STORAGE_SIZE} bytes) even after truncation")
            
            # Save to JSON file
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "sessions": truncated_sessions,
                    "updated_at": datetime.now().isoformat(),
                    "storage_size": total_size,
                    "session_count": len(truncated_sessions)
                }, f, indent=2, default=str)
            
            print(f"DEBUG: Saved {len(truncated_sessions)} conversations for user {self.username} ({total_size} bytes)")
            return True
        except Exception as e:
            print(f"ERROR: Failed to save conversations for user {self.username}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Load conversations from disk.
        
        This method:
        1. Reads sessions from JSON file
        2. Converts list back to dictionary
        3. Returns empty dictionary if file doesn't exist or is invalid
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping session_id -> session data
        """
        try:
            if not os.path.exists(self.sessions_file):
                print(f"DEBUG: No conversations file found for user {self.username}")
                return {}
            
            # Read from JSON file
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract sessions list
            sessions_list = data.get("sessions", [])
            
            # Convert list to dictionary
            sessions_dict = {}
            for session in sessions_list:
                session_id = session.get("id")
                if session_id:
                    sessions_dict[session_id] = session
            
            print(f"DEBUG: Loaded {len(sessions_dict)} conversations for user {self.username}")
            return sessions_dict
        except Exception as e:
            print(f"ERROR: Failed to load conversations for user {self.username}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information for the user.
        
        Returns:
            Dict[str, Any]: Dictionary with storage information:
                - session_count: Number of stored conversations
                - storage_size: Current storage size in bytes
                - max_storage_size: Maximum storage size in bytes
                - max_conversations: Maximum number of conversations
        """
        try:
            if not os.path.exists(self.sessions_file):
                return {
                    "session_count": 0,
                    "storage_size": 0,
                    "max_storage_size": MAX_STORAGE_SIZE,
                    "max_conversations": MAX_CONVERSATIONS
                }
            
            # Read from JSON file
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                "session_count": data.get("session_count", 0),
                "storage_size": data.get("storage_size", 0),
                "max_storage_size": MAX_STORAGE_SIZE,
                "max_conversations": MAX_CONVERSATIONS
            }
        except Exception as e:
            print(f"ERROR: Failed to get storage info for user {self.username}: {str(e)}")
            return {
                "session_count": 0,
                "storage_size": 0,
                "max_storage_size": MAX_STORAGE_SIZE,
                "max_conversations": MAX_CONVERSATIONS
            }
    
    def delete_all_sessions(self) -> bool:
        """
        Delete all stored conversations for the user.
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            if os.path.exists(self.sessions_file):
                os.remove(self.sessions_file)
                print(f"DEBUG: Deleted all conversations for user {self.username}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to delete conversations for user {self.username}: {str(e)}")
            return False

