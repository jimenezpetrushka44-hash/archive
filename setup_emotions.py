"""Download the model once; chat inference then runs locally."""
from huggingface_hub import snapshot_download
from emotion_detector import MODEL_ID, MODEL_PATH, MODEL_REVISION

if __name__ == "__main__":
    snapshot_download(MODEL_ID, revision=MODEL_REVISION, local_dir=str(MODEL_PATH),
                      allow_patterns=["*.json", "*.safetensors", "*.model", "README.md", "LICENSE*"])
    print("Emotion model ready. Start Moodify with python app.py.")
