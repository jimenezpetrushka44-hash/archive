"""Web interface and catalog filtering; the ML module remains unchanged."""
import math
import re
from flask import Flask, render_template, request, jsonify
from recommender import recommend_song, df
from artist_preferences import artist_names, build_aliases, normalize, parse_preferences

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
ARTIST_ALIASES = build_aliases(df)
KNOWN_ARTISTS = set(ARTIST_ALIASES.values())
MOOD_PROFILES = {"happy": (.85, .8), "calm": (.7, .3), "sad": (.2, .3),
                 "intense": (.25, .85), "neutral": (.5, .5)}


def clean_preferences(value):
    if not isinstance(value, dict):
        raise ValueError("Los filtros de artistas no son válidos.")
    result = {}
    for key in ("liked", "disliked"):
        names = value.get(key, [])
        if not isinstance(names, list) or len(names) > 50:
            raise ValueError("Podés seleccionar hasta 50 artistas por filtro.")
        if any(not isinstance(name, str) or normalize(name) not in ARTIST_ALIASES for name in names):
            raise ValueError("Hay un artista que no existe en el catálogo. Revisá los filtros.")
        result[key] = list(dict.fromkeys(ARTIST_ALIASES[normalize(name)] for name in names))
    result["liked"] = [n for n in result["liked"] if n not in result["disliked"]]
    return result


def personalize_result(result, preferences):
    mood = result["mood"]
    valence, energy = MOOD_PROFILES[mood]
    liked, disliked = set(preferences["liked"]), set(preferences["disliked"])
    candidates = df.copy()
    names = candidates.artists.map(lambda value: set(artist_names(value)))
    allowed = names.map(lambda artists: not bool(artists & disliked))
    if liked:
        allowed &= names.map(lambda artists: bool(artists & liked))
    candidates = candidates.loc[allowed].dropna(subset=["valence", "energy", "popularity"])
    candidates = candidates.loc[candidates.spotify_id.astype(str).str.fullmatch(r"[A-Za-z0-9]{22}")].copy()
    finite = candidates[["valence", "energy", "popularity"]].apply(lambda col: col.map(lambda n: math.isfinite(float(n)))).all(axis=1)
    candidates = candidates.loc[finite].copy()
    candidates["distance"] = (candidates.valence - valence) ** 2 + (candidates.energy - energy) ** 2
    candidates["mood_match"] = candidates.mood == mood
    candidates = candidates.sort_values(["mood_match", "distance", "popularity", "spotify_id"],
                                        ascending=[False, True, False, True])
    candidates = candidates.drop_duplicates("spotify_id").head(5)
    songs = []
    for _, song in candidates.iterrows():
        songs.append({"name": str(song["name"]), "artist": str(song.artists),
                      "album": song.album_name if isinstance(song.album_name, str) else "Álbum no disponible",
                      "popularity": int(song.popularity), "valence": float(song.valence),
                      "energy": float(song.energy), "mood": str(song.mood),
                      "spotify_url": "https://open.spotify.com/track/" + str(song.spotify_id)})
    notices = []
    if not songs:
        notices.append("No hay canciones con estos filtros. Quitá un artista preferido o una exclusión para ampliar la búsqueda.")
    elif any(song["mood"] != mood for song in songs):
        notices.append("Completamos la selección con otros moods disponibles, respetando tus filtros de artistas.")
    if songs and len(songs) < 5:
        quantity = "1 canción disponible" if len(songs) == 1 else f"{len(songs)} canciones disponibles"
        notices.append(f"El catálogo tiene {quantity} con estos filtros.")
    return {**result, "songs": songs, "notices": notices, "preferences": preferences}


@app.get("/")
def index():
    return render_template("index.html", artists=sorted(KNOWN_ARTISTS, key=str.casefold))


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="El mensaje es demasiado largo."), 413


@app.post("/recommend")
def recommend():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Enviá un objeto JSON válido."), 400
    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify(error="Escribí cómo te sentís o qué artista querés escuchar."), 400
    if len(message) > 500:
        return jsonify(error="Usá un mensaje de hasta 500 caracteres."), 400
    last_mood = data.get("last_mood", "neutral")
    if not isinstance(last_mood, str) or last_mood not in MOOD_PROFILES:
        return jsonify(error="El mood anterior no es válido."), 400
    try:
        previous = clean_preferences(data.get("preferences", {}))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    text = normalize(message).strip(" .!?¡¿")
    if text in {"reset preferences", "reiniciar preferencias"}:
        previous = {"liked": [], "disliked": []}
        text = ""
    if re.fullmatch(r"(?:hello|hi|hey|hola)(?:\s+(?:moodify|myssy))?", text):
        return jsonify(kind="greeting", reply="¡Hello! ¿Cómo te sentís hoy? También podés decirme qué artista querés escuchar.",
                       songs=[], preferences=previous, mood=last_mood, notices=[])
    preferences, mood_text, updates, unknown = parse_preferences(text, previous, ARTIST_ALIASES)
    if text in ARTIST_ALIASES:
        name = ARTIST_ALIASES[text]
        preferences["liked"] = [name]
        preferences["disliked"] = [n for n in preferences["disliked"] if n != name]
        mood_text = ""
    try:
        preferences = clean_preferences(preferences)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    result = {"mood": last_mood, "sentiment": None, "confidence": None}
    notices = []
    if mood_text and mood_text not in {"recomendar", "recommend", "mas canciones", "more songs"}:
        try:
            prediction = recommend_song(mood_text)
            if prediction.get("mood") not in MOOD_PROFILES:
                raise ValueError("Invalid model mood")
            result.update({key: prediction.get(key) for key in ("mood", "sentiment", "confidence")})
        except Exception:
            app.logger.exception("Sentiment analysis failed")
            notices.append("No pudimos analizar el texto. Usamos el último mood (o neutral) y respetamos tus artistas.")
    if unknown:
        notices.append("No reconocimos: " + ", ".join(unknown) + ". No se aplicó ese filtro; elegí el nombre desde la lista de artistas.")
    try:
        result = personalize_result(result, preferences)
        result["notices"] = notices + result["notices"]
        result["kind"] = "recommendations"
        return jsonify(result)
    except Exception:
        app.logger.exception("Catalog filtering failed")
        return jsonify(error="No pudimos consultar las canciones. Intentá de nuevo."), 500


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
