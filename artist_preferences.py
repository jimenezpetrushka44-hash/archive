"""Explicit artist commands, matched against complete catalog names."""
import re
import unicodedata


def normalize(text):
    text = unicodedata.normalize("NFKD", text.casefold().replace("’", "'"))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def artist_names(value):
    return [name.strip() for name in str(value).split(",") if name.strip()]


def build_aliases(catalog):
    aliases = {normalize(name): name for value in catalog.artists.dropna()
               for name in artist_names(value)}
    if "sabrina carpenter" in aliases:
        aliases["sabrina"] = aliases["sabrina carpenter"]
    return aliases


COMMAND = re.compile(
    r"\b(?P<negative>no me gustan?|no quiero(?: escuchar)?|sin|excluye|odio|"
    r"i (?:don't|dont|do not) like|i dislike|i hate|exclude|without)\s+"
    r"|\b(?P<positive>me gustan?|me encantan?|quiero escuchar|"
    r"recomiendame(?: canciones de)?|i like|i love|play|songs by)\s+"
)
FEELING = re.compile(r"\b(?:pero|but|me siento|estoy|i feel|i am|i'm)\b")


def parse_preferences(message, previous, aliases):
    preferences = {key: list(previous.get(key, [])) for key in ("liked", "disliked")}
    text = normalize(message)
    matches = list(COMMAND.finditer(text))
    removed, updates, unknown = [], [], []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        clause = text[match.end():end]
        stop = FEELING.search(clause)
        if stop:
            clause = clause[:stop.start()]
        # Personal statements are feelings, not artist commands ("I love you").
        if re.match(r"(?:you|my|our|mi|mis|tu|tus|estar|sentirme|como|how|being)\b", clause.strip()):
            continue
        remaining = clause.strip(" ,.!?;:")
        found = []
        while remaining:
            remaining = re.sub(r"^(?:[,;&]+|and\b|y\b|a\b)\s*", "", remaining).strip()
            if not remaining:
                break
            alias = next((a for a in sorted(aliases, key=len, reverse=True)
                          if remaining.startswith(a) and
                          (len(remaining) == len(a) or not remaining[len(a)].isalnum())), None)
            if alias:
                found.append(aliases[alias])
                remaining = remaining[len(alias):].lstrip(" ,.!?;:")
            else:
                part = re.split(r"\s+(?:and|y)\s+|[,;]", remaining, maxsplit=1)
                unknown.append(part[0].strip())
                remaining = part[1].strip() if len(part) > 1 else ""
        key = "disliked" if match.group("negative") else "liked"
        other = "liked" if key == "disliked" else "disliked"
        for name in found:
            if name in preferences[other]:
                preferences[other].remove(name)
            if name not in preferences[key]:
                preferences[key].append(name)
        updates.extend(found)
        removed.append((match.start(), match.end() + len(clause)))
    for start, end in reversed(removed):
        text = text[:start] + " " + text[end:]
    text = re.sub(r"\b(?:hello|hi|hey|hola|and|y|but|pero)\b", " ", text).strip(" ,.!?;:")
    return preferences, text.strip(), updates, unknown
