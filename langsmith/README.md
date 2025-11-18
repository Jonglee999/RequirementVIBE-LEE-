# LangSmith Local Settings

This directory is reserved for optional LangSmith configuration files.  
To customize settings locally without committing secrets:

1. Copy `langsmith_settings.example.json` to `langsmith_settings.json`.
2. Adjust any fields you need for local experimentation (for example, override the project name).
3. Keep your copy of `langsmith_settings.json` private — it is ignored by Git.

Actual tracing behaviour is primarily controlled via environment variables:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com
export LANGSMITH_API_KEY=<your API key>
export LANGSMITH_PROJECT=pr-political-barometer-44
```

All secrets should continue to live in your `.env` file.


