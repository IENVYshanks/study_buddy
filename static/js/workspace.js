const DEFAULT_ASSISTANT_MESSAGE = "Upload your study files in the sidebar, then ask questions here. Everything stays on this page so your files and conversation remain visible together.";
const CHAT_STORAGE_KEY = "study-agent-chat-state";
const ALLOWED_FILE_EXTENSIONS = new Set(["pdf", "txt", "md", "doc", "docx", "csv", "json"]);

const state = {
    uploadedFiles: [],
    chatMessages: loadChatState(),
    username: loadActiveUsername()
};

const fileInput = document.getElementById("file-upload");
const fileList = document.getElementById("uploaded-file-list");
const fileCount = document.getElementById("file-count");
const uploadMoreButton = document.getElementById("upload-more-btn");
const vectorizeFilesButton = document.getElementById("vectorize-files-btn");
const clearFilesButton = document.getElementById("clear-files-btn");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const resetChatButton = document.getElementById("reset-chat-btn");
const toast = document.getElementById("toast");
const chatSubmitButton = chatForm.querySelector("button[type='submit']");
let toastTimer = null;
let isStreaming = false;
let hasTriggeredExitCleanup = false;

function loadChatState() {
    try {
        const savedState = JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY));
        if (Array.isArray(savedState) && savedState.length > 0) {
            return savedState;
        }
    } catch (error) {
        console.warn("Unable to restore chat state.", error);
    }

    return [
        {
            role: "assistant",
            text: DEFAULT_ASSISTANT_MESSAGE
        }
    ];
}

function loadActiveUsername() {
    try {
        const savedUser = JSON.parse(localStorage.getItem("studyAgentUser"));
        return (savedUser?.name || "").trim();
    } catch (error) {
        return "";
    }
}

function ensureActiveUsername() {
    if (state.username) {
        return true;
    }

    showToast("Please sign in with a valid username first.");
    window.location.href = "/";
    return false;
}

function saveChatState() {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(state.chatMessages));
}

function showToast(message) {
    if (!message) {
        return;
    }

    toast.textContent = message;
    toast.classList.add("show");

    if (toastTimer) {
        clearTimeout(toastTimer);
    }

    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

function buildFileItem(filename) {
    const listItem = document.createElement("li");
    listItem.className = "file-item";

    const meta = document.createElement("div");
    meta.className = "file-meta";

    const name = document.createElement("strong");
    name.textContent = filename;

    const status = document.createElement("span");
    status.textContent = "Uploaded";

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "remove-file-btn";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", async () => {
        await removeFile(filename);
    });

    meta.append(name, status);
    listItem.append(meta, removeButton);
    return listItem;
}

function renderFiles() {
    fileCount.textContent = `${state.uploadedFiles.length} file${state.uploadedFiles.length === 1 ? "" : "s"}`;
    fileList.innerHTML = "";

    if (state.uploadedFiles.length === 0) {
        const emptyState = document.createElement("li");
        emptyState.className = "empty-state";
        emptyState.textContent = "No files uploaded yet.";
        fileList.appendChild(emptyState);
        return;
    }

    state.uploadedFiles.forEach((filename) => {
        fileList.appendChild(buildFileItem(filename));
    });
}

function buildMessageNode(message) {
    const messageElement = document.createElement("article");
    messageElement.className = `message ${message.role}`;

    const label = document.createElement("p");
    label.className = "message-label";
    label.textContent = message.role === "assistant" ? "Study Agent" : "You";

    const body = document.createElement("p");
    body.textContent = message.text;

    messageElement.append(label, body);
    return messageElement;
}

function renderMessages() {
    chatMessages.innerHTML = "";

    state.chatMessages.forEach((message) => {
        chatMessages.appendChild(buildMessageNode(message));
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function fetchFiles() {
    if (!ensureActiveUsername()) {
        return;
    }

    try {
        const response = await fetch(`/api/files?username=${encodeURIComponent(state.username)}`, {
            method: "GET"
        });
        const payload = await response.json();

        if (!response.ok) {
            showToast(payload.message || "Unable to load files.");
            return;
        }

        state.uploadedFiles = Array.isArray(payload.files) ? payload.files : [];
        renderFiles();
    } catch (error) {
        showToast("Network error while loading files.");
    }
}

async function uploadFile(file) {
    if (!isAllowedFile(file)) {
        showToast(`Unsupported file type for "${file.name}".`);
        return;
    }

    if (!ensureActiveUsername()) {
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("username", state.username);
    
    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        const payload = await response.json();
        showToast(payload.message || "Upload completed.");

        if (Array.isArray(payload.files)) {
            state.uploadedFiles = payload.files;
            renderFiles();
        }
    } catch (error) {
        showToast("Network error while uploading file.");
    }
}

function isAllowedFile(file) {
    const fileName = file?.name || "";
    const extension = fileName.includes(".") ? fileName.split(".").pop().toLowerCase() : "";
    return ALLOWED_FILE_EXTENSIONS.has(extension);
}

async function removeFile(filename) {
    if (!ensureActiveUsername()) {
        return;
    }

    const formData = new FormData();
    formData.append("filename", filename);
    formData.append("username", state.username);

    try {
        const response = await fetch("/api/delete", {
            method: "POST",
            body: formData
        });
        const payload = await response.json();
        showToast(payload.message || "Delete completed.");

        if (Array.isArray(payload.files)) {
            state.uploadedFiles = payload.files;
            renderFiles();
        }
    } catch (error) {
        showToast("Network error while deleting file.");
    }
}

async function removeAllFiles() {
    if (!ensureActiveUsername()) {
        return;
    }

    try {
        const response = await fetch("/api/delete-all", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username: state.username })
        });
        const payload = await response.json();
        showToast(payload.message || "All files removed.");

        if (Array.isArray(payload.files)) {
            state.uploadedFiles = payload.files;
            renderFiles();
        }
    } catch (error) {
        showToast("Network error while removing files.");
    }
}

fileInput.addEventListener("change", async (event) => {
    const selectedFiles = Array.from(event.target.files || []);

    for (const file of selectedFiles) {
        await uploadFile(file);
    }

    fileInput.value = "";
});

uploadMoreButton.addEventListener("click", () => {
    fileInput.click();
});

clearFilesButton.addEventListener("click", async () => {
    await removeAllFiles();
});

vectorizeFilesButton.addEventListener("click", async () => {
    await vectorizeFiles();
});

chatForm.addEventListener("submit", (event) => {
    sendChatMessage(event);
});

async function sendChatMessage(event) {
    event.preventDefault();
    const userText = chatInput.value.trim();

    if (!userText) {
        return;
    }

    if (isStreaming) {
        showToast("Please wait for the current response to finish.");
        return;
    }

    isStreaming = true;
    setChatLoadingState(true);

    state.chatMessages.push({
        role: "user",
        text: userText
    });

    state.chatMessages.push({
        role: "assistant",
        text: ""
    });

    const assistantIndex = state.chatMessages.length - 1;
    chatForm.reset();
    chatInput.focus();
    renderMessages();

    await requestLLMResponseStream(userText, assistantIndex);
    isStreaming = false;
    setChatLoadingState(false);
}

function setChatLoadingState(isLoading) {
    chatInput.disabled = isLoading;
    chatSubmitButton.disabled = isLoading;
    chatSubmitButton.textContent = isLoading ? "Streaming..." : "Send";
}

async function requestLLMResponseStream(userText, assistantIndex) {
    const fallbackMessage = "I did not receive a response from the model.";

    try {
        const response = await fetch("/api/generate-response-stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ user_input: userText })
        });

        if (!response.ok) {
            const payload = await response.json();
            const errorMessage = payload.message || "Unable to generate a response right now.";
            state.chatMessages[assistantIndex].text = errorMessage;
            showToast(errorMessage);
            saveChatState();
            renderMessages();
            return;
        }

        if (!response.body) {
            state.chatMessages[assistantIndex].text = fallbackMessage;
            saveChatState();
            renderMessages();
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const rawLine of lines) {
                const line = rawLine.trim();
                if (!line) {
                    continue;
                }

                let packet;
                try {
                    packet = JSON.parse(line);
                } catch (error) {
                    continue;
                }

                if (packet.type === "chunk") {
                    state.chatMessages[assistantIndex].text += packet.content || "";
                    renderMessages();
                } else if (packet.type === "error") {
                    const errorMessage = packet.message || "Unable to generate a response right now.";
                    state.chatMessages[assistantIndex].text = errorMessage;
                    showToast(errorMessage);
                    saveChatState();
                    renderMessages();
                    return;
                }
            }
        }

        if (!state.chatMessages[assistantIndex].text.trim()) {
            state.chatMessages[assistantIndex].text = fallbackMessage;
        }

        saveChatState();
        renderMessages();
    } catch (error) {
        const errorMessage = "Network error while getting model response.";
        state.chatMessages[assistantIndex].text = errorMessage;
        showToast(errorMessage);
        saveChatState();
        renderMessages();
    }
}

resetChatButton.addEventListener("click", () => {
    resetChatHistory();
});

async function resetChatHistory() {
    try {
        const response = await fetch("/api/delete-history", {
            method: "POST"
        });
        const payload = await response.json();
        showToast(payload.message || "Chat history reset.");

        if (response.ok) {
            state.chatMessages = [
                {
                    role: "assistant",
                    text: DEFAULT_ASSISTANT_MESSAGE
                }
            ];
            saveChatState();
            renderMessages();
        }
    } catch (error) {
        showToast("Network error while resetting chat history.");
    }
}

async function initializeWorkspace() {
    if (!ensureActiveUsername()) {
        return;
    }

    renderMessages();
    renderFiles();
    await fetchFiles();
}

async function vectorizeFiles() {
    if (state.uploadedFiles.length === 0) {
        showToast("Upload at least one file before vectorizing.");
        return;
    }

    if (!ensureActiveUsername()) {
        return;
    }

    vectorizeFilesButton.disabled = true;
    const originalLabel = vectorizeFilesButton.textContent;
    vectorizeFilesButton.textContent = "Vectorizing...";

    try {
        const response = await fetch("/api/vectorize-files", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username: state.username })
        });
        const payload = await response.json();

        if (!response.ok) {
            showToast(payload.message || "Unable to vectorize files.");
            return;
        }

        const skipped = payload?.summary?.skipped_files || [];
        if (skipped.length > 0) {
            showToast(`${payload.message} Skipped: ${skipped.join(", ")}`);
            return;
        }

        showToast(payload.message || "Vectorization complete.");
    } catch (error) {
        showToast("Network error while vectorizing files.");
    } finally {
        vectorizeFilesButton.disabled = false;
        vectorizeFilesButton.textContent = originalLabel;
    }
}

function deleteFilesOnWindowClose() {
    if (hasTriggeredExitCleanup) {
        return;
    }

    if (!state.username) {
        return;
    }

    hasTriggeredExitCleanup = true;

    try {
        const payload = new Blob([JSON.stringify({ username: state.username })], {
            type: "application/json"
        });
        const wasQueued = navigator.sendBeacon("/api/delete-all", payload);
        if (!wasQueued) {
            fetch("/api/delete-all", {
                method: "POST",
                keepalive: true,
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ username: state.username })
            });
        }
    } catch (error) {
        fetch("/api/delete-all", {
            method: "POST",
            keepalive: true,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username: state.username })
        });
    }
}

window.addEventListener("pagehide", deleteFilesOnWindowClose);
window.addEventListener("beforeunload", deleteFilesOnWindowClose);

initializeWorkspace();
