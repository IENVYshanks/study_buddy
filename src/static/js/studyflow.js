const USER_STORAGE_KEY = "studyAgentUser";
const FILES_STORAGE_KEY = "studyAgentFiles";
const CHAT_STORAGE_KEY = "studyAgentChat";
const DEFAULT_ASSISTANT_MESSAGE = "Upload your study files on the previous page, then ask your question here."
const ALLOWED_FILE_EXTENSIONS = new Set(["pdf", "txt", "md", "doc", "docx", "csv", "json"]);

function loadUserData() {
    try {
        const value = localStorage.getItem(USER_STORAGE_KEY);
        return value ? JSON.parse(value) : null;
    } catch (err) {
        return null;
    }
}

function saveUserData(name, email) {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ name, email }));
}

function loadUploadedFiles() {
    try {
        const value = localStorage.getItem(FILES_STORAGE_KEY);
        return value ? JSON.parse(value) : [];
    } catch (err) {
        return [];
    }
}

function saveUploadedFiles(files) {
    localStorage.setItem(FILES_STORAGE_KEY, JSON.stringify(files));
}

function loadChatState() {
    try {
        const value = localStorage.getItem(CHAT_STORAGE_KEY);
        return value ? JSON.parse(value) : [];
    } catch (err) {
        return [];
    }
}

function saveChatState(messages) {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
}

function clearChatState() {
    localStorage.removeItem(CHAT_STORAGE_KEY);
}

function showToast(message) {
    const toast = document.getElementById("toast");
    if (!toast || !message) {
        return;
    }

    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => {
        toast.classList.remove("show");
    }, 2500);
}

function buildFileItem(filename, removeCallback) {
    const listItem = document.createElement("li");
    listItem.className = "file-item";

    const meta = document.createElement("div");
    meta.className = "file-meta";

    const name = document.createElement("strong");
    name.textContent = filename;

    const status = document.createElement("span");
    status.textContent = "Ready";

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "remove-file-btn";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => removeCallback(filename));

    meta.append(name, status);
    listItem.append(meta, removeButton);
    return listItem;
}

function isAllowedFile(file) {
    const extension = file.name.split('.').pop().toLowerCase();
    return ALLOWED_FILE_EXTENSIONS.has(extension);
}

function renderUploadFiles() {
    const fileList = document.getElementById("upload-file-list");
    const fileCount = document.getElementById("upload-file-count");
    const storedFiles = loadUploadedFiles();

    fileCount.textContent = `${storedFiles.length} file${storedFiles.length === 1 ? "" : "s"}`;
    fileList.innerHTML = "";

    if (storedFiles.length === 0) {
        const empty = document.createElement("li");
        empty.className = "empty-state";
        empty.textContent = "No files uploaded yet.";
        fileList.appendChild(empty);
        return;
    }

    storedFiles.forEach((filename) => {
        fileList.appendChild(buildFileItem(filename, removeUploadFile));
    });
}

function addUploadFiles(fileList) {
    const stored = loadUploadedFiles();
    const nextFiles = [...stored];
    let added = false;

    fileList.forEach((file) => {
        if (!isAllowedFile(file)) {
            showToast(`Unsupported file: ${file.name}`);
            return;
        }
        if (!nextFiles.includes(file.name)) {
            nextFiles.push(file.name);
            added = true;
        }
    });

    if (added) {
        saveUploadedFiles(nextFiles);
        renderUploadFiles();
        showToast("File list updated.");
    } else if (fileList.length > 0) {
        showToast("No new files were added.");
    }
}

function removeUploadFile(filename) {
    const stored = loadUploadedFiles();
    const updated = stored.filter((name) => name !== filename);
    saveUploadedFiles(updated);
    renderUploadFiles();
    showToast(`${filename} removed.`);
}

function clearUploadFiles() {
    saveUploadedFiles([]);
    renderUploadFiles();
    showToast("All files removed.");
}

function renderChatFiles() {
    const fileList = document.getElementById("chat-file-list");
    const fileCount = document.getElementById("chat-file-count");
    const storedFiles = loadUploadedFiles();

    fileCount.textContent = `${storedFiles.length} file${storedFiles.length === 1 ? "" : "s"}`;
    fileList.innerHTML = "";

    if (storedFiles.length === 0) {
        const empty = document.createElement("li");
        empty.className = "empty-state";
        empty.textContent = "No files available. Return to upload to add files.";
        fileList.appendChild(empty);
        return;
    }

    storedFiles.forEach((filename) => {
        const item = document.createElement("li");
        item.className = "file-item";
        item.textContent = filename;
        fileList.appendChild(item);
    });
}

function createMessageNode(message) {
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

function renderChatMessages() {
    const container = document.getElementById("chat-messages");
    const messages = loadChatState();
    container.innerHTML = "";

    if (messages.length === 0) {
        const placeholder = [{ role: "assistant", text: DEFAULT_ASSISTANT_MESSAGE }];
        saveChatState(placeholder);
        placeholder.forEach((msg) => container.appendChild(createMessageNode(msg)));
        return;
    }

    messages.forEach((msg) => {
        container.appendChild(createMessageNode(msg));
    });
    container.scrollTop = container.scrollHeight;
}

function addChatMessage(role, text) {
    const messages = [...loadChatState(), { role, text }];
    saveChatState(messages);
    renderChatMessages();
}

function createAssistantReply(userText) {
    const files = loadUploadedFiles();
    if (files.length === 0) {
        return "I don't have any uploaded files yet. Please go back and add documents, then ask again.";
    }

    return `I reviewed your ${files.length} uploaded file${files.length === 1 ? "" : "s"} (${files.join(", ")}) and found the key context for your question. Here is a sample answer for: ${userText}`;
}

function initializeUploadPage() {
    const user = loadUserData();
    if (!user) {
        window.location.href = "/";
        return;
    }

    const userName = user.name || "Student";
    const welcome = document.getElementById("welcome-heading");
    welcome.textContent = `Hello ${userName}, manage your uploads.`;

    const fileInput = document.getElementById("file-upload");
    const uploadMoreButton = document.getElementById("upload-more-btn");
    const clearFilesButton = document.getElementById("clear-files-btn");
    const toChatButton = document.getElementById("to-chat-btn");

    fileInput.addEventListener("change", (event) => {
        const files = Array.from(event.target.files || []);
        addUploadFiles(files);
        event.target.value = "";
    });

    uploadMoreButton.addEventListener("click", () => fileInput.click());
    clearFilesButton.addEventListener("click", clearUploadFiles);
    toChatButton.addEventListener("click", () => {
        window.location.href = "/chat";
    });

    renderUploadFiles();
}

function initializeChatPage() {
    const user = loadUserData();
    if (!user) {
        window.location.href = "/";
        return;
    }

    const userName = user.name || "Student";
    const welcome = document.getElementById("chat-welcome");
    welcome.textContent = `Chat with Study Agent, ${userName}`;

    const backButton = document.getElementById("back-upload-btn");
    const resetButton = document.getElementById("reset-chat-btn");
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");

    backButton.addEventListener("click", () => {
        window.location.href = "/upload";
    });

    resetButton.addEventListener("click", () => {
        clearChatState();
        renderChatMessages();
        showToast("Conversation reset.");
    });

    chatForm?.addEventListener("submit", (event) => {
        event.preventDefault();
        const text = chatInput.value.trim();
        if (!text) {
            return;
        }
        addChatMessage("user", text);
        const reply = createAssistantReply(text);
        addChatMessage("assistant", reply);
        chatInput.value = "";
    });

    renderChatFiles();
    renderChatMessages();
}

function initializePage() {
    const uploadShell = document.getElementById("upload-file-list");
    const chatShell = document.getElementById("chat-messages");

    if (uploadShell) {
        initializeUploadPage();
        return;
    }

    if (chatShell) {
        initializeChatPage();
        return;
    }
}

window.addEventListener("DOMContentLoaded", initializePage);
