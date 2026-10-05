const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const chatMessages = document.getElementById("chat-messages");

function addUserMessage(message) {
    const article = document.createElement("article");
    article.className = "message message-user";

    const avatar = document.createElement("img");
    avatar.className = "avatar";
    avatar.src = form.dataset.userAvatar;
    avatar.alt = "Your avatar";

    const content = document.createElement("div");
    content.className = "message-content";

    const author = document.createElement("span");
    author.className = "message-author";
    author.textContent = "You";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = message;

    content.append(author, bubble);
    article.append(avatar, content);
    chatMessages.append(article);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addBotMessage(message, songs = []) {
    const article = document.createElement("article");
    article.className = "message message-bot";

    const content = document.createElement("div");
    content.className = "message-content";

    const author = document.createElement("span");
    author.className = "message-author";
    author.textContent = "Moodify";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    const text = document.createElement("p");
    text.textContent = message;
    bubble.append(text);

    for (const song of songs.slice(0, 5)) {
        const card = document.createElement("div");
        card.className = "song-card";

        const title = document.createElement("h3");
        title.textContent = song.name;

        const artist = document.createElement("p");
        artist.textContent = `Artist: ${song.artist}`;

        const album = document.createElement("p");
        album.textContent = `Album: ${song.album}`;

        const link = document.createElement("a");
        link.textContent = "Open in Spotify";
        link.href = song.spotify_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";

        card.append(title, artist, album, link);
        bubble.append(card);
    }

    content.append(author, bubble);
    article.append(content);
    chatMessages.append(article);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

let isLoading = false;

form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const message = input.value.trim();

    if (!message || isLoading) {
        return;
    }

    addUserMessage(message);
    input.value = "";

    const button = form.querySelector('button[type="submit"]');

    isLoading = true;
    button.disabled = true;
    button.textContent = "Thinking...";

    try {
        const response = await fetch("/recommend", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Something went wrong.");
        }

        addBotMessage(
            `Your mood is ${data.mood}. Here are some songs for you!`,
            data.songs
        );
    } catch (error) {
        addBotMessage(
            error.message || "Couldn't connect. Please try again."
        );
    } finally {
        isLoading = false;
        button.disabled = false;
        button.textContent = "Send";
        input.focus();
    }
});