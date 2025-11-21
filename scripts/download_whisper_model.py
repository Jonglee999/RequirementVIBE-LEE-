"""
Script to download Whisper models to the local models/whisper/ directory.

This script downloads the specified Whisper model and saves it to
models/whisper/ so it can be committed to the repository and used
directly on Streamlit Cloud without downloading.

Usage:
    python scripts/download_whisper_model.py [model_name]

Examples:
    python scripts/download_whisper_model.py base    # Default model
    python scripts/download_whisper_model.py medium # Larger, more accurate
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    import whisper
except ImportError:
    print("Error: openai-whisper is not installed.")
    print("Install it with: pip install openai-whisper")
    sys.exit(1)


def download_model(model_name: str = "base"):
    """
    Download a Whisper model to the local models/whisper/ directory.

    Args:
        model_name: Name of the Whisper model to download (default: "medium").
    """
    # Create models directory if it doesn't exist
    models_dir = project_root / "models" / "whisper"
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Whisper model '{model_name}'...")
    print(f"Target directory: {models_dir}")
    print("This may take several minutes depending on your internet connection.")
    print()

    try:
        # Download model to local directory
        model = whisper.load_model(model_name, download_root=str(models_dir))
        
        # Verify the model file exists
        model_file = models_dir / f"{model_name}.pt"
        if model_file.exists():
            file_size_mb = model_file.stat().st_size / (1024 * 1024)
            print(f"✅ Successfully downloaded model '{model_name}'")
            print(f"   Location: {model_file}")
            print(f"   Size: {file_size_mb:.2f} MB")
            print()
            print("Next steps:")
            print("1. The model file is ready to be committed to Git")
            print("2. Make sure Git LFS is configured (see .gitattributes)")
            print("3. Add and commit the model file:")
            print(f"   git add models/whisper/{model_name}.pt")
            print("   git commit -m 'Add Whisper model for local use'")
            print("   git push")
        else:
            print(f"⚠️  Warning: Model file not found at {model_file}")
            print("   The model may have been downloaded to a different location.")
            
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Get model name from command line or use default
    model_name = sys.argv[1] if len(sys.argv) > 1 else "base"
    
    # Validate model name
    valid_models = ["tiny", "base", "small", "medium", "large-v2"]
    if model_name not in valid_models:
        print(f"Error: Invalid model name '{model_name}'")
        print(f"Valid models: {', '.join(valid_models)}")
        sys.exit(1)
    
    download_model(model_name)

