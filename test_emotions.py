import unittest
from emotion_detector import interpret_scores, EMOTION_MOODS


def scores(**values):
    return [{"label": label, "score": values.get(label, .01)} for label in EMOTION_MOODS]


class EmotionTests(unittest.TestCase):
    def test_emotions_are_not_all_sadness(self):
        for label, mood in [("joy", "happy"), ("anger", "intense"), ("fear", "calm"), ("sadness", "sad")]:
            self.assertEqual(interpret_scores(scores(**{label: .9}))["mood"], mood)

    def test_no_signal_is_not_falsely_confident_neutral(self):
        result = interpret_scores(scores(joy=.3))
        self.assertTrue(result["uncertain"])
        self.assertEqual(result["emotions"], [])

    def test_mixed_emotions_are_preserved(self):
        result = interpret_scores(scores(joy=.9, sadness=.85))
        self.assertTrue(result["mixed"])
        self.assertEqual(result["mood"], "neutral")
        self.assertEqual(len(result["emotions"]), 2)

    def test_specific_signal_wins_over_neutral(self):
        self.assertEqual(interpret_scores(scores(neutral=.9, sadness=.8))["emotion"], "sadness")

    def test_invalid_outputs_fail(self):
        for value in (float('nan'), float('inf'), -1, 2):
            with self.assertRaises(ValueError):
                interpret_scores(scores(joy=value))


if __name__ == "__main__":
    unittest.main()
