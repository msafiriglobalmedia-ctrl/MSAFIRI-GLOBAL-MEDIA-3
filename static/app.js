// ============================================================
// MSAFIRI GLOBAL MEDIA
// APP.JS — PHASE 2
// AUTH + POSTS + MEDIA + LIKE + COMMENT + SAVE + SHARE
// ============================================================

"use strict";

const API = "";

let currentUser = null;
let currentFeed = "for-you";
let navStack = [];


// ============================================================
// DOM HELPER
// ============================================================

const $ = (selector) =>
    document.querySelector(selector);

const $$ = (selector) =>
    document.querySelectorAll(selector);


// ============================================================
// API HELPER
// ============================================================

async function apiFetch(url, options = {}) {

    const token =
        localStorage.getItem("token");

    const headers =
        new Headers(
            options.headers || {}
        );

    if (
        !(options.body instanceof FormData) &&
        !headers.has("Content-Type") &&
        options.body
    ) {
        headers.set(
            "Content-Type",
            "application/json"
        );
    }

    if (token) {
        headers.set(
            "Authorization",
            `Bearer ${token}`
        );
    }

    return fetch(
        `${API}${url}`,
        {
            ...options,
            headers,
            credentials: "include",
        }
    );
}


// ============================================================
// INIT
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setTimeout(
            () => {

                const splash =
                    $("#splash");

                if (splash) {
                    splash.classList.add(
                        "hidden"
                    );
                }

                checkAuth();

            },
            1500
        );

        setupAuthForms();
        setupNavigation();
        setupFeedTabs();
        setupDotsMenu();
        setupCreateButtons();
    }
);


// ============================================================
// AUTH CHECK
// ============================================================

async function checkAuth() {

    const token =
        localStorage.getItem("token");

    if (!token) {
        showAuth();
        return;
    }

    try {

        const response =
            await apiFetch(
                "/api/auth/me"
            );

        if (!response.ok) {

            localStorage.removeItem(
                "token"
            );

            currentUser = null;

            showAuth();

            return;
        }

        currentUser =
            await response.json();

        showApp();

    } catch (error) {

        console.error(
            "Auth error:",
            error
        );

        showAuth();
    }
}


// ============================================================
// SHOW AUTH
// ============================================================

function showAuth() {

    const auth =
        $("#auth-screen");

    const app =
        $("#app");

    if (auth) {
        auth.classList.remove(
            "hidden"
        );
    }

    if (app) {
        app.classList.add(
            "hidden"
        );
    }
}


// ============================================================
// SHOW APP
// ============================================================

function showApp() {

    const auth =
        $("#auth-screen");

    const app =
        $("#app");

    if (auth) {
        auth.classList.add(
            "hidden"
        );
    }

    if (app) {
        app.classList.remove(
            "hidden"
        );
    }

    loadHome();
    loadDiscovery();
    loadProfile();
}


// ============================================================
// AUTH FORMS
// ============================================================

function setupAuthForms() {

    $$(".auth-tab").forEach(
        tab => {

            tab.addEventListener(
                "click",
                () => {

                    $$(".auth-tab")
                        .forEach(
                            t =>
                                t.classList.remove(
                                    "active"
                                )
                        );

                    tab.classList.add(
                        "active"
                    );

                    const target =
                        tab.dataset.tab;

                    const login =
                        $("#login-form");

                    const register =
                        $("#register-form");

                    if (login) {
                        login.classList.toggle(
                            "hidden",
                            target !== "login"
                        );
                    }

                    if (register) {
                        register.classList.toggle(
                            "hidden",
                            target !== "register"
                        );
                    }
                }
            );
        }
    );


    const loginForm =
        $("#login-form");

    if (loginForm) {

        loginForm.addEventListener(
            "submit",
            async event => {

                event.preventDefault();

                const username =
                    $("#login-username")
                        ?.value
                        ?.trim();

                const password =
                    $("#login-password")
                        ?.value;

                if (!username || !password) {
                    toast(
                        "Enter username and password"
                    );
                    return;
                }

                try {

                    const response =
                        await apiFetch(
                            "/api/auth/login",
                            {
                                method: "POST",
                                body: JSON.stringify({
                                    username,
                                    password,
                                }),
                            }
                        );

                    const data =
                        await response.json();

                    if (!response.ok) {

                        toast(
                            data.detail ||
                            "Login failed"
                        );

                        return;
                    }

                    if (data.access_token) {

                        localStorage.setItem(
                            "token",
                            data.access_token
                        );
                    }

                    currentUser =
                        data.user || null;

                    toast(
                        "Login successful"
                    );

                    showApp();

                } catch (error) {

                    console.error(error);

                    toast(
                        "Network error"
                    );
                }
            }
        );
    }


    const registerForm =
        $("#register-form");

    if (registerForm) {

        registerForm.addEventListener(
            "submit",
            async event => {

                event.preventDefault();

                const username =
                    $("#reg-username")
                        ?.value
                        ?.trim();

                const email =
                    $("#reg-email")
                        ?.value
                        ?.trim();

                const full_name =
                    $("#reg-fullname")
                        ?.value
                        ?.trim();

                const password =
                    $("#reg-password")
                        ?.value;

                if (
                    !username ||
                    !email ||
                    !password
                ) {

                    toast(
                        "Fill all required fields"
                    );

                    return;
                }

                try {

                    const response =
                        await apiFetch(
                            "/api/auth/register",
                            {
                                method: "POST",
                                body: JSON.stringify({
                                    username,
                                    email,
                                    full_name,
                                    password,
                                }),
                            }
                        );

                    const data =
                        await response.json();

                    if (!response.ok) {

                        toast(
                            data.detail ||
                            "Registration failed"
                        );

                        return;
                    }

                    if (
                        data.access_token
                    ) {

                        localStorage.setItem(
                            "token",
                            data.access_token
                        );

                        currentUser =
                            data.user;

                        toast(
                            "Account created successfully"
                        );

                        showApp();

                        return;
                    }

                    toast(
                        "Account created. Please login."
                    );

                    const loginTab =
                        $('[data-tab="login"]');

                    if (loginTab) {
                        loginTab.click();
                    }

                } catch (error) {

                    console.error(error);

                    toast(
                        "Network error"
                    );
                }
            }
        );
    }
}


// ============================================================
// NAVIGATION
// ============================================================

function setupNavigation() {

    $$(".nav-btn").forEach(
        btn => {

            btn.addEventListener(
                "click",
                () => {

                    const nav =
                        btn.dataset.nav;

                    $$(".nav-btn")
                        .forEach(
                            b =>
                                b.classList.remove(
                                    "active"
                                )
                        );

                    btn.classList.add(
                        "active"
                    );

                    $$(".page")
                        .forEach(
                            page =>
                                page.classList.remove(
                                    "active"
                                )
                        );

                    const page =
                        $(`#page-${nav}`);

                    if (page) {
                        page.classList.add(
                            "active"
                        );
                    }

                    const titles = {
                        home: "MSAFIRI",
                        discovery: "Discovery",
                        chats: "Chats",
                        profile: "Profile",
                    };

                    const title =
                        $("#page-title");

                    if (title) {
                        title.textContent =
                            titles[nav] ||
                            "MSAFIRI";
                    }

                    navStack = [];

                    if (
                        nav === "home"
                    ) {
                        loadHome();
                    }

                    if (
                        nav === "chats"
                    ) {
                        loadChats();
                    }

                    if (
                        nav === "profile"
                    ) {
                        loadProfile();
                    }

                    if (
                        nav === "discovery"
                    ) {
                        loadDiscovery();
                    }
                }
            );
        }
    );


    const back =
        $("#back-btn");

    if (back) {

        back.addEventListener(
            "click",
            () => {

                if (
                    navStack.length > 0
                ) {

                    const previous =
                        navStack.pop();

                    previous();
                }
            }
        );
    }
}


// ============================================================
// SUB PAGE
// ============================================================

function showSubPage(
    title,
    renderFn
) {

    const current =
        document.querySelector(
            ".page.active"
        );

    navStack.push(
        () => {

            const sub =
                $("#page-sub");

            if (sub) {
                sub.classList.remove(
                    "active"
                );
            }

            if (current) {
                current.classList.add(
                    "active"
                );
            }

            const back =
                $("#back-btn");

            if (back) {
                back.classList.add(
                    "hidden"
                );
            }

            const pageTitle =
                $("#page-title");

            if (pageTitle) {
                pageTitle.textContent =
                    "MSAFIRI";
            }
        }
    );

    $$(".page")
        .forEach(
            p =>
                p.classList.remove(
                    "active"
                )
        );

    const sub =
        $("#page-sub");

    if (!sub) return;

    sub.classList.add(
        "active"
    );

    const pageTitle =
        $("#page-title");

    if (pageTitle) {
        pageTitle.textContent =
            title;
    }

    const back =
        $("#back-btn");

    if (back) {
        back.classList.remove(
            "hidden"
        );
    }

    const content =
        $("#sub-content");

    if (content) {
        renderFn(content);
    }
}


// ============================================================
// HOME
// ============================================================

async function loadHome() {

    await loadStories();
    await loadFeed();
}


// ============================================================
// FEED TABS
// ============================================================

function setupFeedTabs() {

    $$(".feed-tab").forEach(
        tab => {

            tab.addEventListener(
                "click",
                () => {

                    $$(".feed-tab")
                        .forEach(
                            t =>
                                t.classList.remove(
                                    "active"
                                )
                        );

                    tab.classList.add(
                        "active"
                    );

                    currentFeed =
                        tab.dataset.feed ||
                        "for-you";

                    loadFeed();
                }
            );
        }
    );
}


// ============================================================
// STORIES
// ============================================================

async function loadStories() {

    try {

        const response =
            await apiFetch(
                "/api/stories"
            );

        if (!response.ok) return;

        const data =
            await response.json();

        const bar =
            $("#stories-bar");

        if (!bar) return;

        bar.querySelectorAll(
            ".story-item:not(.add-story)"
        ).forEach(
            item => item.remove()
        );

        (data.stories || [])
            .forEach(
                story => {

                    const item =
                        document.createElement(
                            "div"
                        );

                    item.className =
                        "story-item";

                    const name =
                        story.username ||
                        "User";

                    item.innerHTML = `
                        <div class="story-avatar">
                            ${escapeHtml(
                                name
                                    .charAt(0)
                                    .toUpperCase()
                            )}
                        </div>
                        <span>
                            ${escapeHtml(name)}
                        </span>
                    `;

                    bar.appendChild(
                        item
                    );
                }
            );

    } catch (error) {

        console.error(
            "Stories:",
            error
        );
    }
}


// ============================================================
// FEED
// ============================================================

async function loadFeed() {

    const feed =
        $("#feed");

    if (!feed) return;

    feed.innerHTML = `
        <p class="muted"
           style="text-align:center;padding:20px;">
            Loading posts...
        </p>
    `;

    try {

        const response =
            await apiFetch(
                `/api/feed?type=${encodeURIComponent(
                    currentFeed
                )}`
            );

        if (!response.ok) {

            throw new Error(
                "Feed request failed"
            );
        }

        const data =
            await response.json();

        const posts =
            data.posts || [];

        if (
            posts.length === 0
        ) {

            feed.innerHTML = `
                <div class="empty-state"
                     style="text-align:center;padding:40px 20px;">
                    <div style="font-size:40px;">
                        📝
                    </div>
                    <h3>No posts yet</h3>
                    <p class="muted">
                        Be the first to share something.
                    </p>
                    <button
                        class="btn-primary"
                        id="empty-create-post">
                        Create Post
                    </button>
                </div>
            `;

            const button =
                $("#empty-create-post");

            if (button) {
                button.addEventListener(
                    "click",
                    openPostComposer
                );
            }

            return;
        }

        feed.innerHTML = "";

        posts.forEach(
            post => {

                feed.appendChild(
                    renderPost(post)
                );
            }
        );

    } catch (error) {

        console.error(
            "Feed error:",
            error
        );

        feed.innerHTML = `
            <div style="text-align:center;padding:30px;">
                <p class="muted">
                    Failed to load posts.
                </p>
                <button
                    class="btn-primary"
                    id="retry-feed">
                    Retry
                </button>
            </div>
        `;

        const retry =
            $("#retry-feed");

        if (retry) {
            retry.addEventListener(
                "click",
                loadFeed
            );
        }
    }
}


// ============================================================
// RENDER POST
// ============================================================

function renderPost(post) {

    const card =
        document.createElement(
            "article"
        );

    card.className =
        "post-card";

    card.dataset.postId =
        post.id;

    const name =
        post.full_name ||
        post.username ||
        `User ${post.user_id}`;

    const initial =
        name
            .charAt(0)
            .toUpperCase();

    const avatar =
        post.avatar_url
            ? `
                <img
                    src="${escapeAttribute(
                        post.avatar_url
                    )}"
                    alt=""
                    class="post-avatar-img"
                >
              `
            : `
                <div class="post-avatar">
                    ${escapeHtml(initial)}
                </div>
              `;

    let media = "";

    if (
        post.media_url &&
        post.media_type === "image"
    ) {

        media = `
            <div class="post-media-wrap">
                <img
                    class="post-media"
                    src="${escapeAttribute(
                        post.media_url
                    )}"
                    alt="Post image"
                    loading="lazy"
                >
            </div>
        `;
    }

    if (
        post.media_url &&
        post.media_type === "video"
    ) {

        media = `
            <div class="post-media-wrap">
                <video
                    class="post-video"
                    src="${escapeAttribute(
                        post.media_url
                    )}"
                    controls
                    playsinline
                    preload="metadata">
                </video>
            </div>
        `;
    }

    const liked =
        post.liked
            ? "liked"
            : "";

    const saved =
        post.saved
            ? "saved"
            : "";

    const deleteButton =
        currentUser &&
        Number(currentUser.id) ===
            Number(post.user_id)
            ? `
                <button
                    class="post-menu-delete"
                    data-action="delete-post">
                    Delete
                </button>
              `
            : "";

    card.innerHTML = `
        <div class="post-header">

            ${avatar}

            <div class="post-user">
                <strong>
                    ${escapeHtml(name)}
                </strong>

                <span>
                    @${escapeHtml(
                        post.username ||
                        "user"
                    )}
                    ·
                    ${timeAgo(
                        post.created_at
                    )}
                </span>
            </div>

            <div class="post-more">
                ${deleteButton}
            </div>

        </div>

        ${
            post.caption
                ? `
                    <p class="post-caption">
                        ${escapeHtml(
                            post.caption
                        )}
                    </p>
                  `
                : ""
        }

        ${media}

        <div class="post-actions">

            <button
                class="post-action like-btn ${liked}"
                data-action="like">
                ❤️
                <span class="like-count">
                    ${post.likes || 0}
                </span>
            </button>

            <button
                class="post-action comment-btn"
                data-action="comments">
                💬
                <span class="comment-count">
                    ${post.comments || 0}
                </span>
            </button>

            <button
                class="post-action share-btn"
                data-action="share">
                ↗️
                <span class="share-count">
                    ${post.shares || 0}
                </span>
            </button>

            <button
                class="post-action save-btn ${saved}"
                data-action="save">
                🔖
                <span class="save-count">
                    ${post.saves || 0}
                </span>
            </button>

        </div>

        <div
            class="comments-area"
            data-comments-area>
        </div>
    `;

    card.addEventListener(
        "click",
        event => {

            const actionButton =
                event.target.closest(
                    "[data-action]"
                );

            if (!actionButton) {
                return;
            }

            const action =
                actionButton.dataset.action;

            if (action === "like") {
                handleLike(
                    post.id,
                    card,
                    actionButton
                );
            }

            if (
                action === "comments"
            ) {
                toggleComments(
                    post.id,
                    card
                );
            }

            if (
                action === "share"
            ) {
                handleShare(
                    post.id,
                    actionButton
                );
            }

            if (
                action === "save"
            ) {
                handleSave(
                    post.id,
                    actionButton
                );
            }

            if (
                action === "delete-post"
            ) {
                handleDeletePost(
                    post.id
                );
            }
        }
    );

    return card;
}


// ============================================================
// LIKE
// ============================================================

async function handleLike(
    postId,
    card,
    button
) {

    if (!ensureLoggedIn()) {
        return;
    }

    try {

        const response =
            await apiFetch(
                `/api/posts/${postId}/like`,
                {
                    method: "POST",
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            toast(
                data.detail ||
                "Unable to like post"
            );

            return;
        }

        button.classList.toggle(
            "liked",
            Boolean(data.liked)
        );

        const count =
            button.querySelector(
                ".like-count"
            );

        if (count) {
            count.textContent =
                data.likes;
        }

    } catch (error) {

        console.error(error);

        toast(
            "Network error"
        );
    }
}


// ============================================================
// SAVE
// ============================================================

async function handleSave(
    postId,
    button
) {

    if (!ensureLoggedIn()) {
        return;
    }

    try {

        const response =
            await apiFetch(
                `/api/posts/${postId}/save`,
                {
                    method: "POST",
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            toast(
                data.detail ||
                "Unable to save post"
            );

            return;
        }

        button.classList.toggle(
            "saved",
            Boolean(data.saved)
        );

        const count =
            button.querySelector(
                ".save-count"
            );

        if (count) {
            count.textContent =
                data.saves;
        }

        toast(
            data.saved
                ? "Post saved"
                : "Removed from saved"
        );

    } catch (error) {

        console.error(error);

        toast(
            "Network error"
        );
    }
}


// ============================================================
// SHARE
// ============================================================

async function handleShare(
    postId,
    button
) {

    if (!ensureLoggedIn()) {
        return;
    }

    try {

        const response =
            await apiFetch(
                `/api/posts/${postId}/share`,
                {
                    method: "POST",
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            toast(
                data.detail ||
                "Unable to share"
            );

            return;
        }

        const count =
            button.querySelector(
                ".share-count"
            );

        if (count) {
            count.textContent =
                data.shares;
        }

        const shareUrl =
            `${window.location.origin}/?post=${postId}`;

        if (
            navigator.clipboard &&
            navigator.clipboard.writeText
        ) {

            await navigator.clipboard.writeText(
                shareUrl
            );

            toast(
                "Post shared and link copied"
            );

        } else {

            toast(
                "Post shared"
            );
        }

    } catch (error) {

        console.error(error);

        toast(
            "Network error"
        );
    }
}


// ============================================================
// COMMENTS
// ============================================================

async function toggleComments(
    postId,
    card
) {

    const area =
        card.querySelector(
            "[data-comments-area]"
        );

    if (!area) return;

    if (
        area.classList.contains(
            "open"
        )
    ) {

        area.classList.remove(
            "open"
        );

        area.innerHTML = "";

        return;
    }

    area.classList.add(
        "open"
    );

    area.innerHTML = `
        <div class="comments-loading">
            Loading comments...
        </div>
    `;

    try {

        const response =
            await apiFetch(
                `/api/posts/${postId}/comments`
            );

        const data =
            await response.json();

        if (!response.ok) {

            area.innerHTML = `
                <p class="muted">
                    Failed to load comments.
                </p>
            `;

            return;
        }

        renderComments(
            postId,
            area,
            data.comments || []
        );

    } catch (error) {

        console.error(error);

        area.innerHTML = `
            <p class="muted">
                Failed to load comments.
            </p>
        `;
    }
}


function renderComments(
    postId,
    area,
    comments
) {

    const list =
        comments.length
            ? comments
                .map(
                    comment => `
                        <div class="comment-item">

                            <div class="comment-avatar">
                                ${escapeHtml(
                                    (
                                        comment.full_name ||
                                        comment.username ||
                                        "U"
                                    )
                                        .charAt(0)
                                        .toUpperCase()
                                )}
                            </div>

                            <div class="comment-body">
                                <strong>
                                    ${escapeHtml(
                                        comment.full_name ||
                                        comment.username ||
                                        "User"
                                    )}
                                </strong>

                                <p>
                                    ${escapeHtml(
                                        comment.text
                                    )}
                                </p>

                                <small>
                                    ${timeAgo(
                                        comment.created_at
                                    )}
                                </small>
                            </div>

                        </div>
                    `
                )
                .join("")
            : `
                <p class="muted">
                    No comments yet.
                </p>
              `;

    area.innerHTML = `
        <div class="comments-list">
            ${list}
        </div>

        ${
            currentUser
                ? `
                    <form
                        class="comment-form"
                        data-comment-form>

                        <input
                            type="text"
                            name="comment"
                            placeholder="Write a comment..."
                            autocomplete="off"
                            required
                        >

                        <button
                            type="submit"
                            class="btn-primary">
                            Send
                        </button>

                    </form>
                  `
                : ""
        }
    `;

    const form =
        area.querySelector(
            "[data-comment-form]"
        );

    if (form) {

        form.addEventListener(
            "submit",
            async event => {

                event.preventDefault();

                const input =
                    form.querySelector(
                        'input[name="comment"]'
                    );

                const text =
                    input.value.trim();

                if (!text) return;

                const formData =
                    new FormData();

                formData.append(
                    "text",
                    text
                );

                try {

                    const response =
                        await apiFetch(
                            `/api/posts/${postId}/comments`,
                            {
                                method: "POST",
                                body: formData,
                            }
                        );

                    const data =
                        await response.json();

                    if (!response.ok) {

                        toast(
                            data.detail ||
                            "Comment failed"
                        );

                        return;
                    }

                    input.value = "";

                    await refreshComments(
                        postId,
                        area
                    );

                    const card =
                        area.closest(
                            ".post-card"
                        );

                    const count =
                        card?.querySelector(
                            ".comment-count"
                        );

                    if (count) {
                        count.textContent =
                            data.comments;
                    }

                } catch (error) {

                    console.error(error);

                    toast(
                        "Network error"
                    );
                }
            }
        );
    }
}


async function refreshComments(
    postId,
    area
) {

    const response =
        await apiFetch(
            `/api/posts/${postId}/comments`
        );

    const data =
        await response.json();

    if (response.ok) {

        renderComments(
            postId,
            area,
            data.comments || []
        );
    }
}


// ============================================================
// DELETE POST
// ============================================================

async function handleDeletePost(
    postId
) {

    if (
        !confirm(
            "Delete this post?"
        )
    ) {
        return;
    }

    try {

        const response =
            await apiFetch(
                `/api/posts/${postId}`,
                {
                    method: "DELETE",
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            toast(
                data.detail ||
                "Unable to delete post"
            );

            return;
        }

        const card =
            document.querySelector(
                `[data-post-id="${postId}"]`
            );

        if (card) {
            card.remove();
        }

        toast(
            "Post deleted"
        );

    } catch (error) {

        console.error(error);

        toast(
            "Network error"
        );
    }
}


// ============================================================
// CREATE BUTTON SETUP
// ============================================================

function setupCreateButtons() {

    const selectors = [
        "#create-btn",
        "#add-post-btn",
        ".create-btn",
        ".fab-create",
        '[data-action="create"]',
        '[data-nav="create"]'
    ];

    selectors.forEach(
        selector => {

            $$(selector).forEach(
                button => {

                    button.addEventListener(
                        "click",
                        event => {

                            event.preventDefault();

                            openPostComposer();
                        }
                    );
                }
            );
        }
    );


    /*
     * Kama HTML yako haina create button,
     * tunatengeneza floating button.
     */

    if (
        !document.querySelector(
            "#dynamic-create-post"
        )
    ) {

        const button =
            document.createElement(
                "button"
            );

        button.id =
            "dynamic-create-post";

        button.type =
            "button";

        button.textContent =
            "+";

        button.title =
            "Create Post";

        button.style.cssText = `
            position:fixed;
            right:20px;
            bottom:85px;
            width:58px;
            height:58px;
            border-radius:50%;
            border:none;
            background:linear-gradient(
                135deg,
                #6c5ce7,
                #8e44ad
            );
            color:white;
            font-size:30px;
            font-weight:bold;
            z-index:9999;
            cursor:pointer;
            box-shadow:0 8px 25px rgba(0,0,0,.25);
        `;

        button.addEventListener(
            "click",
            openPostComposer
        );

        document.body.appendChild(
            button
        );
    }
}


// ============================================================
// POST COMPOSER
// ============================================================

function openPostComposer() {

    if (!ensureLoggedIn()) {
        return;
    }

    let modal =
        $("#post-composer-modal");

    if (modal) {

        modal.classList.remove(
            "hidden"
        );

        return;
    }

    modal =
        document.createElement(
            "div"
        );

    modal.id =
        "post-composer-modal";

    modal.innerHTML = `
        <div class="post-composer-overlay">

            <div class="post-composer-card">

                <div class="composer-header">

                    <h2>
                        Create Post
                    </h2>

                    <button
                        type="button"
                        id="close-composer">
                        ×
                    </button>

                </div>

                <div class="composer-user">

                    <div class="composer-avatar">
                        ${escapeHtml(
                            (
                                currentUser?.full_name ||
                                currentUser?.username ||
                                "U"
                            )
                                .charAt(0)
                                .toUpperCase()
                        )}
                    </div>

                    <div>
                        <strong>
                            ${escapeHtml(
                                currentUser?.full_name ||
                                currentUser?.username ||
                                "User"
                            )}
                        </strong>

                        <small>
                            Public
                        </small>
                    </div>

                </div>

                <textarea
                    id="post-caption-input"
                    placeholder="What's happening?"
                    maxlength="5000"></textarea>

                <div
                    id="post-media-preview"
                    class="media-preview">
                </div>

                <div class="composer-tools">

                    <label
                        class="composer-tool">

                        🖼️ Photo

                        <input
                            type="file"
                            id="post-image-input"
                            accept="image/*"
                            hidden>

                    </label>

                    <label
                        class="composer-tool">

                        🎬 Video

                        <input
                            type="file"
                            id="post-video-input"
                            accept="video/*"
                            hidden>

                    </label>

                    <button
                        type="button"
                        id="remove-media"
                        class="composer-tool hidden">
                        ✕ Remove
                    </button>

                </div>

                <div class="composer-footer">

                    <span
                        id="upload-status"
                        class="muted">
                    </span>

                    <button
                        type="button"
                        id="publish-post"
                        class="btn-primary">
                        Post
                    </button>

                </div>

            </div>

        </div>
    `;

    document.body.appendChild(
        modal
    );

    injectComposerStyles();

    setupComposerEvents(
        modal
    );
}


function setupComposerEvents(
    modal
) {

    const close =
        modal.querySelector(
            "#close-composer"
        );

    const imageInput =
        modal.querySelector(
            "#post-image-input"
        );

    const videoInput =
        modal.querySelector(
            "#post-video-input"
        );

    const remove =
        modal.querySelector(
            "#remove-media"
        );

    const publish =
        modal.querySelector(
            "#publish-post"
        );

    if (close) {

        close.addEventListener(
            "click",
            closePostComposer
        );
    }

    imageInput?.addEventListener(
        "change",
        () => {

            if (
                imageInput.files &&
                imageInput.files[0]
            ) {

                videoInput.value =
                    "";

                showMediaPreview(
                    imageInput.files[0]
                );
            }
        }
    );

    videoInput?.addEventListener(
        "change",
        () => {

            if (
                videoInput.files &&
                videoInput.files[0]
            ) {

                imageInput.value =
                    "";

                showMediaPreview(
                    videoInput.files[0]
                );
            }
        }
    );

    remove?.addEventListener(
        "click",
        () => {

            imageInput.value =
                "";

            videoInput.value =
                "";

            clearMediaPreview();
        }
    );

    publish?.addEventListener(
        "click",
        publishPost
    );


    modal.addEventListener(
        "click",
        event => {

            if (
                event.target.classList.contains(
                    "post-composer-overlay"
                )
            ) {

                closePostComposer();
            }
        }
    );
}


// ============================================================
// MEDIA PREVIEW
// ============================================================

function showMediaPreview(
    file
) {

    const preview =
        $("#post-media-preview");

    const remove =
        $("#remove-media");

    if (!preview) return;

    const url =
        URL.createObjectURL(
            file
        );

    if (
        file.type.startsWith(
            "image/"
        )
    ) {

        preview.innerHTML = `
            <img
                src="${url}"
                alt="Preview">
        `;

    } else if (
        file.type.startsWith(
            "video/"
        )
    ) {

        preview.innerHTML = `
            <video
                src="${url}"
                controls
                playsinline>
            </video>
        `;
    }

    remove?.classList.remove(
        "hidden"
    );
}


function clearMediaPreview() {

    const preview =
        $("#post-media-preview");

    const remove =
        $("#remove-media");

    if (preview) {
        preview.innerHTML =
            "";
    }

    remove?.classList.add(
        "hidden"
    );
}


// ============================================================
// PUBLISH POST
// ============================================================

async function publishPost() {

    if (!ensureLoggedIn()) {
        return;
    }

    const caption =
        $("#post-caption-input")
            ?.value
            ?.trim() ||
        "";

    const image =
        $("#post-image-input")
            ?.files?.[0] ||
        null;

    const video =
        $("#post-video-input")
            ?.files?.[0] ||
        null;

    if (
        !caption &&
        !image &&
        !video
    ) {

        toast(
            "Write something or select media."
        );

        return;
    }

    if (
        image &&
        image.size >
            15 * 1024 * 1024
    ) {

        toast(
            "Image is too large. Maximum 15MB."
        );

        return;
    }

    if (
        video &&
        video.size >
            100 * 1024 * 1024
    ) {

        toast(
            "Video is too large. Maximum 100MB."
        );

        return;
    }

    const button =
        $("#publish-post");

    const status =
        $("#upload-status");

    if (button) {
        button.disabled =
            true;

        button.textContent =
            "Posting...";
    }

    if (status) {
        status.textContent =
            "Uploading...";
    }

    try {

        const formData =
            new FormData();

        formData.append(
            "caption",
            caption
        );

        if (image) {

            formData.append(
                "media",
                image
            );
        }

        if (video) {

            formData.append(
                "media",
                video
            );
        }

        const response =
            await apiFetch(
                "/api/posts/create",
                {
                    method: "POST",
                    body: formData,
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            toast(
                data.detail ||
                "Post failed"
            );

            return;
        }

        toast(
            "Post published successfully!"
        );

        closePostComposer();

        await loadFeed();

    } catch (error) {

        console.error(
            "Publish error:",
            error
        );

        toast(
            "Network error while posting"
        );

    } finally {

        if (button) {
            button.disabled =
                false;

            button.textContent =
                "Post";
        }

        if (status) {
            status.textContent =
                "";
        }
    }
}


// ============================================================
// CLOSE COMPOSER
// ============================================================

function closePostComposer() {

    const modal =
        $("#post-composer-modal");

    if (!modal) return;

    modal.remove();
}


// ============================================================
// DISCOVERY
// ============================================================

async function loadDiscovery() {

    const grid =
        $("#discovery-grid");

    if (!grid) return;

    try {

        const response =
            await apiFetch(
                "/api/discovery"
            );

        if (!response.ok) return;

        const data =
            await response.json();

        grid.innerHTML =
            "";

        (data.cards || [])
            .forEach(
                card => {

                    const element =
                        document.createElement(
                            "div"
                        );

                    element.className =
                        "disc-card";

                    element.innerHTML = `
                        <span class="icon">
                            ${escapeHtml(
                                card.icon
                            )}
                        </span>

                        <div class="title">
                            ${escapeHtml(
                                card.title
                            )}
                        </div>

                        <div class="desc">
                            ${escapeHtml(
                                card.desc
                            )}
                        </div>
                    `;

                    element.addEventListener(
                        "click",
                        () =>
                            handleDiscoveryCard(
                                card.id
                            )
                    );

                    grid.appendChild(
                        element
                    );
                }
            );

    } catch (error) {

        console.error(
            "Discovery:",
            error
        );
    }
}


// ============================================================
// DISCOVERY ROUTER
// ============================================================

function handleDiscoveryCard(
    id
) {

    const handlers = {

        "ai-council":
            showAICouncil,

        "creative-studio":
            showStudio,

        "market":
            showMarket,

        "world-map":
            showWorldMap,

        "channels":
            showChannels,

        "communities":
            showCommunities,

        "videos":
            showVideos,

        "settings":
            showSettings,
    };

    const handler =
        handlers[id];

    if (handler) {
        handler();
    } else {
        toast(
            "Coming soon"
        );
    }
}


// ============================================================
// AI COUNCIL
// ============================================================

async function showAICouncil() {

    showSubPage(
        "AI Council",
        async content => {

            content.innerHTML = `
                <h2>AI Council</h2>
                <p class="muted">
                    Choose an AI assistant
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/ai-council"
                );

            const data =
                await response.json();

            (data.ais || [])
                .forEach(
                    ai => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                ${escapeHtml(
                                    ai.icon
                                )}
                            </span>

                            <div class="text">
                                <strong>
                                    ${escapeHtml(
                                        ai.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHtml(
                                        ai.desc
                                    )}
                                </span>
                            </div>
                        `;

                        item.addEventListener(
                            "click",
                            () => {

                                if (
                                    ai.id ===
                                    "education"
                                ) {

                                    showEducationAICountries();

                                } else {

                                    showAIChat(
                                        ai.id
                                    );
                                }
                            }
                        );

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// EDUCATION COUNTRIES
// ============================================================

async function showEducationAICountries() {

    showSubPage(
        "Education AI",
        async content => {

            content.innerHTML = `
                <h2>
                    Step 1 — Choose Country
                </h2>

                <p class="muted">
                    Select your country
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/ai-council/countries"
                );

            const data =
                await response.json();

            (data.countries || [])
                .forEach(
                    country => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                🌍
                            </span>

                            <div class="text">
                                <strong>
                                    ${escapeHtml(
                                        country
                                    )}
                                </strong>
                            </div>
                        `;

                        item.addEventListener(
                            "click",
                            () =>
                                showEducationAILevels(
                                    country
                                )
                        );

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// EDUCATION LEVELS
// ============================================================

async function showEducationAILevels(
    country
) {

    showSubPage(
        `Education — ${country}`,
        async content => {

            content.innerHTML = `
                <h2>
                    Step 2 — Choose Level
                </h2>

                <p class="muted">
                    ${escapeHtml(country)}
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/ai-council/levels"
                );

            const data =
                await response.json();

            (data.levels || [])
                .forEach(
                    level => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                🎓
                            </span>

                            <div class="text">
                                <strong>
                                    ${escapeHtml(
                                        level
                                    )}
                                </strong>
                            </div>
                        `;

                        item.addEventListener(
                            "click",
                            () =>
                                showEducationAIContent(
                                    country,
                                    level
                                )
                        );

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// EDUCATION CONTENT
// ============================================================

async function showEducationAIContent(
    country,
    level
) {

    showSubPage(
        `Education — ${level}`,
        async content => {

            content.innerHTML = `
                <h2>
                    Step 3 — Choose Content
                </h2>

                <p class="muted">
                    ${escapeHtml(country)}
                    •
                    ${escapeHtml(level)}
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/ai-council/content-types"
                );

            const data =
                await response.json();

            (data.content_types || [])
                .forEach(
                    type => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                📄
                            </span>

                            <div class="text">
                                <strong>
                                    ${escapeHtml(
                                        type
                                    )}
                                </strong>
                            </div>
                        `;

                        item.addEventListener(
                            "click",
                            () =>
                                showAIChat(
                                    "education",
                                    {
                                        country,
                                        level,
                                        content:
                                            type,
                                    }
                                )
                        );

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// AI CHAT
// ============================================================

function showAIChat(
    ai,
    context = {}
) {

    showSubPage(
        "AI Chat",
        content => {

            content.innerHTML = `
                <h2>
                    ${escapeHtml(
                        ai
                            .charAt(0)
                            .toUpperCase() +
                        ai.slice(1)
                    )}
                    AI
                </h2>

                <div
                    id="ai-chat-messages"
                    class="chat-msgs">

                    <div class="msg ai">
                        Hello! I'm your
                        ${escapeHtml(
                            context.content ||
                            ""
                        )}
                        assistant for
                        ${escapeHtml(
                            context.level ||
                            ""
                        )}
                        curriculum in
                        ${escapeHtml(
                            context.country ||
                            ""
                        )}.
                        Ask me anything.
                    </div>

                </div>

                <div
                    style="
                        display:flex;
                        gap:8px;
                        margin-top:12px;
                    ">

                    <input
                        id="ai-input"
                        type="text"
                        placeholder="Ask a question..."
                        style="flex:1;">

                    <button
                        id="ai-send"
                        class="btn-primary">
                        Send
                    </button>

                </div>
            `;

            const send =
                async () => {

                    const input =
                        $("#ai-input");

                    const question =
                        input?.value?.trim();

                    if (!question) {
                        return;
                    }

                    const messages =
                        $("#ai-chat-messages");

                    messages.innerHTML += `
                        <div class="msg user">
                            ${escapeHtml(
                                question
                            )}
                        </div>
                    `;

                    input.value = "";

                    try {

                        const params =
                            new URLSearchParams({
                                ai,
                                ...context,
                                q: question,
                            });

                        const response =
                            await apiFetch(
                                `/api/ai-council/chat?${params}`
                            );

                        const data =
                            await response.json();

                        messages.innerHTML += `
                            <div class="msg ai">
                                ${escapeHtml(
                                    data.reply ||
                                    "No response."
                                )}
                            </div>
                        `;

                    } catch {

                        messages.innerHTML += `
                            <div class="msg ai">
                                Error reaching AI.
                            </div>
                        `;
                    }

                    messages.scrollTop =
                        messages.scrollHeight;
                };

            $("#ai-send")
                ?.addEventListener(
                    "click",
                    send
                );

            $("#ai-input")
                ?.addEventListener(
                    "keydown",
                    event => {

                        if (
                            event.key ===
                            "Enter"
                        ) {
                            send();
                        }
                    }
                );
        }
    );
}


// ============================================================
// STUDIO
// ============================================================

async function showStudio() {

    showSubPage(
        "Creative Studio",
        async content => {

            content.innerHTML = `
                <h2>
                    Creative Studio
                </h2>

                <p class="muted">
                    Canva-style tools
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/studio"
                );

            const data =
                await response.json();

            (data.tools || [])
                .forEach(
                    tool => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                ${escapeHtml(
                                    tool.icon
                                )}
                            </span>

                            <div class="text">
                                <strong>
                                    ${escapeHtml(
                                        tool.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHtml(
                                        tool.desc
                                    )}
                                </span>
                            </div>
                        `;

                        item.addEventListener(
                            "click",
                            () =>
                                toast(
                                    `${tool.title} coming soon`
                                )
                        );

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// MARKET
// ============================================================

async function showMarket() {

    showSubPage(
        "Market",
        async content => {

            content.innerHTML = `
                <h2>Market</h2>
                <p class="muted">
                    Buy and sell
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/market/categories"
                );

            const data =
                await response.json();

            (data.categories || [])
                .forEach(
                    category => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                🛍️
                            </span>

                            <div class="text">
                                <strong>
                                    ${escapeHtml(
                                        category.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHtml(
                                        category.desc
                                    )}
                                </span>
                            </div>
                        `;

                        item.addEventListener(
                            "click",
                            () =>
                                toast(
                                    `${category.title} coming soon`
                                )
                        );

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// WORLD MAP
// ============================================================

async function showWorldMap() {

    showSubPage(
        "World Map",
        async content => {

            content.innerHTML = `
                <h2>World Map</h2>
                <p class="muted">
                    Explore the world
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/world-map/countries"
                );

            const data =
                await response.json();

            (data.countries || [])
                .forEach(
                    country => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                🌍
                            </span>

                            <div class="text">

                                <strong>
                                    ${escapeHtml(
                                        country.name
                                    )}
                                </strong>

                                <span>
                                    ${country.users}
                                    users •
                                    ${country.posts}
                                    posts
                                </span>

                            </div>
                        `;

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// CHANNELS
// ============================================================

async function showChannels() {

    showSubPage(
        "Channels",
        async content => {

            content.innerHTML = `
                <h2>Channels</h2>
                <p class="muted">
                    News and media
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/channels"
                );

            const data =
                await response.json();

            (data.channels || [])
                .forEach(
                    channel => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                📺
                            </span>

                            <div class="text">

                                <strong>
                                    ${escapeHtml(
                                        channel.name
                                    )}
                                </strong>

                                <span>
                                    ${escapeHtml(
                                        channel.desc
                                    )}
                                </span>

                            </div>
                        `;

                        item.addEventListener(
                            "click",
                            () =>
                                toast(
                                    `${channel.name} coming soon`
                                )
                        );

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// COMMUNITIES
// ============================================================

async function showCommunities() {

    showSubPage(
        "Communities",
        async content => {

            content.innerHTML = `
                <h2>Communities</h2>
                <p class="muted">
                    Join groups and communities
                </p>
            `;

            const response =
                await apiFetch(
                    "/api/communities/categories"
                );

            const data =
                await response.json();

            (data.categories || [])
                .forEach(
                    category => {

                        const item =
                            document.createElement(
                                "div"
                            );

                        item.className =
                            "sub-item";

                        item.innerHTML = `
                            <span class="icon">
                                👥
                            </span>

                            <div class="text">

                                <strong>
                                    ${escapeHtml(
                                        category.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHtml(
                                        category.desc
                                    )}
                                </span>

                            </div>
                        `;

                        item.addEventListener(
                            "click",
                            () =>
                                toast(
                                    `${category.title} coming soon`
                                )
                        );

                        content.appendChild(
                            item
                        );
                    }
                );
        }
    );
}


// ============================================================
// VIDEOS
// ============================================================

async function showVideos() {

    showSubPage(
        "Videos",
        content => {

            content.innerHTML = `
                <h2>Videos</h2>

                <p class="muted">
                    Short video feed
                </p>

                <div class="sub-item">

                    <span class="icon">
                        ▶️
                    </span>

                    <div class="text">

                        <strong>
                            Video Feed
                        </strong>

                        <span>
                            TikTok-style feed
                            coming in next phase
                        </span>

                    </div>

                </div>
            `;
        }
    );
}


// ============================================================
// SETTINGS
// ============================================================

function showSettings() {

    showSubPage(
        "Settings",
        content => {

            content.innerHTML = `
                <h2>Settings</h2>

                <div
                    class="sub-item"
                    id="setting-manual">

                    <span class="icon">
                        📖
                    </span>

                    <div class="text">
                        <strong>
                            User Manual
                        </strong>

                        <span>
                            How to use the app
                        </span>
                    </div>

                </div>

                <div
                    class="sub-item"
                    id="setting-theme">

                    <span class="icon">
                        🌓
                    </span>

                    <div class="text">
                        <strong>
                            Theme
                        </strong>

                        <span>
                            Light / Dark
                        </span>
                    </div>

                </div>

                <div
                    class="sub-item">

                    <span class="icon">
                        ℹ️
                    </span>

                    <div class="text">
                        <strong>
                            Version
                        </strong>

                        <span>
                            MSAFIRI MEDIA V0.0.1
                        </span>
                    </div>

                </div>

                <div
                    class="sub-item"
                    id="setting-logout">

                    <span class="icon">
                        🚪
                    </span>

                    <div class="text">
                        <strong>
                            Logout
                        </strong>

                        <span>
                            Sign out
                        </span>
                    </div>

                </div>
            `;

            $("#setting-manual")
                ?.addEventListener(
                    "click",
                    showUserManual
                );

            $("#setting-theme")
                ?.addEventListener(
                    "click",
                    toggleTheme
                );

            $("#setting-logout")
                ?.addEventListener(
                    "click",
                    logout
                );
        }
    );
}


// ============================================================
// USER MANUAL
// ============================================================

async function showUserManual() {

    showSubPage(
        "User Manual",
        async content => {

            try {

                const response =
                    await apiFetch(
                        "/api/user-manual"
                    );

                const manual =
                    await response.json();

                content.innerHTML = `
                    <div
                        style="
                            text-align:center;
                            margin-bottom:20px;
                        ">

                        <div
                            class="auth-logo"
                            style="
                                margin:0 auto 12px;
                            ">
                            M
                        </div>

                        <h2>
                            ${escapeHtml(
                                manual.app
                            )}
                        </h2>

                        <p class="muted">
                            ${escapeHtml(
                                manual.tagline
                            )}
                        </p>

                        <p class="muted">
                            Founder:
                            ${escapeHtml(
                                manual.founder
                            )}
                        </p>

                        <p class="muted">
                            ${escapeHtml(
                                manual.company
                            )}
                        </p>

                        <p class="muted">
                            Version:
                            ${escapeHtml(
                                manual.version
                            )}
                        </p>

                    </div>

                    <div class="manual-section">

                        <h3>
                            About MSAFIRI
                        </h3>

                        <p>
                            ${escapeHtml(
                                manual.about
                            )}
                        </p>

                    </div>

                    <div class="manual-section">

                        <h3>
                            Sections
                        </h3>

                        <ul>

                            ${Object.entries(
                                manual.sections ||
                                {}
                            )
                                .map(
                                    ([key, value]) =>
                                        `<li>
                                            <strong>
                                                ${escapeHtml(
                                                    key
                                                )}:
                                            </strong>
                                            ${escapeHtml(
                                                value
                                            )}
                                        </li>`
                                )
                                .join("")}

                        </ul>

                    </div>

                    <div class="manual-section">

                        <h3>
                            How to Use
                        </h3>

                        <ul>

                            ${Object.entries(
                                manual.how_to_use ||
                                {}
                            )
                                .map(
                                    ([key, value]) =>
                                        `<li>
                                            <strong>
                                                ${escapeHtml(
                                                    key.replace(
                                                        /_/g,
                                                        " "
                                                    )
                                                )}:
                                            </strong>
                                            ${escapeHtml(
                                                value
                                            )}
                                        </li>`
                                )
                                .join("")}

                        </ul>

                    </div>

                    <div class="manual-section">

                        <h3>
                            Support
                        </h3>

                        <p>
                            ${escapeHtml(
                                manual.support
                            )}
                        </p>

                    </div>

                    <button
                        class="btn-primary"
                        id="download-manual"
                        style="width:100%;margin-top:16px;">

                        📥 Download User Manual

                    </button>
                `;

                $("#download-manual")
                    ?.addEventListener(
                        "click",
                        () =>
                            downloadManual(
                                manual
                            )
                    );

            } catch (error) {

                console.error(error);

                content.innerHTML = `
                    <p class="muted">
                        Unable to load manual.
                    </p>
                `;
            }
        }
    );
}


// ============================================================
// DOWNLOAD MANUAL
// ============================================================

function downloadManual(
    manual
) {

    const text = `
MSAFIRI GLOBAL MEDIA
${manual.tagline}

Founder:
${manual.founder}

Company:
${manual.company}

Version:
${manual.version}


ABOUT
${manual.about}


SECTIONS
${Object.entries(
    manual.sections || {}
)
    .map(
        ([key, value]) =>
            `- ${key}: ${value}`
    )
    .join("\n")}


HOW TO USE
${Object.entries(
    manual.how_to_use || {}
)
    .map(
        ([key, value]) =>
            `- ${key}: ${value}`
    )
    .join("\n")}


SUPPORT
${manual.support}
`;

    const blob =
        new Blob(
            [text],
            {
                type:
                    "text/plain;charset=utf-8",
            }
        );

    const url =
        URL.createObjectURL(
            blob
        );

    const anchor =
        document.createElement(
            "a"
        );

    anchor.href =
        url;

    anchor.download =
        "MSAFIRI-UserManual.txt";

    document.body.appendChild(
        anchor
    );

    anchor.click();

    anchor.remove();

    URL.revokeObjectURL(
        url
    );

    toast(
        "User Manual downloaded"
    );
}


// ============================================================
// DOTS MENU
// ============================================================

function setupDotsMenu() {

    const dots =
        $("#dots-btn");

    const menu =
        $("#dots-menu");

    if (!dots || !menu) {
        return;
    }

    dots.addEventListener(
        "click",
        event => {

            event.stopPropagation();

            menu.classList.toggle(
                "hidden"
            );
        }
    );

    document.addEventListener(
        "click",
        () => {

            menu.classList.add(
                "hidden"
            );
        }
    );

    menu.querySelectorAll(
        "button"
    ).forEach(
        button => {

            button.addEventListener(
                "click",
                event => {

                    event.stopPropagation();

                    const action =
                        button.dataset.action;

                    if (
                        action ===
                        "manual"
                    ) {
                        showUserManual();
                    }

                    if (
                        action ===
                        "settings"
                    ) {
                        showSettings();
                    }

                    if (
                        action ===
                        "logout"
                    ) {
                        logout();
                    }

                    menu.classList.add(
                        "hidden"
                    );
                }
            );
        }
    );
}


// ============================================================
// CHATS
// ============================================================

async function loadChats() {

    const list =
        $("#chat-list");

    if (!list) return;

    try {

        const response =
            await apiFetch(
                "/api/messages"
            );

        if (!response.ok) {

            list.innerHTML = `
                <p class="muted"
                   style="padding:20px;text-align:center;">
                    No chats yet
                </p>
            `;

            return;
        }

        const data =
            await response.json();

        const messages =
            data.messages || [];

        if (
            messages.length === 0
        ) {

            list.innerHTML = `
                <p class="muted"
                   style="padding:20px;text-align:center;">
                    No chats yet
                </p>
            `;

            return;
        }

        list.innerHTML = "";

        messages.forEach(
            message => {

                const item =
                    document.createElement(
                        "div"
                    );

                item.className =
                    "sub-item";

                item.innerHTML = `
                    <span class="icon">
                        💬
                    </span>

                    <div class="text">

                        <strong>
                            ${escapeHtml(
                                message.username ||
                                "User"
                            )}
                        </strong>

                        <span>
                            ${escapeHtml(
                                message.text ||
                                message.content ||
                                ""
                            )}
                        </span>

                    </div>
                `;

                list.appendChild(
                    item
                );
            }
        );

    } catch (error) {

        console.error(
            "Chats:",
            error
        );

        list.innerHTML = `
            <p class="muted"
               style="padding:20px;text-align:center;">
                No chats yet
            </p>
        `;
    }
}


// ============================================================
// PROFILE
// ============================================================

async function loadProfile() {

    try {

        const response =
            await apiFetch(
                "/api/auth/me"
            );

        if (!response.ok) {
            return;
        }

        const user =
            await response.json();

        currentUser =
            user;

        const name =
            $("#profile-name");

        const username =
            $("#profile-username");

        const bio =
            $("#profile-bio");

        const avatar =
            $("#profile-avatar");

        if (name) {

            name.textContent =
                user.full_name ||
                user.username ||
                "User";
        }

        if (username) {

            username.textContent =
                "@" +
                (
                    user.username ||
                    "user"
                );
        }

        if (bio) {

            bio.textContent =
                user.bio ||
                "Welcome to Msafiri";
        }

        if (avatar) {

            avatar.textContent =
                (
                    user.full_name ||
                    user.username ||
                    "U"
                )
                    .charAt(0)
                    .toUpperCase();
        }

    } catch (error) {

        console.error(
            "Profile:",
            error
        );
    }
}


// ============================================================
// THEME
// ============================================================

function toggleTheme() {

    const html =
        document.documentElement;

    const current =
        html.dataset.theme ||
        "dark";

    const next =
        current === "dark"
            ? "light"
            : "dark";

    html.dataset.theme =
        next;

    localStorage.setItem(
        "theme",
        next
    );

    toast(
        `Theme: ${next}`
    );
}


function loadSavedTheme() {

    const theme =
        localStorage.getItem(
            "theme"
        );

    if (theme) {

        document.documentElement
            .dataset
            .theme = theme;
    }
}


// ============================================================
// LOGOUT
// ============================================================

async function logout() {

    try {

        await apiFetch(
            "/api/auth/logout",
            {
                method: "POST",
            }
        );

    } catch {}

    localStorage.removeItem(
        "token"
    );

    currentUser =
        null;

    location.reload();
}


// ============================================================
// AUTH CHECK HELPER
// ============================================================

function ensureLoggedIn() {

    if (!currentUser) {

        toast(
            "Please login first."
        );

        showAuth();

        return false;
    }

    return true;
}


// ============================================================
// TOAST
// ============================================================

function toast(
    message
) {

    const old =
        document.querySelectorAll(
            ".msafiri-toast"
        );

    if (old.length > 3) {
        old[0].remove();
    }

    const element =
        document.createElement(
            "div"
        );

    element.className =
        "msafiri-toast";

    element.textContent =
        message;

    element.style.cssText = `
        position:fixed;
        left:50%;
        bottom:30px;
        transform:translateX(-50%);
        z-index:100000;
        padding:12px 18px;
        border-radius:12px;
        background:#111827;
        color:white;
        font-size:14px;
        box-shadow:0 10px 30px rgba(0,0,0,.25);
    `;

    document.body.appendChild(
        element
    );

    setTimeout(
        () => {

            element.remove();

        },
        2500
    );
}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(
    value
) {

    const div =
        document.createElement(
            "div"
        );

    div.textContent =
        value == null
            ? ""
            : String(value);

    return div.innerHTML;
}


function escapeAttribute(
    value
) {

    return escapeHtml(
        value
    )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#39;"
        );
}


// ============================================================
// TIME AGO
// ============================================================

function timeAgo(
    iso
) {

    if (!iso) {
        return "now";
    }

    const date =
        new Date(iso);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "now";
    }

    const seconds =
        Math.floor(
            (
                Date.now() -
                date.getTime()
            ) / 1000
        );

    if (seconds < 10) {
        return "now";
    }

    if (seconds < 60) {
        return `${seconds}s`;
    }

    if (seconds < 3600) {
        return `${Math.floor(
            seconds / 60
        )}m`;
    }

    if (seconds < 86400) {
        return `${Math.floor(
            seconds / 3600
        )}h`;
    }

    return `${Math.floor(
        seconds / 86400
    )}d`;
}


// ============================================================
// COMPOSER CSS
// ============================================================

function injectComposerStyles() {

    if (
        document.getElementById(
            "msafiri-composer-css"
        )
    ) {
        return;
    }

    const style =
        document.createElement(
            "style"
        );

    style.id =
        "msafiri-composer-css";

    style.textContent = `

        .post-composer-overlay {
            position:fixed;
            inset:0;
            z-index:99999;
            background:rgba(0,0,0,.65);
            display:flex;
            align-items:center;
            justify-content:center;
            padding:20px;
        }

        .post-composer-card {
            width:min(600px, 100%);
            max-height:90vh;
            overflow:auto;
            background:var(
                --card-bg,
                #ffffff
            );
            color:var(
                --text-color,
                #111827
            );
            border-radius:20px;
            padding:20px;
            box-shadow:0 20px 70px rgba(0,0,0,.35);
        }

        .composer-header {
            display:flex;
            align-items:center;
            justify-content:space-between;
            margin-bottom:18px;
        }

        .composer-header h2 {
            margin:0;
        }

        .composer-header button {
            border:0;
            background:none;
            font-size:30px;
            cursor:pointer;
        }

        .composer-user {
            display:flex;
            gap:10px;
            align-items:center;
            margin-bottom:14px;
        }

        .composer-user small {
            display:block;
            opacity:.6;
        }

        .composer-avatar {
            width:42px;
            height:42px;
            border-radius:50%;
            display:flex;
            align-items:center;
            justify-content:center;
            background:linear-gradient(
                135deg,
                #6c5ce7,
                #8e44ad
            );
            color:white;
            font-weight:bold;
        }

        #post-caption-input {
            width:100%;
            min-height:120px;
            resize:vertical;
            border:1px solid #ddd;
            border-radius:14px;
            padding:14px;
            font-size:16px;
            outline:none;
            box-sizing:border-box;
        }

        .media-preview {
            margin-top:14px;
        }

        .media-preview img,
        .media-preview video {
            width:100%;
            max-height:350px;
            object-fit:contain;
            border-radius:14px;
            background:#000;
        }

        .composer-tools {
            display:flex;
            gap:10px;
            flex-wrap:wrap;
            margin-top:14px;
        }

        .composer-tool {
            border:1px solid #ddd;
            padding:10px 14px;
            border-radius:12px;
            cursor:pointer;
            background:transparent;
        }

        .composer-footer {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:10px;
            margin-top:16px;
        }

        .post-media-wrap {
            margin-top:10px;
        }

        .post-media,
        .post-video {
            width:100%;
            max-height:650px;
            object-fit:cover;
            border-radius:12px;
        }

        .post-avatar-img {
            width:42px;
            height:42px;
            border-radius:50%;
            object-fit:cover;
        }

        .post-action.liked {
            font-weight:bold;
        }

        .post-action.saved {
            font-weight:bold;
        }

        .comments-area {
            margin-top:10px;
        }

        .comment-item {
            display:flex;
            gap:10px;
            margin:10px 0;
        }

        .comment-avatar {
            width:34px;
            height:34px;
            min-width:34px;
            border-radius:50%;
            display:flex;
            align-items:center;
            justify-content:center;
            background:#eee;
            font-weight:bold;
        }

        .comment-body {
            flex:1;
        }

        .comment-body p {
            margin:3px 0;
        }

        .comment-body small {
            opacity:.55;
        }

        .comment-form {
            display:flex;
            gap:8px;
            margin-top:12px;
        }

        .comment-form input {
            flex:1;
            min-width:0;
            padding:10px 12px;
            border-radius:12px;
            border:1px solid #ddd;
        }

    `;

    document.head.appendChild(
        style
    );
}


// ============================================================
// START SAVED THEME
// ============================================================

loadSavedTheme();


// ============================================================
// GLOBAL EXPORTS
// ============================================================

window.openPostComposer =
    openPostComposer;

window.loadFeed =
    loadFeed;

window.logout =
    logout;

window.showSettings =
    showSettings;

window.showUserManual =
    showUserManual;
