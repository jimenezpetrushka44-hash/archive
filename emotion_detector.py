"""Local multilingual emotion inference, separate from the original recommender.

Model: https://huggingface.co/tabularisai/multilingual-emotion-classification
Scores are independent sigmoid outputs, not calibrated accuracy percentages.
"""
from pathlib import Path
from threading import Lock
import math

MODEL_ID = "tabularisai/multilingual-emotion-classification"
MODEL_REVISION = "a2b9b4d9640c53e84ab7abdd2a66146d3dafb10c"
MODEL_PATH = Path(__file__).resolve().parent / ".models" / "emotions"
EMOTION_MOODS = {
    "joy": "happy", "sadness": "sad", "anger": "intense",
    "frustration": "intense", "disgust": "intense", "contempt": "intense",
    "fear": "calm", "love": "calm", "gratitude": "calm",
    "neutral": "neutral", "surprise": "neutral",
}
_pipeline = None
_lock = Lock()


def interpret_scores(scores):
    """Threshold each label independently, retaining ambiguity rather than guessing."""
    values = {item["label"].lower(): float(item["score"]) for item in scores}
    if set(values) != set(EMOTION_MOODS) or any(not math.isfinite(v) or not 0 <= v <= 1 for v in values.values()):
        raise ValueError("Unexpected emotion model output")
    ranked = sorted(values.items(), key=lambda item: item[1], reverse=True)
    active = [(label, score) for label, score in ranked if score >= .5]
    # Neutral must not hide a specific emotion above the threshold.
    specific = [(label, score) for label, score in active if label != "neutral"]
    chosen = specific or active
    if not chosen:
        return {"emotion": "uncertain", "emotions": [], "mood": "neutral",
                "confidence": ranked[0][1], "uncertain": True, "mixed": False,
                "emotion_source": "multilingual_model"}
    label, score = chosen[0]
    close_moods = {EMOTION_MOODS[name] for name, value in chosen if score - value <= .15}
    mixed = len(specific) > 1
    return {"emotion": label, "emotions": [{"label": name, "score": value} for name, value in chosen],
            "mood": "neutral" if len(close_moods) > 1 else EMOTION_MOODS[label],
            "confidence": score, "uncertain": False, "mixed": mixed,
            "emotion_source": "multilingual_model"}


def detect_emotions(text):
    global _pipeline
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Emotion text must not be empty")
    # No network calls during a chat request. Install once with setup_emotions.py.
    with _lock:
        if _pipeline is None:
            if not (MODEL_PATH / "config.json").exists():
                raise RuntimeError("Run setup_emotions.py to install the local emotion model")
            from transformers import pipeline
            _pipeline = pipeline("text-classification", model=str(MODEL_PATH),
                                 tokenizer=str(MODEL_PATH), device=-1,
                                 function_to_apply="sigmoid", top_k=None)
        output = _pipeline(text, truncation=True, max_length=192)
    scores = output[0] if output and isinstance(output[0], list) else output
    return interpret_scores(scores)
