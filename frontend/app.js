
const API_URL = "http://127.0.0.1:8000/chat";

// HTML elements
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const messages = document.getElementById("messages");
const sendButton = document.getElementById("sendButton");
const clearButton = document.getElementById("clearButton");
const statusText = document.getElementById("statusText");


// Create a unique ID for each conversation
function createConversationId() {
    if (typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }

    // Fallback for browsers without crypto.randomUUID
    return "eva-" + Date.now() + "-" +
        Math.random().toString(36).substring(2);
}


// Keep the same ID for all messages in the current conversation
let conversationId = createConversationId();


// Display a message in the chat
function addMessage(sender, text) {
    const row = document.createElement("div");

    row.className = `message ${
        sender === "You" ? "user-message" : "eva-message"
    }`;

    // Add EVA avatar
    if (sender !== "You") {
        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = "E";

        row.appendChild(avatar);
    }

    // Create message bubble
    const bubble = document.createElement("div");
    bubble.className = "bubble";

    // Sender name
    const label = document.createElement("span");
    label.className = "sender";
    label.textContent = sender;

    // Message text
    const paragraph = document.createElement("p");
    paragraph.textContent = text;

    bubble.append(label, paragraph);
    row.appendChild(bubble);

    messages.appendChild(row);

    // Scroll to latest message
    messages.scrollTop = messages.scrollHeight;

    return paragraph;
}


// Send a message to EVA
async function sendMessage(message) {
    const cleanMessage = message.trim();

    // Do not send empty messages
    if (!cleanMessage) {
        return;
    }

    // Prevent multiple simultaneous requests
    if (sendButton.disabled) {
        return;
    }

    // Show user's message
    addMessage("You", cleanMessage);

    // Clear input
    messageInput.value = "";

    // Disable send button while EVA responds
    sendButton.disabled = true;
    statusText.textContent = "EVA is thinking...";

    // Show temporary loading message
    const loadingBubble = addMessage("EVA", "Thinking...");

    try {
        // Send message and conversation ID to FastAPI
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: cleanMessage,
                conversation_id: conversationId
            })
        });

        // Read response from FastAPI
        const data = await response.json();

        // Handle unsuccessful HTTP response
        if (!response.ok) {
            let errorMessage = `AI service returned HTTP ${response.status}.`;

            if (data.detail) {
                if (typeof data.detail === "string") {
                    errorMessage = data.detail;
                } else {
                    errorMessage = JSON.stringify(data.detail);
                }
            }

            throw new Error(errorMessage);
        }

        // Validate response
        if (
            typeof data.response !== "string" ||
            !data.response.trim()
        ) {
            throw new Error("EVA returned an empty response.");
        }

        // Display EVA's answer
        loadingBubble.textContent = data.response;

        statusText.textContent = "Response received";

    } catch (error) {
        console.error("EVA chat error:", error);

        // Display error inside the existing EVA message bubble
        loadingBubble.textContent =
            `Unable to get a response. ${error.message}`;

        statusText.textContent = "Connection or AI error";

    } finally {
        // Enable sending messages again
        sendButton.disabled = false;

        messageInput.focus();
        messages.scrollTop = messages.scrollHeight;
    }
}


// Handle the chat form submission
chatForm.addEventListener("submit", (event) => {
    event.preventDefault();

    sendMessage(messageInput.value);
});


// Send message when Enter is pressed
// Shift + Enter allows a new line
messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();

        chatForm.requestSubmit();
    }
});


// Start a new conversation when Clear is clicked
clearButton.addEventListener("click", () => {
    // Generate a fresh conversation ID
    conversationId = createConversationId();

    // Remove all previous messages from the UI
    messages.replaceChildren();

    // Display EVA's welcome message
    addMessage(
        "EVA",
        "Hello! I'm EVA. What would you like to talk about?"
    );

    statusText.textContent = "New conversation started";

    messageInput.focus();
});


// Handle suggestion buttons
document.querySelectorAll(".suggestion").forEach((button) => {
    button.addEventListener("click", () => {
        sendMessage(button.textContent);
    });
});
