const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const chatMessages = document.getElementById("chat-messages");
const statusText = document.getElementById("request-status");
const filterStatus = document.getElementById("filter-status");
const artistInput = document.getElementById("artist-input");
const artists = [...document.querySelectorAll("#artist-list option")].map(option => option.value);
const normalize = text => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
const moodNames = { happy: "Feliz", sad: "Triste", calm: "Calmado", intense: "Intenso", neutral: "Neutral" };
let preferences = { liked: [], disliked: [] };
let lastMood = "neutral";
let isLoading = false;

// Storage is optional: private browsing or blocked storage must not break the chat.
function saveState() {
    try { sessionStorage.setItem("moodify-session", JSON.stringify({ preferences, lastMood })); } catch (_) {}
}
try {
    const saved = JSON.parse(sessionStorage.getItem("moodify-session"));
    if (saved && saved.preferences) {
        for (const key of ["liked", "disliked"]) {
            if (Array.isArray(saved.preferences[key])) preferences[key] = [...new Set(saved.preferences[key].filter(name => artists.includes(name)))].slice(0, 50);
        }
        preferences.liked = preferences.liked.filter(name => !preferences.disliked.includes(name));
        if (Object.hasOwn(moodNames, saved.lastMood)) lastMood = saved.lastMood;
    }
} catch (_) {}

const themeButton = document.getElementById("theme-toggle");
function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    themeButton.textContent = theme === "dark" ? "☀ Modo día" : "☾ Modo noche";
    themeButton.setAttribute("aria-pressed", String(theme === "dark"));
}
let initialTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
try { const saved = localStorage.getItem("moodify-theme"); if (["light", "dark"].includes(saved)) initialTheme = saved; } catch (_) {}
setTheme(initialTheme);
themeButton.addEventListener("click", () => {
    const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(theme);
    try { localStorage.setItem("moodify-theme", theme); } catch (_) {}
});

function renderPreferences() {
    const container = document.getElementById("preference-chips");
    container.replaceChildren();
    for (const key of ["liked", "disliked"]) {
        for (const name of preferences[key]) {
            const chip = document.createElement("span");
            chip.className = `chip ${key === "disliked" ? "excluded" : ""}`;
            chip.append(document.createTextNode(`${key === "liked" ? "♡" : "−"} ${name}`));
            const remove = document.createElement("button");
            remove.type = "button";
            remove.textContent = "×";
            remove.setAttribute("aria-label", `Quitar ${name} de ${key === "liked" ? "favoritos" : "excluidos"}`);
            remove.disabled = isLoading;
            remove.addEventListener("click", () => {
                preferences[key] = preferences[key].filter(artist => artist !== name);
                saveState(); renderPreferences();
                filterStatus.textContent = "Filtro quitado. Presioná Buscar para actualizar las canciones.";
            });
            chip.append(remove); container.append(chip);
        }
    }
}
function addArtist(key) {
    if (isLoading) return;
    const query = normalize(artistInput.value);
    const name = artists.find(artist => normalize(artist) === (query === "sabrina" ? "sabrina carpenter" : query));
    if (!name) { filterStatus.textContent = "Seleccioná un artista de la lista del catálogo."; return; }
    if (preferences[key].length >= 50) { filterStatus.textContent = "El límite es de 50 artistas por filtro."; return; }
    const other = key === "liked" ? "disliked" : "liked";
    preferences[other] = preferences[other].filter(artist => artist !== name);
    if (!preferences[key].includes(name)) preferences[key].push(name);
    artistInput.value = "";
    filterStatus.textContent = "Filtro guardado. Presioná Buscar para escuchar tu selección.";
    saveState(); renderPreferences();
}
document.getElementById("like-artist").addEventListener("click", () => addArtist("liked"));
document.getElementById("exclude-artist").addEventListener("click", () => addArtist("disliked"));
document.getElementById("clear-filters").addEventListener("click", () => {
    if (isLoading) return;
    preferences = { liked: [], disliked: [] };
    saveState(); renderPreferences(); filterStatus.textContent = "Filtros borrados. La siguiente búsqueda incluirá todos los artistas.";
});

function addMessage(text, user = false) {
    const article = document.createElement("article");
    article.className = `message message-${user ? "user" : "bot"}`;
    const avatar = document.createElement("img");
    avatar.className = "avatar"; avatar.alt = "";
    avatar.src = user ? form.dataset.userAvatar : form.dataset.botAvatar;
    const content = document.createElement("div"); content.className = "message-content";
    const author = document.createElement("span"); author.className = "message-author";
    author.textContent = user ? "VOS" : "MYSSY · TU SELECCIÓN";
    const bubble = document.createElement("div"); bubble.className = "message-bubble";
    const paragraph = document.createElement("p"); paragraph.textContent = text; bubble.append(paragraph);
    content.append(author, bubble); article.append(avatar, content); chatMessages.append(article);
    return bubble;
}
function showSongs(data) {
    const bubble = addMessage(data.kind === "greeting" ? data.reply : `${data.songs.length} canciones para vos · Mood: ${moodNames[data.mood] || data.mood}`);
    for (const notice of data.notices || []) {
        const text = document.createElement("p"); text.className = "notice"; text.textContent = notice; bubble.append(text);
    }
    for (const [index, song] of data.songs.entries()) {
        const card = document.createElement("div"); card.className = "song-card";
        const title = document.createElement("h3"); title.textContent = `${String(index + 1).padStart(2, "0")}  ${song.name}`;
        const artist = document.createElement("p"); artist.textContent = song.artist;
        const album = document.createElement("p"); album.textContent = `Álbum · ${song.album}`;
        card.append(title, artist, album);
        try {
            const url = new URL(song.spotify_url);
            if (url.protocol === "https:" && url.hostname === "open.spotify.com" && /^\/track\/[A-Za-z0-9]{22}$/.test(url.pathname)) {
                const link = document.createElement("a"); link.href = url.href; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = "Abrir en Spotify ↗"; card.append(link);
            }
        } catch (_) {}
        bubble.append(card);
    }
}
function setLoading(value) {
    isLoading = value;
    for (const button of document.querySelectorAll(".preferences-panel button, .suggestions button, #send-button")) button.disabled = value;
    artistInput.disabled = value;
    chatMessages.setAttribute("aria-busy", String(value));
    statusText.textContent = value ? "Buscando canciones para vos…" : "";
    document.getElementById("send-button").textContent = value ? "Buscando…" : "Enviar ↗";
}
async function sendMessage(message) {
    message = message.trim();
    if (!message || isLoading) return;
    if (message.length > 500) { statusText.textContent = "Usá hasta 500 caracteres."; return; }
    addMessage(message, true); setLoading(true);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60000);
    try {
        const response = await fetch("/recommend", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, preferences, last_mood: lastMood }), signal: controller.signal });
        let data;
        try { data = await response.json(); } catch (_) { throw new Error("El servidor no respondió correctamente. Verificá que Flask esté funcionando."); }
        if (!response.ok) throw new Error(data.error || "No se pudo completar la búsqueda.");
        if (!Array.isArray(data.songs) || !data.preferences || !Object.hasOwn(moodNames, data.mood)) throw new Error("La respuesta está incompleta. Intentá de nuevo.");
        preferences = data.preferences; lastMood = data.mood; saveState(); renderPreferences(); showSongs(data);
    } catch (error) {
        const bubble = addMessage(error.name === "AbortError" ? "La búsqueda tardó demasiado. Podés volver a intentarlo." : error instanceof TypeError ? "No hay conexión con Flask. Revisá el servidor y volvé a intentar." : error.message);
        const retry = document.createElement("button"); retry.type = "button"; retry.className = "soft-button"; retry.textContent = "Reintentar";
        retry.addEventListener("click", () => sendMessage(message)); bubble.append(retry);
    } finally {
        clearTimeout(timer); setLoading(false); renderPreferences();
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}
input.addEventListener("input", () => { document.getElementById("character-count").textContent = `${input.value.length} / 500`; });
form.addEventListener("submit", event => {
    event.preventDefault(); if (isLoading || !input.value.trim()) return;
    const message = input.value; input.value = ""; input.dispatchEvent(new Event("input")); sendMessage(message); input.focus();
});
document.querySelectorAll("[data-message]").forEach(button => button.addEventListener("click", () => sendMessage(button.dataset.message)));
document.getElementById("apply-filters").addEventListener("click", () => sendMessage("Recomendar"));
renderPreferences();
