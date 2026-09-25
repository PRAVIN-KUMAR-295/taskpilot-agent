// TaskPilot Frontend Logic
const API_URL = window.TASKPILOT_API_URL || "http://127.0.0.1:8001";

const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const chatBox = document.getElementById("chatBox");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

let isWaitingForResponse = false;


// ==========================================
// Check Backend Health
// ==========================================

async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_URL}/health`, { method: "GET" });
        if (response.ok) {
            const data = await response.json();
            statusDot.className = "status-dot online";
            statusText.textContent = `Online (${data.tasks_count || 0} tasks)`;
            statusText.title = `Model: ${data.model || "default"} | Pending: ${data.pending_tasks || 0}`;
        } else {
            statusDot.className = "status-dot offline";
            statusText.textContent = `Error (${response.status})`;
        }
    } catch (err) {
        statusDot.className = "status-dot offline";
        statusText.textContent = "Offline (Port 8001)";
    }
}

// Initial check & interval
checkBackendHealth();
setInterval(checkBackendHealth, 10000);


// ==========================================
// Render Messages & Elements
// ==========================================

function appendUserMessage(text) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "message user";

    const content = document.createElement("div");
    content.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    content.appendChild(bubble);
    messageDiv.appendChild(content);
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTypingIndicator() {
    const indicatorDiv = document.createElement("div");
    indicatorDiv.id = "typingIndicator";
    indicatorDiv.className = "message assistant";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "AI";

    const content = document.createElement("div");
    content.className = "message-content";

    const typing = document.createElement("div");
    typing.className = "typing-indicator";
    typing.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    content.appendChild(typing);
    indicatorDiv.appendChild(avatar);
    indicatorDiv.appendChild(content);
    chatBox.appendChild(indicatorDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById("typingIndicator");
    if (indicator) {
        indicator.remove();
    }
}

function renderTaskCards(tasks) {
    if (!Array.isArray(tasks) || tasks.length === 0) return null;

    const listDiv = document.createElement("div");
    listDiv.className = "task-card-list";

    tasks.forEach(task => {
        const card = document.createElement("div");
        card.className = "task-card";

        const header = document.createElement("div");
        header.className = "task-card-header";

        const titleSpan = document.createElement("span");
        titleSpan.className = "task-title";
        titleSpan.textContent = task.title || "Untitled Task";

        const idBadge = document.createElement("span");
        idBadge.className = "badge badge-id";
        idBadge.textContent = `#${task.id}`;

        header.appendChild(titleSpan);
        header.appendChild(idBadge);
        card.appendChild(header);

        const meta = document.createElement("div");
        meta.className = "task-meta";

        const statusBadge = document.createElement("span");
        const status = (task.status || (task.completed ? "completed" : "pending")).toLowerCase();
        statusBadge.className = `badge badge-status ${status}`;
        statusBadge.textContent = status;
        meta.appendChild(statusBadge);

        const priorityBadge = document.createElement("span");
        const priority = (task.priority || "medium").toLowerCase();
        priorityBadge.className = `badge badge-priority ${priority}`;
        priorityBadge.textContent = `${priority} priority`;
        meta.appendChild(priorityBadge);

        if (task.due_date) {
            const dueBadge = document.createElement("span");
            dueBadge.className = "badge badge-due";
            dueBadge.textContent = `Due: ${task.due_date}`;
            meta.appendChild(dueBadge);
        }

        card.appendChild(meta);
        listDiv.appendChild(card);
    });

    return listDiv;
}

function renderApprovalCard(approval) {
    const card = document.createElement("div");
    card.className = "approval-card";

    const header = document.createElement("div");
    header.className = "approval-header";
    header.textContent = "Action Approval Required";
    card.appendChild(header);

    const promptP = document.createElement("div");
    promptP.className = "approval-prompt";
    promptP.innerHTML = `<strong>${escapeHtml(approval.prompt)}</strong><br><small style="color: #b45309;">${escapeHtml(approval.warning || "Requires confirmation.")}</small>`;
    card.appendChild(promptP);

    const actions = document.createElement("div");
    actions.className = "approval-actions";

    const confirmBtn = document.createElement("button");
    confirmBtn.type = "button";
    confirmBtn.className = "btn-confirm";
    confirmBtn.textContent = "Confirm & Proceed";
    confirmBtn.onclick = () => {
        actions.innerHTML = "<em style='font-size: 12px; color: #15803d;'>Confirmation sent...</em>";
        sendMessage(`Confirmed: ${approval.action_type}`, approval);
    };

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "btn-cancel";
    cancelBtn.textContent = "Cancel";
    cancelBtn.onclick = () => {
        actions.innerHTML = "<em style='font-size: 12px; color: #64748b;'>Action cancelled.</em>";
    };

    actions.appendChild(confirmBtn);
    actions.appendChild(cancelBtn);
    card.appendChild(actions);

    return card;
}

function appendAssistantMessage(data) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "message assistant";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "AI";

    const content = document.createElement("div");
    content.className = "message-content";

    const sender = document.createElement("div");
    sender.className = "sender";
    sender.textContent = "TaskPilot";
    content.appendChild(sender);

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = data.response || "No response provided.";
    content.appendChild(bubble);

    // If human approval is required, attach approval card
    if (data.action_pending_approval) {
        const approvalCard = renderApprovalCard(data.action_pending_approval);
        content.appendChild(approvalCard);
    }

    // If structured tasks returned, render task cards
    if (data.tasks && data.tasks.length > 0) {
        const taskCards = renderTaskCards(data.tasks);
        if (taskCards) {
            content.appendChild(taskCards);
        }
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


// ==========================================
// Send Message
// ==========================================

async function sendMessage(customText, confirmedAction = null) {
    const message = (customText !== undefined ? customText : messageInput.value).trim();
    if (!message || isWaitingForResponse) return;

    if (customText === undefined) {
        messageInput.value = "";
    }

    appendUserMessage(message);

    isWaitingForResponse = true;
    sendButton.disabled = true;
    messageInput.disabled = true;
    showTypingIndicator();

    try {
        const payload = {
            message: message,
            confirmed_action: confirmedAction
        };

        const response = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        removeTypingIndicator();

        if (!response.ok) {
            const errText = await response.text();
            appendAssistantMessage({
                response: `Server communication error (${response.status}): ${errText || "Unable to reach TaskPilot backend."}`
            });
            return;
        }

        const data = await response.json();
        appendAssistantMessage(data);

        // Refresh task status in header
        checkBackendHealth();

    } catch (err) {
        removeTypingIndicator();
        appendAssistantMessage({
            response: `Unable to connect to TaskPilot backend at ${API_URL}. Please ensure the backend server is running with 'uvicorn backend.main:app --port 8001'.`
        });
    } finally {
        isWaitingForResponse = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}


// ==========================================
// Event Listeners
// ==========================================

sendButton.addEventListener("click", () => sendMessage());

messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

// Setup quick suggestion chips
document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
        const prompt = chip.getAttribute("data-prompt");
        if (prompt) {
            messageInput.value = prompt;
            sendMessage();
        }
    });
});

messageInput.focus();
