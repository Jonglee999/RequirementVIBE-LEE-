<<<<<<< HEAD
# RequirementVIBE
This is a requirementVIBE chating paradigm to Requirement Engineering 
=======
# ReqVibe - AI Requirements Analyst

A Streamlit application that uses DeepSeek API to analyze and refine software requirements.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your DeepSeek API key as an environment variable:

**Windows (PowerShell)** - Run this command:
```powershell
$env:DEEPSEEK_API_KEY="YOUR API KEY"
```

**Windows (Command Prompt)** - Run this command:
```cmd
set DEEPSEEK_API_KEY=YOUR_API_KEY
```

**Linux/Mac** - Run this command:
```bash
export DEEPSEEK_API_KEY=YOUR_API_KEY
```

**Note:** The environment variable is set only for the current terminal session. To make it permanent, you can:
- Add it to your system environment variables (Windows)
- Add it to your `~/.bashrc` or `~/.zshrc` file (Linux/Mac)
- Or run the setup script: `.\setup.ps1` (Windows PowerShell)

## Running the App

```bash
streamlit run app.py
```

The app will open in your default web browser.

## Usage

1. Enter your requirement or question in the text input box
2. Click the "Ask" button
3. View the AI response below
4. Continue the conversation or clear it to start over

## Requirements

- Python 3.7+
- DeepSeek API key
- streamlit
- openai (required for DeepSeek API - DeepSeek uses OpenAI-compatible SDK)

## Security Note

⚠️ **Important:** Never commit your API key to version control. The API key in the setup script and README is for convenience only. In production, use environment variables or secure credential management systems.

## Streamlit Cloud Deployment

To deploy this app to Streamlit Cloud:

1. Push your code to GitHub
2. Go to [Streamlit Cloud](https://share.streamlit.io/)
3. Sign in with your GitHub account
4. Click "New app" and select your repository
5. Set the main file path to: `app.py`
6. Add your `DEEPSEEK_API_KEY` in the Secrets section
7. Click "Deploy"

**Important:** Set the `DEEPSEEK_API_KEY` in Streamlit Cloud Secrets (not in the code):
```
DEEPSEEK_API_KEY = "YOUR API KEY"
```

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Features

- ✅ Chat history maintained in session state
- ✅ Volere template structure for requirements analysis
- ✅ Professional requirements engineering prompts
- ✅ Real-time API responses with loading indicators
- ✅ Clear conversation functionality
- ✅ Responsive UI with Streamlit chat interface

>>>>>>> 655292d (The first version of ReqVIBE!)
