# Whisper Model Setup for Streamlit Cloud

This guide explains how to pre-download and commit the Whisper model to avoid download delays on Streamlit Cloud.

## Problem

When deploying to Streamlit Cloud, the first transcription request triggers a download of the Whisper medium model (~1.4GB), which can:
- Cause timeouts or errors
- Slow down the first user experience
- Consume bandwidth unnecessarily

## Solution

Pre-download the model locally and commit it to the repository using Git LFS (Large File Storage). This way, Streamlit Cloud will use the model directly from the repository.

## Step-by-Step Setup

### 1. Install Git LFS

Git LFS is required because the model file exceeds GitHub's 100MB file size limit.

**Windows:**
- Download from: https://git-lfs.github.com/
- Or use: `choco install git-lfs`

**macOS:**
```bash
brew install git-lfs
```

**Linux:**
```bash
sudo apt install git-lfs  # Debian/Ubuntu
```

After installation, initialize Git LFS:
```bash
git lfs install
```

### 2. Download the Model

Run the download script:

```bash
python scripts/download_whisper_model.py medium
```

This will:
- Download the medium Whisper model (~1.4GB)
- Save it to `models/whisper/medium.pt`
- Take 5-15 minutes depending on your internet speed

### 3. Commit and Push

Add the model file to Git (Git LFS will handle it automatically):

```bash
# Stage the model file
git add models/whisper/medium.pt
git add .gitattributes  # If not already committed

# Commit
git commit -m "Add Whisper medium model for local use on Streamlit Cloud"

# Push to GitHub
git push
```

**Note:** The first push may take longer as Git LFS uploads the large file.

### 4. Verify on Streamlit Cloud

After deploying:
1. The model file will be available in the repository
2. No download will occur on first transcription
3. Transcription will work immediately

## How It Works

The code in `infrastructure/voice/whisper_service.py`:
1. First checks for `models/whisper/medium.pt` in the project
2. If found, loads it directly (no download)
3. If not found, falls back to Whisper's default behavior (downloads to cache)

## Troubleshooting

### Git LFS not tracking files

If the model file isn't being tracked by Git LFS:

```bash
# Re-initialize Git LFS
git lfs install

# Track .pt files
git lfs track "models/whisper/*.pt"

# Re-add the file
git add .gitattributes
git add models/whisper/medium.pt
git commit -m "Configure Git LFS for Whisper models"
```

### Model file too large for GitHub

If you see errors about file size:
- Ensure Git LFS is properly installed and initialized
- Verify `.gitattributes` includes the model file pattern
- Check that the file is actually tracked by LFS: `git lfs ls-files`

### Model not found on Streamlit Cloud

If the model isn't found after deployment:
- Verify the file was pushed to GitHub (check the repository)
- Ensure Git LFS files were uploaded (GitHub shows LFS badge on large files)
- Check Streamlit Cloud build logs for any errors

## Alternative: Use Smaller Model

If you want faster downloads or smaller repository size, you can use a smaller model:

```bash
# Download base model (~150MB, faster but less accurate)
python scripts/download_whisper_model.py base

# Or tiny model (~75MB, fastest but least accurate)
python scripts/download_whisper_model.py tiny
```

Then update the default model in `infrastructure/voice/client.py` if needed.

## File Structure

After setup, your repository will have:

```
RequirenebtVIBE/
├── models/
│   └── whisper/
│       ├── medium.pt      # Model file (tracked by Git LFS)
│       └── README.md      # Documentation
├── scripts/
│   └── download_whisper_model.py  # Download script
└── .gitattributes         # Git LFS configuration
```

## Benefits

✅ No download delays on Streamlit Cloud  
✅ Faster first transcription  
✅ More reliable deployments  
✅ Better user experience  

