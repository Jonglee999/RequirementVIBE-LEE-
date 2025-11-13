"""
Authentication Module for ReqVibe

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
from typing import Optional, Dict, Any
from datetime import datetime

# Path to user database file
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DB_PATH = os.path.join(_CURRENT_DIR, "users.json")

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
    
    def _ensure_db_exists(self):
        """Create the user database file if it doesn't exist."""
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w') as f:
                json.dump({}, f)
    
    def _load_users(self) -> Dict[str, Any]:
        """
        Load all users from the database file.
        
        Returns:
            Dictionary mapping username to user data
        """
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_users(self, users: Dict[str, Any]):
        """
        Save users dictionary to the database file.
        
        Args:
            users: Dictionary mapping username to user data
        """
        with open(self.db_path, 'w') as f:
            json.dump(users, f, indent=2)
    
    def register_user(self, username: str, password: str, email: Optional[str] = None) -> tuple[bool, str]:
        """
        Register a new user.
        
        This method:
        1. Validates username (must be unique, non-empty)
        2. Validates password (minimum length)
        3. Hashes the password using bcrypt
        4. Stores user data in the database
        
        Args:
            username: Unique username for the user
            password: Plain text password (will be hashed)
            email: Optional email address
        
        Returns:
            Tuple of (success: bool, message: str)
            - success: True if registration successful, False otherwise
            - message: Success or error message
        """
        # Validate username
        if not username or not username.strip():
            return False, "Username cannot be empty"
        
        username = username.strip().lower()
        
        # Validate password
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long"
        
        # Load existing users
        users = self._load_users()
        
        # Check if username already exists
        if username in users:
            return False, "Username already exists. Please choose a different username."
        
        # Hash the password using bcrypt
        # bcrypt automatically generates a salt and includes it in the hash
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
    
    def login_user(self, username: str, password: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Authenticate a user and log them in.
        
        This method:
        1. Checks if username exists
        2. Verifies password against stored hash
        3. Updates last login timestamp
        4. Returns user data if successful
        
        Args:
            username: Username to authenticate
            password: Plain text password to verify
        
        Returns:
            Tuple of (success: bool, message: str, user_data: Optional[Dict])
            - success: True if login successful, False otherwise
            - message: Success or error message
            - user_data: User data dictionary if successful, None otherwise
        """
        # Validate input
        if not username or not password:
            return False, "Username and password are required", None
        
        username = username.strip().lower()
        
        # Load users
        users = self._load_users()
        
        # Check if user exists
        if username not in users:
            return False, "Invalid username or password", None
        
        user_data = users[username]
        
        # Verify password
        stored_hash = user_data["password_hash"]
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return False, "Invalid username or password", None
        
        # Update last login timestamp
        user_data["last_login"] = datetime.now().isoformat()
        users[username] = user_data
        self._save_users(users)
        
        # Return user data (without password hash)
        user_info = {
            "username": user_data["username"],
            "email": user_data.get("email"),
            "created_at": user_data.get("created_at"),
            "last_login": user_data["last_login"]
        }
        
        return True, f"Welcome back, {username}!", user_info
    
    def user_exists(self, username: str) -> bool:
        """
        Check if a username already exists.
        
        Args:
            username: Username to check
        
        Returns:
            True if username exists, False otherwise
        """
        users = self._load_users()
        return username.strip().lower() in users
    
    def get_user_count(self) -> int:
        """
        Get the total number of registered users.
        
        Returns:
            Number of registered users
        """
        users = self._load_users()
        return len(users)

