# Environment Variables Configuration

This document describes the environment variables required by the ReqVibe application.

## Automatic Loading

The application automatically loads environment variables from a `.env` file in the project root directory when it starts. You don't need to manually set environment variables each time.

## Setup Instructions

1. **Create a `.env` file** in the project root directory (same directory as `app.py`)
2. **Copy the template below** and fill in your actual values
3. **Install dependencies** (if not already done):
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variables

### Required Variables

#### `CENTRALIZED_LLM_API_KEY`
- **Description**: API key for the centralized LLM API service
- **Used by**: LLM client for making API calls to DeepSeek, GPT, Claude, Grok
- **Example**: `CENTRALIZED_LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx`

#### `UNSTRUCTURED_API_KEY`
- **Description**: API key for Unstructured.io document processing service
- **Used by**: Document processing service for PDF, Word, and ReqIF file processing
- **Example**: `UNSTRUCTURED_API_KEY=your_unstructured_api_key_here`

### Optional Variables

#### `UNSTRUCTURED_API_URL`
- **Description**: Custom URL for Unstructured API endpoint
- **Default**: `https://api.unstructured.io/general/v0/general`
- **Example**: `UNSTRUCTURED_API_URL=https://api.unstructured.io/general/v0/general`

#### `RESEND_API_KEY`
- **Description**: API key for Resend email service (if email features are enabled)
- **Used by**: Email verification service
- **Example**: `RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxx`

#### LangSmith Tracing (optional but recommended for observability)
- `LANGSMITH_TRACING` – set to `true` to enable tracing
- `LANGSMITH_ENDPOINT` – defaults to `https://api.smith.langchain.com`
- `LANGSMITH_API_KEY` – your LangSmith API key
- `LANGSMITH_PROJECT` – e.g. `pr-political-barometer-44`
- `OPENAI_API_KEY` – required only if your LangSmith workspace proxies OpenAI calls

## .env File Template

Create a `.env` file in the project root with the following format:

```env
# Centralized LLM API Configuration
CENTRALIZED_LLM_API_KEY=your_centralized_llm_api_key_here

# Unstructured API Configuration
UNSTRUCTURED_API_KEY=your_unstructured_api_key_here
# Optional: Custom Unstructured API URL
# UNSTRUCTURED_API_URL=https://api.unstructured.io/general/v0/general

# Email Service Configuration (Resend) - Optional
# RESEND_API_KEY=your_resend_api_key_here

# LangSmith Observability (Optional)
# LANGSMITH_TRACING=true
# LANGSMITH_ENDPOINT=https://api.smith.langchain.com
# LANGSMITH_API_KEY=your_langsmith_api_key_here
# LANGSMITH_PROJECT=pr-political-barometer-44
# OPENAI_API_KEY=your_openai_api_key_if_required
```

## Security Notes

- **Never commit your `.env` file** to version control
- The `.env` file is already in `.gitignore` and will not be committed
- Keep your API keys secure and don't share them
- Use different API keys for development and production environments

## Troubleshooting

### Environment variables not loading?

1. **Check file location**: Ensure `.env` is in the project root (same directory as `app.py`)
2. **Check file name**: The file must be named exactly `.env` (with the leading dot)
3. **Check format**: Each line should be `KEY=value` format (no spaces around `=`)
4. **Restart the application**: After creating or modifying `.env`, restart Streamlit

### Verify environment variables are loaded

You can verify that environment variables are loaded by checking the application logs or adding a temporary print statement in `app.py`:

```python
import os
print(f"CENTRALIZED_LLM_API_KEY loaded: {bool(os.getenv('CENTRALIZED_LLM_API_KEY'))}")
```

## Alternative: Manual Environment Variable Setup

If you prefer not to use a `.env` file, you can set environment variables manually:

**Windows (PowerShell):**
```powershell
$env:CENTRALIZED_LLM_API_KEY="your_key_here"
$env:UNSTRUCTURED_API_KEY="your_key_here"
```

**Windows (Command Prompt):**
```cmd
set CENTRALIZED_LLM_API_KEY=your_key_here
set UNSTRUCTURED_API_KEY=your_key_here
```

**Linux/Mac:**
```bash
export CENTRALIZED_LLM_API_KEY="your_key_here"
export UNSTRUCTURED_API_KEY="your_key_here"
```

However, using a `.env` file is recommended as it's more convenient and consistent.

