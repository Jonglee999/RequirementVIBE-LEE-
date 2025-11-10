# Setup script for ReqVibe - Sets DeepSeek API key environment variable
# Run this script in PowerShell: .\setup.ps1

$apiKey = "YOUR API KEY"
$env:DEEPSEEK_API_KEY = $apiKey

Write-Host "DeepSeek API key has been set for this session." -ForegroundColor Green
Write-Host "You can now run: streamlit run app.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: This setting is only for the current PowerShell session." -ForegroundColor Yellow
Write-Host "To make it permanent, add it to your system environment variables." -ForegroundColor Yellow

