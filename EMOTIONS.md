# Emotion detection in Moodify

Moodify uses a local, multilingual, multi-label classifier instead of converting
positive/negative sentiment into an emotion. The original `recommender.py`,
notebook and CSV are unchanged. The web app uses `emotion_detector.py` for text
analysis and keeps its existing song ranking and artist exclusions.

## Installation

Using the same virtual environment as Moodify:

```powershell
.\.venv\Scripts\python.exe setup_emotions.py
.\.venv\Scripts\python.exe app.py
```

The first command downloads the model into `.models/emotions` (ignored by Git).
Run it again on another computer after cloning. Chat requests run locally and
do not call an external inference API. If the model is missing or fails, the app
reports that and preserves the last musical mood instead of inventing an emotion.

## Interpretation

Each of the 11 labels has an independent sigmoid score. Labels at or above 0.5
are retained. Scores are not calibrated measures of real-world accuracy. When
no label reaches the threshold, the result is inconclusive. When strong labels
suggest different musical moods and differ by no more than 0.15, the selection
uses a neutral mood and displays the mixed emotions. These are application
heuristics, not clinically validated thresholds.

| Emotion | Musical mood |
| --- | --- |
| Joy | Happy |
| Sadness | Sad |
| Anger, frustration, disgust, contempt | Intense |
| Fear, love, gratitude | Calm |
| Neutral, surprise or inconclusive | Neutral |

Fear maps to calm music as a product choice; it does not mean that fear and
calmness are the same emotion. The model does not have separate anxiety or
calmness labels. Artist-only requests and “Otra selección” retain the previous
mood without reinterpreting artist names as feelings.

## Source and limitations

Model: [tabularisai/multilingual-emotion-classification](https://huggingface.co/tabularisai/multilingual-emotion-classification).
Its author documents Spanish and English support and training on synthetic data.
License: **CC BY-NC 4.0** (noncommercial use, with attribution).
Local examples do not establish general accuracy; slang, irony, negation and
mixed contexts still need evaluation with representative messages.

Run software tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest test_web test_emotions -v
```
