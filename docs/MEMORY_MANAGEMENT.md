# Memory Management in ReqVIBE

This document provides a comprehensive overview of how memory management is implemented in the ReqVIBE project, covering both in-memory (short-term) and persistent (long-term) storage mechanisms.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Short-Term Memory](#short-term-memory)
4. [Session State Management](#session-state-management)
5. [Persistent Storage](#persistent-storage)
6. [Caching Mechanisms](#caching-mechanisms)
7. [Token Management](#token-management)
8. [Memory Lifecycle](#memory-lifecycle)
9. [Performance Optimizations](#performance-optimizations)

---

## Overview

ReqVIBE uses a multi-layered memory management system:

- **Short-Term Memory**: In-memory storage for active conversation context (managed by `ShortTermMemory`)
- **Session State**: Streamlit session state for UI state and active session data
- **Persistent Storage**: Disk-based storage for conversation history across sessions (managed by `ConversationStorage`)
- **Caching**: Performance optimizations for model lists, icons, and role data

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Session State                   │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  ShortTermMemory │  │  Session Storage │                │
│  │  (Active Memory) │  │  (sessions dict) │                │
│  └──────────────────┘  └──────────────────┘                │
│           │                      │                           │
│           └──────────┬───────────┘                           │
│                      │                                        │
│              ┌───────▼────────┐                              │
│              │ ConversationStorage │                         │
│              │  (Persistent Layer) │                         │
│              └─────────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │  Disk Storage    │
            │  (JSON Files)    │
            └──────────────────┘
```

---

## Short-Term Memory

### Class: `ShortTermMemory`

**Location**: `core/models/memory.py`

The `ShortTermMemory` class manages the active conversation context during a session. It is stored in Streamlit's session state and provides:

#### Key Features

1. **Chat History Management**
   - Stores messages as a list of dictionaries with `role` and `content` keys
   - Supports filtering (include/exclude system messages)
   - Provides methods to add, retrieve, and load messages

2. **Requirements Storage**
   - Maintains a list of extracted requirements during conversation
   - Each requirement is a dictionary with `id`, `text`, and `volere` keys

3. **Token Counting**
   - Uses `tiktoken` library for accurate token estimation (if available)
   - Falls back to character-based approximation (4 chars per token) if `tiktoken` is unavailable
   - Automatically updates token count when messages are added

#### Core Methods

```python
# Message Management
add_message(role: str, content: str) -> None
get_messages(include_system: bool = True) -> List[Dict[str, str]]
load_messages(messages: List[Dict[str, str]], reset: bool = True) -> None
get_history_length() -> int

# Requirements Management
add_requirement(requirement: Dict[str, Any]) -> None
get_requirements() -> List[Dict[str, Any]]

# Token Management
estimate_tokens(messages_list: List[Dict[str, str]]) -> int
get_context_for_api(max_tokens: int = 3500) -> List[Dict[str, str]]
```

#### Token Estimation

The `estimate_tokens()` method:
- Uses `tiktoken` with `cl100k_base` encoding (GPT-3.5/GPT-4 compatible)
- Counts tokens for both `role` and `content` fields
- Adds 4 tokens overhead per message for structure
- Falls back to `char_count // 4` approximation if `tiktoken` unavailable

#### Context Window Management

The `get_context_for_api()` method:
- Retrieves messages that fit within a token limit (default: 3500 tokens)
- Returns all messages if within limit
- Otherwise, returns the most recent messages that fit
- Ensures API calls don't exceed token limits

---

## Session State Management

### Initialization

**Location**: `utils/state_manager.py`

The `initialize_session_state()` function sets up all required session state variables:

#### Memory-Related State

```python
# Short-term memory instance
st.session_state.memory = ShortTermMemory()

# Session storage (dictionary of session_id -> session_data)
st.session_state.sessions = {}

# Current active session ID
st.session_state.current_session_id = None

# Conversation persistence
st.session_state.conversation_storage = None  # ConversationStorage instance
st.session_state.conversation_persistence_enabled = False
```

#### Session Data Structure

Each session in `st.session_state.sessions` contains:

```python
{
    "id": "uuid-string",           # Unique session identifier
    "messages": [...],             # List of message dictionaries
    "title": "Session Title",      # Display title
    "created_at": "ISO-timestamp", # Creation timestamp
    "model": "model-name"          # LLM model used in this session
}
```

### Session Lifecycle

**Location**: `domain/sessions/service.py`

1. **Session Creation** (`create_new_session()`)
   - Generates new UUID for session ID
   - Saves current session's memory to storage before creating new one
   - Creates new session entry with empty messages
   - Resets `ShortTermMemory` to empty state
   - Updates `current_session_id`

2. **Session Retrieval** (`get_current_session()`)
   - Auto-creates session if none exists
   - Returns current session dictionary

3. **Session Switching**
   - Saves current session's memory to `sessions` dict
   - Loads target session's messages into `ShortTermMemory`
   - Updates `current_session_id`

---

## Persistent Storage

### Class: `ConversationStorage`

**Location**: `domain/conversations/service.py`

The `ConversationStorage` class provides persistent disk-based storage for conversation sessions.

#### Storage Structure

```
conversations/
└── {username}/
    └── sessions.json
```

Each user has their own directory and `sessions.json` file, ensuring data isolation.

#### Storage Limits

- **MAX_CONVERSATIONS**: 10 most recent conversations per user
- **MAX_STORAGE_SIZE**: 1MB total storage per user
- If limits are exceeded:
  - Only the 10 most recent conversations are kept
  - Messages from oldest conversations are truncated to stay under size limit

#### Key Methods

```python
# Save/Load Operations
save_sessions(sessions: Dict[str, Dict[str, Any]]) -> bool
load_sessions() -> Dict[str, Dict[str, Any]]

# Storage Information
get_storage_info() -> Dict[str, Any]  # Returns count, size, limits
```

#### Save Optimization

The `save_sessions()` method includes a performance optimization:
- Calculates a hash signature of the payload before writing
- Skips disk write if content hasn't changed since last save
- Reduces unnecessary I/O operations

```python
if payload == self._last_saved_signature:
    return True  # Skip write if unchanged
```

#### Data Format

The `sessions.json` file structure:

```json
{
    "sessions": [
        {
            "id": "uuid-string",
            "messages": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ],
            "title": "Session Title",
            "created_at": "2024-01-01T12:00:00",
            "model": "deepseek-v3.1"
        }
    ]
}
```

---

## Caching Mechanisms

### Model List Caching

**Location**: `config/models.py`

The model list is cached to avoid repeated API calls:

1. **Disk Cache**
   - Location: `.cache/models.json`
   - TTL: 3600 seconds (1 hour, configurable via `REQVIBE_MODEL_CACHE_TTL`)
   - Cache is checked before API fetch
   - Falls back to stale cache if API fails

2. **Cache Strategy**
   ```
   API Fetch → Check Cache → Use Cache (if valid)
                ↓ (if expired/missing)
                Fetch from API → Update Cache → Return Models
                ↓ (if API fails)
                Use Stale Cache (if available) → Fallback to Defaults
   ```

### Streamlit Caching

**Location**: `presentation/components/sidebar.py`

Streamlit's `@st.cache_data` decorator is used for:

1. **Icon Loading** (TTL: 3600 seconds)
   - Caches base64-encoded icon data
   - Avoids repeated file reads and encoding operations

2. **Role Data Loading** (TTL: 300 seconds)
   - Caches loaded role JSON files
   - Reduces disk I/O for role definitions

---

## Token Management

### Token Counting

Token counting is performed using:

1. **Primary Method**: `tiktoken` library
   - Encoding: `cl100k_base` (GPT-3.5/GPT-4 compatible)
   - Accurate token estimation for API calls
   - Handles role and content separately

2. **Fallback Method**: Character approximation
   - Formula: `total_chars // 4`
   - Used when `tiktoken` is unavailable

### Context Window Optimization

The `get_context_for_api()` method ensures:
- Messages fit within token limits (default: 3500 tokens)
- Most recent messages are prioritized
- System messages are excluded from context calculation
- Prevents API errors from exceeding token limits

### Token Count Tracking

Token count is automatically updated:
- When messages are added via `add_message()`
- When messages are loaded via `load_messages()`
- Stored in `self.token_count` attribute

---

## Memory Lifecycle

### 1. Application Startup

```
1. initialize_session_state() called
   └─> Creates empty ShortTermMemory instance
   └─> Initializes empty sessions dict
   └─> Sets conversation_storage = None

2. User logs in
   └─> ConversationStorage instance created
   └─> Previous sessions loaded from disk
   └─> Sessions merged into session_state.sessions

3. Session auto-created (if none exists)
   └─> create_new_session() called
   └─> New ShortTermMemory instance created
```

### 2. During Conversation

```
User sends message:
1. Message added to ShortTermMemory via add_message()
2. Token count updated automatically
3. Message displayed in UI from memory.get_messages()

AI responds:
1. Context retrieved via get_context_for_api()
2. Response added to ShortTermMemory
3. Requirements extracted and added via add_requirement()
4. Session storage updated with current memory state
```

### 3. Session Switching

```
User switches session:
1. Current session's memory saved to sessions dict
2. Target session's messages loaded into ShortTermMemory
3. current_session_id updated
4. UI refreshed with new session's messages
```

### 4. Persistence Operations

```
Periodic Save (if enabled):
1. All sessions in session_state.sessions serialized
2. Truncated to MAX_CONVERSATIONS and MAX_STORAGE_SIZE
3. Written to conversations/{username}/sessions.json
4. Signature checked to avoid redundant writes

On Logout:
1. Final save of all sessions
2. ConversationStorage persists to disk
3. Session state cleared (except authentication)
```

### 5. Application Shutdown

```
Streamlit rerun or page refresh:
1. Session state persists (Streamlit feature)
2. Memory remains in session_state.memory
3. Sessions remain in session_state.sessions
4. Persistent storage remains on disk
```

---

## Performance Optimizations

### 1. Lazy Loading

- Model list fetched only when needed
- Role data loaded on-demand
- Conversation storage loaded only after authentication

### 2. Caching

- **Model List**: Disk cache with TTL (1 hour)
- **Icons**: Streamlit cache (1 hour)
- **Role Data**: Streamlit cache (5 minutes)

### 3. Write Optimization

- **Conversation Storage**: Signature-based skip for unchanged data
- **Session Updates**: Only saved when persistence enabled
- **Token Counting**: Cached encoding object reused

### 4. Memory Efficiency

- **Context Window**: Automatic truncation to fit token limits
- **Storage Limits**: Enforced to prevent unbounded growth
- **Message Filtering**: System messages excluded from context when appropriate

### 5. HTTP Connection Reuse

**Location**: `infrastructure/llm/client.py`

- `requests.Session` object reused for API calls
- Maintains connection pooling and TLS session reuse
- Reduces overhead of repeated API requests

---

## Best Practices

### For Developers

1. **Always use `ShortTermMemory` for active conversation**
   - Don't directly manipulate `chat_history`
   - Use provided methods (`add_message`, `get_messages`, etc.)

2. **Sync memory with session storage**
   - Save memory to session before switching sessions
   - Load session messages into memory when switching

3. **Respect token limits**
   - Use `get_context_for_api()` for API calls
   - Don't manually truncate messages (let memory handle it)

4. **Enable persistence only when needed**
   - Set `conversation_persistence_enabled = True` only for authenticated users
   - Save periodically, not on every message

5. **Handle errors gracefully**
   - Memory operations should not crash the app
   - Fall back to defaults if API/cache fails

### For Users

1. **Conversation Persistence**
   - Enable persistence in sidebar to save conversations
   - Conversations are saved per user account
   - Only 10 most recent conversations are kept

2. **Session Management**
   - Create new sessions for different topics
   - Switch between sessions to access previous conversations
   - Session titles auto-generated from first message

---

## Troubleshooting

### Common Issues

1. **Memory not persisting**
   - Check if `conversation_persistence_enabled` is `True`
   - Verify `ConversationStorage` instance exists
   - Check disk permissions for `conversations/` directory

2. **Token count inaccurate**
   - Verify `tiktoken` is installed: `pip install tiktoken`
   - Check encoding is loaded correctly
   - Fallback approximation may be less accurate

3. **Sessions not loading**
   - Verify user is authenticated
   - Check `conversations/{username}/sessions.json` exists
   - Check JSON file is valid (not corrupted)

4. **Storage size exceeded**
   - Oldest conversations are automatically truncated
   - Only 10 most recent conversations are kept
   - Messages from oldest sessions may be removed

---

## Summary

ReqVIBE's memory management system provides:

- ✅ **Efficient in-memory storage** for active conversations
- ✅ **Persistent disk storage** for conversation history
- ✅ **Automatic token management** for API compatibility
- ✅ **Performance optimizations** through caching and write skipping
- ✅ **User isolation** through per-user storage directories
- ✅ **Storage limits** to prevent unbounded growth
- ✅ **Graceful fallbacks** when APIs or libraries are unavailable

The system is designed to balance performance, reliability, and user experience while maintaining data integrity and respecting resource constraints.

