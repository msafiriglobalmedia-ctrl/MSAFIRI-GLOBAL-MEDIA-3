/* ============================================================
   MSAFIRI GLOBAL MEDIA
   APP.JS — PHASE 2
   ------------------------------------------------------------
   Compatible with:
   - FastAPI main.py
   - /api/posts
   - /api/profile
   - /api/messages
   - /api/discovery
   - /api/ai-council
   - /api/studio
   - /api/market
   - /api/world-map
   - /api/channels
   - /api/communities
   - /api/user-manual
   - /api/settings
   - /api/health
   ============================================================ */

'use strict';

/* ============================================================
   GLOBAL CONFIG
   ============================================================ */

const API = window.location.origin;

const APP_NAME = 'MSAFIRI GLOBAL MEDIA';
const APP_VERSION = '6.0.0-PHASE2';
const APP_TAGLINE = 'Connect beyond — Media V0.0.1';

const STORAGE = {
    TOKEN: 'msafiri_token',
    USER: 'msafiri_user',
    THEME: 'msafiri_theme',
    VIEW: 'msafiri_view'
};

let TOKEN = localStorage.getItem(STORAGE.TOKEN) || '';
let CURRENT_USER = readJSON(STORAGE.USER, null);

let CURRENT_VIEW =
    localStorage.getItem(STORAGE.VIEW) || 'home';

let CURRENT_POSTS = [];
let CURRENT_CHATS = [];
let CURRENT_PROFILE = null;

let DISCOVERY_DATA = [];
let SEARCH_RESULTS = [];

let CURRENT_CHAT_USER = null;

let AI_STATE = {
    ai: 'education',
    country: 'Tanzania',
    level: 'Degree',
    content: 'Notes'
};


/* ============================================================
   DOM HELPERS
   ============================================================ */

const $ = (selector, root = document) =>
    root.querySelector(selector);

const $$ = (selector, root = document) =>
    Array.from(root.querySelectorAll(selector));

function byId(id) {
    return document.getElementById(id);
}

function safeText(value) {
    if (value === null || value === undefined) {
        return '';
    }

    return String(value);
}

function escapeHTML(value) {
    return safeText(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function readJSON(key, fallback = null) {
    try {
        const value = localStorage.getItem(key);

        if (!value) {
            return fallback;
        }

        return JSON.parse(value);
    } catch (error) {
        console.warn('JSON storage error:', error);
        return fallback;
    }
}

function saveJSON(key, value) {
    try {
        localStorage.setItem(
            key,
            JSON.stringify(value)
        );
    } catch (error) {
        console.warn('Storage save error:', error);
    }
}

function removeStorage(key) {
    try {
        localStorage.removeItem(key);
    } catch (error) {
        console.warn(error);
    }
}

function sleep(ms) {
    return new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}


/* ============================================================
   NOTIFICATION / TOAST
   ============================================================ */

function showToast(message, type = 'info') {

    let container =
        byId('msafiri-toast-container');

    if (!container) {
        container = document.createElement('div');

        container.id =
            'msafiri-toast-container';

        container.style.position = 'fixed';
        container.style.left = '50%';
        container.style.bottom = '85px';
        container.style.transform = 'translateX(-50%)';
        container.style.zIndex = '999999';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '8px';
        container.style.pointerEvents = 'none';

        document.body.appendChild(container);
    }

    const toast =
        document.createElement('div');

    toast.textContent = message;

    toast.style.padding = '12px 18px';
    toast.style.borderRadius = '14px';
    toast.style.background =
        type === 'error'
            ? '#dc3545'
            : type === 'success'
                ? '#198754'
                : '#212529';

    toast.style.color = '#fff';
    toast.style.fontSize = '14px';
    toast.style.maxWidth = '90vw';
    toast.style.boxShadow =
        '0 8px 25px rgba(0,0,0,.25)';

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3500);
}


/* ============================================================
   API REQUEST HELPER
   ============================================================ */

async function apiRequest(
    path,
    options = {}
) {

    const config = {
        ...options,
        headers: {
            ...(options.headers || {})
        }
    };

    if (!(config.body instanceof FormData)) {
        config.headers['Content-Type'] =
            config.headers['Content-Type'] ||
            'application/json';
    }

    if (TOKEN) {
        config.headers.Authorization =
            `Bearer ${TOKEN}`;
    }

    const response =
        await fetch(`${API}${path}`, config);

    let data = null;

    const contentType =
        response.headers.get('content-type') || '';

    if (contentType.includes('application/json')) {
        try {
            data = await response.json();
        } catch {
            data = null;
        }
    } else {
        try {
            data = await response.text();
        } catch {
            data = null;
        }
    }

    if (!response.ok) {

        let message =
            data?.detail ||
            data?.message ||
            `Request failed (${response.status})`;

        if (response.status === 401) {
            message =
                'Your session has expired. Please login again.';
        }

        if (response.status === 405) {
            message =
                'This action is not allowed by the current backend route.';
        }

        const error =
            new Error(message);

        error.status = response.status;
        error.data = data;

        throw error;
    }

    return data;
}


/* ============================================================
   API SHORTCUTS
   ============================================================ */

async function GET(path) {
    return apiRequest(path, {
        method: 'GET'
    });
}

async function POST(path, body = null) {

    const options = {
        method: 'POST'
    };

    if (body instanceof FormData) {
        options.body = body;
    } else if (body !== null) {
        options.body = JSON.stringify(body);
    }

    return apiRequest(path, options);
}

async function PATCH(path, body = {}) {
    return apiRequest(path, {
        method: 'PATCH',
        body: JSON.stringify(body)
    });
}

async function DELETE(path) {
    return apiRequest(path, {
        method: 'DELETE'
    });
}


/* ============================================================
   AUTH STATE
   ============================================================ */

function setAuth(token, user = null) {

    TOKEN = token || '';

    if (TOKEN) {
        localStorage.setItem(
            STORAGE.TOKEN,
            TOKEN
        );
    } else {
        removeStorage(STORAGE.TOKEN);
    }

    if (user) {
        CURRENT_USER = user;

        saveJSON(
            STORAGE.USER,
            CURRENT_USER
        );
    }

    updateAuthUI();
}

function clearAuth() {

    TOKEN = '';
    CURRENT_USER = null;

    removeStorage(STORAGE.TOKEN);
    removeStorage(STORAGE.USER);

    updateAuthUI();
}

function isLoggedIn() {
    return Boolean(TOKEN);
}

function updateAuthUI() {

    document.body.classList.toggle(
        'msafiri-authenticated',
        isLoggedIn()
    );

    document.body.classList.toggle(
        'msafiri-guest',
        !isLoggedIn()
    );

    const userName =
        CURRENT_USER?.full_name ||
        CURRENT_USER?.username ||
        'User';

    $$('[data-current-user-name]')
        .forEach(el => {
            el.textContent = userName;
        });

    $$('[data-current-username]')
        .forEach(el => {
            el.textContent =
                CURRENT_USER?.username
                    ? `@${CURRENT_USER.username}`
                    : '';
        });

    $$('[data-current-avatar]')
        .forEach(el => {

            const avatar =
                CURRENT_USER?.avatar_url || '';

            if (avatar) {
                el.src = absoluteURL(avatar);
            }
        });
}


/* ============================================================
   URL HELPERS
   ============================================================ */

function absoluteURL(url) {

    if (!url) {
        return '';
    }

    if (
        url.startsWith('http://') ||
        url.startsWith('https://') ||
        url.startsWith('data:')
    ) {
        return url;
    }

    if (url.startsWith('/')) {
        return `${API}${url}`;
    }

    return `${API}/${url}`;
}


/* ============================================================
   VIEW NAVIGATION
   ============================================================ */

function setView(view) {

    CURRENT_VIEW = view;

    localStorage.setItem(
        STORAGE.VIEW,
        view
    );

    $$('[data-view]').forEach(el => {

        const target =
            el.dataset.view;

        el.classList.toggle(
            'active',
            target === view
        );
    });

    $$(
        '[data-page]'
    ).forEach(page => {

        const pageName =
            page.dataset.page;

        page.hidden =
            pageName !== view;
    });

    if (view === 'home') {
        loadFeed();
    }

    if (view === 'discovery') {
        loadDiscovery();
    }

    if (view === 'chats') {
        loadChats();
    }

    if (view === 'profile') {
        loadOwnProfile();
    }
}


/* ============================================================
   FIND OR CREATE APP CONTAINER
   ============================================================ */

function getAppContainer() {

    let app =
        byId('app');

    if (!app) {
        app =
            document.querySelector(
                '[data-app]'
            );
    }

    return app || document.body;
}


/* ============================================================
   FEED
   ============================================================ */

async function loadFeed() {

    const container =
        byId('feed') ||
        document.querySelector(
            '[data-feed]'
        );

    if (!container) {
        return;
    }

    container.innerHTML =
        '<div class="loading">Loading posts...</div>';

    const possibleEndpoints = [
        '/api/feed',
        '/api/posts',
        '/api/posts/feed'
    ];

    let result = null;

    for (const endpoint of possibleEndpoints) {

        try {
            result = await GET(endpoint);

            if (result) {
                break;
            }

        } catch (error) {

            if (
                error.status !== 404 &&
                error.status !== 405
            ) {
                console.warn(
                    endpoint,
                    error
                );
            }
        }
    }

    if (!result) {
        container.innerHTML =
            emptyState(
                'No posts available yet.'
            );
        return;
    }

    const posts =
        normalizePosts(result);

    CURRENT_POSTS = posts;

    renderPosts(
        posts,
        container
    );
}

function normalizePosts(data) {

    if (Array.isArray(data)) {
        return data;
    }

    if (Array.isArray(data?.posts)) {
        return data.posts;
    }

    if (Array.isArray(data?.items)) {
        return data.items;
    }

    if (Array.isArray(data?.feed)) {
        return data.feed;
    }

    return [];
}

function renderPosts(posts, container) {

    if (!posts.length) {
        container.innerHTML =
            emptyState(
                'No posts yet. Be the first to post.'
            );

        return;
    }

    container.innerHTML =
        posts
            .map(renderPost)
            .join('');

    bindPostEvents(container);
}

function renderPost(post) {

    const avatar =
        absoluteURL(
            post.avatar_url
        );

    const name =
        post.full_name ||
        post.username ||
        'User';

    const username =
        post.username
            ? `@${post.username}`
            : '';

    const media =
        renderPostMedia(post);

    return `
        <article
            class="msafiri-post"
            data-post-id="${escapeHTML(post.id)}"
        >

            <header class="post-header">

                <button
                    class="post-user"
                    data-open-profile="${escapeHTML(post.user_id || '')}"
                >

                    ${
                        avatar
                            ? `<img
                                src="${escapeHTML(avatar)}"
                                alt=""
                                class="post-avatar"
                              >`
                            : `<div class="post-avatar placeholder">
                                ${escapeHTML(
                                    name.charAt(0).toUpperCase()
                                )}
                              </div>`
                    }

                    <span>
                        <strong>
                            ${escapeHTML(name)}
                        </strong>

                        <small>
                            ${escapeHTML(username)}
                        </small>
                    </span>

                </button>

                <button
                    class="post-more"
                    data-post-menu="${escapeHTML(post.id)}"
                >
                    ⋯
                </button>

            </header>

            ${
                post.caption
                    ? `<div class="post-caption">
                        ${escapeHTML(post.caption)}
                       </div>`
                    : ''
            }

            ${media}

            <div class="post-actions">

                <button
                    data-like-post="${post.id}"
                    class="${post.liked ? 'active' : ''}"
                >
                    ❤️
                    <span>${post.likes || 0}</span>
                </button>

                <button
                    data-comment-post="${post.id}"
                >
                    💬
                    <span>${post.comments || 0}</span>
                </button>

                <button
                    data-save-post="${post.id}"
                    class="${post.saved ? 'active' : ''}"
                >
                    🔖
                    <span>${post.saves || 0}</span>
                </button>

                <button
                    data-share-post="${post.id}"
                >
                    ↗️
                    <span>${post.shares || 0}</span>
                </button>

            </div>

        </article>
    `;
}

function renderPostMedia(post) {

    if (!post.media_url) {
        return '';
    }

    const url =
        absoluteURL(
            post.media_url
        );

    if (post.media_type === 'video') {

        return `
            <video
                class="post-media"
                src="${escapeHTML(url)}"
                controls
                playsinline
                preload="metadata"
            ></video>
        `;
    }

    if (post.media_type === 'image') {

        return `
            <img
                class="post-media"
                src="${escapeHTML(url)}"
                alt="Post media"
                loading="lazy"
            >
        `;
    }

    return '';
}

function bindPostEvents(container) {

    $$(
        '[data-like-post]',
        container
    ).forEach(button => {

        button.addEventListener(
            'click',
            () => toggleLike(
                button.dataset.likePost,
                button
            )
        );
    });

    $$(
        '[data-save-post]',
        container
    ).forEach(button => {

        button.addEventListener(
            'click',
            () => toggleSave(
                button.dataset.savePost,
                button
            )
        );
    });

    $$(
        '[data-share-post]',
        container
    ).forEach(button => {

        button.addEventListener(
            'click',
            () => sharePost(
                button.dataset.sharePost
            )
        );
    });

    $$(
        '[data-comment-post]',
        container
    ).forEach(button => {

        button.addEventListener(
            'click',
            () => openComments(
                button.dataset.commentPost
            )
        );
    });

    $$(
        '[data-open-profile]',
        container
    ).forEach(button => {

        button.addEventListener(
            'click',
            () => openProfile(
                button.dataset.openProfile
            )
        );
    });

    $$(
        '[data-post-menu]',
        container
    ).forEach(button => {

        button.addEventListener(
            'click',
            () => postMenu(
                button.dataset.postMenu
            )
        );
    });
}


/* ============================================================
   CREATE POST
   ============================================================ */

async function createPost(form) {

    if (!isLoggedIn()) {
        showToast(
            'Please login before posting.',
            'error'
        );
        return;
    }

    const captionInput =
        form.querySelector(
            '[name="caption"]'
        );

    const fileInput =
        form.querySelector(
            '[name="media"]'
        );

    const caption =
        captionInput?.value?.trim() || '';

    const file =
        fileInput?.files?.[0] || null;

    if (!caption && !file) {
        showToast(
            'Write a caption or select an image/video.',
            'error'
        );
        return;
    }

    const data =
        new FormData();

    data.append(
        'caption',
        caption
    );

    if (file) {
        data.append(
            'media',
            file
        );
    }

    try {

        const result =
            await POST(
                '/api/posts/create',
                data
            );

        showToast(
            result?.message ||
            'Post created successfully.',
            'success'
        );

        form.reset();

        closeCreatePost();

        await loadFeed();

    } catch (error) {

        console.error(
            'Create post error:',
            error
        );

        showToast(
            error.message ||
            'Could not create post.',
            'error'
        );
    }
}


/* ============================================================
   CREATE POST MODAL
   ============================================================ */

function openCreatePost() {

    let modal =
        byId('create-post-modal');

    if (!modal) {

        modal =
            document.createElement('div');

        modal.id =
            'create-post-modal';

        modal.className =
            'msafiri-modal';

        modal.innerHTML = `
            <div class="msafiri-modal-card">

                <button
                    class="modal-close"
                    data-close-create
                >
                    ×
                </button>

                <h2>Create Post</h2>

                <form
                    id="dynamic-create-post-form"
                >

                    <textarea
                        name="caption"
                        placeholder="What's on your mind?"
                        rows="5"
                    ></textarea>

                    <input
                        type="file"
                        name="media"
                        accept="image/*,video/*"
                    >

                    <button
                        type="submit"
                    >
                        Post
                    </button>

                </form>

            </div>
        `;

        document.body.appendChild(
            modal
        );

        modal.querySelector(
            '[data-close-create]'
        ).addEventListener(
            'click',
            closeCreatePost
        );

        modal.querySelector(
            'form'
        ).addEventListener(
            'submit',
            event => {

                event.preventDefault();

                createPost(
                    event.currentTarget
                );
            }
        );
    }

    modal.hidden = false;
}

function closeCreatePost() {

    const modal =
        byId('create-post-modal');

    if (modal) {
        modal.hidden = true;
    }
}


/* ============================================================
   LIKE
   ============================================================ */

async function toggleLike(
    postId,
    button
) {

    try {

        const result =
            await POST(
                `/api/posts/${postId}/like`
            );

        button.classList.toggle(
            'active',
            Boolean(result?.liked)
        );

        const count =
            button.querySelector('span');

        if (count) {
            count.textContent =
                result?.likes ?? 0;
        }

    } catch (error) {

        showToast(
            error.message ||
            'Unable to like post.',
            'error'
        );
    }
}


/* ============================================================
   SAVE
   ============================================================ */

async function toggleSave(
    postId,
    button
) {

    try {

        const result =
            await POST(
                `/api/posts/${postId}/save`
            );

        button.classList.toggle(
            'active',
            Boolean(result?.saved)
        );

        const count =
            button.querySelector('span');

        if (count) {
            count.textContent =
                result?.saves ?? 0;
        }

    } catch (error) {

        showToast(
            error.message ||
            'Unable to save post.',
            'error'
        );
    }
}


/* ============================================================
   SHARE
   ============================================================ */

async function sharePost(postId) {

    try {

        const result =
            await POST(
                `/api/posts/${postId}/share`
            );

        const shareURL =
            `${window.location.origin}/?post=${postId}`;

        if (
            navigator.share
        ) {

            try {

                await navigator.share({
                    title: APP_NAME,
                    text: 'Check out this post on MSAFIRI GLOBAL MEDIA.',
                    url: shareURL
                });

            } catch {
                /* User cancelled native share */
            }

        } else if (
            navigator.clipboard
        ) {

            await navigator.clipboard.writeText(
                shareURL
            );

            showToast(
                'Post link copied.',
                'success'
            );
        }

        console.log(
            'Share result:',
            result
        );

    } catch (error) {

        showToast(
            error.message ||
            'Unable to share post.',
            'error'
        );
    }
}


/* ============================================================
   COMMENTS
   ============================================================ */

async function openComments(postId) {

    try {

        const result =
            await GET(
                `/api/posts/${postId}/comments`
            );

        const comments =
            result?.comments || [];

        let modal =
            byId('comments-modal');

        if (!modal) {

            modal =
                document.createElement('div');

            modal.id =
                'comments-modal';

            modal.className =
                'msafiri-modal';

            document.body.appendChild(
                modal
            );
        }

        modal.innerHTML = `
            <div class="msafiri-modal-card">

                <button
                    class="modal-close"
                    data-close-comments
                >
                    ×
                </button>

                <h2>Comments</h2>

                <div
                    class="comments-list"
                    id="comments-list"
                >
                    ${
                        comments.length
                            ? comments
                                .map(renderComment)
                                .join('')
                            : '<p>No comments yet.</p>'
                    }
                </div>

                <form
                    id="comment-form"
                    data-post-id="${postId}"
                >

                    <input
                        name="text"
                        type="text"
                        placeholder="Write a comment..."
                        required
                    >

                    <button type="submit">
                        Send
                    </button>

                </form>

            </div>
        `;

        modal.hidden = false;

        modal.querySelector(
            '[data-close-comments]'
        ).onclick = () => {
            modal.hidden = true;
        };

        modal.querySelector(
            '#comment-form'
        ).addEventListener(
            'submit',
            event => {

                event.preventDefault();

                createComment(
                    postId,
                    event.currentTarget
                );
            }
        );

    } catch (error) {

        showToast(
            error.message ||
            'Unable to load comments.',
            'error'
        );
    }
}

function renderComment(comment) {

    return `
        <div class="comment-item">

            <strong>
                ${escapeHTML(
                    comment.full_name ||
                    comment.username ||
                    'User'
                )}
            </strong>

            <p>
                ${escapeHTML(
                    comment.text
                )}
            </p>

        </div>
    `;
}

async function createComment(
    postId,
    form
) {

    const text =
        form.querySelector(
            '[name="text"]'
        )?.value?.trim();

    if (!text) {
        return;
    }

    const data =
        new FormData();

    data.append(
        'text',
        text
    );

    try {

        await POST(
            `/api/posts/${postId}/comments`,
            data
        );

        form.reset();

        await openComments(
            postId
        );

        showToast(
            'Comment added.',
            'success'
        );

    } catch (error) {

        showToast(
            error.message ||
            'Unable to comment.',
            'error'
        );
    }
}


/* ============================================================
   POST MENU
   ============================================================ */

function postMenu(postId) {

    const post =
        CURRENT_POSTS.find(
            item =>
                String(item.id) ===
                String(postId)
        );

    if (!post) {
        return;
    }

    const own =
        CURRENT_USER &&
        Number(post.user_id) ===
        Number(CURRENT_USER.id);

    const choice =
        window.prompt(
            own
                ? 'Type DELETE to delete this post, or Cancel.'
                : 'Post options: type SHARE to share.'
        );

    if (
        own &&
        choice &&
        choice.toUpperCase() === 'DELETE'
    ) {

        deletePost(
            postId
        );
    }
}


/* ============================================================
   DELETE POST
   ============================================================ */

async function deletePost(postId) {

    if (
        !window.confirm(
            'Delete this post?'
        )
    ) {
        return;
    }

    try {

        await DELETE(
            `/api/posts/${postId}`
        );

        showToast(
            'Post deleted.',
            'success'
        );

        await loadFeed();

    } catch (error) {

        showToast(
            error.message ||
            'Unable to delete post.',
            'error'
        );
    }
}


/* ============================================================
   PROFILE
   ============================================================ */

async function openProfile(userId) {

    if (!userId) {
        return;
    }

    try {

        const result =
            await GET(
                `/api/profile/${userId}`
            );

        CURRENT_PROFILE =
            result;

        renderProfilePage(
            result
        );

        setView('profile');

    } catch (error) {

        showToast(
            error.message ||
            'User not found.',
            'error'
        );
    }
}

async function loadOwnProfile() {

    if (!CURRENT_USER?.id) {
        return;
    }

    await openProfile(
        CURRENT_USER.id
    );
}

function renderProfilePage(user) {

    const container =
        byId('profile-content') ||
        document.querySelector(
            '[data-profile-content]'
        );

    if (!container) {
        return;
    }

    const avatar =
        absoluteURL(
            user.avatar_url
        );

    container.innerHTML = `

        <section class="profile-header">

            ${
                avatar
                    ? `<img
                        src="${escapeHTML(avatar)}"
                        class="profile-avatar"
                        alt=""
                      >`
                    : `<div class="profile-avatar placeholder">
                        ${escapeHTML(
                            (
                                user.full_name ||
                                user.username ||
                                'U'
                            ).charAt(0)
                        )}
                      </div>`
            }

            <h2>
                ${escapeHTML(
                    user.full_name ||
                    user.username ||
                    'User'
                )}
            </h2>

            <p>
                @${escapeHTML(
                    user.username || ''
                )}
            </p>

            <p>
                ${escapeHTML(
                    user.bio || ''
                )}
            </p>

            <p>
                📍 ${escapeHTML(
                    user.location || ''
                )}
            </p>

            ${
                CURRENT_USER &&
                Number(user.id) ===
                Number(CURRENT_USER.id)
                    ? `
                        <button
                            data-edit-profile
                        >
                            Edit Profile
                        </button>
                      `
                    : `
                        <button
                            data-message-user="${user.id}"
                        >
                            💬 Message
                        </button>
                      `
            }

        </section>
    `;

    const editButton =
        container.querySelector(
            '[data-edit-profile]'
        );

    if (editButton) {
        editButton.onclick =
            openEditProfile;
    }

    const messageButton =
        container.querySelector(
            '[data-message-user]'
        );

    if (messageButton) {

        messageButton.onclick =
            () => openChatWithUser(
                user
            );
    }
}


/* ============================================================
   EDIT PROFILE
   ============================================================ */

function openEditProfile() {

    if (!CURRENT_USER) {
        return;
    }

    const fullName =
        window.prompt(
            'Full name:',
            CURRENT_USER.full_name || ''
        );

    if (fullName === null) {
        return;
    }

    const bio =
        window.prompt(
            'Bio:',
            CURRENT_USER.bio || ''
        );

    if (bio === null) {
        return;
    }

    const location =
        window.prompt(
            'Location:',
            CURRENT_USER.location || ''
        );

    if (location === null) {
        return;
    }

    updateProfile({
        full_name: fullName,
        bio,
        location
    });
}

async function updateProfile(data) {

    try {

        const result =
            await PATCH(
                '/api/profile',
                data
            );

        CURRENT_USER =
            result;

        saveJSON(
            STORAGE.USER,
            CURRENT_USER
        );

        updateAuthUI();

        renderProfilePage(
            result
        );

        showToast(
            'Profile updated.',
            'success'
        );

    } catch (error) {

        showToast(
            error.message ||
            'Unable to update profile.',
            'error'
        );
    }
}


/* ============================================================
   USER SEARCH
   ============================================================ */

/*
   IMPORTANT:
   The current backend supplied by the user does NOT contain
   a search endpoint.

   This function tries several possible endpoints safely.
   When none exists, it tells the user instead of crashing.
*/

async function searchUsers(query) {

    query =
        safeText(query).trim();

    if (!query) {
        SEARCH_RESULTS = [];
        renderSearchResults([]);
        return;
    }

    const endpoints = [

        `/api/profile/search?q=${encodeURIComponent(query)}`,

        `/api/users/search?q=${encodeURIComponent(query)}`,

        `/api/auth/users?q=${encodeURIComponent(query)}`

    ];

    for (const endpoint of endpoints) {

        try {

            const result =
                await GET(endpoint);

            const users =
                Array.isArray(result)
                    ? result
                    : (
                        result?.users ||
                        result?.results ||
                        []
                    );

            SEARCH_RESULTS =
                users;

            renderSearchResults(
                users
            );

            return;

        } catch (error) {

            if (
                error.status !== 404 &&
                error.status !== 405
            ) {
                console.warn(
                    'Search error:',
                    error
                );
            }
        }
    }

    SEARCH_RESULTS = [];

    renderSearchResults([]);

    showToast(
        'User search endpoint is not yet available in the backend.',
        'error'
    );
}

function renderSearchResults(users) {

    const container =
        byId('search-results') ||
        document.querySelector(
            '[data-search-results]'
        );

    if (!container) {
        return;
    }

    if (!users.length) {

        container.innerHTML =
            '<div class="search-empty">No users found.</div>';

        return;
    }

    container.innerHTML =
        users
            .map(user => {

                const avatar =
                    absoluteURL(
                        user.avatar_url
                    );

                return `
                    <button
                        class="search-user"
                        data-search-user="${escapeHTML(user.id)}"
                    >

                        ${
                            avatar
                                ? `<img
                                    src="${escapeHTML(avatar)}"
                                    alt=""
                                  >`
                                : '👤'
                        }

                        <span>
                            <strong>
                                ${escapeHTML(
                                    user.full_name ||
                                    user.username ||
                                    'User'
                                )}
                            </strong>

                            <small>
                                @${escapeHTML(
                                    user.username || ''
                                )}
                            </small>
                        </span>

                    </button>
                `;
            })
            .join('');

    $$(
        '[data-search-user]',
        container
    ).forEach(button => {

        button.onclick =
            () => openProfile(
                button.dataset.searchUser
            );
    });
}


/* ============================================================
   CHAT
   ============================================================ */

async function loadChats() {

    const container =
        byId('chat-list') ||
        document.querySelector(
            '[data-chat-list]'
        );

    if (!container) {
        return;
    }

    container.innerHTML =
        '<div class="loading">Loading chats...</div>';

    try {

        const result =
            await GET(
                '/api/messages'
            );

        CURRENT_CHATS =
            result?.chats || [];

        renderChatList(
            CURRENT_CHATS,
            container
        );

    } catch (error) {

        console.error(
            'Chat loading error:',
            error
        );

        container.innerHTML =
            emptyState(
                'Unable to load chats.'
            );
    }
}

function renderChatList(
    chats,
    container
) {

    if (!chats.length) {

        container.innerHTML = `
            <div class="chat-empty">

                <div style="font-size:40px;">
                    💬
                </div>

                <h3>No chats yet</h3>

                <p>
                    Search for another user and
                    start a conversation.
                </p>

            </div>
        `;

        return;
    }

    container.innerHTML =
        chats
            .map(chat => {

                const user =
                    chat.user ||
                    chat.other_user ||
                    chat;

                return `
                    <button
                        class="chat-item"
                        data-chat-user="${escapeHTML(
                            user.id || ''
                        )}"
                    >

                        <div class="chat-avatar">
                            ${
                                user.avatar_url
                                    ? `<img
                                        src="${escapeHTML(
                                            absoluteURL(
                                                user.avatar_url
                                            )
                                        )}"
                                        alt=""
                                      >`
                                    : '👤'
                            }
                        </div>

                        <div>
                            <strong>
                                ${escapeHTML(
                                    user.full_name ||
                                    user.username ||
                                    'User'
                                )}
                            </strong>

                            <p>
                                ${escapeHTML(
                                    chat.last_message ||
                                    ''
                                )}
                            </p>
                        </div>

                    </button>
                `;
            })
            .join('');

    $$(
        '[data-chat-user]',
        container
    ).forEach(button => {

        button.onclick =
            async () => {

                const userId =
                    button.dataset.chatUser;

                try {

                    const user =
                        await GET(
                            `/api/profile/${userId}`
                        );

                    openChatWithUser(
                        user
                    );

                } catch (error) {

                    showToast(
                        error.message,
                        'error'
                    );
                }
            };
    });
}


/* ============================================================
   OPEN CHAT
   ============================================================ */

function openChatWithUser(user) {

    CURRENT_CHAT_USER =
        user;

    setView('chats');

    renderChatWindow(
        user
    );
}

function renderChatWindow(user) {

    let container =
        byId('chat-window') ||
        document.querySelector(
            '[data-chat-window]'
        );

    if (!container) {

        container =
            document.createElement('div');

        container.id =
            'chat-window';

        container.className =
            'chat-window';

        document.body.appendChild(
            container
        );
    }

    container.innerHTML = `

        <div class="chat-header">

            <button
                data-close-chat
            >
                ←
            </button>

            <div>

                <strong>
                    ${escapeHTML(
                        user.full_name ||
                        user.username ||
                        'User'
                    )}
                </strong>

                <small>
                    @${escapeHTML(
                        user.username || ''
                    )}
                </small>

            </div>

            <div>
                📞
                🎥
            </div>

        </div>

        <div
            class="chat-messages"
            id="chat-messages"
        >
            <div class="chat-placeholder">
                Chat messages will appear here.
            </div>
        </div>

        <form
            id="chat-message-form"
            class="chat-input-area"
        >

            <button
                type="button"
                data-chat-attachment
            >
                +
            </button>

            <input
                type="text"
                name="message"
                placeholder="Message..."
                autocomplete="off"
                required
            >

            <button
                type="submit"
            >
                ➤
            </button>

        </form>

    `;

    container.hidden = false;

    container.querySelector(
        '[data-close-chat]'
    ).onclick = () => {

        container.hidden = true;

        loadChats();
    };

    container.querySelector(
        '#chat-message-form'
    ).addEventListener(
        'submit',
        event => {

            event.preventDefault();

            sendMessage(
                user,
                event.currentTarget
            );
        }
    );

    loadConversation(
        user
    );
}


/* ============================================================
   LOAD CONVERSATION
   ============================================================ */

async function loadConversation(user) {

    const container =
        byId('chat-messages');

    if (!container) {
        return;
    }

    /*
       The current backend only exposes:
       GET /api/messages

       Therefore we safely try conversation endpoints
       but do not crash if they are unavailable.
    */

    const endpoints = [

        `/api/messages/${user.id}`,

        `/api/messages/chat/${user.id}`,

        `/api/messages/conversation/${user.id}`

    ];

    for (const endpoint of endpoints) {

        try {

            const result =
                await GET(endpoint);

            const messages =
                result?.messages ||
                result?.chat ||
                (
                    Array.isArray(result)
                        ? result
                        : []
                );

            renderMessages(
                messages,
                container
            );

            return;

        } catch (error) {

            if (
                error.status !== 404 &&
                error.status !== 405
            ) {
                console.warn(
                    error
                );
            }
        }
    }

    container.innerHTML = `
        <div class="chat-placeholder">

            <div style="font-size:40px;">
                💬
            </div>

            <p>
                Conversation is ready,
                but the message conversation
                endpoint has not been added
                to the backend yet.
            </p>

        </div>
    `;
}

function renderMessages(
    messages,
    container
) {

    if (!messages.length) {

        container.innerHTML =
            '<div class="chat-placeholder">No messages yet.</div>';

        return;
    }

    container.innerHTML =
        messages
            .map(message => {

                const mine =
                    Number(message.sender_id) ===
                    Number(CURRENT_USER?.id);

                return `
                    <div
                        class="chat-message ${
                            mine
                                ? 'mine'
                                : 'theirs'
                        }"
                    >
                        ${escapeHTML(
                            message.text ||
                            message.content ||
                            message.message ||
                            ''
                        )}
                    </div>
                `;
            })
            .join('');
}


/* ============================================================
   SEND MESSAGE
   ============================================================ */

async function sendMessage(
    user,
    form
) {

    const input =
        form.querySelector(
            '[name="message"]'
        );

    const text =
        input?.value?.trim();

    if (!text) {
        return;
    }

    /*
       Current backend does not yet have
       POST /api/messages.

       Try common endpoints safely.
    */

    const endpoints = [
        '/api/messages',
        `/api/messages/${user.id}`
    ];

    let sent = false;

    for (const endpoint of endpoints) {

        try {

            const result =
                await POST(
                    endpoint,
                    {
                        recipient_id: user.id,
                        receiver_id: user.id,
                        text
                    }
                );

            sent = true;

            input.value = '';

            appendLocalMessage(
                text,
                true
            );

            console.log(
                'Message sent:',
                result
            );

            break;

        } catch (error) {

            if (
                error.status !== 404 &&
                error.status !== 405
            ) {
                console.warn(
                    endpoint,
                    error
                );
            }
        }
    }

    if (!sent) {

        showToast(
            'Message sending is not available yet because the backend has no POST message route.',
            'error'
        );
    }
}

function appendLocalMessage(
    text,
    mine
) {

    const container =
        byId('chat-messages');

    if (!container) {
        return;
    }

    const placeholder =
        container.querySelector(
            '.chat-placeholder'
        );

    if (placeholder) {
        placeholder.remove();
    }

    const message =
        document.createElement('div');

    message.className =
        `chat-message ${
            mine
                ? 'mine'
                : 'theirs'
        }`;

    message.textContent =
        text;

    container.appendChild(
        message
    );

    container.scrollTop =
        container.scrollHeight;
}


/* ============================================================
   DISCOVERY
   ============================================================ */

async function loadDiscovery() {

    const container =
        byId('discovery-content') ||
        document.querySelector(
            '[data-discovery]'
        );

    if (!container) {
        return;
    }

    container.innerHTML =
        '<div class="loading">Loading Discovery...</div>';

    try {

        const result =
            await GET(
                '/api/discovery'
            );

        DISCOVERY_DATA =
            result?.cards || [];

        renderDiscovery(
            DISCOVERY_DATA,
            container
        );

    } catch (error) {

        container.innerHTML =
            emptyState(
                'Unable to load Discovery.'
            );

        showToast(
            error.message,
            'error'
        );
    }
}

function renderDiscovery(
    cards,
    container
) {

    container.innerHTML = `
        <section class="discovery-page">

            <header>
                <h1>Discovery</h1>
                <p>
                    Explore MSAFIRI GLOBAL MEDIA
                </p>
            </header>

            <div class="discovery-grid">

                ${
                    cards
                        .map(card => `
                            <button
                                class="discovery-card"
                                data-discovery-id="${escapeHTML(
                                    card.id
                                )}"
                            >

                                <div class="discovery-icon">
                                    ${escapeHTML(
                                        card.icon
                                    )}
                                </div>

                                <strong>
                                    ${escapeHTML(
                                        card.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        card.desc
                                    )}
                                </span>

                            </button>
                        `)
                        .join('')
                }

            </div>

        </section>
    `;

    $$(
        '[data-discovery-id]',
        container
    ).forEach(card => {

        card.onclick =
            () => openDiscoveryFeature(
                card.dataset.discoveryId
            );
    });
}


/* ============================================================
   DISCOVERY ROUTER
   ============================================================ */

async function openDiscoveryFeature(id) {

    switch (id) {

        case 'ai-council':
            await openAICouncil();
            break;

        case 'creative-studio':
            await openStudio();
            break;

        case 'market':
            await openMarket();
            break;

        case 'world-map':
            await openWorldMap();
            break;

        case 'channels':
            await openChannels();
            break;

        case 'communities':
            await openCommunities();
            break;

        case 'videos':
            setView('videos');
            break;

        case 'settings':
            openSettings();
            break;

        default:
            showToast(
                'Feature not available.',
                'error'
            );
    }
}


/* ============================================================
   DISCOVERY SUBPAGE
   ============================================================ */

function openDiscoveryPage(
    title,
    content,
    onBack = null
) {

    let page =
        byId('discovery-subpage');

    if (!page) {

        page =
            document.createElement('div');

        page.id =
            'discovery-subpage';

        page.className =
            'msafiri-discovery-subpage';

        document.body.appendChild(
            page
        );
    }

    page.innerHTML = `

        <div class="subpage-header">

            <button
                data-subpage-back
            >
                ←
            </button>

            <h2>
                ${escapeHTML(title)}
            </h2>

        </div>

        <div class="subpage-content">
            ${content}
        </div>

    `;

    page.hidden = false;

    page.querySelector(
        '[data-subpage-back]'
    ).onclick = () => {

        page.hidden = true;

        if (typeof onBack === 'function') {
            onBack();
        }
    };
}


/* ============================================================
   AI COUNCIL
   ============================================================ */

async function openAICouncil() {

    try {

        const result =
            await GET(
                '/api/ai-council'
            );

        const ais =
            result?.ais || [];

        openDiscoveryPage(
            'AI Council',
            `
                <div class="option-grid">

                    ${
                        ais
                            .map(ai => `
                                <button
                                    data-ai="${escapeHTML(
                                        ai.id
                                    )}"
                                >

                                    <span>
                                        ${escapeHTML(
                                            ai.icon
                                        )}
                                    </span>

                                    <strong>
                                        ${escapeHTML(
                                            ai.title
                                        )}
                                    </strong>

                                    <small>
                                        ${escapeHTML(
                                            ai.desc
                                        )}
                                    </small>

                                </button>
                            `)
                            .join('')
                    }

                </div>
            `
        );

        $$(
            '[data-ai]',
            byId('discovery-subpage')
        ).forEach(button => {

            button.onclick =
                () => openAI(
                    button.dataset.ai
                );
        });

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}


/* ============================================================
   EDUCATION AI
   ============================================================ */

async function openAI(ai) {

    if (ai !== 'education') {

        openDiscoveryPage(
            `${ai} AI`,
            `
                <div class="ai-placeholder">

                    <h3>
                        ${escapeHTML(
                            ai
                        )} AI
                    </h3>

                    <p>
                        AI chat interface prepared
                        for a future AI integration.
                    </p>

                </div>
            `
        );

        return;
    }

    try {

        const countryResult =
            await GET(
                '/api/ai-council/countries'
            );

        const countries =
            countryResult?.countries || [];

        openDiscoveryPage(
            'Education AI — Choose Country',
            `
                <div class="option-grid">

                    ${
                        countries
                            .map(country => `
                                <button
                                    data-ai-country="${escapeHTML(
                                        country
                                    )}"
                                >
                                    🌍
                                    ${escapeHTML(
                                        country
                                    )}
                                </button>
                            `)
                            .join('')
                    }

                </div>
            `
        );

        $$(
            '[data-ai-country]',
            byId('discovery-subpage')
        ).forEach(button => {

            button.onclick =
                () => {

                    AI_STATE.country =
                        button.dataset.aiCountry;

                    openAILevels();
                };
        });

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}

async function openAILevels() {

    const result =
        await GET(
            '/api/ai-council/levels'
        );

    const levels =
        result?.levels || [];

    openDiscoveryPage(
        `Education AI — ${AI_STATE.country}`,
        `
            <div class="option-grid">

                ${
                    levels
                        .map(level => `
                            <button
                                data-ai-level="${escapeHTML(
                                    level
                                )}"
                            >
                                🎓
                                ${escapeHTML(
                                    level
                                )}
                            </button>
                        `)
                        .join('')
                }

            </div>
        `
    );

    $$(
        '[data-ai-level]',
        byId('discovery-subpage')
    ).forEach(button => {

        button.onclick =
            () => {

                AI_STATE.level =
                    button.dataset.aiLevel;

                openAIContentTypes();
            };
    });
}

async function openAIContentTypes() {

    const result =
        await GET(
            '/api/ai-council/content-types'
        );

    const types =
        result?.content_types || [];

    openDiscoveryPage(
        `Choose Content — ${AI_STATE.level}`,
        `
            <div class="option-grid">

                ${
                    types
                        .map(type => `
                            <button
                                data-ai-content="${escapeHTML(
                                    type
                                )}"
                            >
                                📚
                                ${escapeHTML(
                                    type
                                )}
                            </button>
                        `)
                        .join('')
                }

            </div>
        `
    );

    $$(
        '[data-ai-content]',
        byId('discovery-subpage')
    ).forEach(button => {

        button.onclick =
            () => {

                AI_STATE.content =
                    button.dataset.aiContent;

                openAIChat();
            };
    });
}

function openAIChat() {

    openDiscoveryPage(
        'AI Chat',
        `

            <div class="ai-chat">

                <div class="ai-message">
                    Hello! I'm your
                    ${escapeHTML(
                        AI_STATE.content
                    )}
                    assistant for
                    ${escapeHTML(
                        AI_STATE.level
                    )}
                    curriculum in
                    ${escapeHTML(
                        AI_STATE.country
                    )}.
                    Ask me anything about
                    a subject or topic.
                </div>

                <div
                    id="ai-chat-messages"
                ></div>

                <form
                    id="ai-question-form"
                >

                    <input
                        name="question"
                        placeholder="Ask a question..."
                        required
                    >

                    <button>
                        Ask
                    </button>

                </form>

            </div>

        `
    );

    const form =
        byId('ai-question-form');

    form?.addEventListener(
        'submit',
        async event => {

            event.preventDefault();

            const question =
                form.querySelector(
                    '[name="question"]'
                ).value.trim();

            if (!question) {
                return;
            }

            await askAI(
                question
            );

            form.reset();
        }
    );
}

async function askAI(question) {

    try {

        const params =
            new URLSearchParams({
                ai: 'education',
                country: AI_STATE.country,
                level: AI_STATE.level,
                content: AI_STATE.content,
                q: question
            });

        const result =
            await GET(
                `/api/ai-council/chat?${params}`
            );

        const container =
            byId('ai-chat-messages');

        if (!container) {
            return;
        }

        container.insertAdjacentHTML(
            'beforeend',
            `
                <div class="ai-question">
                    ${escapeHTML(
                        question
                    )}
                </div>

                <div class="ai-answer">
                    ${escapeHTML(
                        result?.reply ||
                        'No answer.'
                    )}
                </div>
            `
        );

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}


/* ============================================================
   CREATIVE STUDIO
   ============================================================ */

async function openStudio() {

    try {

        const result =
            await GET(
                '/api/studio'
            );

        const tools =
            result?.tools || [];

        openDiscoveryPage(
            'Creative Studio',
            `
                <div class="option-grid">

                    ${
                        tools
                            .map(tool => `
                                <button
                                    data-studio-tool="${escapeHTML(
                                        tool.id
                                    )}"
                                >

                                    <span>
                                        ${escapeHTML(
                                            tool.icon
                                        )}
                                    </span>

                                    <strong>
                                        ${escapeHTML(
                                            tool.title
                                        )}
                                    </strong>

                                    <small>
                                        ${escapeHTML(
                                            tool.desc
                                        )}
                                    </small>

                                </button>
                            `)
                            .join('')
                    }

                </div>
            `
        );

        $$(
            '[data-studio-tool]',
            byId('discovery-subpage')
        ).forEach(button => {

            button.onclick =
                () => {

                    showToast(
                        'Creative Studio tool prepared for the next phase.',
                        'info'
                    );
                };
        });

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}


/* ============================================================
   MARKET
   ============================================================ */

async function openMarket() {

    try {

        const result =
            await GET(
                '/api/market/categories'
            );

        const categories =
            result?.categories || [];

        openDiscoveryPage(
            'MSAFIRI MARKET',
            `
                <div class="option-grid">

                    ${
                        categories
                            .map(category => `
                                <button
                                    data-market-category="${escapeHTML(
                                        category.id
                                    )}"
                                >

                                    🛍️

                                    <strong>
                                        ${escapeHTML(
                                            category.title
                                        )}
                                    </strong>

                                    <small>
                                        ${escapeHTML(
                                            category.desc
                                        )}
                                    </small>

                                </button>
                            `)
                            .join('')
                    }

                </div>
            `
        );

        $$(
            '[data-market-category]',
            byId('discovery-subpage')
        ).forEach(button => {

            button.onclick =
                () => openMarketItems(
                    button.dataset.marketCategory
                );
        });

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}

async function openMarketItems(category) {

    try {

        const result =
            await GET(
                `/api/market/items?category=${encodeURIComponent(category)}`
            );

        const items =
            result?.items || [];

        openDiscoveryPage(
            `Market — ${category}`,
            items.length
                ? items
                    .map(item => `
                        <article class="market-item">

                            <h3>
                                ${escapeHTML(
                                    item.name ||
                                    'Product'
                                )}
                            </h3>

                            <p>
                                ${escapeHTML(
                                    item.description ||
                                    ''
                                )}
                            </p>

                        </article>
                    `)
                    .join('')
                : `
                    <div class="empty-state">

                        <div style="font-size:40px;">
                            🛍️
                        </div>

                        <h3>
                            No items yet
                        </h3>

                        <p>
                            Market items will appear here
                            when sellers publish products.
                        </p>

                    </div>
                `
        );

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}


/* ============================================================
   WORLD MAP
   ============================================================ */

async function openWorldMap() {

    try {

        const result =
            await GET(
                '/api/world-map/countries'
            );

        const countries =
            result?.countries || [];

        openDiscoveryPage(
            'World Map',
            `
                <div class="world-map-placeholder">

                    <div style="font-size:70px;">
                        🌍
                    </div>

                    <h3>
                        MSAFIRI World
                    </h3>

                    <p>
                        Explore users and content
                        around the world.
                    </p>

                </div>

                <div class="option-grid">

                    ${
                        countries
                            .map(country => `
                                <button
                                    data-map-country="${escapeHTML(
                                        country.name
                                    )}"
                                >

                                    🌍
                                    ${escapeHTML(
                                        country.name
                                    )}

                                    <small>
                                        Users:
                                        ${country.users || 0}
                                    </small>

                                    <small>
                                        Posts:
                                        ${country.posts || 0}
                                    </small>

                                </button>
                            `)
                            .join('')
                    }

                </div>
            `
        );

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}


/* ============================================================
   CHANNELS
   ============================================================ */

async function openChannels() {

    try {

        const result =
            await GET(
                '/api/channels'
            );

        const channels =
            result?.channels || [];

        openDiscoveryPage(
            'Channels',
            `
                <div class="channel-list">

                    ${
                        channels
                            .map(channel => `
                                <button
                                    class="channel-item"
                                    data-channel-id="${escapeHTML(
                                        channel.id
                                    )}"
                                >

                                    📺

                                    <strong>
                                        ${escapeHTML(
                                            channel.name
                                        )}
                                    </strong>

                                    <small>
                                        ${escapeHTML(
                                            channel.desc
                                        )}
                                    </small>

                                </button>
                            `)
                            .join('')
                    }

                </div>
            `
        );

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}


/* ============================================================
   COMMUNITIES
   ============================================================ */

async function openCommunities() {

    try {

        const result =
            await GET(
                '/api/communities/categories'
            );

        const categories =
            result?.categories || [];

        openDiscoveryPage(
            'Communities',
            `
                <div class="option-grid">

                    ${
                        categories
                            .map(category => `
                                <button
                                    data-community-category="${escapeHTML(
                                        category.id
                                    )}"
                                >

                                    👥

                                    <strong>
                                        ${escapeHTML(
                                            category.title
                                        )}
                                    </strong>

                                    <small>
                                        ${escapeHTML(
                                            category.desc
                                        )}
                                    </small>

                                </button>
                            `)
                            .join('')
                    }

                </div>
            `
        );

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}


/* ============================================================
   SETTINGS
   ============================================================ */

async function openSettings() {

    try {

        const result =
            await GET(
                '/api/settings'
            );

        openDiscoveryPage(
            'Settings',
            `

                <div class="settings-list">

                    <button
                        data-setting-manual
                    >
                        📖
                        <span>
                            User Manual
                        </span>
                    </button>

                    <button
                        data-setting-theme
                    >
                        🌓
                        <span>
                            Toggle Theme
                        </span>
                    </button>

                    <button>
                        ℹ️
                        <span>
                            Version
                            ${escapeHTML(
                                result?.version ||
                                APP_VERSION
                            )}
                        </span>
                    </button>

                    <button
                        data-setting-logout
                    >
                        🚪
                        <span>
                            Logout
                        </span>
                    </button>

                </div>

            `
        );

        const page =
            byId(
                'discovery-subpage'
            );

        page.querySelector(
            '[data-setting-manual]'
        )?.addEventListener(
            'click',
            openUserManual
        );

        page.querySelector(
            '[data-setting-theme]'
        )?.addEventListener(
            'click',
            toggleTheme
        );

        page.querySelector(
            '[data-setting-logout]'
        )?.addEventListener(
            'click',
            logout
        );

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}


/* ============================================================
   USER MANUAL
   ============================================================ */

async function openUserManual() {

    try {

        const manual =
            await GET(
                '/api/user-manual'
            );

        openDiscoveryPage(
            'User Manual',
            `

                <div class="user-manual">

                    <div class="manual-logo">
                        M
                    </div>

                    <h1>
                        ${escapeHTML(
                            manual.app
                        )}
                    </h1>

                    <p>
                        ${escapeHTML(
                            manual.tagline
                        )}
                    </p>

                    <hr>

                    <h2>
                        About MSAFIRI
                    </h2>

                    <p>
                        ${escapeHTML(
                            manual.about
                        )}
                    </p>

                    <h2>
                        Sections of the App
                    </h2>

                    ${
                        Object.entries(
                            manual.sections || {}
                        )
                        .map(
                            ([key, value]) => `
                                <p>
                                    <strong>
                                        ${escapeHTML(
                                            key
                                        )}
                                    :
                                    </strong>
                                    ${escapeHTML(
                                        value
                                    )}
                                </p>
                            `
                        )
                        .join('')
                    }

                    <h2>
                        How to Use MSAFIRI
                    </h2>

                    ${
                        Object.entries(
                            manual.how_to_use || {}
                        )
                        .map(
                            ([key, value]) => `
                                <p>
                                    <strong>
                                        ${escapeHTML(
                                            key
                                        )}
                                    :
                                    </strong>
                                    ${escapeHTML(
                                        value
                                    )}
                                </p>
                            `
                        )
                        .join('')
                    }

                    <h2>
                        Support
                    </h2>

                    <p>
                        ${escapeHTML(
                            manual.support
                        )}
                    </p>

                    <button
                        id="download-manual"
                    >
                        📥 Download User Manual
                    </button>

                </div>

            `
        );

        byId(
            'download-manual'
        )?.addEventListener(
            'click',
            () => downloadManual(
                manual
            )
        );

    } catch (error) {

        showToast(
            error.message,
            'error'
        );
    }
}

function downloadManual(manual) {

    const text = `
MSAFIRI GLOBAL MEDIA
${manual.tagline}

USER MANUAL

ABOUT MSAFIRI
${manual.about}

SECTIONS OF THE APP

${Object.entries(
    manual.sections || {}
)
.map(
    ([key, value]) =>
        `${key}: ${value}`
)
.join('\n')}

HOW TO USE MSAFIRI

${Object.entries(
    manual.how_to_use || {}
)
.map(
    ([key, value]) =>
        `${key}: ${value}`
)
.join('\n')}

SUPPORT
${manual.support}

Version:
${manual.version}

Founder:
${manual.founder}

Company:
${manual.company}
`.trim();

    const blob =
        new Blob(
            [text],
            {
                type:
                    'text/plain;charset=utf-8'
            }
        );

    const url =
        URL.createObjectURL(
            blob
        );

    const anchor =
        document.createElement('a');

    anchor.href = url;
    anchor.download =
        'MSAFIRI-UserManual.txt';

    document.body.appendChild(
        anchor
    );

    anchor.click();

    anchor.remove();

    URL.revokeObjectURL(
        url
    );

    showToast(
        'User Manual downloaded.',
        'success'
    );
}


/* ============================================================
   THEME
   ============================================================ */

function applyTheme(theme) {

    if (
        theme !== 'light' &&
        theme !== 'dark'
    ) {
        theme = 'dark';
    }

    document.documentElement.dataset.theme =
        theme;

    localStorage.setItem(
        STORAGE.THEME,
        theme
    );

    document.body.classList.toggle(
        'dark-theme',
        theme === 'dark'
    );

    document.body.classList.toggle(
        'light-theme',
        theme === 'light'
    );
}

function toggleTheme() {

    const current =
        localStorage.getItem(
            STORAGE.THEME
        ) || 'dark';

    const next =
        current === 'dark'
            ? 'light'
            : 'dark';

    applyTheme(
        next
    );

    showToast(
        `Theme changed to ${next}.`,
        'success'
    );
}


/* ============================================================
   LOGOUT
   ============================================================ */

async function logout() {

    try {

        await POST(
            '/api/auth/logout'
        );

    } catch {
        /*
           Logout endpoint may not exist.
           Local logout still proceeds.
        */
    }

    clearAuth();

    showToast(
        'Logged out.',
        'success'
    );

    setView(
        'home'
    );

    setTimeout(
        () => {
            window.location.reload();
        },
        500
    );
}


/* ============================================================
   AUTH FORM HANDLING
   ============================================================ */

async function handleLogin(form) {

    const username =
        form.querySelector(
            '[name="username"]'
        )?.value?.trim();

    const email =
        form.querySelector(
            '[name="email"]'
        )?.value?.trim();

    const password =
        form.querySelector(
            '[name="password"]'
        )?.value || '';

    if (!password) {

        showToast(
            'Password is required.',
            'error'
        );

        return;
    }

    /*
       Support common OAuth2-style login.
    */

    const data =
        new URLSearchParams();

    data.append(
        'username',
        username || email || ''
    );

    data.append(
        'password',
        password
    );

    try {

        const result =
            await apiRequest(
                '/api/auth/login',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type':
                            'application/x-www-form-urlencoded'
                    },
                    body: data
                }
            );

        const token =
            result?.access_token ||
            result?.token ||
            result?.accessToken;

        if (!token) {

            throw new Error(
                'Login succeeded but no access token was returned.'
            );
        }

        setAuth(
            token,
            result?.user || null
        );

        showToast(
            'Login successful.',
            'success'
        );

        setView(
            'home'
        );

    } catch (error) {

        showToast(
            error.message ||
            'Login failed.',
            'error'
        );
    }
}


/* ============================================================
   REGISTER
   ============================================================ */

async function handleRegister(form) {

    const payload = {

        username:
            form.querySelector(
                '[name="username"]'
            )?.value?.trim(),

        email:
            form.querySelector(
                '[name="email"]'
            )?.value?.trim(),

        password:
            form.querySelector(
                '[name="password"]'
            )?.value || '',

        full_name:
            form.querySelector(
                '[name="full_name"]'
            )?.value?.trim() || ''

    };

    if (
        !payload.username ||
        !payload.email ||
        !payload.password
    ) {

        showToast(
            'Username, email and password are required.',
            'error'
        );

        return;
    }

    try {

        const result =
            await POST(
                '/api/auth/register',
                payload
            );

        showToast(
            result?.message ||
            'Account created successfully.',
            'success'
        );

        const token =
            result?.access_token ||
            result?.token;

        if (token) {

            setAuth(
                token,
                result?.user || null
            );

            setView(
                'home'
            );
        }

    } catch (error) {

        showToast(
            error.message ||
            'Registration failed.',
            'error'
        );
    }
}


/* ============================================================
   SEARCH BAR
   ============================================================ */

function setupSearch() {

    const inputs =
        $$(
            '[data-user-search], #user-search, #search-input'
        );

    inputs.forEach(input => {

        let timeout = null;

        input.addEventListener(
            'input',
            () => {

                clearTimeout(
                    timeout
                );

                const value =
                    input.value.trim();

                timeout =
                    setTimeout(
                        () => {

                            if (value) {
                                searchUsers(
                                    value
                                );
                            } else {
                                renderSearchResults(
                                    []
                                );
                            }

                        },
                        350
                    );
            }
        );

        input.addEventListener(
            'keydown',
            event => {

                if (
                    event.key === 'Enter'
                ) {

                    event.preventDefault();

                    searchUsers(
                        input.value
                    );
                }
            }
        );
    });
}


/* ============================================================
   BOTTOM NAVIGATION
   ============================================================ */

function setupNavigation() {

    $$(
        '[data-view]'
    ).forEach(button => {

        button.addEventListener(
            'click',
            () => {

                const view =
                    button.dataset.view;

                if (view) {
                    setView(
                        view
                    );
                }
            }
        );
    });

    $$(
        '[data-nav-home]'
    ).forEach(button => {

        button.onclick =
            () => setView('home');
    });

    $$(
        '[data-nav-discovery]'
    ).forEach(button => {

        button.onclick =
            () => setView(
                'discovery'
            );
    });

    $$(
        '[data-nav-chats]'
    ).forEach(button => {

        button.onclick =
            () => setView('chats');
    });

    $$(
        '[data-nav-profile]'
    ).forEach(button => {

        button.onclick =
            () => setView('profile');
    });

    $$(
        '[data-create-post]'
    ).forEach(button => {

        button.onclick =
            openCreatePost;
    });

    $$(
        '#create-button, #post-button'
    ).forEach(button => {

        button.onclick =
            openCreatePost;
    });
}


/* ============================================================
   3-DOTS MENU
   ============================================================ */

function setupThreeDots() {

    $$(
        '[data-menu], #three-dots, #more-menu'
    ).forEach(button => {

        button.addEventListener(
            'click',
            openMainMenu
        );
    });
}

function openMainMenu() {

    let menu =
        byId('msafiri-main-menu');

    if (!menu) {

        menu =
            document.createElement('div');

        menu.id =
            'msafiri-main-menu';

        menu.className =
            'msafiri-menu';

        menu.innerHTML = `

            <button data-main-manual>
                📖 User Manual
            </button>

            <button data-main-settings>
                ⚙️ Settings
            </button>

            <button data-main-theme>
                🌓 Toggle Theme
            </button>

            <button data-main-logout>
                🚪 Logout
            </button>

        `;

        document.body.appendChild(
            menu
        );

        menu.querySelector(
            '[data-main-manual]'
        ).onclick =
            openUserManual;

        menu.querySelector(
            '[data-main-settings]'
        ).onclick =
            openSettings;

        menu.querySelector(
            '[data-main-theme]'
        ).onclick =
            toggleTheme;

        menu.querySelector(
            '[data-main-logout]'
        ).onclick =
            logout;
    }

    menu.hidden =
        !menu.hidden;
}


/* ============================================================
   STORY / STATUS
   ============================================================ */

async function loadStories() {

    const container =
        byId('stories') ||
        document.querySelector(
            '[data-stories]'
        );

    if (!container) {
        return;
    }

    const endpoints = [
        '/api/stories',
        '/api/statuses'
    ];

    for (const endpoint of endpoints) {

        try {

            const result =
                await GET(
                    endpoint
                );

            const stories =
                result?.stories ||
                result?.statuses ||
                [];

            renderStories(
                stories,
                container
            );

            return;

        } catch (error) {

            if (
                error.status !== 404 &&
                error.status !== 405
            ) {
                console.warn(
                    error
                );
            }
        }
    }

    renderStories(
        [],
        container
    );
}

function renderStories(
    stories,
    container
) {

    container.innerHTML = `

        <div class="story-add"
             data-story-create>

            <div class="story-avatar">
                +
            </div>

            <span>
                My Story
            </span>

        </div>

        ${
            stories
                .map(story => `
                    <button
                        class="story-item"
                        data-story-id="${escapeHTML(
                            story.id
                        )}"
                    >

                        <div class="story-avatar">
                            ${
                                story.media_url
                                    ? `<img
                                        src="${escapeHTML(
                                            absoluteURL(
                                                story.media_url
                                            )
                                        )}"
                                        alt=""
                                      >`
                                    : '👤'
                            }
                        </div>

                        <span>
                            ${escapeHTML(
                                story.username ||
                                'User'
                            )}
                        </span>

                    </button>
                `)
                .join('')
        }

    `;

    container.querySelector(
        '[data-story-create]'
    )?.addEventListener(
        'click',
        () => {

            showToast(
                'Story creator will be connected to the status upload route.',
                'info'
            );
        }
    );
}


/* ============================================================
   HEALTH CHECK
   ============================================================ */

async function checkServer() {

    try {

        const result =
            await GET(
                '/api/health'
            );

        console.log(
            `${APP_NAME} server:`,
            result
        );

        document.body.dataset.server =
            'online';

        return true;

    } catch (error) {

        console.warn(
            'Server health check failed:',
            error
        );

        document.body.dataset.server =
            'offline';

        return false;
    }
}


/* ============================================================
   EMPTY STATE
   ============================================================ */

function emptyState(message) {

    return `
        <div class="empty-state">

            <div style="font-size:42px;">
                🌍
            </div>

            <p>
                ${escapeHTML(
                    message
                )}
            </p>

        </div>
    `;
}


/* ============================================================
   GLOBAL CLICK HANDLER
   ============================================================ */

document.addEventListener(
    'click',
    event => {

        const target =
            event.target.closest(
                '[data-action]'
            );

        if (!target) {
            return;
        }

        const action =
            target.dataset.action;

        switch (action) {

            case 'home':
                setView('home');
                break;

            case 'discovery':
                setView('discovery');
                break;

            case 'chats':
                setView('chats');
                break;

            case 'profile':
                setView('profile');
                break;

            case 'create-post':
                openCreatePost();
                break;

            case 'logout':
                logout();
                break;

            case 'theme':
                toggleTheme();
                break;

            case 'manual':
                openUserManual();
                break;

            default:
                break;
        }
    }
);


/* ============================================================
   FORM AUTO-DETECTION
   ============================================================ */

document.addEventListener(
    'submit',
    event => {

        const form =
            event.target;

        if (!(form instanceof HTMLFormElement)) {
            return;
        }

        if (
            form.matches(
                '#login-form, [data-login-form]'
            )
        ) {

            event.preventDefault();

            handleLogin(
                form
            );

            return;
        }

        if (
            form.matches(
                '#register-form, [data-register-form]'
            )
        ) {

            event.preventDefault();

            handleRegister(
                form
            );

            return;
        }

        if (
            form.matches(
                '#create-post-form, [data-create-post-form]'
            )
        ) {

            event.preventDefault();

            createPost(
                form
            );
        }
    }
);


/* ============================================================
   INITIALIZATION
   ============================================================ */

async function initializeApp() {

    console.log(
        '================================================'
    );

    console.log(
        `${APP_NAME} ${APP_VERSION}`
    );

    console.log(
        APP_TAGLINE
    );

    console.log(
        'Initializing application...'
    );

    console.log(
        '================================================'
    );

    applyTheme(
        localStorage.getItem(
            STORAGE.THEME
        ) || 'dark'
    );

    updateAuthUI();

    setupNavigation();

    setupSearch();

    setupThreeDots();

    await checkServer();

    if (CURRENT_VIEW === 'home') {

        await loadFeed();

        await loadStories();

    } else {

        setView(
            CURRENT_VIEW
        );
    }

    console.log(
        'MSAFIRI GLOBAL MEDIA initialized successfully.'
    );
}


/* ============================================================
   DOM READY
   ============================================================ */

if (
    document.readyState === 'loading'
) {

    document.addEventListener(
        'DOMContentLoaded',
        initializeApp
    );

} else {

    initializeApp();
}


/* ============================================================
   GLOBAL API
   ------------------------------------------------------------
   Useful if index.html has inline buttons or other scripts.
   ============================================================ */

window.MSAFIRI = {

    API,

    APP_NAME,

    APP_VERSION,

    getToken: () =>
        TOKEN,

    getCurrentUser: () =>
        CURRENT_USER,

    isLoggedIn,

    setView,

    loadFeed,

    loadStories,

    loadChats,

    searchUsers,

    openProfile,

    openChatWithUser,

    openCreatePost,

    openAICouncil,

    openStudio,

    openMarket,

    openWorldMap,

    openChannels,

    openCommunities,

    openSettings,

    openUserManual,

    toggleTheme,

    logout,

    createPost,

    toggleLike,

    toggleSave,

    sharePost,

    openComments,

    checkServer

};
