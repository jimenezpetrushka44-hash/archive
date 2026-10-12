r"""Run: .\.venv\Scripts\python.exe -m unittest test_web -v

Use the real catalog and a mock sentiment model for deterministic edge cases.
"""
import sys
import types
import unittest
from unittest.mock import Mock, patch
import pandas as pd

catalog = pd.read_csv("universal_top_spotify_songs.csv").drop_duplicates("spotify_id")
v, e = catalog.valence, catalog.energy
catalog["mood"] = "neutral"
for mood, mask in [("happy", (v >= .6) & (e >= .6)), ("calm", (v >= .6) & (e < .6)),
                   ("sad", (v < .4) & (e < .6)), ("intense", (v < .4) & (e >= .6))]:
    catalog.loc[mask, "mood"] = mood
fake = types.ModuleType("recommender")
fake.df = catalog
fake.recommend_song = Mock(return_value={"mood": "happy", "sentiment": "POSITIVE", "confidence": .95})
with patch.dict(sys.modules, {"recommender": fake}):
    import app as web
from artist_preferences import artist_names


class WebTests(unittest.TestCase):
    def setUp(self):
        self.client = web.app.test_client()
        fake.recommend_song.reset_mock(side_effect=True)
        detector = patch.object(web, "detect_emotions", fake.recommend_song)
        detector.start()
        self.addCleanup(detector.stop)

    def send(self, message, **extra):
        response = self.client.post("/recommend", json={"message": message, **extra})
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def test_page_and_assets(self):
        for path in ("/", "/static/style.css", "/static/script.js", "/static/images/missy_hello.png"):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)

    def test_artist_only_recommends_immediately(self):
        for message in ("me gusta illit", "Sabrina", "songs by Sabrina Carpenter"):
            data = self.send(message, artist_mode="only")
            self.assertTrue(data["songs"])
            for song in data["songs"]:
                self.assertTrue(set(artist_names(song["artist"])) & set(data["preferences"]["liked"]))
        fake.recommend_song.assert_not_called()

    def test_mixed_message_and_exclusions(self):
        data = self.send("me gusta Sabrina y no me gusta Bad Bunny pero I feel sad")
        self.assertEqual(data["preferences"], {"liked": ["Sabrina Carpenter"], "disliked": ["Bad Bunny"]})
        fake.recommend_song.assert_called_with("i feel sad")
        data = self.send("Recomendar", preferences={"disliked": ["Bad Bunny"]})
        self.assertEqual(len(data["songs"]), 5)
        self.assertTrue(all("Bad Bunny" not in artist_names(s["artist"]) for s in data["songs"]))

    def test_multiple_and_unknown_names(self):
        data = self.send("I like ILLIT and Sabrina and nonexistentartist")
        self.assertEqual(data["preferences"]["liked"], ["ILLIT", "Sabrina Carpenter"])
        self.assertTrue(data["songs"])
        self.assertTrue(any("nonexistentartist" in n for n in data["notices"]))

    def test_no_substring_artist_match(self):
        data = self.send("I like SabrinaFake")
        self.assertEqual(data["preferences"]["liked"], [])
        self.assertTrue(data["notices"])

    def test_greeting_and_last_mood(self):
        self.assertEqual(self.send("hello!")["kind"], "greeting")
        self.assertEqual(self.send("me gusta ILLIT", last_mood="sad")["mood"], "sad")
        fake.recommend_song.assert_not_called()

    def test_love_statement_is_not_an_artist_filter(self):
        for message in ("I love you", "Te amo y me encanta estar contigo"):
            data = self.send(message)
            fake.recommend_song.assert_called_with(message)
            self.assertEqual(data["preferences"]["liked"], [])
            self.assertFalse(any("No reconocimos" in notice for notice in data["notices"]))

    def test_exclusion_wins_and_can_be_reversed(self):
        data = self.send("Recomendar", preferences={"liked": ["Bad Bunny"], "disliked": ["Bad Bunny"]})
        self.assertEqual(data["preferences"]["liked"], [])
        data = self.send("me gusta Bad Bunny", preferences=data["preferences"])
        self.assertEqual(data["preferences"]["disliked"], [])

    def test_model_failure_falls_back(self):
        with patch.object(web, "detect_emotions", side_effect=RuntimeError("offline")), patch.object(web.app.logger, "exception"):
            data = self.send("I feel great", preferences={"liked": ["ILLIT"]}, last_mood="calm")
        self.assertEqual(data["mood"], "calm")
        self.assertTrue(data["songs"])
        self.assertTrue(data["notices"])

    def test_empty_catalog_does_not_break(self):
        with patch.object(web, "df", catalog.iloc[0:0]):
            data = self.send("Recomendar")
        self.assertEqual(data["songs"], [])
        self.assertTrue(data["notices"])

    def test_bad_requests(self):
        for payload in ([], {}, {"message": " "}, {"message": 1}, {"message": "a" * 501},
                        {"message": "hi", "preferences": []}, {"message": "hi", "last_mood": []},
                        {"message": "hi", "preferences": {"liked": [12]}}):
            self.assertEqual(self.client.post("/recommend", json=payload).status_code, 400)
        self.assertEqual(self.client.post("/recommend", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/recommend", json={"message": "a" * 400000}).status_code, 413)

    def test_another_selection_avoids_previous_songs(self):
        first = self.send("Recomendar", last_mood="sad")
        ids = [song["spotify_id"] for song in first["songs"]]
        second = self.send("Otra selección", seen_ids=ids, last_mood="sad")
        self.assertEqual(len(second["songs"]), 5)
        self.assertEqual(second["mood"], "sad")
        self.assertFalse(set(ids) & {s["spotify_id"] for s in second["songs"]})
        fake.recommend_song.assert_not_called()

    def test_prefer_fills_with_other_artists_but_only_does_not(self):
        prefs = {"liked": ["ILLIT"], "disliked": ["Bad Bunny"]}
        strict = self.send("Recomendar", preferences=prefs, artist_mode="only")
        preferred = self.send("Recomendar", preferences=prefs, artist_mode="prefer")
        self.assertLess(len(strict["songs"]), 5)
        self.assertEqual(len(preferred["songs"]), 5)
        self.assertIn("ILLIT", artist_names(preferred["songs"][0]["artist"]))
        self.assertTrue(all("ILLIT" in artist_names(s["artist"]) for s in strict["songs"]))
        self.assertTrue(all("Bad Bunny" not in artist_names(s["artist"]) for s in preferred["songs"]))

    def test_exhaustion_and_explicit_history_reset(self):
        prefs = {"liked": ["ILLIT"]}
        first = self.send("Recomendar", preferences=prefs, artist_mode="only")
        ids = [s["spotify_id"] for s in first["songs"]]
        exhausted = self.send("Otra selección", preferences=prefs, artist_mode="only", seen_ids=ids)
        self.assertEqual(exhausted["songs"], [])
        self.assertFalse(exhausted["has_more"])
        self.assertIn("Ya viste", exhausted["notices"][0])
        reset = self.send("Otra selección", preferences=prefs, artist_mode="only", seen_ids=[])
        self.assertEqual([s["spotify_id"] for s in reset["songs"]], ids)

    def test_bad_discovery_parameters(self):
        for extra in ({"artist_mode": "invalid"}, {"artist_mode": []}, {"seen_ids": "abc"},
                      {"seen_ids": [None]}, {"seen_ids": ["bad-id"]}, {"seen_ids": ["A" * 22] * 10001}):
            response = self.client.post("/recommend", json={"message": "Recomendar", **extra})
            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
