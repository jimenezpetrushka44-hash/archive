from recommender import recommend_song


# ============================================================
# TEST MOODIFY
# ============================================================

user_text = "I feel really happy today!"

result = recommend_song(user_text)


print("\n==============================")
print("       MOODIFY TEST")
print("==============================")

print("\nUser:")
print(user_text)

print("\nSentiment:")
print(result["sentiment"])

print("\nConfidence:")
print(round(result["confidence"], 3))

print("\nDetected Mood:")
print(result["mood"])

print("\nRecommended Songs:")
print("------------------------------")


for number, song in enumerate(result["songs"], start=1):

    print(f"\n{number}. {song['name']}")
    print(f"   Artist: {song['artist']}")
    print(f"   Album: {song['album']}")
    print(f"   Popularity: {song['popularity']}")
    print(f"   Valence: {song['valence']}")
    print(f"   Energy: {song['energy']}")
    print(f"   Spotify: {song['spotify_url']}")


print("\n==============================")