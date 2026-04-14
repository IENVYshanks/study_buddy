const CHAT_STORAGE_KEY = "study-agent-chat-state";
const COLLECTION_STORAGE_KEY = "study-agent-active-collection";
const RAG_LOCK_STORAGE_KEY = "study-agent-rag-locked";
const UPLOAD_PANEL_STORAGE_KEY = "study-agent-upload-panel-open";
const SIDEBAR_OPEN_STORAGE_KEY = "study-agent-sidebar-open";
const ALLOWED_FILE_EXTENSIONS = new Set(["pdf", "txt", "md", "doc", "docx", "csv", "json"]);

const state = {
    uploadedFiles: [],
    chatMessages: loadChatState(),
    username: loadActiveUsername(),
    collectionName: loadCollectionName(),
    ragLocked: loadRagLockState(),
    isUploadPanelOpen: loadUploadPanelState(),
    isSidebarOpen: loadSidebarState()
};

const workspaceShell = document.querySelector(".workspace-shell");
const workspaceSidebar = document.getElementById("workspace-sidebar");
const toggleSidebarButton = document.getElementById("toggle-sidebar-btn");
const uploadPanel = document.getElementById("upload-panel");
const toggleUploadButton = document.getElementById("toggle-upload-btn");
const fileInput = document.getElementById("file-upload");
const fileList = document.getElementById("uploaded-file-list");
const fileCount = document.getElementById("file-count");
const uploadMoreButton = document.getElementById("upload-more-btn");
const vectorizeFilesButton = document.getElementById("vectorize-files-btn");
const clearFilesButton = document.getElementById("clear-files-btn");
const goBackButton = document.getElementById("go-back-btn");
const ragStatus = document.getElementById("rag-status");
const chatSection = document.querySelector(".chat-section");
const chatStartScreen = document.getElementById("chat-start-screen");
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
        if (Array.isArray(savedState)) {
            return savedState;
        }
    } catch (error) {
        console.warn("Unable to restore chat state.", error);
    }

    return [];
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

function loadCollectionName() {
    return (localStorage.getItem(COLLECTION_STORAGE_KEY) || "").trim();
}

function loadRagLockState() {
    return localStorage.getItem(RAG_LOCK_STORAGE_KEY) === "true";
}

function loadUploadPanelState() {
    const saved = localStorage.getItem(UPLOAD_PANEL_STORAGE_KEY);
    return saved === null ? true : saved === "true";
}

function loadSidebarState() {
    const saved = localStorage.getItem(SIDEBAR_OPEN_STORAGE_KEY);
    return saved === null ? true : saved === "true";
}

function saveCollectionName(collectionName) {
    const value = (collectionName || "").trim();
    state.collectionName = value;

    if (value) {
        localStorage.setItem(COLLECTION_STORAGE_KEY, value);
        return;
    }

    localStorage.removeItem(COLLECTION_STORAGE_KEY);
}

function saveRagLockState(isLocked) {
    state.ragLocked = Boolean(isLocked);
    localStorage.setItem(RAG_LOCK_STORAGE_KEY, state.ragLocked ? "true" : "false");
}

function saveUploadPanelState(isOpen) {
    state.isUploadPanelOpen = Boolean(isOpen);
    localStorage.setItem(UPLOAD_PANEL_STORAGE_KEY, state.isUploadPanelOpen ? "true" : "false");
}

function saveSidebarState(isOpen) {
    state.isSidebarOpen = Boolean(isOpen);
    localStorage.setItem(SIDEBAR_OPEN_STORAGE_KEY, state.isSidebarOpen ? "true" : "false");
}

function renderUploadPanelState() {
    if (!uploadPanel || !toggleUploadButton) {
        return;
    }

    uploadPanel.classList.toggle("collapsed", !state.isUploadPanelOpen);
    toggleUploadButton.textContent = state.isUploadPanelOpen ? "Close" : "Open";
    toggleUploadButton.setAttribute("aria-expanded", state.isUploadPanelOpen ? "true" : "false");
}

function renderSidebarState() {
    if (!workspaceShell || !toggleSidebarButton) {
        return;
    }

    const shouldShowSidebar = state.isSidebarOpen || window.innerWidth <= 940;
    workspaceShell.classList.toggle("sidebar-collapsed", !shouldShowSidebar);
    toggleSidebarButton.textContent = shouldShowSidebar ? "Hide Sidebar" : "Show Sidebar";
    toggleSidebarButton.setAttribute("aria-expanded", shouldShowSidebar ? "true" : "false");

    if (workspaceSidebar) {
        workspaceSidebar.setAttribute("aria-hidden", shouldShowSidebar ? "false" : "true");
    }
}

function updateWorkspaceLockState() {
    const isLocked = state.ragLocked;
    uploadMoreButton.disabled = isLocked;
    fileInput.disabled = isLocked;
    clearFilesButton.disabled = isLocked;
    vectorizeFilesButton.disabled = isLocked || state.uploadedFiles.length === 0;
    goBackButton.disabled = !isLocked;

    if (ragStatus) {
        ragStatus.textContent = isLocked
            ? "RAG is active. File changes are locked until you click Go Back, which removes the user's files and vector collection."
            : "Files can still be edited. Vectorize to lock the current set for chat.";
    }
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
    removeButton.disabled = state.ragLocked;
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
        updateWorkspaceLockState();
        return;
    }

    state.uploadedFiles.forEach((filename) => {
        fileList.appendChild(buildFileItem(filename));
    });
    updateWorkspaceLockState();
}

function buildMessageNode(message) {
    const messageElement = document.createElement("article");
    messageElement.className = `message ${message.role}`;

    const label = document.createElement("p");
    label.className = "message-label";
    label.textContent = message.role === "assistant" ? "Study Agent" : "You";

    const body = document.createElement("div");
    body.className = "message-body";
    if (message.role === "assistant") {
        body.innerHTML = renderMarkdown(message.text || "");
    } else {
        body.textContent = message.text;
    }

    messageElement.append(label, body);
    return messageElement;
}

function escapeHtml(text) {
    return text
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function renderInlineMarkdown(text) {
    let escaped = escapeHtml(text);
    escaped = escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    escaped = escaped.replace(/\*(.+?)\*/g, "<em>$1</em>");
    escaped = escaped.replace(/`([^`]+)`/g, "<code>$1</code>");
    return escaped;
}

function renderMarkdown(text) {
    const normalized = (text || "").replace(/\r\n/g, "\n").trim();
    if (!normalized) {
        return "";
    }

    const lines = normalized.split("\n");
    const blocks = [];
    let currentList = null;

    function flushList() {
        if (currentList) {
            blocks.push(`<ul>${currentList.join("")}</ul>`);
            currentList = null;
        }
    }

    for (const rawLine of lines) {
        const line = rawLine.trim();

        if (!line) {
            flushList();
            continue;
        }

        if (line.startsWith("* ") || line.startsWith("- ")) {
            if (!currentList) {
                currentList = [];
            }
            currentList.push(`<li>${renderInlineMarkdown(line.slice(2).trim())}</li>`);
            continue;
        }

        const numberedMatch = line.match(/^\d+\.\s+(.+)$/);
        if (numberedMatch) {
            if (!currentList) {
                currentList = [];
            }
            currentList.push(`<li>${renderInlineMarkdown(numberedMatch[1].trim())}</li>`);
            continue;
        }

        flushList();

        if (line.startsWith("### ")) {
            blocks.push(`<h3>${renderInlineMarkdown(line.slice(4).trim())}</h3>`);
        } else if (line.startsWith("## ")) {
            blocks.push(`<h2>${renderInlineMarkdown(line.slice(3).trim())}</h2>`);
        } else if (line.startsWith("# ")) {
            blocks.push(`<h1>${renderInlineMarkdown(line.slice(2).trim())}</h1>`);
        } else {
            blocks.push(`<p>${renderInlineMarkdown(line)}</p>`);
        }
    }

    flushList();
    return blocks.join("");
}

function renderMessages() {
    const hasConversation = state.chatMessages.length > 0;
    chatSection.classList.toggle("chat-start-mode", !hasConversation);
    if (chatStartScreen) {
        chatStartScreen.setAttribute("aria-hidden", hasConversation ? "true" : "false");
    }

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

    if (state.ragLocked) {
        showToast("Files are locked after vectorization. Click Go Back to reset this workspace.");
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

    if (state.ragLocked) {
        showToast("Files are locked after vectorization. Click Go Back to reset this workspace.");
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

    if (state.ragLocked) {
        showToast("Files are locked after vectorization. Click Go Back to reset this workspace.");
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

toggleUploadButton.addEventListener("click", () => {
    saveUploadPanelState(!state.isUploadPanelOpen);
    renderUploadPanelState();
});

toggleSidebarButton.addEventListener("click", () => {
    saveSidebarState(!state.isSidebarOpen);
    renderSidebarState();
});

clearFilesButton.addEventListener("click", async () => {
    await removeAllFiles();
});

goBackButton.addEventListener("click", async () => {
    await goBackAndResetWorkspace();
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
            body: JSON.stringify({
                user_input: userText,
                username: state.username,
                collection_name: state.collectionName
            })
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

function getInitialChatMessages() {
    return [];
}

async function resetChatHistory(options = {}) {
    const { silent = false } = options;

    try {
        const response = await fetch("/api/delete-history", {
            method: "POST"
        });
        const payload = await response.json();
        if (!silent) {
            showToast(payload.message || "Chat history reset.");
        }

        if (response.ok) {
            state.chatMessages = getInitialChatMessages();
            saveChatState();
            renderMessages();
        }
    } catch (error) {
        if (!silent) {
            showToast("Network error while resetting chat history.");
        }
    }
}

async function initializeWorkspace() {
    if (!ensureActiveUsername()) {
        return;
    }

    renderSidebarState();
    renderUploadPanelState();
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

    if (state.ragLocked) {
        showToast("RAG is already active for this workspace. Click Go Back to reset it.");
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
        const collectionName = payload?.summary?.collection_name || "";
        saveCollectionName(collectionName);
        saveRagLockState(Boolean(collectionName));
        await resetChatHistory({ silent: true });
        renderFiles();
        if (skipped.length > 0) {
            showToast(`${payload.message} Skipped: ${skipped.join(", ")}`);
            return;
        }

        showToast(payload.message || "Vectorization complete.");
    } catch (error) {
        showToast("Network error while vectorizing files.");
    } finally {
        vectorizeFilesButton.textContent = originalLabel;
        updateWorkspaceLockState();
    }
}

async function goBackAndResetWorkspace() {
    if (!ensureActiveUsername()) {
        return;
    }

    if (!state.ragLocked) {
        window.location.href = "/";
        return;
    }

    goBackButton.disabled = true;
    const originalLabel = goBackButton.textContent;
    goBackButton.textContent = "Resetting...";

    try {
        const response = await fetch("/api/go-back", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: state.username,
                collection_name: state.collectionName
            })
        });
        const payload = await response.json();

        if (!response.ok) {
            showToast(payload.message || "Unable to reset workspace.");
            return;
        }

        state.uploadedFiles = [];
        saveCollectionName("");
        saveRagLockState(false);
        renderFiles();
        showToast(payload.message || "Workspace reset.");
        window.location.href = "/";
    } catch (error) {
        showToast("Network error while resetting workspace.");
    } finally {
        goBackButton.textContent = originalLabel;
        updateWorkspaceLockState();
    }
}

function deleteFilesOnWindowClose() {
    if (hasTriggeredExitCleanup) {
        return;
    }

    if (!state.username) {
        return;
    }

    if (state.ragLocked) {
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
window.addEventListener("resize", renderSidebarState);

initializeWorkspace();
