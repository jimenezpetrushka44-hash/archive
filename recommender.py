import pandas as pd
from transformers import pipeline



#LOAD DATASET


df = pd.read_csv("universal_top_spotify_songs.csv")



# CLEAN DATASET

# Keep only the columns Moodify needs
df = df[
    [
        "spotify_id",
        "name",
        "artists",
        "album_name",
        "popularity",
        "danceability",
        "energy",
        "valence",
        "tempo"
    ]
].copy()


# Remove songs with missing important information
df = df.dropna(
    subset=[
        "spotify_id",
        "name",
        "artists",
        "energy",
        "valence"
    ]
)


# Remove duplicate songs
df = df.drop_duplicates(
    subset="spotify_id"
).reset_index(drop=True)



# CLASSIFY SONGS BY MOOD


def classify_song_mood(row):

    valence = row["valence"]
    energy = row["energy"]

    # Positive valence + high energy
    if valence >= 0.6 and energy >= 0.6:
        return "happy"

    # Positive valence + lower energy
    elif valence >= 0.6 and energy < 0.6:
        return "calm"

    # Negative valence + high energy
    elif valence < 0.4 and energy >= 0.6:
        return "intense"

    # Negative valence + low energy
    elif valence < 0.4 and energy < 0.6:
        return "sad"

    # Songs that fall in the middle
    else:
        return "neutral"


# Apply mood classification to every song
df["mood"] = df.apply(
    classify_song_mood,
    axis=1
)



# LOAD SENTIMENT ANALYSIS MODEL


sentiment_pipeline = pipeline(
    task="sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)



# RECOMMENDATION FUNCTION


def recommend_song(user_text):

    # Analyze the user's message
    result = sentiment_pipeline(user_text)

    sentiment = result[0]["label"]
    confidence = result[0]["score"]



    # Convert sentiment into a musical mood
 

    if sentiment == "POSITIVE":

        if confidence >= 0.85:
            target_mood = "happy"

        else:
            target_mood = "calm"

    else:

        if confidence >= 0.85:
            target_mood = "sad"

        else:
            target_mood = "neutral"


    # Find songs matching the mood

    songs = df[
        df["mood"] == target_mood
    ]


    # Prefer popular / recognizable songs


    popular_songs = songs[
        songs["popularity"] >= 60
    ]

    # Only use popularity filter if enough songs exist
    if len(popular_songs) >= 5:
        songs = popular_songs


    # Choose 5 random recommendations


    recommendations = songs.sample(
        n=min(5, len(songs))
    )


    # Convert Pandas rows into normal Python dictionaries


    song_list = []

    for _, song in recommendations.iterrows():

        song_list.append(
            {
                "name": song["name"],
                "artist": song["artists"],
                "album": song["album_name"],
                "popularity": int(song["popularity"]),
                "valence": float(song["valence"]),
                "energy": float(song["energy"]),
                "mood": target_mood,
                "spotify_url": (
                    "https://open.spotify.com/track/"
                    + str(song["spotify_id"])
                )
            }
        )

    # Return result


    return {
        "sentiment": sentiment,
        "confidence": float(confidence),
        "mood": target_mood,
        "songs": song_list
    }