const API_URL = "http://127.0.0.1:8001";

const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const chatBox = document.getElementById("chatBox");


// ==============================
// Add message to chat
// ==============================

function addMessage(message, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}`;

    // Assistant avatar
    if (sender === "assistant") {
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = "AI";

        messageDiv.appendChild(avatar);
    }

    const content = document.createElement("div");
    content.className = "message-content";

    // Assistant name
    if (sender === "assistant") {
        const senderName = document.createElement("div");
        senderName.className = "sender";
        senderName.textContent = "TaskPilot";

        content.appendChild(senderName);
    }

    // Message bubble
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = message;

    content.appendChild(bubble);
    messageDiv.appendChild(content);

    chatBox.appendChild(messageDiv);

    // Scroll to latest message
    chatBox.scrollTop = chatBox.scrollHeight;
}


// ==============================
// Loading state
// ==============================

function setLoading(loading) {
    sendButton.disabled = loading;
    messageInput.disabled = loading;

    sendButton.textContent = loading
        ? "Sending..."
        : "Send";
}


// ==============================
// Send message to backend
// ==============================

async function sendMessage() {
    const message = messageInput.value.trim();

    // Don't send empty messages
    if (!message) {
        return;
    }

    // Show user's message
    addMessage(message, "user");

    // Clear input
    messageInput.value = "";

    // Show loading
    setLoading(true);

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })
        });

        // Read backend response
        const responseText = await response.text();

        console.log("Backend status:", response.status);
        console.log("Backend response:", responseText);


        // ==============================
        // Backend returned an error
        // ==============================

        if (!response.ok) {
            console.error(
                "Backend error:",
                response.status,
                responseText
            );

            addMessage(
                `Backend error (${response.status}): ${responseText}`,
                "assistant"
            );

            return;
        }


        // ==============================
        // Parse JSON
        // ==============================

        let data;

        try {
            data = JSON.parse(responseText);
        } catch (error) {
            console.error("JSON parse error:", error);

            addMessage(
                responseText,
                "assistant"
            );

            return;
        }


        // ==============================
        // Check assistant response
        // ==============================

        if (!data.response) {
            console.error(
                "Invalid backend response:",
                data
            );

            addMessage(
                "Backend ne valid response nahi diya.",
                "assistant"
            );

            return;
        }


        // ==============================
        // Show assistant response
        // ==============================

        addMessage(
            data.response,
            "assistant"
        );

    } catch (error) {

        // ==============================
        // Connection error
        // ==============================

        console.error(
            "Connection error:",
            error
        );

        addMessage(
            `Backend connection error: ${error.message}`,
            "assistant"
        );

    } finally {

        // Stop loading
        setLoading(false);

        // Focus input again
        messageInput.focus();
    }
}


// ==============================
// Send button
// ==============================

sendButton.addEventListener(
    "click",
    sendMessage
);


// ==============================
// Enter key
// ==============================

messageInput.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }

    }
);


// ==============================
// Initial focus
// ==============================

messageInput.focus();
