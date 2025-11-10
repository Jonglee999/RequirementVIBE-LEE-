# Streamlit Cloud Deployment Instructions

## Prerequisites

1. A GitHub account
2. A Streamlit Cloud account (free at https://streamlit.io/cloud)
3. Your DeepSeek API key

## Deployment Steps

### 1. Push Your Code to GitHub

1. Initialize a git repository (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit - ReqVibe app"
   ```

2. Create a new repository on GitHub (e.g., `ReqVibe`)

3. Push your code to GitHub:
   ```bash
   git remote add origin https://github.com/yourusername/ReqVibe.git
   git branch -M main
   git push -u origin main
   ```

### 2. Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository and branch (usually `main`)
5. Set the main file path to: `app.py`
6. Click "Deploy"

### 3. Configure Secrets (API Key)

1. In your Streamlit Cloud app dashboard, click on "⋮" (three dots) → "Settings"
2. Go to "Secrets" tab
3. Add your DeepSeek API key:
   ```toml
   DEEPSEEK_API_KEY = "YOUR_API_KEY_HERE"
   ```
4. Click "Save"

### 4. Restart Your App

1. After saving secrets, go to "Manage app"
2. Click "⋮" → "Restart app"
3. Your app will restart with the new configuration

## File Structure for Deployment

```
RequirenebtVIBE/
├── app.py                  # Main application file
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml        # Streamlit configuration
└── README.md              # Project documentation
```

## Important Notes

- **Never commit your API key to GitHub!** Always use Streamlit Cloud's Secrets feature.
- The app will automatically redeploy when you push changes to the main branch.
- Make sure `requirements.txt` includes all necessary dependencies.
- The `.streamlit/config.toml` file is optional but recommended for better app configuration.
- The `openai` package in requirements.txt is required because DeepSeek API uses an OpenAI-compatible SDK.

## Troubleshooting

### App fails to deploy
- Check that `app.py` is in the root directory
- Verify `requirements.txt` has all dependencies
- Check the logs in Streamlit Cloud dashboard

### API key not working
- Verify the secret is set correctly in Streamlit Cloud
- Check that the secret name matches `DEEPSEEK_API_KEY`
- Ensure there are no extra spaces or quotes in the secret value

### App loads but shows error
- Check the app logs in Streamlit Cloud
- Verify the API key is valid
- Ensure the DeepSeek API is accessible from Streamlit Cloud servers

## Environment Variables

The app uses the following environment variable:
- `DEEPSEEK_API_KEY`: Your DeepSeek API key (set via Streamlit Cloud Secrets)

## Custom Domain (Optional)

Streamlit Cloud allows you to use a custom domain:
1. Go to app settings
2. Navigate to "Custom domain"
3. Follow the instructions to configure your domain

