# Whisper Models Directory

This directory contains pre-downloaded Whisper model files to avoid downloading them on Streamlit Cloud.

## Setup Instructions

### 1. Install Git LFS

Git LFS (Large File Storage) is required to store the large model files (>100MB).

**Windows:**
```bash
# Download and install from: https://git-lfs.github.com/
# Or use Chocolatey:
choco install git-lfs
```

**macOS:**
```bash
brew install git-lfs
```

**Linux:**
```bash
sudo apt install git-lfs  # Debian/Ubuntu
# or
sudo yum install git-lfs  # RHEL/CentOS
```

After installation, initialize Git LFS in your repository:
```bash
git lfs install
```

### 2. Download the Model

Run the download script to download the medium Whisper model:

```bash
python scripts/download_whisper_model.py medium
```

This will:
- Download the medium model (~1.4GB)
- Save it to `models/whisper/medium.pt`
- Take several minutes depending on your internet connection

### 3. Commit the Model to Git

After downloading, commit the model file using Git LFS:

```bash
# Add the model file (Git LFS will handle it automatically)
git add models/whisper/medium.pt

# Commit
git commit -m "Add Whisper medium model for local use"

# Push to GitHub
git push
```

### 4. Verify on Streamlit Cloud

After deploying to Streamlit Cloud:
- The model file will be available in the repository
- No download will occur on first run
- Transcription will start immediately

## Model Files

- `medium.pt` - Medium Whisper model (~1.4GB, recommended for good accuracy/speed balance)

## Notes

- The model files are tracked by Git LFS, so they won't bloat your repository
- If you need a different model size, you can download it using the same script:
  ```bash
  python scripts/download_whisper_model.py base    # Smaller, faster
  python scripts/download_whisper_model.py large-v2  # Larger, more accurate
  ```
- The code will automatically check this directory first before downloading

