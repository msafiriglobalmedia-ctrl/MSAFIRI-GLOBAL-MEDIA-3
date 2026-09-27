/* ============================================================
   MSAFIRI GLOBAL MEDIA
   APP.JS — STABLE FRONTEND
   Compatible with supplied:
   - index.html
   - style.css
   - /api/health
   - /api/feed
   - /api/posts/*
   - /api/profile/*
   - /api/messages
   ============================================================ */

'use strict';

/* ============================================================
   CONFIG
   ============================================================ */

const API = window.location.origin;

const STORAGE = {
    TOKEN: 'msafiri_token',
    USER: 'msafiri_user',
    THEME: 'msafiri_theme'
};

const ENDPOINTS = {
    health: '/api/health',
    feed: '/api/feed',
    messages: '/api/messages',
    posts: '/api/posts',
    profile: '/api/profile'
};

let TOKEN = localStorage.getItem(STORAGE.TOKEN) || '';
let CURRENT_USER = safeJSONParse(
    localStorage.getItem(STORAGE.USER)
) || null;

let CURRENT_VIEW = 'home';
let CURRENT_FEED = 'for-you';
let CACHED_POSTS = [];
let CACHED_CHATS = [];
let CURRENT_CHAT = null;
let SEARCH_TIMER = null;
let SPLASH_FINISHED = false;

/* ============================================================
   DOM HELPERS
   ============================================================ */

const $ = (selector) => {
    try {
        return document.querySelector(selector);
    } catch {
        return null;
    }
};

const $$ = (selector) => {
    try {
        return Array.from(document.querySelectorAll(selector));
    } catch {
        return [];
    }
};

function byId(id) {
    return document.getElementById(id);
}

function safeJSONParse(value) {
    if (!value) return null;

    try {
        return JSON.parse(value);
    } catch {
        return null;
    }
}

function escapeHTML(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function initials(name) {
    const text = String(name || 'M').trim();

    if (!text) return 'M';

    return text
        .split(/\s+/)
        .slice(0, 2)
        .map(part => part.charAt(0))
        .join('')
        .toUpperCase();
}

function absoluteURL(url) {
    if (!url) return '';

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

function formatDate(dateValue) {
    if (!dateValue) return '';

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
        return '';
    }

    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d`;

    return date.toLocaleDateString();
}

/* ============================================================
   TOAST
   ============================================================ */

function showToast(message, duration = 2600) {
    if (!message) return;

    const old = byId('msafiri-toast');

    if (old) {
        old.remove();
    }

    const toast = document.createElement('div');

    toast.id = 'msafiri-toast';
    toast.className = 'toast';
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, duration);
}

/* ============================================================
   API REQUEST
   ============================================================ */

async function apiRequest(
    path,
    options = {},
    allow401 = false
) {
    const config = {
        method: options.method || 'GET',
        headers: {
            ...(options.headers || {})
        }
    };

    if (TOKEN) {
        config.headers.Authorization = `Bearer ${TOKEN}`;
    }

    if (
        options.body &&
        !(options.body instanceof FormData) &&
        !(options.body instanceof Blob)
    ) {
        config.headers['Content-Type'] =
            'application/json';

        config.body = JSON.stringify(options.body);
    } else if (options.body) {
        config.body = options.body;
    }

    let response;

    try {
        response = await fetch(
            `${API}${path}`,
            config
        );
    } catch (error) {
        console.error('Network error:', error);

        throw new Error(
            'Unable to connect to the server.'
        );
    }

    const text = await response.text();

    let data = {};

    if (text) {
        try {
            data = JSON.parse(text);
        } catch {
            data = {
                raw: text
            };
        }
    }

    if (response.status === 401 && !allow401) {
        clearSession();
        showAuth();
        throw new Error('Session expired.');
    }

    if (!response.ok) {
        const detail =
            data?.detail ||
            data?.message ||
            data?.error ||
            `Request failed (${response.status})`;

        throw new Error(detail);
    }

    return data;
}

/* ============================================================
   SESSION
   ============================================================ */

function saveSession(token, user) {
    TOKEN = token || '';

    CURRENT_USER = user || null;

    if (TOKEN) {
        localStorage.setItem(
            STORAGE.TOKEN,
            TOKEN
        );
    }

    if (CURRENT_USER) {
        localStorage.setItem(
            STORAGE.USER,
            JSON.stringify(CURRENT_USER)
        );
    }
}

function clearSession() {
    TOKEN = '';
    CURRENT_USER = null;

    localStorage.removeItem(STORAGE.TOKEN);
    localStorage.removeItem(STORAGE.USER);
}

/* ============================================================
   SPLASH
   ============================================================ */

function finishSplash() {
    if (SPLASH_FINISHED) return;

    SPLASH_FINISHED = true;

    const splash = byId('splash');

    if (!splash) {
        bootApplication();
        return;
    }

    splash.style.pointerEvents = 'none';
    splash.style.opacity = '0';
    splash.style.visibility = 'hidden';

    setTimeout(() => {
        splash.classList.add('hidden');
        bootApplication();
    }, 650);
}

/* ============================================================
   AUTH / APP VISIBILITY
   ============================================================ */

function showAuth() {
    const auth = byId('auth-screen');
    const app = byId('app');

    if (auth) {
        auth.classList.remove('hidden');
    }

    if (app) {
        app.classList.add('hidden');
    }
}

function showApp() {
    const auth = byId('auth-screen');
    const app = byId('app');

    if (auth) {
        auth.classList.add('hidden');
    }

    if (app) {
        app.classList.remove('hidden');
    }
}

function bootApplication() {
    try {
        if (TOKEN) {
            showApp();
            navigate('home');
            loadHome();
        } else {
            showAuth();
        }
    } catch (error) {
        console.error(
            'Application boot error:',
            error
        );

        showAuth();
    }
}

/* ============================================================
   AUTH TABS
   ============================================================ */

function setupAuthTabs() {
    $$('.auth-tab').forEach(button => {
        button.addEventListener(
            'click',
            () => {
                const tab =
                    button.dataset.tab;

                $$('.auth-tab').forEach(btn => {
                    btn.classList.toggle(
                        'active',
                        btn === button
                    );
                });

                const loginForm =
                    byId('login-form');

                const registerForm =
                    byId('register-form');

                if (loginForm) {
                    loginForm.classList.toggle(
                        'hidden',
                        tab !== 'login'
                    );
                }

                if (registerForm) {
                    registerForm.classList.toggle(
                        'hidden',
                        tab !== 'register'
                    );
                }
            }
        );
    });
}

/* ============================================================
   LOGIN
   ============================================================ */

async function login() {
    const username =
        byId('login-username')?.value.trim();

    const password =
        byId('login-password')?.value || '';

    if (!username || !password) {
        showToast(
            'Please enter username/email and password.'
        );

        return;
    }

    const button =
        $('#login-form button[type="submit"]');

    setButtonLoading(button, true);

    try {
        /*
         * Supports common FastAPI OAuth login.
         */

        const body =
            new URLSearchParams();

        body.append(
            'username',
            username
        );

        body.append(
            'password',
            password
        );

        let data;

        try {
            data = await apiRequest(
                '/api/auth/login',
                {
                    method: 'POST',
                    body
                },
                true
            );
        } catch (firstError) {
            /*
             * Some backends use /api/login.
             */

            data = await apiRequest(
                '/api/login',
                {
                    method: 'POST',
                    body
                },
                true
            );
        }

        const token =
            data?.access_token ||
            data?.token ||
            data?.data?.access_token ||
            '';

        const user =
            data?.user ||
            data?.data?.user ||
            null;

        if (!token) {
            throw new Error(
                data?.detail ||
                'Login succeeded but no token was returned.'
            );
        }

        saveSession(token, user);

        showApp();
        navigate('home');

        await loadHome();

        showToast('Welcome back!');
    } catch (error) {
        console.error('Login error:', error);

        showToast(
            error.message ||
            'Login failed.'
        );
    } finally {
        setButtonLoading(button, false);
    }
}

/* ============================================================
   REGISTER
   ============================================================ */

async function register() {
    const username =
        byId('reg-username')?.value.trim();

    const email =
        byId('reg-email')?.value.trim();

    const fullName =
        byId('reg-fullname')?.value.trim();

    const password =
        byId('reg-password')?.value || '';

    if (
        !username ||
        !email ||
        !fullName ||
        !password
    ) {
        showToast(
            'Please complete all registration fields.'
        );

        return;
    }

    const button =
        $('#register-form button[type="submit"]');

    setButtonLoading(button, true);

    try {
        const data =
            await apiRequest(
                '/api/auth/register',
                {
                    method: 'POST',
                    body: {
                        username,
                        email,
                        full_name: fullName,
                        password
                    }
                },
                true
            );

        const token =
            data?.access_token ||
            data?.token ||
            data?.data?.access_token;

        const user =
            data?.user ||
            data?.data?.user ||
            null;

        if (token) {
            saveSession(
                token,
                user
            );

            showApp();
            navigate('home');

            await loadHome();

            showToast(
                'Account created successfully.'
            );
        } else {
            showToast(
                'Account created. Please login.'
            );

            const loginTab =
                $('.auth-tab[data-tab="login"]');

            if (loginTab) {
                loginTab.click();
            }
        }
    } catch (error) {
        console.error(
            'Register error:',
            error
        );

        showToast(
            error.message ||
            'Registration failed.'
        );
    } finally {
        setButtonLoading(
            button,
            false
        );
    }
}

/* ============================================================
   BUTTON LOADING
   ============================================================ */

function setButtonLoading(
    button,
    loading
) {
    if (!button) return;

    if (loading) {
        button.dataset.originalText =
            button.textContent;

        button.disabled = true;
        button.textContent = 'Please wait...';
    } else {
        button.disabled = false;

        if (
            button.dataset.originalText
        ) {
            button.textContent =
                button.dataset.originalText;
        }
    }
}

/* ============================================================
   NAVIGATION
   ============================================================ */

function navigate(view) {
    const validViews = [
        'home',
        'discovery',
        'chats',
        'profile'
    ];

    if (!validViews.includes(view)) {
        view = 'home';
    }

    CURRENT_VIEW = view;

    $$('.page').forEach(page => {
        page.classList.remove('active');
    });

    const target =
        byId(`page-${view}`);

    if (target) {
        target.classList.add('active');
    }

    $$('.nav-btn').forEach(button => {
        button.classList.toggle(
            'active',
            button.dataset.nav === view
        );
    });

    const title =
        byId('page-title');

    if (title) {
        const titles = {
            home: 'MSAFIRI',
            discovery: 'Discovery',
            chats: 'Chats',
            profile: 'Profile'
        };

        title.textContent =
            titles[view];
    }

    const backButton =
        byId('back-btn');

    if (backButton) {
        backButton.classList.add('hidden');
    }

    if (view === 'home') {
        loadHome();
    }

    if (view === 'discovery') {
        loadDiscovery();
    }

    if (view === 'chats') {
        loadChats();
    }

    if (view === 'profile') {
        loadProfile();
    }
}

/* ============================================================
   FEED
   ============================================================ */

async function loadHome() {
    const feed =
        byId('feed');

    if (!feed) return;

    renderFeedLoading(feed);

    try {
        const data =
            await apiRequest(
                ENDPOINTS.feed
            );

        const posts =
            extractPosts(data);

        CACHED_POSTS = posts;

        renderFeed(
            feed,
            posts
        );
    } catch (error) {
        console.error(
            'Feed error:',
            error
        );

        feed.innerHTML = `
            <div class="sub-item">
                <div class="icon">📡</div>
                <div class="text">
                    <strong>Unable to load feed</strong>
                    <span>${escapeHTML(error.message)}</span>
                </div>
            </div>
        `;
    }
}

function renderFeedLoading(feed) {
    feed.innerHTML = `
        <div class="sub-item">
            <div class="icon">⏳</div>
            <div class="text">
                <strong>Loading feed...</strong>
                <span>Please wait.</span>
            </div>
        </div>
    `;
}

function extractPosts(data) {
    if (Array.isArray(data)) {
        return data;
    }

    if (Array.isArray(data?.posts)) {
        return data.posts;
    }

    if (Array.isArray(data?.feed)) {
        return data.feed;
    }

    if (Array.isArray(data?.items)) {
        return data.items;
    }

    if (Array.isArray(data?.data)) {
        return data.data;
    }

    return [];
}

/* ============================================================
   RENDER FEED
   ============================================================ */

function renderFeed(
    container,
    posts
) {
    if (!container) return;

    if (!posts.length) {
        container.innerHTML = `
            <div class="sub-item">
                <div class="icon">🌍</div>
                <div class="text">
                    <strong>No posts yet</strong>
                    <span>Create the first post on MSAFIRI GLOBAL MEDIA.</span>
                </div>
            </div>
        `;

        return;
    }

    container.innerHTML =
        posts.map(
            renderPost
        ).join('');
}

function renderPost(post) {
    const name =
        post.full_name ||
        post.username ||
        'MSAFIRI USER';

    const username =
        post.username ||
        'user';

    const avatar =
        post.avatar_url;

    const mediaURL =
        absoluteURL(
            post.media_url
        );

    let mediaHTML = '';

    if (
        mediaURL &&
        post.media_type === 'image'
    ) {
        mediaHTML = `
            <img
                class="post-media"
                src="${escapeHTML(mediaURL)}"
                alt="Post image"
                loading="lazy"
                onerror="this.style.display='none'"
            >
        `;
    }

    if (
        mediaURL &&
        post.media_type === 'video'
    ) {
        mediaHTML = `
            <video
                class="post-media"
                src="${escapeHTML(mediaURL)}"
                controls
                playsinline
                preload="metadata"
            ></video>
        `;
    }

    const avatarHTML =
        avatar
            ? `
                <img
                    class="post-avatar"
                    src="${escapeHTML(absoluteURL(avatar))}"
                    alt=""
                    style="object-fit:cover"
                >
              `
            : `
                <div class="post-avatar">
                    ${escapeHTML(initials(name))}
                </div>
              `;

    return `
        <article
            class="post-card"
            data-post-id="${Number(post.id) || 0}"
        >

            <div class="post-header">

                ${avatarHTML}

                <div class="post-user">
                    <strong>
                        ${escapeHTML(name)}
                    </strong>

                    <span>
                        @${escapeHTML(username)}
                        ${post.created_at
                            ? ` · ${escapeHTML(formatDate(post.created_at))}`
                            : ''
                        }
                    </span>
                </div>

            </div>

            ${
                post.caption
                    ? `
                        <div class="post-caption">
                            ${escapeHTML(post.caption)}
                        </div>
                      `
                    : ''
            }

            ${mediaHTML}

            <div class="post-actions">

                <button
                    type="button"
                    data-post-action="like"
                    data-post-id="${Number(post.id)}"
                    class="${post.liked ? 'liked' : ''}"
                >
                    ❤️ ${Number(post.likes) || 0}
                </button>

                <button
                    type="button"
                    data-post-action="comment"
                    data-post-id="${Number(post.id)}"
                >
                    💬 ${Number(post.comments) || 0}
                </button>

                <button
                    type="button"
                    data-post-action="save"
                    data-post-id="${Number(post.id)}"
                >
                    🔖 ${Number(post.saves) || 0}
                </button>

                <button
                    type="button"
                    data-post-action="share"
                    data-post-id="${Number(post.id)}"
                >
                    ↗️ ${Number(post.shares) || 0}
                </button>

            </div>

        </article>
    `;
}

/* ============================================================
   POST ACTIONS
   ============================================================ */

async function handlePostAction(
    action,
    postId
) {
    if (!postId) return;

    try {
        let data;

        if (action === 'like') {
            data = await apiRequest(
                `${ENDPOINTS.posts}/${postId}/like`,
                {
                    method: 'POST'
                }
            );

            updatePostCounts(
                postId,
                data
            );

            return;
        }

        if (action === 'save') {
            data = await apiRequest(
                `${ENDPOINTS.posts}/${postId}/save`,
                {
                    method: 'POST'
                }
            );

            updatePostCounts(
                postId,
                data
            );

            return;
        }

        if (action === 'share') {
            data = await apiRequest(
                `${ENDPOINTS.posts}/${postId}/share`,
                {
                    method: 'POST'
                }
            );

            updatePostCounts(
                postId,
                data
            );

            showToast(
                'Post shared successfully.'
            );

            return;
        }

        if (action === 'comment') {
            openCommentModal(
                postId
            );

            return;
        }
    } catch (error) {
        console.error(
            'Post action error:',
            error
        );

        showToast(
            error.message ||
            'Action failed.'
        );
    }
}

function updatePostCounts(
    postId,
    data
) {
    const card =
        document.querySelector(
            `.post-card[data-post-id="${CSS.escape(String(postId))}"]`
        );

    if (!card) return;

    const buttons =
        card.querySelectorAll(
            '[data-post-action]'
        );

    buttons.forEach(button => {
        const action =
            button.dataset.postAction;

        if (
            action === 'like' &&
            data.likes !== undefined
        ) {
            button.textContent =
                `❤️ ${data.likes}`;

            button.classList.toggle(
                'liked',
                Boolean(data.liked)
            );
        }

        if (
            action === 'save' &&
            data.saves !== undefined
        ) {
            button.textContent =
                `🔖 ${data.saves}`;
        }

        if (
            action === 'share' &&
            data.shares !== undefined
        ) {
            button.textContent =
                `↗️ ${data.shares}`;
        }
    });
}

/* ============================================================
   COMMENTS
   ============================================================ */

async function openCommentModal(
    postId
) {
    const body =
        byId('modal-body');

    if (!body) return;

    openModal();

    body.innerHTML = `
        <h2>Comments</h2>
        <div id="comments-list">
            <div class="sub-item">
                Loading comments...
            </div>
        </div>

        <form id="comment-form"
              style="margin-top:16px;display:flex;gap:8px;">

            <input
                id="comment-input"
                type="text"
                placeholder="Write a comment..."
                required
                style="
                    flex:1;
                    padding:12px;
                    border-radius:10px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                    outline:none;
                "
            >

            <button
                type="submit"
                class="btn-primary"
            >
                Send
            </button>

        </form>
    `;

    try {
        const data =
            await apiRequest(
                `${ENDPOINTS.posts}/${postId}/comments`
            );

        const comments =
            Array.isArray(data?.comments)
                ? data.comments
                : [];

        const list =
            byId('comments-list');

        if (!list) return;

        if (!comments.length) {
            list.innerHTML = `
                <div class="sub-item">
                    No comments yet.
                </div>
            `;
        } else {
            list.innerHTML =
                comments.map(
                    comment => `
                        <div class="sub-item">
                            <div class="icon">
                                ${escapeHTML(
                                    initials(
                                        comment.full_name ||
                                        comment.username
                                    )
                                )}
                            </div>

                            <div class="text">
                                <strong>
                                    ${escapeHTML(
                                        comment.full_name ||
                                        comment.username ||
                                        'User'
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        comment.text
                                    )}
                                </span>
                            </div>
                        </div>
                    `
                ).join('');
        }
    } catch (error) {
        console.error(error);

        const list =
            byId('comments-list');

        if (list) {
            list.innerHTML = `
                <div class="sub-item">
                    Unable to load comments.
                </div>
            `;
        }
    }

    const form =
        byId('comment-form');

    if (form) {
        form.addEventListener(
            'submit',
            async event => {
                event.preventDefault();

                const input =
                    byId('comment-input');

                const text =
                    input?.value.trim();

                if (!text) return;

                const formData =
                    new FormData();

                formData.append(
                    'text',
                    text
                );

                try {
                    await apiRequest(
                        `${ENDPOINTS.posts}/${postId}/comments`,
                        {
                            method: 'POST',
                            body: formData
                        }
                    );

                    showToast(
                        'Comment added.'
                    );

                    closeModal();

                    await loadHome();
                } catch (error) {
                    showToast(
                        error.message ||
                        'Unable to comment.'
                    );
                }
            }
        );
    }
}

/* ============================================================
   CREATE POST
   ============================================================ */

function openCreatePost() {
    const body =
        byId('modal-body');

    if (!body) return;

    openModal();

    body.innerHTML = `
        <h2>Create Post</h2>

        <form id="create-post-form">

            <textarea
                id="create-caption"
                placeholder="What's happening?"
                rows="5"
                style="
                    width:100%;
                    resize:vertical;
                    padding:14px;
                    border-radius:12px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                    outline:none;
                    margin-bottom:12px;
                    font-family:inherit;
                "
            ></textarea>

            <input
                id="create-media"
                type="file"
                accept="image/*,video/*"
                style="margin-bottom:16px;width:100%;"
            >

            <button
                type="submit"
                class="btn-primary"
                style="width:100%;"
            >
                Publish Post
            </button>

        </form>
    `;

    const form =
        byId('create-post-form');

    if (!form) return;

    form.addEventListener(
        'submit',
        async event => {
            event.preventDefault();

            const caption =
                byId('create-caption')?.value.trim() ||
                '';

            const file =
                byId('create-media')?.files?.[0] ||
                null;

            if (!caption && !file) {
                showToast(
                    'Write something or choose media.'
                );

                return;
            }

            const formData =
                new FormData();

            formData.append(
                'caption',
                caption
            );

            if (file) {
                formData.append(
                    'media',
                    file
                );
            }

            const submit =
                form.querySelector(
                    'button[type="submit"]'
                );

            setButtonLoading(
                submit,
                true
            );

            try {
                await apiRequest(
                    `${ENDPOINTS.posts}/create`,
                    {
                        method: 'POST',
                        body: formData
                    }
                );

                closeModal();

                showToast(
                    'Post published!'
                );

                await loadHome();
            } catch (error) {
                console.error(
                    error
                );

                showToast(
                    error.message ||
                    'Unable to publish post.'
                );
            } finally {
                setButtonLoading(
                    submit,
                    false
                );
            }
        }
    );
}

/* ============================================================
   DISCOVERY
   ============================================================ */

function loadDiscovery() {
    const grid =
        byId('discovery-grid');

    if (!grid) return;

    const cards = [
        {
            icon: '👥',
            title: 'People',
            desc: 'Discover people on MSAFIRI.'
        },
        {
            icon: '🔥',
            title: 'Trending',
            desc: 'See what is getting attention.'
        },
        {
            icon: '🎬',
            title: 'Media',
            desc: 'Explore photos and videos.'
        },
        {
            icon: '🌍',
            title: 'Global',
            desc: 'Connect beyond borders.'
        },
        {
            icon: '🤖',
            title: 'AI',
            desc: 'AI features are coming.'
        },
        {
            icon: '🛍️',
            title: 'MSAFIRI MARKET',
            desc: 'Marketplace coming soon.'
        }
    ];

    grid.innerHTML =
        cards.map(card => `
            <div class="disc-card">
                <span class="icon">
                    ${card.icon}
                </span>

                <div class="title">
                    ${escapeHTML(card.title)}
                </div>

                <div class="desc">
                    ${escapeHTML(card.desc)}
                </div>
            </div>
        `).join('');
}

/* ============================================================
   CHATS
   ============================================================ */

async function loadChats() {
    const list =
        byId('chat-list');

    if (!list) return;

    list.innerHTML = `
        <div class="sub-item">
            <div class="icon">💬</div>
            <div class="text">
                <strong>Loading chats...</strong>
                <span>Please wait.</span>
            </div>
        </div>
    `;

    try {
        const data =
            await apiRequest(
                ENDPOINTS.messages
            );

        const chats =
            Array.isArray(data?.chats)
                ? data.chats
                : Array.isArray(data)
                    ? data
                    : [];

        CACHED_CHATS = chats;

        renderChats(
            list,
            chats
        );
    } catch (error) {
        console.error(
            'Chats error:',
            error
        );

        list.innerHTML = `
            <div class="sub-item">
                <div class="icon">💬</div>
                <div class="text">
                    <strong>No chats yet</strong>
                    <span>
                        Messaging backend is ready to grow.
                    </span>
                </div>
            </div>
        `;
    }
}

function renderChats(
    container,
    chats
) {
    if (!chats.length) {
        container.innerHTML = `
            <div class="sub-item">
                <div class="icon">💬</div>
                <div class="text">
                    <strong>No conversations</strong>
                    <span>
                        Start connecting with people.
                    </span>
                </div>
            </div>
        `;

        return;
    }

    container.innerHTML =
        chats.map(
            chat => {
                const name =
                    chat.full_name ||
                    chat.username ||
                    chat.name ||
                    'User';

                const avatar =
                    chat.avatar_url ||
                    chat.avatar ||
                    '';

                const last =
                    chat.last_message ||
                    chat.message ||
                    'No messages yet';

                return `
                    <div
                        class="chat-item"
                        data-chat-id="${escapeHTML(
                            chat.id ??
                            chat.user_id ??
                            ''
                        )}"
                    >

                        ${
                            avatar
                                ? `
                                    <img
                                        class="chat-avatar"
                                        src="${escapeHTML(
                                            absoluteURL(avatar)
                                        )}"
                                        alt=""
                                        style="object-fit:cover"
                                    >
                                  `
                                : `
                                    <div class="chat-avatar">
                                        ${escapeHTML(
                                            initials(name)
                                        )}
                                    </div>
                                  `
                        }

                        <div class="chat-info">
                            <strong>
                                ${escapeHTML(name)}
                            </strong>

                            <span>
                                ${escapeHTML(last)}
                            </span>
                        </div>

                    </div>
                `;
            }
        ).join('');
}

/* ============================================================
   PROFILE
   ============================================================ */

async function loadProfile() {
    if (!CURRENT_USER) {
        showAuth();
        return;
    }

    const name =
        CURRENT_USER.full_name ||
        CURRENT_USER.username ||
        'User';

    const username =
        CURRENT_USER.username ||
        'user';

    const avatar =
        CURRENT_USER.avatar_url ||
        '';

    const profileName =
        byId('profile-name');

    const profileUsername =
        byId('profile-username');

    const profileBio =
        byId('profile-bio');

    const profileAvatar =
        byId('profile-avatar');

    if (profileName) {
        profileName.textContent =
            name;
    }

    if (profileUsername) {
        profileUsername.textContent =
            `@${username}`;
    }

    if (profileBio) {
        profileBio.textContent =
            CURRENT_USER.bio ||
            'Welcome to Msafiri';
    }

    if (profileAvatar) {
        if (avatar) {
            profileAvatar.innerHTML = `
                <img
                    src="${escapeHTML(
                        absoluteURL(avatar)
                    )}"
                    alt=""
                    style="
                        width:100%;
                        height:100%;
                        object-fit:cover;
                        border-radius:50%;
                    "
                >
            `;
        } else {
            profileAvatar.textContent =
                initials(name);
        }
    }

    const id =
        CURRENT_USER.id;

    if (!id) return;

    try {
        const data =
            await apiRequest(
                `${ENDPOINTS.profile}/${id}`
            );

        const user =
            data?.user ||
            data;

        if (user) {
            CURRENT_USER = {
                ...CURRENT_USER,
                ...user
            };

            localStorage.setItem(
                STORAGE.USER,
                JSON.stringify(
                    CURRENT_USER
                )
            );

            updateProfileUI(
                CURRENT_USER
            );
        }
    } catch (error) {
        console.warn(
            'Profile refresh:',
            error.message
        );
    }
}

function updateProfileUI(user) {
    const name =
        user.full_name ||
        user.username ||
        'User';

    const username =
        user.username ||
        'user';

    const avatar =
        user.avatar_url ||
        '';

    const profileName =
        byId('profile-name');

    const profileUsername =
        byId('profile-username');

    const profileBio =
        byId('profile-bio');

    const profileAvatar =
        byId('profile-avatar');

    if (profileName) {
        profileName.textContent =
            name;
    }

    if (profileUsername) {
        profileUsername.textContent =
            `@${username}`;
    }

    if (profileBio) {
        profileBio.textContent =
            user.bio ||
            'Welcome to Msafiri';
    }

    if (profileAvatar) {
        if (avatar) {
            profileAvatar.innerHTML = `
                <img
                    src="${escapeHTML(
                        absoluteURL(avatar)
                    )}"
                    alt=""
                    style="
                        width:100%;
                        height:100%;
                        object-fit:cover;
                        border-radius:50%;
                    "
                >
            `;
        } else {
            profileAvatar.textContent =
                initials(name);
        }
    }
}

/* ============================================================
   EDIT PROFILE
   ============================================================ */

function openEditProfile() {
    const body =
        byId('modal-body');

    if (!body || !CURRENT_USER) return;

    openModal();

    body.innerHTML = `
        <h2>Edit Profile</h2>

        <form id="edit-profile-form">

            <input
                id="edit-full-name"
                value="${escapeHTML(
                    CURRENT_USER.full_name || ''
                )}"
                placeholder="Full name"
                style="
                    width:100%;
                    padding:13px;
                    margin-bottom:10px;
                    border-radius:10px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                "
            >

            <textarea
                id="edit-bio"
                rows="4"
                placeholder="Bio"
                style="
                    width:100%;
                    padding:13px;
                    margin-bottom:10px;
                    border-radius:10px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                "
            >${escapeHTML(
                CURRENT_USER.bio || ''
            )}</textarea>

            <input
                id="edit-location"
                value="${escapeHTML(
                    CURRENT_USER.location || ''
                )}"
                placeholder="Location"
                style="
                    width:100%;
                    padding:13px;
                    margin-bottom:14px;
                    border-radius:10px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                "
            >

            <button
                type="submit"
                class="btn-primary"
                style="width:100%;"
            >
                Save Changes
            </button>

        </form>
    `;

    const form =
        byId('edit-profile-form');

    if (!form) return;

    form.addEventListener(
        'submit',
        async event => {
            event.preventDefault();

            const fullName =
                byId('edit-full-name')?.value.trim();

            const bio =
                byId('edit-bio')?.value.trim();

            const location =
                byId('edit-location')?.value.trim();

            try {
                const data =
                    await apiRequest(
                        ENDPOINTS.profile,
                        {
                            method: 'PATCH',
                            body: {
                                full_name: fullName,
                                bio,
                                location
                            }
                        }
                    );

                CURRENT_USER =
                    data?.user ||
                    data;

                localStorage.setItem(
                    STORAGE.USER,
                    JSON.stringify(
                        CURRENT_USER
                    )
                );

                updateProfileUI(
                    CURRENT_USER
                );

                closeModal();

                showToast(
                    'Profile updated.'
                );
            } catch (error) {
                showToast(
                    error.message ||
                    'Unable to update profile.'
                );
            }
        }
    );
}

/* ============================================================
   SEARCH
   ============================================================ */

function setupSearch() {
    const input =
        byId('search-input');

    if (!input) return;

    input.addEventListener(
        'input',
        () => {
            clearTimeout(
                SEARCH_TIMER
            );

            const value =
                input.value.trim();

            SEARCH_TIMER =
                setTimeout(
                    () => {
                        if (!value) {
                            renderFeed(
                                byId('feed'),
                                CACHED_POSTS
                            );

                            return;
                        }

                        const results =
                            CACHED_POSTS.filter(
                                post => {
                                    const text =
                                        [
                                            post.username,
                                            post.full_name,
                                            post.caption
                                        ]
                                            .join(' ')
                                            .toLowerCase();

                                    return text.includes(
                                        value.toLowerCase()
                                    );
                                }
                            );

                        renderFeed(
                            byId('feed'),
                            results
                        );
                    },
                    250
                );
        }
    );
}

/* ============================================================
   FEED TABS
   ============================================================ */

function setupFeedTabs() {
    $$('.feed-tab').forEach(
        button => {
            button.addEventListener(
                'click',
                () => {
                    $$('.feed-tab')
                        .forEach(btn => {
                            btn.classList.toggle(
                                'active',
                                btn === button
                            );
                        });

                    CURRENT_FEED =
                        button.dataset.feed ||
                        'for-you';

                    /*
                     * Following filtering can be connected
                     * when follow-feed backend is available.
                     */

                    renderFeed(
                        byId('feed'),
                        CACHED_POSTS
                    );
                }
            );
        }
    );
}

/* ============================================================
   DROPDOWN
   ============================================================ */

function setupDropdown() {
    const button =
        byId('dots-btn');

    const menu =
        byId('dots-menu');

    if (!button || !menu) return;

    button.addEventListener(
        'click',
        event => {
            event.stopPropagation();

            menu.classList.toggle(
                'hidden'
            );
        }
    );

    document.addEventListener(
        'click',
        event => {
            if (
                !menu.contains(event.target) &&
                event.target !== button
            ) {
                menu.classList.add(
                    'hidden'
                );
            }
        }
    );

    menu.querySelectorAll(
        'button'
    ).forEach(
        item => {
            item.addEventListener(
                'click',
                () => {
                    menu.classList.add(
                        'hidden'
                    );

                    const action =
                        item.dataset.action;

                    handleMenuAction(
                        action
                    );
                }
            );
        }
    );
}

function handleMenuAction(action) {
    if (action === 'logout') {
        logout();
        return;
    }

    if (action === 'settings') {
        openSettings();
        return;
    }

    if (action === 'manual') {
        openManual();
        return;
    }
}

/* ============================================================
   SETTINGS
   ============================================================ */

function openSettings() {
    const body =
        byId('modal-body');

    if (!body) return;

    openModal();

    body.innerHTML = `
        <h2>Settings</h2>

        <div class="sub-item"
             id="settings-theme">
            <div class="icon">🌙</div>
            <div class="text">
                <strong>Appearance</strong>
                <span>
                    Toggle dark/light interface.
                </span>
            </div>
        </div>

        <div class="sub-item"
             id="settings-logout">
            <div class="icon">🚪</div>
            <div class="text">
                <strong>Logout</strong>
                <span>Sign out of this device.</span>
            </div>
        </div>
    `;

    byId('settings-theme')
        ?.addEventListener(
            'click',
            toggleTheme
        );

    byId('settings-logout')
        ?.addEventListener(
            'click',
            logout
        );
}

function toggleTheme() {
    const current =
        document.documentElement
            .dataset.theme;

    const next =
        current === 'light'
            ? 'dark'
            : 'light';

    document.documentElement
        .dataset.theme = next;

    localStorage.setItem(
        STORAGE.THEME,
        next
    );

    showToast(
        `${next === 'dark'
            ? 'Dark'
            : 'Light'} mode enabled.`
    );
}

function restoreTheme() {
    const theme =
        localStorage.getItem(
            STORAGE.THEME
        );

    if (theme) {
        document.documentElement
            .dataset.theme =
            theme;
    }
}

/* ============================================================
   MANUAL
   ============================================================ */

function openManual() {
    const body =
        byId('modal-body');

    if (!body) return;

    openModal();

    body.innerHTML = `
        <h2>MSAFIRI GLOBAL MEDIA</h2>

        <div class="manual-section">
            <h3>Home</h3>
            <p>
                View posts, photos and videos
                shared by people.
            </p>
        </div>

        <div class="manual-section">
            <h3>Discovery</h3>
            <p>
                Explore people and future
                MSAFIRI services.
            </p>
        </div>

        <div class="manual-section">
            <h3>Chats</h3>
            <p>
                Messaging features are being
                connected to the backend.
            </p>
        </div>

        <div class="manual-section">
            <h3>Profile</h3>
            <p>
                View and update your profile.
            </p>
        </div>
    `;
}

/* ============================================================
   LOGOUT
   ============================================================ */

function logout() {
    clearSession();

    closeModal();

    showAuth();

    showToast(
        'You have been logged out.'
    );
}

/* ============================================================
   MODAL
   ============================================================ */

function openModal() {
    const modal =
        byId('modal');

    if (!modal) return;

    modal.classList.remove(
        'hidden'
    );
}

function closeModal() {
    const modal =
        byId('modal');

    if (!modal) return;

    modal.classList.add(
        'hidden'
    );
}

/* ============================================================
   EVENT DELEGATION
   ============================================================ */

function setupGlobalEvents() {
    document.addEventListener(
        'click',
        event => {
            const nav =
                event.target.closest(
                    '.nav-btn'
                );

            if (nav) {
                navigate(
                    nav.dataset.nav
                );

                return;
            }

            const postButton =
                event.target.closest(
                    '[data-post-action]'
                );

            if (postButton) {
                handlePostAction(
                    postButton.dataset.postAction,
                    postButton.dataset.postId
                );

                return;
            }

            const chat =
                event.target.closest(
                    '.chat-item'
                );

            if (chat) {
                openChat(
                    chat.dataset.chatId
                );

                return;
            }
        }
    );
}

/* ============================================================
   CHAT VIEW
   ============================================================ */

function openChat(chatId) {
    const chat =
        CACHED_CHATS.find(
            item =>
                String(
                    item.id ??
                    item.user_id
                ) === String(chatId)
        );

    CURRENT_CHAT =
        chat || {
            id: chatId
        };

    const page =
        byId('page-sub');

    const content =
        byId('sub-content');

    if (!page || !content) return;

    $$('.page').forEach(
        p => p.classList.remove('active')
    );

    page.classList.add('active');

    const back =
        byId('back-btn');

    if (back) {
        back.classList.remove(
            'hidden'
        );
    }

    const name =
        chat?.full_name ||
        chat?.username ||
        chat?.name ||
        'Chat';

    const avatar =
        chat?.avatar_url ||
        chat?.avatar ||
        '';

    content.innerHTML = `
        <div style="
            display:flex;
            align-items:center;
            gap:12px;
            margin-bottom:12px;
            padding-bottom:12px;
            border-bottom:1px solid var(--border);
        ">

            ${
                avatar
                    ? `
                        <img
                            class="chat-avatar"
                            src="${escapeHTML(
                                absoluteURL(avatar)
                            )}"
                            alt=""
                            style="object-fit:cover"
                        >
                      `
                    : `
                        <div class="chat-avatar">
                            ${escapeHTML(
                                initials(name)
                            )}
                        </div>
                      `
            }

            <div style="flex:1">
                <strong>
                    ${escapeHTML(name)}
                </strong>

                <div class="muted">
                    Online status will appear here
                </div>
            </div>

            <button
                class="icon-btn"
                type="button"
                title="Voice call"
                onclick="showToast('Voice calls coming soon.')"
            >
                📞
            </button>

            <button
                class="icon-btn"
                type="button"
                title="Video call"
                onclick="showToast('Video calls coming soon.')"
            >
                📹
            </button>

            <button
                class="icon-btn"
                type="button"
                onclick="openChatMenu()"
            >
                ⋮
            </button>

        </div>

        <div
            id="chat-messages"
            class="chat-msgs"
        >
            <div class="sub-item">
                <div class="icon">💬</div>
                <div class="text">
                    <strong>Conversation</strong>
                    <span>
                        Messaging API is ready for expansion.
                    </span>
                </div>
            </div>
        </div>

        <form
            id="chat-compose"
            style="
                position:sticky;
                bottom:0;
                display:flex;
                gap:8px;
                padding:10px 0;
                background:var(--bg);
            "
        >

            <button
                type="button"
                class="icon-btn"
                id="chat-plus"
            >
                ＋
            </button>

            <input
                id="chat-input"
                type="text"
                placeholder="Message..."
                style="
                    flex:1;
                    padding:12px;
                    border-radius:12px;
                    border:1px solid var(--border);
                    background:var(--bg-2);
                    color:var(--text);
                    outline:none;
                "
            >

            <button
                type="button"
                class="icon-btn"
                id="chat-mic"
            >
                🎙️
            </button>

            <button
                type="submit"
                class="btn-primary"
            >
                Send
            </button>

        </form>
    `;

    setupChatComposer();
}

function setupChatComposer() {
    const form =
        byId('chat-compose');

    const input =
        byId('chat-input');

    const plus =
        byId('chat-plus');

    const mic =
        byId('chat-mic');

    if (!form) return;

    form.addEventListener(
        'submit',
        event => {
            event.preventDefault();

            const text =
                input?.value.trim();

            if (!text) return;

            /*
             * The supplied message.py currently
             * only exposes GET /api/messages.
             *
             * Therefore we do NOT call a
             * nonexistent POST endpoint.
             */

            appendLocalMessage(
                text
            );

            input.value = '';

            showToast(
                'Message composer ready. Backend send endpoint will be connected next.'
            );
        }
    );

    plus?.addEventListener(
        'click',
        openAttachmentMenu
    );

    mic?.addEventListener(
        'click',
        () => {
            showToast(
                'Voice recording UI ready for backend/media endpoint.'
            );
        }
    );
}

function appendLocalMessage(
    text
) {
    const messages =
        byId('chat-messages');

    if (!messages) return;

    const wrapper =
        document.createElement('div');

    wrapper.className =
        'msg user';

    wrapper.textContent =
        text;

    messages.appendChild(
        wrapper
    );

    messages.scrollTop =
        messages.scrollHeight;
}

/* ============================================================
   CHAT ATTACHMENTS
   ============================================================ */

function openAttachmentMenu() {
    const body =
        byId('modal-body');

    if (!body) return;

    openModal();

    body.innerHTML = `
        <h2>Send attachment</h2>

        <div
            class="sub-item"
            data-attach="photo"
        >
            <div class="icon">📷</div>
            <div class="text">
                <strong>Photo</strong>
                <span>Choose an image.</span>
            </div>
        </div>

        <div
            class="sub-item"
            data-attach="video"
        >
            <div class="icon">🎬</div>
            <div class="text">
                <strong>Video</strong>
                <span>Choose a video.</span>
            </div>
        </div>

        <div
            class="sub-item"
            data-attach="document"
        >
            <div class="icon">📄</div>
            <div class="text">
                <strong>Document</strong>
                <span>Choose a document.</span>
            </div>
        </div>

        <div
            class="sub-item"
            data-attach="voice"
        >
            <div class="icon">🎙️</div>
            <div class="text">
                <strong>Voice</strong>
                <span>Voice notes coming soon.</span>
            </div>
        </div>
    `;

    body.querySelectorAll(
        '[data-attach]'
    ).forEach(
        item => {
            item.addEventListener(
                'click',
                () => {
                    const type =
                        item.dataset.attach;

                    if (
                        type === 'voice'
                    ) {
                        showToast(
                            'Voice notes coming soon.'
                        );

                        return;
                    }

                    const input =
                        document.createElement(
                            'input'
                        );

                    input.type =
                        'file';

                    if (
                        type === 'photo'
                    ) {
                        input.accept =
                            'image/*';
                    }

                    if (
                        type === 'video'
                    ) {
                        input.accept =
                            'video/*';
                    }

                    if (
                        type === 'document'
                    ) {
                        input.accept =
                            '.pdf,.doc,.docx,.txt,.xls,.xlsx,.ppt,.pptx';
                    }

                    input.click();

                    input.addEventListener(
                        'change',
                        () => {
                            if (
                                input.files?.length
                            ) {
                                showToast(
                                    `${type} selected.`
                                );
                            }
                        }
                    );
                }
            );
        }
    );
}

/* ============================================================
   CHAT 3-DOTS MENU
   ============================================================ */

function openChatMenu() {
    const body =
        byId('modal-body');

    if (!body) return;

    openModal();

    body.innerHTML = `
        <h2>Chat options</h2>

        <div
            class="sub-item"
            onclick="chooseWallpaper()"
        >
            <div class="icon">🖼️</div>
            <div class="text">
                <strong>Change wallpaper</strong>
                <span>
                    Choose a background from gallery.
                </span>
            </div>
        </div>

        <div
            class="sub-item"
            onclick="toggleChatBlock()"
        >
            <div class="icon">🚫</div>
            <div class="text">
                <strong>Block / Unblock</strong>
                <span>
                    Manage this conversation.
                </span>
            </div>
        </div>

        <div
            class="sub-item"
            onclick="toggleChatPin()"
        >
            <div class="icon">📌</div>
            <div class="text">
                <strong>Pin chat</strong>
                <span>
                    Keep this chat at the top.
                </span>
            </div>
        </div>

        <div
            class="sub-item"
            onclick="showToast('Translation will be enabled in a future version.')"
        >
            <div class="icon">🌐</div>
            <div class="text">
                <strong>Translate text</strong>
                <span>
                    Coming in a future version.
                </span>
            </div>
        </div>

        <div
            class="sub-item"
            onclick="toggleFavouriteChat()"
        >
            <div class="icon">⭐</div>
            <div class="text">
                <strong>Add to favourites</strong>
                <span>
                    Keep important chats easy to find.
                </span>
            </div>
        </div>

        <div
            class="sub-item"
            onclick="clearLocalChat()"
        >
            <div class="icon">🧹</div>
            <div class="text">
                <strong>Clear chat</strong>
                <span>
                    Clear local conversation display.
                </span>
            </div>
        </div>

        <div
            class="sub-item"
            onclick="showChatInfo()"
        >
            <div class="icon">ℹ️</div>
            <div class="text">
                <strong>Chat info</strong>
                <span>
                    View conversation information.
                </span>
            </div>
        </div>

        <div
            class="sub-item"
            onclick="reportChat()"
        >
            <div class="icon">⚠️</div>
            <div class="text">
                <strong>Report</strong>
                <span>
                    Report a problem with this chat.
                </span>
            </div>
        </div>
    `;
}

/* ============================================================
   CHAT OPTIONS
   ============================================================ */

function chooseWallpaper() {
    const input =
        document.createElement(
            'input'
        );

    input.type =
        'file';

    input.accept =
        'image/*';

    input.click();

    input.addEventListener(
        'change',
        () => {
            const file =
                input.files?.[0];

            if (!file) return;

            const reader =
                new FileReader();

            reader.onload =
                event => {
                    const page =
                        byId('page-sub');

                    if (page) {
                        page.style.backgroundImage =
                            `url("${event.target.result}")`;

                        page.style.backgroundSize =
                            'cover';

                        page.style.backgroundPosition =
                            'center';
                    }

                    closeModal();

                    showToast(
                        'Chat wallpaper changed.'
                    );
                };

            reader.readAsDataURL(
                file
            );
        }
    );
}

function toggleChatBlock() {
    showToast(
        'Block/Unblock UI is ready for backend persistence.'
    );
}

function toggleChatPin() {
    showToast(
        'Pin chat selected.'
    );
}

function toggleFavouriteChat() {
    showToast(
        'Chat added to favourites.'
    );
}

function clearLocalChat() {
    const messages =
        byId('chat-messages');

    if (messages) {
        messages.innerHTML = '';
    }

    closeModal();

    showToast(
        'Local chat display cleared.'
    );
}

function showChatInfo() {
    const name =
        CURRENT_CHAT?.full_name ||
        CURRENT_CHAT?.username ||
        CURRENT_CHAT?.name ||
        'User';

    closeModal();

    showToast(
        `Chat: ${name}`
    );
}

function reportChat() {
    closeModal();

    showToast(
        'Report feature prepared for backend integration.'
    );
}

/* ============================================================
   BACK BUTTON
   ============================================================ */

function setupBackButton() {
    const button =
        byId('back-btn');

    if (!button) return;

    button.addEventListener(
        'click',
        () => {
            navigate('chats');
        }
    );
}

/* ============================================================
   MODAL EVENTS
   ============================================================ */

function setupModal() {
    const close =
        byId('modal-close');

    const modal =
        byId('modal');

    close?.addEventListener(
        'click',
        closeModal
    );

    modal?.addEventListener(
        'click',
        event => {
            if (
                event.target === modal
            ) {
                closeModal();
            }
        }
    );
}

/* ============================================================
   STORY PLACEHOLDER
   ============================================================ */

function setupStoryButton() {
    const button =
        byId('add-story-btn');

    if (!button) return;

    button.addEventListener(
        'click',
        () => {
            showToast(
                'Stories are ready for future media integration.'
            );
        }
    );
}

/* ============================================================
   HEALTH CHECK
   ============================================================ */

async function checkBackend() {
    try {
        const data =
            await apiRequest(
                ENDPOINTS.health,
                {},
                true
            );

        console.log(
            'MSAFIRI backend:',
            data
        );

        return true;
    } catch (error) {
        console.warn(
            'Backend health check failed:',
            error.message
        );

        return false;
    }
}

/* ============================================================
   INITIALIZATION
   ============================================================ */

function init() {
    try {
        restoreTheme();

        setupAuthTabs();
        setupSearch();
        setupFeedTabs();
        setupDropdown();
        setupGlobalEvents();
        setupBackButton();
        setupModal();
        setupStoryButton();

        const loginForm =
            byId('login-form');

        if (loginForm) {
            loginForm.addEventListener(
                'submit',
                event => {
                    event.preventDefault();
                    login();
                }
            );
        }

        const registerForm =
            byId('register-form');

        if (registerForm) {
            registerForm.addEventListener(
                'submit',
                event => {
                    event.preventDefault();
                    register();
                }
            );
        }

        byId('fab-create')
            ?.addEventListener(
                'click',
                openCreatePost
            );

        byId('edit-profile-btn')
            ?.addEventListener(
                'click',
                openEditProfile
            );

        /*
         * Do not wait for backend health.
         * The UI must still open even if backend
         * temporarily responds slowly.
         */

        setTimeout(
            finishSplash,
            2500
        );

        checkBackend();

        console.log(
            'MSAFIRI GLOBAL MEDIA initialized successfully.'
        );
    } catch (error) {
        console.error(
            'Fatal initialization error:',
            error
        );

        /*
         * Critical fallback:
         * never leave the user staring at
         * the splash screen.
         */

        const splash =
            byId('splash');

        if (splash) {
            splash.classList.add(
                'hidden'
            );
        }

        if (TOKEN) {
            showApp();
        } else {
            showAuth();
        }
    }
}

/* ============================================================
   GLOBAL EXPORTS
   ============================================================ */

window.MSAFIRI = {
    API,
    navigate,
    loadHome,
    loadChats,
    loadProfile,
    openCreatePost,
    openChat,
    openChatMenu,
    chooseWallpaper,
    logout,
    showToast,
    apiRequest
};

window.openChatMenu =
    openChatMenu;

window.chooseWallpaper =
    chooseWallpaper;

window.toggleChatBlock =
    toggleChatBlock;

window.toggleChatPin =
    toggleChatPin;

window.toggleFavouriteChat =
    toggleFavouriteChat;

window.clearLocalChat =
    clearLocalChat;

window.showChatInfo =
    showChatInfo;

window.reportChat =
    reportChat;

/* ============================================================
   START
   ============================================================ */

if (
    document.readyState ===
    'loading'
) {
    document.addEventListener(
        'DOMContentLoaded',
        init,
        {
            once: true
        }
    );
} else {
    init();
}
