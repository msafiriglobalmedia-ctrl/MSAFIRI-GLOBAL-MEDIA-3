/* ============================================================
   MSAFIRI GLOBAL MEDIA — Chat Logic
   Version: Media V0.0.1
   Purpose: Chat list, conversation view, messaging
   ============================================================ */

// ------------------------------------------------------------
// 1. GLOBAL STATE
// ------------------------------------------------------------
let CHAT_POLLING_INTERVAL = null; // For real-time message updates
let CURRENT_CONVERSATION_ID = null;

// ------------------------------------------------------------
// 2. LOAD CHAT LIST (Chats Page)
// ------------------------------------------------------------
async function loadChats() {
    const container = document.getElementById("chat-list");
    if (!container) return;

    container.innerHTML = '<p class="loading-text">Loading chats...</p>';

    const result = await apiFetch("/messages/conversations");
    if (!result || !result.ok) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comment-dots"></i>
                <h3>No conversations</h3>
                <p>Start connecting with people.</p>
            </div>
        `;
        return;
    }

    const chats = result.data.conversations || result.data || [];
    CACHED_CHATS = chats;

    if (chats.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comment-dots"></i>
                <h3>No conversations</h3>
                <p>Start connecting with people.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = chats.map(chat => renderChatItem(chat)).join("");
}

/**
 * Render a single chat item in the list
 */
function renderChatItem(chat) {
    const user = chat.user || chat.participant || {};
    const username = user.username || "User";
    const initial = username.charAt(0).toUpperCase();
    const avatar = user.profile_pic || "";
    const lastMsg = chat.last_message || "No messages yet";
    const time = timeAgo(chat.updated_at || chat.created_at);
    const unread = chat.unread_count || 0;

    return `
        <div class="chat-item" onclick="openChatConversation(${chat.id})">
            <div class="chat-avatar">
                ${avatar
                    ? `<img src="${escapeHtml(avatar)}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`
                    : initial
                }
            </div>
            <div class="chat-info">
                <strong>${escapeHtml(username)}</strong>
                <small>${escapeHtml(lastMsg)}</small>
            </div>
            <div class="chat-meta">
                <span class="chat-time">${time}</span>
                ${unread > 0 ? `<span class="unread-badge">${unread}</span>` : ""}
            </div>
        </div>
    `;
}

// ------------------------------------------------------------
// 3. SEARCH CHATS
// ------------------------------------------------------------
function searchChats(query) {
    const container = document.getElementById("chat-list");
    if (!container) return;

    if (!query || query.length === 0) {
        loadChats();
        return;
    }

    const filtered = CACHED_CHATS.filter(c => {
        const user = c.user || c.participant || {};
        const username = (user.username || "").toLowerCase();
        return username.includes(query.toLowerCase());
    });

    if (filtered.length === 0) {
        container.innerHTML = `<p class="loading-text">No results for "${escapeHtml(query)}"</p>`;
        return;
    }

    container.innerHTML = filtered.map(chat => renderChatItem(chat)).join("");
}

// ------------------------------------------------------------
// 4. OPEN CHAT CONVERSATION
// ------------------------------------------------------------
async function openChatConversation(chatId) {
    CURRENT_CONVERSATION_ID = chatId;

    // Hide all pages, show conversation view
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.getElementById("page-chats").classList.add("active");

    const container = document.getElementById("page-chats");
    container.innerHTML = `
        <div class="conversation-view">
            <div class="conversation-header">
                <i class="fas fa-arrow-left back-btn" onclick="closeConversation()"></i>
                <div class="conversation-user">
                    <div class="chat-avatar" id="conv-avatar">?</div>
                    <div>
                        <strong id="conv-username">Loading...</strong>
                        <small id="conv-status">online</small>
                    </div>
                </div>
                <div class="conversation-actions">
                    <i class="fas fa-phone" onclick="startVoiceCall()"></i>
                    <i class="fas fa-video" onclick="startVideoCall()"></i>
                    <i class="fas fa-ellipsis-v"></i>
                </div>
            </div>

            <div class="conversation-messages" id="conversation-messages">
                <p class="loading-text">Loading messages...</p>
            </div>

            <div class="conversation-input">
                <i class="fas fa-plus-circle" onclick="toggleChatAttachments()"></i>
                <input type="text" id="message-input" placeholder="Type a message..."
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <i class="fas fa-microphone" id="mic-btn"
                   onmousedown="startVoiceRecord()" onmouseup="stopVoiceRecord()"
                   ontouchstart="startVoiceRecord()" ontouchend="stopVoiceRecord()"></i>
                <button class="send-btn" onclick="sendMessage()">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>

            <div class="chat-attachments" id="chat-attachments" style="display:none;">
                <div class="attachment-option" onclick="attachPhoto()">
                    <i class="fas fa-image"></i> Photo
                </div>
                <div class="attachment-option" onclick="attachVideo()">
                    <i class="fas fa-video"></i> Video
                </div>
                <div class="attachment-option" onclick="attachDocument()">
                    <i class="fas fa-file"></i> Document
                </div>
                <div class="attachment-option" onclick="attachLocation()">
                    <i class="fas fa-map-marker-alt"></i> Location
                </div>
            </div>
        </div>
    `;

    // Load messages
    await loadMessages(chatId);

    // Update conversation header
    const chat = CACHED_CHATS.find(c => c.id === chatId);
    if (chat) {
        const user = chat.user || chat.participant || {};
        const username = user.username || "User";
        const initial = username.charAt(0).toUpperCase();
        const avatar = user.profile_pic || "";

        const avatarEl = document.getElementById("conv-avatar");
        if (avatar) {
            avatarEl.innerHTML = `<img src="${escapeHtml(avatar)}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
        } else {
            avatarEl.textContent = initial;
        }
        document.getElementById("conv-username").textContent = username;
    }

    // Start polling for new messages (every 3 seconds)
    startMessagePolling(chatId);
}

/**
 * Close conversation and return to chat list
 */
function closeConversation() {
    stopMessagePolling();
    CURRENT_CONVERSATION_ID = null;
    loadPage("chats");
}

// ------------------------------------------------------------
// 5. LOAD MESSAGES
// ------------------------------------------------------------
async function loadMessages(chatId) {
    const container = document.getElementById("conversation-messages");
    if (!container) return;

    const result = await apiFetch(`/messages/${chatId}`);
    if (!result || !result.ok) {
        container.innerHTML = '<p class="loading-text">Failed to load messages</p>';
        return;
    }

    const messages = result.data.messages || result.data || [];
    renderMessages(messages);
}

/**
 * Render all messages in a conversation
 */
function renderMessages(messages) {
    const container = document.getElementById("conversation-messages");
    if (!container) return;

    if (messages.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comment"></i>
                <p>No messages yet. Say hello!</p>
            </div>
        `;
        return;
    }

    const currentUser = USER() || {};
    container.innerHTML = messages.map(msg => renderMessage(msg, currentUser)).join("");
    container.scrollTop = container.scrollHeight;
}

/**
 * Render a single message bubble
 */
function renderMessage(msg, currentUser) {
    const isMine = msg.sender_id === currentUser.id || msg.is_mine;
    const bubbleClass = isMine ? "my-message" : "their-message";
    const time = timeAgo(msg.created_at);

    if (msg.media_url) {
        return `
            <div class="message-bubble ${bubbleClass}">
                <img src="${escapeHtml(msg.media_url)}" class="message-media" alt="media">
                <span class="message-time">${time}</span>
            </div>
        `;
    }

    return `
        <div class="message-bubble ${bubbleClass}">
            <p>${escapeHtml(msg.content || msg.text || "")}</p>
            <span class="message-time">${time}</span>
        </div>
    `;
}

// ------------------------------------------------------------
// 6. SEND MESSAGE
// ------------------------------------------------------------
async function sendMessage() {
    const input = document.getElementById("message-input");
    const content = input.value.trim();
    if (!content || !CURRENT_CONVERSATION_ID) return;

    // Optimistic UI — show message immediately
    const container = document.getElementById("conversation-messages");
    const currentUser = USER() || {};
    container.innerHTML += renderMessage(
        { content, sender_id: currentUser.id, created_at: new Date().toISOString() },
        currentUser
    );
    container.scrollTop = container.scrollHeight;
    input.value = "";

    // Send to backend
    const result = await apiFetch(`/messages/${CURRENT_CONVERSATION_ID}`, {
        method: "POST",
        body: JSON.stringify({ content })
    });

    if (!result || !result.ok) {
        showToast("Failed to send message");
    }
}

// ------------------------------------------------------------
// 7. MESSAGE POLLING (Real-time updates)
// ------------------------------------------------------------
function startMessagePolling(chatId) {
    stopMessagePolling();
    CHAT_POLLING_INTERVAL = setInterval(async () => {
        const result = await apiFetch(`/messages/${chatId}`);
        if (result && result.ok) {
            const messages = result.data.messages || result.data || [];
            renderMessages(messages);
        }
    }, 3000); // Every 3 seconds
}

function stopMessagePolling() {
    if (CHAT_POLLING_INTERVAL) {
        clearInterval(CHAT_POLLING_INTERVAL);
        CHAT_POLLING_INTERVAL = null;
    }
}

// ------------------------------------------------------------
// 8. CHAT ATTACHMENTS
// ------------------------------------------------------------
function toggleChatAttachments() {
    const el = document.getElementById("chat-attachments");
    if (el) el.style.display = el.style.display === "none" ? "grid" : "none";
}

function attachPhoto() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => uploadAttachment(e.target.files[0], "image");
    input.click();
}

function attachVideo() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "video/*";
    input.onchange = async (e) => uploadAttachment(e.target.files[0], "video");
    input.click();
}

function attachDocument() {
    const input = document.createElement("input");
    input.type = "file";
    input.onchange = async (e) => uploadAttachment(e.target.files[0], "document");
    input.click();
}

function attachLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((pos) => {
            const { latitude, longitude } = pos.coords;
            sendLocationMessage(latitude, longitude);
        });
    } else {
        showToast("Location not supported");
    }
}

async function uploadAttachment(file, type) {
    if (!file || !CURRENT_CONVERSATION_ID) return;

    const formData = new FormData();
    formData.append("media", file);
    formData.append("type", type);

    showToast(`Uploading ${type}...`);

    const result = await apiFetch(`/messages/${CURRENT_CONVERSATION_ID}/media`, {
        method: "POST",
        body: formData
    });

    if (result && result.ok) {
        showToast(`${type} sent!`);
        loadMessages(CURRENT_CONVERSATION_ID);
    } else {
        showToast(`Failed to send ${type}`);
    }
}

async function sendLocationMessage(lat, lng) {
    const result = await apiFetch(`/messages/${CURRENT_CONVERSATION_ID}`, {
        method: "POST",
        body: JSON.stringify({ content: `📍 My location: ${lat}, ${lng}` })
    });
    if (result && result.ok) loadMessages(CURRENT_CONVERSATION_ID);
}

// ------------------------------------------------------------
// 9. VOICE RECORDING
// ------------------------------------------------------------
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;

async function startVoiceRecord() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        recordingStartTime = Date.now();

        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            const duration = (Date.now() - recordingStartTime) / 1000;
            if (duration < 1) {
                showToast("Recording too short");
                return;
            }
            await uploadVoiceNote(audioBlob);
            stream.getTracks().forEach(t => t.stop());
        };

        mediaRecorder.start();
        document.getElementById("mic-btn")?.classList.add("recording");
        showToast("Recording... release to send");
    } catch (err) {
        showToast("Microphone access denied");
        console.error(err);
    }
}

function stopVoiceRecord() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        document.getElementById("mic-btn")?.classList.remove("recording");
    }
}

async function uploadVoiceNote(blob) {
    if (!CURRENT_CONVERSATION_ID) return;
    const formData = new FormData();
    formData.append("media", blob, "voice-note.webm");
    formData.append("type", "voice");

    showToast("Sending voice note...");

    const result = await apiFetch(`/messages/${CURRENT_CONVERSATION_ID}/media`, {
        method: "POST",
        body: formData
    });

    if (result && result.ok) {
        showToast("Voice note sent!");
        loadMessages(CURRENT_CONVERSATION_ID);
    } else {
        showToast("Failed to send voice note");
    }
}

// ------------------------------------------------------------
// 10. VOICE / VIDEO CALLS
// ------------------------------------------------------------
function startVoiceCall() {
    showToast("Voice call coming soon!");
}

function startVideoCall() {
    showToast("Video call coming soon!");
}

// ------------------------------------------------------------
// 11. NEW CHAT
// ------------------------------------------------------------
function openNewChat() {
    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.id = "new-chat-modal";
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-btn" onclick="document.getElementById('new-chat-modal').remove()">&times;</span>
            <h2 style="margin-bottom:20px;">New Chat</h2>
            <div class="search-bar-container">
                <i class="fas fa-search"></i>
                <input type="text" id="new-chat-search" placeholder="Search users..." 
                       onkeyup="searchNewChatUsers(this.value)">
            </div>
            <div id="new-chat-results"></div>
        </div>
    `;
    document.body.appendChild(modal);
}

async function searchNewChatUsers(query) {
    if (!query || query.length < 2) return;
    const results = document.getElementById("new-chat-results");
    results.innerHTML = '<p class="loading-text">Searching...</p>';

    const result = await apiFetch(`/profile/search?q=${encodeURIComponent(query)}`);
    if (!result || !result.ok) {
        results.innerHTML = '<p class="loading-text">Search failed</p>';
        return;
    }

    const users = result.data.users || result.data || [];
    if (users.length === 0) {
        results.innerHTML = '<p class="loading-text">No users found</p>';
        return;
    }

    results.innerHTML = users.map(user => {
        const username = user.username || "User";
        const initial = username.charAt(0).toUpperCase();
        return `
            <div class="chat-item" onclick="startNewChat(${user.id})">
                <div class="chat-avatar">${initial}</div>
                <div class="chat-info">
                    <strong>${escapeHtml(user.name || username)}</strong>
                    <small>@${escapeHtml(username)}</small>
                </div>
            </div>
        `;
    }).join("");
}

async function startNewChat(userId) {
    const result = await apiFetch("/messages/conversations", {
        method: "POST",
        body: JSON.stringify({ participant_id: userId })
    });

    if (result && result.ok) {
        document.getElementById("new-chat-modal")?.remove();
        const chatId = result.data.conversation_id || result.data.id;
        if (chatId) openChatConversation(chatId);
    } else {
        showToast("Failed to start chat");
    }
}

// ------------------------------------------------------------
// 12. INITIALIZATION
// ------------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
    // Stop polling when leaving page
    window.addEventListener("beforeunload", stopMessagePolling);
});

// Expose functions globally
window.loadChats = loadChats;
window.searchChats = searchChats;
window.openChatConversation = openChatConversation;
window.closeConversation = closeConversation;
window.sendMessage = sendMessage;
window.toggleChatAttachments = toggleChatAttachments;
window.attachPhoto = attachPhoto;
window.attachVideo = attachVideo;
window.attachDocument = attachDocument;
window.attachLocation = attachLocation;
window.startVoiceRecord = startVoiceRecord;
window.stopVoiceRecord = stopVoiceRecord;
window.startVoiceCall = startVoiceCall;
window.startVideoCall = startVideoCall;
window.openNewChat = openNewChat;
window.searchNewChatUsers = searchNewChatUsers;
window.startNewChat = startNewChat;
