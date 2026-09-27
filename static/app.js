/* ============================================================
   MSAFIRI GLOBAL MEDIA — Core Application Logic
   Version: Media V0.0.1
   Purpose: Navigation, API calls, Feed, Profile, Search
   ============================================================ */

// ------------------------------------------------------------
// 1. GLOBAL CONFIGURATION
// ------------------------------------------------------------
const API_URL = window.location.origin + "/api"; // Auto-detect backend URL
const TOKEN = () => localStorage.getItem("STORAGE_TOKEN") || "";
const USER = () => {
    try {
        return JSON.parse(localStorage.getItem("STORAGE_USER")) || null;
    } catch {
        return null;
    }
};

// Global state
let CACHED_CHATS = [];
let CURRENT_CHAT = null;
let CACHED_FEED = [];

// ------------------------------------------------------------
// 2. HELPER FUNCTIONS
// ------------------------------------------------------------

/**
 * Authenticated fetch — automatically adds Bearer token
 */
async function apiFetch(endpoint, options = {}) {
    const headers = {
        "Authorization": `Bearer ${TOKEN()}`,
        ...(options.headers || {})
    };

    // Only add Content-Type for non-FormData requests
    if (!(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            // Token expired — redirect to login
            localStorage.removeItem("STORAGE_TOKEN");
            localStorage.removeItem("STORAGE_USER");
            window.location.href = "/login";
            return null;
        }

        const data = await response.json();
        return { ok: response.ok, status: response.status, data };
    } catch (error) {
        console.error("API Error:", endpoint, error);
        return { ok: false, status: 0, data: { error: "Network error" } };
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 100px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--bg-card);
        color: var(--text-light);
        padding: 12px 24px;
        border-radius: 25px;
        border: 1px solid var(--border-color);
        z-index: 10000;
        font-size: 14px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.5);
        animation: fadeIn 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

/**
 * Format timestamp to "2h ago" style
 */
function timeAgo(dateString) {
    if (!dateString) return "";
    const date = new Date(dateString);
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return "Just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ------------------------------------------------------------
// 3. PAGE NAVIGATION
// ------------------------------------------------------------

/**
 * Main navigation function — switches between pages
 */
function loadPage(page) {
    // Hide all pages
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));

    // Show target page
    const target = document.getElementById(`page-${page}`);
    if (target) target.classList.add("active");

    // Update sidebar active state
    document.querySelectorAll(".nav-link").forEach(link => {
        link.classList.toggle("active", link.dataset.page === page);
    });

    // Update bottom nav active state
    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.toggle("active", item.dataset.page === page);
    });

    // Close sidebar on mobile
    document.getElementById("sidebar")?.classList.remove("open");

    // Load page-specific content
    switch (page) {
        case "feed":
            loadFeed();
            loadStories();
            break;
        case "discovery":
            if (typeof loadDiscovery === "function") loadDiscovery();
            break;
        case "chats":
            loadChats();
            break;
        case "profile":
            loadProfile();
            break;
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });
}

/**
 * Toggle sidebar (mobile)
 */
function toggleSidebar() {
    document.getElementById("sidebar")?.classList.toggle("open");
}

/**
 * Focus search input
 */
function focusSearch() {
    const input = document.getElementById("home-search");
    if (input) {
        input.focus();
        loadPage("feed");
    }
}

// ------------------------------------------------------------
// 4. FEED LOGIC
// ------------------------------------------------------------

/**
 * Load feed posts from backend
 */
async function loadFeed() {
    const container = document.getElementById("feed-posts");
    if (!container) return;

    container.innerHTML = '<p class="loading-text">Loading feed...</p>';

    const result = await apiFetch("/feed");
    if (!result || !result.ok) {
        container.innerHTML = '<p class="loading-text">Failed to load feed. Try again.</p>';
        return;
    }

    const posts = result.data.posts || result.data || [];
    CACHED_FEED = posts;

    if (posts.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-newspaper"></i>
                <h3>No posts yet</h3>
                <p>Be the first to share something!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = posts.map(post => renderPost(post)).join("");
}

/**
 * Render a single post as HTML
 */
function renderPost(post) {
    const user = post.user || {};
    const username = user.username || post.username || "Unknown";
    const avatar = user.profile_pic || post.user_profile_pic || "";
    const initial = username.charAt(0).toUpperCase();

    return `
        <div class="post" data-post-id="${post.id}">
            <div class="post-header">
                ${avatar
                    ? `<img src="${escapeHtml(avatar)}" alt="${escapeHtml(username)}">`
                    : `<div class="post-avatar">${initial}</div>`
                }
                <div class="post-info">
                    <strong>${escapeHtml(username)}</strong>
                    <small>${timeAgo(post.created_at)}</small>
                </div>
            </div>
            <div class="post-content">${escapeHtml(post.content || post.caption || "")}</div>
            ${post.media_url ? `<img src="${escapeHtml(post.media_url)}" class="post-media" alt="post media">` : ""}
            <div class="post-actions">
                <button onclick="likePost(${post.id}, this)">
                    <i class="fas fa-heart"></i> <span>${post.likes_count || 0}</span>
                </button>
                <button onclick="commentPost(${post.id})">
                    <i class="fas fa-comment"></i> <span>${post.comments_count || 0}</span>
                </button>
                <button onclick="sharePost(${post.id})">
                    <i class="fas fa-share"></i> <span>Share</span>
                </button>
            </div>
        </div>
    `;
}

/**
 * Switch feed tab (For You / Following)
 */
function switchFeedTab(tab, btn) {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    // TODO: Filter feed based on tab
    loadFeed();
}

/**
 * Like a post
 */
async function likePost(postId, btn) {
    const result = await apiFetch(`/posts/${postId}/like`, { method: "POST" });
    if (result && result.ok) {
        btn.classList.toggle("liked");
    }
}

/**
 * Comment on a post
 */
function commentPost(postId) {
    showToast("Comments coming soon!");
}

/**
 * Share a post
 */
function sharePost(postId) {
    const url = `${window.location.origin}/post/${postId}`;
    if (navigator.share) {
        navigator.share({ title: "MSAFIRI Post", url });
    } else {
        navigator.clipboard.writeText(url);
        showToast("Link copied!");
    }
}

// ------------------------------------------------------------
// 5. STORIES LOGIC
// ------------------------------------------------------------

/**
 * Load stories (24hr expiry)
 */
async function loadStories() {
    const container = document.getElementById("stories-list");
    if (!container) return;

    const result = await apiFetch("/stories");
    if (!result || !result.ok) {
        container.innerHTML = "";
        return;
    }

    const stories = result.data.stories || result.data || [];

    if (stories.length === 0) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = stories.map(story => {
        const user = story.user || {};
        const username = user.username || "User";
        const initial = username.charAt(0).toUpperCase();
        const avatar = user.profile_pic || "";

        return `
            <div class="story-item" onclick="viewStory(${story.id})">
                <div class="story-avatar" style="background-image: url('${escapeHtml(avatar)}'); background-size: cover; background-position: center;">
                    ${avatar ? "" : initial}
                </div>
                <span>${escapeHtml(username)}</span>
            </div>
        `;
    }).join("");
}

/**
 * Upload a new story
 */
function uploadStory() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*,video/*";
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("media", file);

        showToast("Uploading story...");

        const result = await apiFetch("/stories/upload", {
            method: "POST",
            body: formData
        });

        if (result && result.ok) {
            showToast("Story posted!");
            loadStories();
        } else {
            showToast("Failed to upload story");
        }
    };
    input.click();
}

/**
 * View a story
 */
function viewStory(storyId) {
    showToast("Story viewer coming soon!");
}

// ------------------------------------------------------------
// 6. PROFILE LOGIC
// ------------------------------------------------------------

/**
 * Load user profile
 */
async function loadProfile() {
    const container = document.getElementById("page-profile");
    if (!container) return;

    container.innerHTML = '<p class="loading-text">Loading profile...</p>';

    const result = await apiFetch("/profile/me");
    if (!result || !result.ok) {
        container.innerHTML = '<p class="loading-text">Failed to load profile</p>';
        return;
    }

    const profile = result.data.user || result.data;
    renderProfile(profile);
}

/**
 * Render profile page
 */
function renderProfile(profile) {
    const container = document.getElementById("page-profile");
    const username = profile.username || "User";
    const initial = username.charAt(0).toUpperCase();
    const avatar = profile.profile_pic || "";

    container.innerHTML = `
        <div class="profile-header" style="text-align:center; padding: 20px 0;">
            <div class="profile-avatar-large" style="
                width: 100px; height: 100px;
                border-radius: 50%;
                background: ${avatar ? `url('${escapeHtml(avatar)}') center/cover` : "var(--gradient)"};
                display: flex; align-items: center; justify-content: center;
                font-size: 40px; font-weight: bold; color: #fff;
                margin: 0 auto 15px;
                border: 3px solid var(--primary);
            ">
                ${avatar ? "" : initial}
            </div>
            <h2>${escapeHtml(profile.name || username)}</h2>
            <p style="color: var(--text-gray);">@${escapeHtml(username)}</p>
            ${profile.bio ? `<p style="margin-top:10px;">${escapeHtml(profile.bio)}</p>` : ""}
            ${profile.location ? `<p style="color: var(--text-muted); font-size: 13px;"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(profile.location)}</p>` : ""}

            <div class="profile-stats" style="display:flex; justify-content:center; gap:30px; margin: 20px 0;">
                <div><strong>${profile.posts_count || 0}</strong><br><small>Posts</small></div>
                <div><strong>${profile.followers_count || 0}</strong><br><small>Followers</small></div>
                <div><strong>${profile.following_count || 0}</strong><br><small>Following</small></div>
            </div>

            <div style="display:flex; gap:10px; justify-content:center;">
                <button class="primary-btn" style="max-width:200px;" onclick="openEditProfile()">
                    <i class="fas fa-edit"></i> Edit Profile
                </button>
                <button class="primary-btn" style="max-width:200px; background: var(--bg-card); border: 1px solid var(--border-color);" onclick="changeProfilePic()">
                    <i class="fas fa-camera"></i> Change Photo
                </button>
            </div>
        </div>
    `;
}

/**
 * Change profile picture from gallery
 */
function changeProfilePic() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("profile_pic", file);

        showToast("Uploading...");

        const result = await apiFetch("/profile/upload_pic", {
            method: "POST",
            body: formData
        });

        if (result && result.ok) {
            showToast("Profile picture updated!");
            loadProfile();
        } else {
            showToast("Failed to update profile picture");
        }
    };
    input.click();
}

/**
 * Open edit profile modal
 */
function openEditProfile() {
    const user = USER() || {};
    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.id = "edit-profile-modal";
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-btn" onclick="document.getElementById('edit-profile-modal').remove()">&times;</span>
            <h2 style="margin-bottom:20px;">Edit Profile</h2>
            <div class="upload-form">
                <input type="text" id="edit-name" placeholder="Full Name" value="${escapeHtml(user.name || "")}">
                <textarea id="edit-bio" placeholder="Bio">${escapeHtml(user.bio || "")}</textarea>
                <input type="text" id="edit-location" placeholder="Location" value="${escapeHtml(user.location || "")}">
                <button onclick="saveProfile()">Save Changes</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

/**
 * Save profile changes
 */
async function saveProfile() {
    const name = document.getElementById("edit-name").value;
    const bio = document.getElementById("edit-bio").value;
    const location = document.getElementById("edit-location").value;

    const result = await apiFetch("/profile/update", {
        method: "PUT",
        body: JSON.stringify({ name, bio, location })
    });

    if (result && result.ok) {
        showToast("Profile updated!");
        document.getElementById("edit-profile-modal")?.remove();
        loadProfile();
    } else {
        showToast("Failed to update profile");
    }
}

// ------------------------------------------------------------
// 7. CHATS LOGIC
// ------------------------------------------------------------

/**
 * Load chat list
 */
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

    container.innerHTML = chats.map(chat => {
        const user = chat.user || {};
        const username = user.username || "User";
        const initial = username.charAt(0).toUpperCase();
        const avatar = user.profile_pic || "";

        return `
            <div class="chat-item" onclick="openChat(${chat.id})">
                <div class="chat-avatar">
                    ${avatar ? `<img src="${escapeHtml(avatar)}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">` : initial}
                </div>
                <div class="chat-info">
                    <strong>${escapeHtml(username)}</strong>
                    <small>${escapeHtml(chat.last_message || "No messages yet")}</small>
                </div>
                <div class="chat-time">${timeAgo(chat.updated_at)}</div>
            </div>
        `;
    }).join("");
}

/**
 * Search chats
 */
function searchChats(query) {
    if (!query) {
        loadChats();
        return;
    }
    const filtered = CACHED_CHATS.filter(c =>
        (c.user?.username || "").toLowerCase().includes(query.toLowerCase())
    );
    // Re-render with filtered
    const container = document.getElementById("chat-list");
    if (filtered.length === 0) {
        container.innerHTML = `<p class="loading-text">No results for "${escapeHtml(query)}"</p>`;
        return;
    }
    container.innerHTML = filtered.map(chat => {
        const user = chat.user || {};
        const username = user.username || "User";
        const initial = username.charAt(0).toUpperCase();
        return `
            <div class="chat-item" onclick="openChat(${chat.id})">
                <div class="chat-avatar">${initial}</div>
                <div class="chat-info">
                    <strong>${escapeHtml(username)}</strong>
                    <small>${escapeHtml(chat.last_message || "")}</small>
                </div>
            </div>
        `;
    }).join("");
}

/**
 * Open a chat conversation
 */
function openChat(chatId) {
    if (typeof openChatConversation === "function") {
        openChatConversation(chatId);
    } else {
        showToast("Chat feature coming soon!");
    }
}

/**
 * Open new chat
 */
function openNewChat() {
    showToast("New chat feature coming soon!");
}

// ------------------------------------------------------------
// 8. SEARCH USERS
// ------------------------------------------------------------

let searchTimeout = null;

/**
 * Search users (debounced)
 */
function searchUsers(query) {
    clearTimeout(searchTimeout);
    if (!query || query.length < 2) {
        loadFeed();
        return;
    }

    searchTimeout = setTimeout(async () => {
        const container = document.getElementById("feed-posts");
        container.innerHTML = '<p class="loading-text">Searching...</p>';

        const result = await apiFetch(`/profile/search?q=${encodeURIComponent(query)}`);
        if (!result || !result.ok) {
            container.innerHTML = '<p class="loading-text">Search failed</p>';
            return;
        }

        const users = result.data.users || result.data || [];
        if (users.length === 0) {
            container.innerHTML = `<p class="loading-text">No users found for "${escapeHtml(query)}"</p>`;
            return;
        }

        container.innerHTML = users.map(user => {
            const username = user.username || "User";
            const initial = username.charAt(0).toUpperCase();
            const avatar = user.profile_pic || "";
            return `
                <div class="chat-item" onclick="viewUserProfile(${user.id})">
                    <div class="chat-avatar">
                        ${avatar ? `<img src="${escapeHtml(avatar)}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">` : initial}
                    </div>
                    <div class="chat-info">
                        <strong>${escapeHtml(user.name || username)}</strong>
                        <small>@${escapeHtml(username)}</small>
                    </div>
                </div>
            `;
        }).join("");
    }, 400);
}

/**
 * View another user's profile
 */
function viewUserProfile(userId) {
    showToast(`Viewing profile of user #${userId}`);
    // TODO: Navigate to user profile page
}

// ------------------------------------------------------------
// 9. POST CREATOR
// ------------------------------------------------------------

/**
 * Open post creator modal
 */
function openPostCreator() {
    document.getElementById("post-creator-modal").style.display = "flex";
}

/**
 * Close post creator modal
 */
function closePostCreator() {
    document.getElementById("post-creator-modal").style.display = "none";
    document.getElementById("post-caption").value = "";
    document.getElementById("post-media").value = "";
    document.getElementById("post-file").value = "";
}

/**
 * Submit a new post
 */
async function submitPost() {
    const caption = document.getElementById("post-caption").value.trim();
    const mediaInput = document.getElementById("post-media");
    const fileInput = document.getElementById("post-file");

    const mediaFile = mediaInput.files[0];
    const attachFile = fileInput.files[0];

    if (!caption && !mediaFile && !attachFile) {
        showToast("Write something or attach a file");
        return;
    }

    const formData = new FormData();
    if (caption) formData.append("caption", caption);
    if (mediaFile) formData.append("media", mediaFile);
    if (attachFile) formData.append("file", attachFile);

    showToast("Posting...");

    const result = await apiFetch("/posts", {
        method: "POST",
        body: formData
    });

    if (result && result.ok) {
        showToast("Posted successfully!");
        closePostCreator();
        loadFeed();
    } else {
        showToast("Failed to post");
    }
}

// ------------------------------------------------------------
// 10. INITIALIZATION
// ------------------------------------------------------------

/**
 * Initialize app on page load
 */
window.addEventListener("DOMContentLoaded", () => {
    // Check if user is logged in
    if (!TOKEN()) {
        console.warn("No auth token found — user may need to login");
    }

    // Load initial page
    loadPage("feed");

    // Handle Enter key in search
    const searchInput = document.getElementById("home-search");
    if (searchInput) {
        searchInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") searchUsers(e.target.value);
        });
    }

    // Close modals on overlay click
    document.querySelectorAll(".modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.style.display = "none";
            }
        });
    });
});

// Expose functions globally (for inline onclick handlers)
window.loadPage = loadPage;
window.toggleSidebar = toggleSidebar;
window.focusSearch = focusSearch;
window.loadFeed = loadFeed;
window.switchFeedTab = switchFeedTab;
window.likePost = likePost;
window.commentPost = commentPost;
window.sharePost = sharePost;
window.loadStories = loadStories;
window.uploadStory = uploadStory;
window.viewStory = viewStory;
window.loadProfile = loadProfile;
window.changeProfilePic = changeProfilePic;
window.openEditProfile = openEditProfile;
window.saveProfile = saveProfile;
window.loadChats = loadChats;
window.searchChats = searchChats;
window.openChat = openChat;
window.openNewChat = openNewChat;
window.searchUsers = searchUsers;
window.viewUserProfile = viewUserProfile;
window.openPostCreator = openPostCreator;
window.closePostCreator = closePostCreator;
window.submitPost = submitPost;
