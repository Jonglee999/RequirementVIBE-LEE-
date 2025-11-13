"""
Authentication Service for ReqVibe

This module provides user authentication functionality including:
- User registration with password hashing
- User login with credential verification
- Secure password storage using bcrypt
- User data persistence in JSON file

Security Features:
- Passwords are hashed using bcrypt (one-way hashing)
- Salt is automatically generated for each password
- User data is stored in a simple JSON file (can be upgraded to database)
"""

import json
import os
import bcrypt
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

# Path to user database file - use absolute path relative to project root
# Get the directory where this file is located (services/)
_current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to project root (RequirenebtVIBE/)
_project_root = os.path.dirname(_current_dir)
USER_DB_PATH = os.path.join(_project_root, "users.json")


class AuthManager:
    """
    Manages user authentication including registration and login.
    
    This class handles:
    - User registration with password hashing
    - User login with credential verification
    - User data persistence
    - Session management
    
    Security:
    - Uses bcrypt for password hashing (industry standard)
    - Each password gets a unique salt automatically
    - Passwords are never stored in plain text
    """
    
    def __init__(self, db_path: str = USER_DB_PATH):
        """
        Initialize the authentication manager.
        
        Args:
            db_path: Path to the JSON file storing user data
        """
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self) -> None:
        """Ensure the user database file exists, create if it doesn't."""
        if not os.path.exists(self.db_path):
            # Create directory if it doesn't exist (only if path has a directory component)
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
    
    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Load user data from the database file.
        
        Supports both old format (flat dict) and new format (with "users" key).
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of users keyed by username
        """
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Support both formats:
                # Old format: {"username": {...}}
                # New format: {"users": {"username": {...}}}
                if "users" in data:
                    return data["users"]
                else:
                    # Old format - return the data directly
                    return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_users(self, users: Dict[str, Dict[str, Any]]) -> None:
        """
        Save user data to the database file.
        
        Uses the old format (flat dict) for backward compatibility.
        
        Args:
            users: Dictionary of users keyed by username
        """
        # Create directory if it doesn't exist (only if path has a directory component)
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        # Save in old format (flat dict) for backward compatibility
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    
    def register_user(self, username: str, password: str, email: Optional[str] = None) -> Tuple[bool, str]:
        """
        Register a new user.
        
        This function:
        1. Validates username uniqueness
        2. Validates email (required and unique)
        3. Hashes the password using bcrypt
        4. Stores user data in the database
        5. Returns success status and message
        
        Args:
            username: Username for the new user
            password: Plain text password (will be hashed)
            email: Email address (required)
        
        Returns:
            Tuple[bool, str]: (success, message) tuple
        """
        users = self._load_users()
        
        # Check if username already exists
        if username in users:
            return False, "Username already exists. Please choose a different username."
        
        # Validate email (required)
        if not email or not email.strip():
            return False, "Email address is required for registration."
        
        email = email.strip().lower()
        
        # Check if email is already registered
        for existing_username, user_data in users.items():
            if user_data.get("email", "").lower() == email:
                return False, "This email address is already registered. Please use a different email or try logging in."
        
        # Validate password length
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        
        # Hash password using bcrypt
        # bcrypt automatically generates a salt and hashes the password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user record
        user_data = {
            "username": username,
            "password_hash": password_hash,
            "email": email,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        
        # Save user to database
        users[username] = user_data
        self._save_users(users)
        
        return True, f"User '{username}' registered successfully!"
    
    def login_user(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Authenticate a user and log them in.
        
        This function:
        1. Checks if username exists
        2. Verifies password against stored hash
        3. Updates last login timestamp
        4. Returns user data on success
        
        Args:
            username: Username to authenticate
            password: Plain text password to verify
        
        Returns:
            Tuple[bool, str, Optional[Dict[str, Any]]]: (success, message, user_data) tuple
                - success: True if authentication successful, False otherwise
                - message: Success or error message
                - user_data: User data dictionary if successful, None otherwise
        """
        users = self._load_users()
        
        # Check if username exists
        if username not in users:
            return False, "Invalid username or password.", None
        
        user_data = users[username]
        stored_hash = user_data.get("password_hash", "")
        
        # Verify password
        try:
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                # Update last login timestamp
                user_data["last_login"] = datetime.now().isoformat()
                users[username] = user_data
                self._save_users(users)
                
                # Return user data (without password hash)
                return_data = {
                    "username": user_data["username"],
                    "email": user_data.get("email"),
                    "created_at": user_data.get("created_at"),
                    "last_login": user_data.get("last_login")
                }
                return True, f"Welcome back, {username}!", return_data
            else:
                return False, "Invalid username or password.", None
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None
    
    def user_exists(self, username: str) -> bool:
        """
        Check if a user exists in the database.
        
        Args:
            username: Username to check
        
        Returns:
            bool: True if user exists, False otherwise
        """
        users = self._load_users()
        return username in users
    
    def reset_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset a user's password.
        
        This function:
        1. Checks if username exists
        2. Validates new password length
        3. Hashes the new password using bcrypt
        4. Updates the password in the database
        
        Args:
            username: Username of the user
            new_password: New plain text password (will be hashed)
        
        Returns:
            Tuple[bool, str]: (success, message) tuple
        """
        users = self._load_users()
        
        # Check if username exists
        if username not in users:
            return False, "User not found."
        
        # Validate password length
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters long."
        
        # Hash the new password
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update password
        user_data = users[username]
        user_data["password_hash"] = password_hash
        users[username] = user_data
        self._save_users(users)
        
        return True, "Password reset successfully!"

