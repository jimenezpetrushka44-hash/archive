"""Small reproducible smoke evaluation, not a representative accuracy benchmark."""
import json
from pathlib import Path
from emotion_detector import detect_emotions, MODEL_ID, MODEL_REVISION

CASES = [
    ("Estoy muy feliz porque aprobé mi examen", "joy"),
    ("Me siento triste y tengo ganas de llorar", "sadness"),
    ("Estoy furiosa, me mintieron otra vez", "anger"),
    ("Tengo miedo de lo que pueda pasar mañana", "fear"),
    ("Estoy frustrada porque nada sale como esperaba", "frustration"),
    ("Te amo y me encanta estar contigo", "love"),
    ("Gracias por ayudarme, te lo agradezco mucho", "gratitude"),
    ("No estoy feliz, estoy muy triste", "sadness"),
    ("I am so happy I passed my exam", "joy"),
    ("I feel lonely and sad and want to cry", "sadness"),
    ("I am furious that they lied to me again", "anger"),
    ("I am scared of what might happen tomorrow", "fear"),
    ("I feel frustrated because nothing works", "frustration"),
    ("I love you and love spending time with you", "love"),
    ("Thank you so much for helping me", "gratitude"),
    ("I am not happy, I am very sad", "sadness"),
]

if __name__ == "__main__":
    rows = []
    for text, expected in CASES:
        result = detect_emotions(text)
        detected = [item["label"] for item in result["emotions"]]
        rows.append({"text": text, "expected": expected, "detected": detected,
                     "mood": result["mood"], "hit": expected in detected})
    report = {"model": MODEL_ID, "revision": MODEL_REVISION, "cases": len(rows),
              "expected_label_present": sum(row["hit"] for row in rows),
              "limitation": "Handwritten smoke cases, not held-out accuracy or precision.", "results": rows}
    Path("emotion_evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
