/* ============================================================
   MSAFIRI GLOBAL MEDIA
   APP.JS — PHASE 2
   ------------------------------------------------------------
   Frontend controller for:
   - Splash screen
   - Authentication
   - Home / Feed
   - People search
   - User profiles
   - Posts
   - Likes
   - Comments
   - Saves
   - Shares
   - Stories
   - Discovery
   - AI Council navigation
   - Creative Studio
   - Market
   - World Map
   - Channels
   - Communities
   - Videos
   - Chats
   - User Manual
   - Settings
   - Theme
   - Back navigation
   ------------------------------------------------------------
   Backend:
   FastAPI + SQLAlchemy
   ============================================================ */

"use strict";

/* ============================================================
   GLOBAL CONFIG
   ============================================================ */

const API = window.location.origin;

const APP_NAME = "MSAFIRI GLOBAL MEDIA";
const APP_VERSION = "Media V0.0.1";
const FOUNDER = "MSAFIRI WILLIAM MUNGA";
const COMPANY = "ZetroLink Technology Limited";

const TOKEN_KEY = "msafiri_access_token";
const USER_KEY = "msafiri_current_user";
const THEME_KEY = "msafiri_theme";

/* ============================================================
   GLOBAL STATE
   ============================================================ */

let TOKEN = localStorage.getItem(TOKEN_KEY) || null;

let CURRENT_USER = null;

try {
    const savedUser = localStorage.getItem(USER_KEY);
    CURRENT_USER = savedUser ? JSON.parse(savedUser) : null;
} catch (error) {
    console.warn("Could not restore saved user:", error);
    CURRENT_USER = null;
}

let CURRENT_PAGE = "home";

let PAGE_HISTORY = [];

let CURRENT_FEED = "for-you";

let CACHED_POSTS = [];

let CACHED_CHATS = [];

let SEARCH_RESULTS = [];

let SEARCH_TIMER = null;

let CURRENT_PROFILE_ID = null;

let CURRENT_CHAT_USER = null;

let CURRENT_POST_ID = null;

let SPLASH_DONE = false;


/* ============================================================
   DOM HELPER
   ============================================================ */

function $(selector) {
    return document.querySelector(selector);
}

function $all(selector) {
    return Array.from(document.querySelectorAll(selector));
}


/* ============================================================
   SAFE HTML
   ============================================================ */

function escapeHTML(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/* ============================================================
   INITIALIZATION
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
    try {
        initializeTheme();
        initializeEvents();
        initializeSplash();

        /*
         * IMPORTANT:
         * The splash screen uses CSS animation.
         * We do not depend only on animationend because some
         * browsers can behave differently with visibility.
         */
        setTimeout(() => {
            finishSplash();
        }, 2800);

    } catch (error) {
        console.error("Application initialization error:", error);
        emergencyStart();
    }
});


/* ============================================================
   SPLASH
   ============================================================ */

function initializeSplash() {
    const splash = $("#splash");

    if (!splash) {
        finishSplash();
        return;
    }

    splash.addEventListener("animationend", (event) => {
        if (event.animationName === "fadeOut") {
            finishSplash();
        }
    });
}


function finishSplash() {
    if (SPLASH_DONE) {
        return;
    }

    SPLASH_DONE = true;

    const splash = $("#splash");

    if (splash) {
        splash.classList.add("hidden");
    }

    if (TOKEN) {
        showApp();

        loadCurrentUser()
            .then(() => {
                loadHome();
            })
            .catch(() => {
                /*
                 * If token is invalid, show authentication.
                 */
                showAuth();
            });

    } else {
        showAuth();
    }
}


function emergencyStart() {
    const splash = $("#splash");
    const auth = $("#auth-screen");
    const app = $("#app");

    if (splash) {
        splash.classList.add("hidden");
    }

    if (TOKEN) {
        if (app) app.classList.remove("hidden");
        if (auth) auth.classList.add("hidden");
        loadHome();
    } else {
        if (auth) auth.classList.remove("hidden");
        if (app) app.classList.add("hidden");
    }
}


/* ============================================================
   AUTH / APP VISIBILITY
   ============================================================ */

function showAuth() {
    const auth = $("#auth-screen");
    const app = $("#app");

    if (auth) {
        auth.classList.remove("hidden");
    }

    if (app) {
        app.classList.add("hidden");
    }
}


function showApp() {
    const auth = $("#auth-screen");
    const app = $("#app");

    if (auth) {
        auth.classList.add("hidden");
    }

    if (app) {
        app.classList.remove("hidden");
    }

    updatePageTitle("MSAFIRI");
}


/* ============================================================
   EVENTS
   ============================================================ */

function initializeEvents() {

    /* AUTH TABS */

    $all(".auth-tab").forEach((button) => {
        button.addEventListener("click", () => {
            switchAuthTab(button.dataset.tab);
        });
    });


    /* LOGIN */

    const loginForm = $("#login-form");

    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            await login();
        });
    }


    /* REGISTER */

    const registerForm = $("#register-form");

    if (registerForm) {
        registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            await register();
        });
    }


    /* BOTTOM NAV */

    $all(".nav-btn").forEach((button) => {
        button.addEventListener("click", () => {
            const page = button.dataset.nav;

            if (page) {
                navigate(page);
            }
        });
    });


    /* BACK */

    const backButton = $("#back-btn");

    if (backButton) {
        backButton.addEventListener("click", () => {
            goBack();
        });
    }


    /* THREE DOTS */

    const dotsButton = $("#dots-btn");

    if (dotsButton) {
        dotsButton.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleDotsMenu();
        });
    }


    /* CLOSE DROPDOWN WHEN CLICKING OUTSIDE */

    document.addEventListener("click", (event) => {
        const menu = $("#dots-menu");
        const button = $("#dots-btn");

        if (
            menu &&
            !menu.contains(event.target) &&
            button &&
            !button.contains(event.target)
        ) {
            menu.classList.add("hidden");
        }
    });


    /* DROPDOWN */

    $all("#dots-menu button").forEach((button) => {
        button.addEventListener("click", () => {
            const action = button.dataset.action;

            closeDotsMenu();

            if (action === "manual") {
                showUserManual();
            }

            if (action === "settings") {
                openSettings();
            }

            if (action === "logout") {
                logout();
            }
        });
    });


    /* SEARCH */

    const searchInput = $("#search-input");

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            const query = searchInput.value.trim();

            clearTimeout(SEARCH_TIMER);

            if (!query) {
                closeSearchResults();
                return;
            }

            SEARCH_TIMER = setTimeout(() => {
                searchPeople(query);
            }, 350);
        });

        searchInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();

                const query = searchInput.value.trim();

                if (query) {
                    searchPeople(query);
                }
            }
        });
    }


    /* FEED TABS */

    $all(".feed-tab").forEach((button) => {
        button.addEventListener("click", () => {
            $all(".feed-tab").forEach((item) => {
                item.classList.remove("active");
            });

            button.classList.add("active");

            CURRENT_FEED = button.dataset.feed || "for-you";

            loadFeed();
        });
    });


    /* CREATE POST */

    const createButton = $("#fab-create");

    if (createButton) {
        createButton.addEventListener("click", () => {
            openCreatePost();
        });
    }


    /* STORY */

    const storyButton = $("#add-story-btn");

    if (storyButton) {
        storyButton.addEventListener("click", () => {
            openCreateStory();
        });
    }


    /* EDIT PROFILE */

    const editProfileButton = $("#edit-profile-btn");

    if (editProfileButton) {
        editProfileButton.addEventListener("click", () => {
            openEditProfile();
        });
    }


    /* MODAL CLOSE */

    const modalClose = $("#modal-close");

    if (modalClose) {
        modalClose.addEventListener("click", closeModal);
    }

    const modal = $("#modal");

    if (modal) {
        modal.addEventListener("click", (event) => {
            if (event.target === modal) {
                closeModal();
            }
        });
    }


    /* ESCAPE KEY */

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeModal();
            closeDotsMenu();
        }
    });
}


/* ============================================================
   AUTH TABS
   ============================================================ */

function switchAuthTab(tab) {

    $all(".auth-tab").forEach((button) => {
        button.classList.toggle(
            "active",
            button.dataset.tab === tab
        );
    });

    const loginForm = $("#login-form");
    const registerForm = $("#register-form");

    if (tab === "login") {

        if (loginForm) {
            loginForm.classList.remove("hidden");
        }

        if (registerForm) {
            registerForm.classList.add("hidden");
        }

    } else {

        if (loginForm) {
            loginForm.classList.add("hidden");
        }

        if (registerForm) {
            registerForm.classList.remove("hidden");
        }
    }
}


/* ============================================================
   API HELPER
   ============================================================ */

async function apiFetch(path, options = {}) {

    const config = {
        ...options,
        headers: {
            ...(options.headers || {})
        }
    };

    /*
     * Do not automatically send Content-Type for FormData.
     * Browser must generate multipart boundary.
     */

    if (
        TOKEN &&
        !config.headers.Authorization
    ) {
        config.headers.Authorization = `Bearer ${TOKEN}`;
    }

    let response;

    try {
        response = await fetch(`${API}${path}`, config);
    } catch (error) {
        console.error("Network error:", error);
        throw new Error("Network connection failed.");
    }

    const contentType =
        response.headers.get("content-type") || "";

    let data = null;

    try {

        if (contentType.includes("application/json")) {
            data = await response.json();

        } else {
            data = await response.text();
        }

    } catch (error) {
        data = null;
    }


    if (!response.ok) {

        let message =
            `Request failed (${response.status})`;

        if (data) {

            if (typeof data === "object") {
                message =
                    data.detail ||
                    data.message ||
                    message;
            } else if (typeof data === "string" && data.trim()) {
                message = data;
            }
        }

        const error = new Error(message);
        error.status = response.status;
        error.data = data;

        throw error;
    }

    return data;
}


/* ============================================================
   LOGIN
   ============================================================ */

async function login() {

    const usernameInput = $("#login-username");
    const passwordInput = $("#login-password");

    if (!usernameInput || !passwordInput) {
        return;
    }

    const username =
        usernameInput.value.trim();

    const password =
        passwordInput.value;

    if (!username || !password) {
        toast("Enter username/email and password.");
        return;
    }

    const button =
        $("#login-form .btn-primary");

    setButtonLoading(button, true, "Logging in...");

    try {

        /*
         * Most FastAPI OAuth2 implementations expect
         * application/x-www-form-urlencoded.
         */

        const form = new URLSearchParams();

        form.append("username", username);
        form.append("password", password);

        let data;

        try {

            data = await apiFetch(
                "/api/auth/login",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/x-www-form-urlencoded"
                    },
                    body: form.toString()
                }
            );

        } catch (firstError) {

            /*
             * Some custom auth routers use JSON.
             * Try JSON as a fallback.
             */

            data = await apiFetch(
                "/api/auth/login",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        username,
                        email: username,
                        password
                    })
                }
            );
        }


        const token =
            data.access_token ||
            data.token ||
            data.accessToken;

        if (!token) {
            throw new Error(
                "Login succeeded but no access token was returned."
            );
        }

        TOKEN = token;

        localStorage.setItem(
            TOKEN_KEY,
            TOKEN
        );


        CURRENT_USER =
            data.user ||
            data.current_user ||
            data.profile ||
            null;


        if (CURRENT_USER) {
            saveCurrentUser(CURRENT_USER);
        }


        showApp();

        await loadCurrentUser();

        navigate("home", false);

        toast("Welcome back!");

        await loadHome();

    } catch (error) {

        console.error("Login error:", error);

        toast(
            error.message ||
            "Login failed."
        );

    } finally {

        setButtonLoading(
            button,
            false,
            "Login"
        );
    }
}


/* ============================================================
   REGISTER
   ============================================================ */

async function register() {

    const username =
        $("#reg-username")?.value.trim();

    const email =
        $("#reg-email")?.value.trim();

    const fullName =
        $("#reg-fullname")?.value.trim();

    const password =
        $("#reg-password")?.value;

    if (
        !username ||
        !email ||
        !fullName ||
        !password
    ) {
        toast("Please fill all registration fields.");
        return;
    }

    if (password.length < 6) {
        toast("Password must contain at least 6 characters.");
        return;
    }

    const button =
        $("#register-form .btn-primary");

    setButtonLoading(
        button,
        true,
        "Creating..."
    );

    try {

        let data;

        /*
         * First try JSON.
         */

        try {

            data = await apiFetch(
                "/api/auth/register",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        username,
                        email,
                        full_name: fullName,
                        password
                    })
                }
            );

        } catch (jsonError) {

            /*
             * Fallback for Form based auth.
             */

            const form =
                new URLSearchParams();

            form.append("username", username);
            form.append("email", email);
            form.append("full_name", fullName);
            form.append("password", password);

            data = await apiFetch(
                "/api/auth/register",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/x-www-form-urlencoded"
                    },
                    body: form.toString()
                }
            );
        }


        const token =
            data?.access_token ||
            data?.token ||
            data?.accessToken;


        if (token) {

            TOKEN = token;

            localStorage.setItem(
                TOKEN_KEY,
                TOKEN
            );

            CURRENT_USER =
                data.user ||
                data.current_user ||
                null;

            if (CURRENT_USER) {
                saveCurrentUser(CURRENT_USER);
            }

            showApp();

            await loadCurrentUser();

            navigate("home", false);

            await loadHome();

            toast("Account created successfully!");

        } else {

            toast(
                "Account created. Please login."
            );

            switchAuthTab("login");

            const loginUsername =
                $("#login-username");

            if (loginUsername) {
                loginUsername.value = username;
            }
        }

    } catch (error) {

        console.error(
            "Registration error:",
            error
        );

        toast(
            error.message ||
            "Registration failed."
        );

    } finally {

        setButtonLoading(
            button,
            false,
            "Create Account"
        );
    }
}


/* ============================================================
   CURRENT USER
   ============================================================ */

async function loadCurrentUser() {

    if (!TOKEN) {
        return null;
    }

    /*
     * We don't know which exact current-user endpoint
     * your auth router exposes, so try common endpoints.
     */

    const candidates = [
        "/api/auth/me",
        "/api/profile/me",
        "/api/auth/user"
    ];

    for (const endpoint of candidates) {

        try {

            const data =
                await apiFetch(endpoint);

            const user =
                data?.user ||
                data?.profile ||
                data;

            if (
                user &&
                typeof user === "object" &&
                user.id
            ) {

                CURRENT_USER = user;

                saveCurrentUser(user);

                updateOwnProfileUI();

                return user;
            }

        } catch (error) {
            /*
             * Try next endpoint.
             */
        }
    }

    /*
     * If backend does not expose /me,
     * keep locally stored user.
     */

    if (CURRENT_USER) {
        updateOwnProfileUI();
    }

    return CURRENT_USER;
}


function saveCurrentUser(user) {

    CURRENT_USER = user;

    try {
        localStorage.setItem(
            USER_KEY,
            JSON.stringify(user)
        );
    } catch (error) {
        console.warn(
            "Could not save user:",
            error
        );
    }
}


function updateOwnProfileUI() {

    if (!CURRENT_USER) {
        return;
    }

    const name =
        CURRENT_USER.full_name ||
        CURRENT_USER.username ||
        "User";

    const username =
        CURRENT_USER.username ||
        "user";

    const bio =
        CURRENT_USER.bio ||
        "Welcome to Msafiri";

    const nameElement =
        $("#profile-name");

    const usernameElement =
        $("#profile-username");

    const bioElement =
        $("#profile-bio");

    const avatar =
        $("#profile-avatar");

    if (nameElement) {
        nameElement.textContent = name;
    }

    if (usernameElement) {
        usernameElement.textContent =
            `@${username}`;
    }

    if (bioElement) {
        bioElement.textContent = bio;
    }

    if (avatar) {

        if (CURRENT_USER.avatar_url) {

            avatar.innerHTML =
                `<img src="${escapeHTML(
                    mediaURL(CURRENT_USER.avatar_url)
                )}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;

        } else {

            avatar.textContent =
                getInitial(
                    name
                );
        }
    }
}


/* ============================================================
   NAVIGATION
   ============================================================ */

function navigate(page, remember = true) {

    const allowed = [
        "home",
        "discovery",
        "chats",
        "profile",
        "sub"
    ];

    if (!allowed.includes(page)) {
        page = "home";
    }

    if (
        remember &&
        CURRENT_PAGE !== page &&
        CURRENT_PAGE !== "sub"
    ) {
        PAGE_HISTORY.push(
            CURRENT_PAGE
        );
    }

    CURRENT_PAGE = page;


    $all(".page").forEach((section) => {
        section.classList.remove("active");
    });


    const pageElement =
        $(`#page-${page}`);

    if (pageElement) {
        pageElement.classList.add("active");
    }


    /*
     * Bottom navigation only reflects
     * the four main pages.
     */

    let navPage = page;

    if (page === "sub") {
        navPage = inferParentNavigation();
    }

    $all(".nav-btn").forEach((button) => {

        button.classList.toggle(
            "active",
            button.dataset.nav === navPage
        );
    });


    updateBackButton();

    if (page === "home") {
        updatePageTitle("MSAFIRI");
        loadHome();
    }

    if (page === "discovery") {
        updatePageTitle("Discovery");
        loadDiscovery();
    }

    if (page === "chats") {
        updatePageTitle("Chats");
        loadChats();
    }

    if (page === "profile") {
        updatePageTitle("Profile");
        loadMyProfile();
    }
}


function inferParentNavigation() {

    if (
        PAGE_HISTORY.length &&
        [
            "home",
            "discovery",
            "chats",
            "profile"
        ].includes(
            PAGE_HISTORY[
                PAGE_HISTORY.length - 1
            ]
        )
    ) {
        return PAGE_HISTORY[
            PAGE_HISTORY.length - 1
        ];
    }

    return "discovery";
}


function goBack() {

    if (
        PAGE_HISTORY.length === 0
    ) {

        navigate(
            "home",
            false
        );

        return;
    }

    const previous =
        PAGE_HISTORY.pop();

    navigate(
        previous,
        false
    );
}


function updateBackButton() {

    const button =
        $("#back-btn");

    if (!button) {
        return;
    }

    if (
        CURRENT_PAGE === "sub" ||
        PAGE_HISTORY.length > 0
    ) {
        button.classList.remove("hidden");
    } else {
        button.classList.add("hidden");
    }
}


function updatePageTitle(title) {

    const element =
        $("#page-title");

    if (element) {
        element.textContent =
            title || "MSAFIRI";
    }
}


/* ============================================================
   HOME
   ============================================================ */

async function loadHome() {

    try {

        await Promise.allSettled([
            loadFeed(),
            loadStories()
        ]);

    } catch (error) {
        console.error(
            "Home loading error:",
            error
        );
    }
}


/* ============================================================
   FEED
   ============================================================ */

async function loadFeed() {

    const feed =
        $("#feed");

    if (!feed) {
        return;
    }

    feed.innerHTML =
        `<div class="muted" style="padding:20px;text-align:center;">
            Loading posts...
        </div>`;

    try {

        let data =
            await apiFetch(
                "/api/feed"
            );

        let posts =
            extractPosts(data);

        /*
         * Following filter is handled client-side
         * only when backend doesn't provide a separate
         * endpoint.
         */

        if (
            CURRENT_FEED === "following" &&
            CURRENT_USER?.id
        ) {

            /*
             * Keep all posts if no follow metadata exists.
             * This avoids falsely hiding posts.
             */

            posts =
                posts.filter(
                    (post) =>
                        post.user_id !==
                        CURRENT_USER.id
                );
        }


        CACHED_POSTS = posts;

        renderFeed(
            posts
        );

    } catch (error) {

        console.error(
            "Feed error:",
            error
        );

        feed.innerHTML = `
            <div class="post-card">
                <strong>Unable to load feed</strong>
                <p class="muted" style="margin-top:8px;">
                    ${escapeHTML(
                        error.message
                    )}
                </p>
                <button
                    class="btn-secondary"
                    style="margin-top:12px;"
                    onclick="loadFeed()"
                >
                    Retry
                </button>
            </div>
        `;
    }
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

    return [];
}


/* ============================================================
   RENDER FEED
   ============================================================ */

function renderFeed(posts) {

    const feed =
        $("#feed");

    if (!feed) {
        return;
    }

    if (!posts.length) {

        feed.innerHTML = `
            <div class="post-card" style="text-align:center;">
                <div style="font-size:40px;">🌍</div>
                <strong>No posts yet</strong>
                <p class="muted" style="margin-top:6px;">
                    Be the first person to share something.
                </p>
            </div>
        `;

        return;
    }


    feed.innerHTML =
        posts
            .map(
                (post) =>
                    renderPost(post)
            )
            .join("");
}


/* ============================================================
   POST HTML
   ============================================================ */

function renderPost(post) {

    const name =
        post.full_name ||
        post.username ||
        "User";

    const username =
        post.username ||
        "user";

    const avatar =
        post.avatar_url
            ? `<img src="${escapeHTML(
                mediaURL(post.avatar_url)
              )}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`
            : escapeHTML(
                getInitial(name)
              );


    let mediaHTML = "";

    if (
        post.media_url &&
        post.media_type === "image"
    ) {

        mediaHTML = `
            <img
                class="post-media"
                src="${escapeHTML(
                    mediaURL(post.media_url)
                )}"
                alt="Post image"
                loading="lazy"
            >
        `;

    } else if (
        post.media_url &&
        post.media_type === "video"
    ) {

        mediaHTML = `
            <video
                class="post-media"
                src="${escapeHTML(
                    mediaURL(post.media_url)
                )}"
                controls
                playsinline
                preload="metadata"
            ></video>
        `;
    }


    const liked =
        post.liked
            ? "liked"
            : "";

    const likeIcon =
        post.liked
            ? "❤️"
            : "♡";

    const saveIcon =
        post.saved
            ? "🔖"
            : "🔖";


    return `
        <article
            class="post-card"
            data-post-id="${Number(post.id) || 0}"
        >

            <div
                class="post-header"
                onclick="openUserProfile(${Number(post.user_id) || 0})"
                style="cursor:pointer;"
            >

                <div class="post-avatar">
                    ${avatar}
                </div>

                <div class="post-user">
                    <strong>
                        ${escapeHTML(name)}
                    </strong>

                    <span>
                        @${escapeHTML(username)}
                        ${post.created_at
                            ? ` · ${formatTime(post.created_at)}`
                            : ""}
                    </span>
                </div>

            </div>


            ${
                post.caption
                    ? `
                        <div class="post-caption">
                            ${formatText(
                                post.caption
                            )}
                        </div>
                      `
                    : ""
            }


            ${mediaHTML}


            <div class="post-actions">

                <button
                    class="${liked}"
                    onclick="toggleLike(${Number(post.id) || 0})"
                >
                    ${likeIcon}
                    <span>
                        ${Number(post.likes) || 0}
                    </span>
                </button>

                <button
                    onclick="openComments(${Number(post.id) || 0})"
                >
                    💬
                    <span>
                        ${Number(post.comments) || 0}
                    </span>
                </button>

                <button
                    onclick="toggleSave(${Number(post.id) || 0})"
                >
                    ${saveIcon}
                    <span>
                        ${Number(post.saves) || 0}
                    </span>
                </button>

                <button
                    onclick="sharePost(${Number(post.id) || 0})"
                >
                    ↗️
                    <span>
                        ${Number(post.shares) || 0}
                    </span>
                </button>

            </div>

        </article>
    `;
}


/* ============================================================
   LIKE
   ============================================================ */

async function toggleLike(postId) {

    if (!requireLogin()) {
        return;
    }

    try {

        const result =
            await apiFetch(
                `/api/posts/${postId}/like`,
                {
                    method: "POST"
                }
            );

        const post =
            CACHED_POSTS.find(
                (item) =>
                    Number(item.id) ===
                    Number(postId)
            );

        if (post) {

            post.liked =
                !!result.liked;

            post.likes =
                Number(result.likes) || 0;
        }

        renderFeed(
            CACHED_POSTS
        );

    } catch (error) {

        console.error(
            "Like error:",
            error
        );

        toast(
            error.message ||
            "Could not update like."
        );
    }
}


/* ============================================================
   SAVE
   ============================================================ */

async function toggleSave(postId) {

    if (!requireLogin()) {
        return;
    }

    try {

        const result =
            await apiFetch(
                `/api/posts/${postId}/save`,
                {
                    method: "POST"
                }
            );

        const post =
            CACHED_POSTS.find(
                (item) =>
                    Number(item.id) ===
                    Number(postId)
            );

        if (post) {

            post.saved =
                !!result.saved;

            post.saves =
                Number(result.saves) || 0;
        }

        renderFeed(
            CACHED_POSTS
        );

    } catch (error) {

        console.error(
            "Save error:",
            error
        );

        toast(
            error.message ||
            "Could not save post."
        );
    }
}


/* ============================================================
   SHARE
   ============================================================ */

async function sharePost(postId) {

    if (!requireLogin()) {
        return;
    }

    try {

        const result =
            await apiFetch(
                `/api/posts/${postId}/share`,
                {
                    method: "POST"
                }
            );

        const post =
            CACHED_POSTS.find(
                (item) =>
                    Number(item.id) ===
                    Number(postId)
            );

        if (post) {
            post.shares =
                Number(result.shares) || 0;
        }

        renderFeed(
            CACHED_POSTS
        );

        const shareURL =
            `${window.location.origin}/?post=${postId}`;

        if (
            navigator.clipboard &&
            navigator.clipboard.writeText
        ) {

            try {
                await navigator.clipboard.writeText(
                    shareURL
                );

                toast(
                    "Post link copied."
                );

            } catch {
                toast(
                    "Post shared."
                );
            }

        } else {
            toast(
                "Post shared."
            );
        }

    } catch (error) {

        console.error(
            "Share error:",
            error
        );

        toast(
            error.message ||
            "Could not share post."
        );
    }
}


/* ============================================================
   COMMENTS
   ============================================================ */

async function openComments(postId) {

    CURRENT_POST_ID = postId;

    openModal(
        `<h2>Comments</h2>
         <div id="comments-container">
            <p class="muted">Loading comments...</p>
         </div>
         <form
            id="comment-form"
            style="margin-top:16px;display:flex;gap:8px;"
         >
            <input
                id="comment-input"
                type="text"
                placeholder="Write a comment..."
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
                class="btn-primary"
                type="submit"
            >
                Send
            </button>
         </form>`
    );


    const form =
        $("#comment-form");

    if (form) {

        form.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                await createComment(
                    postId
                );
            }
        );
    }


    await loadComments(
        postId
    );
}


async function loadComments(postId) {

    const container =
        $("#comments-container");

    if (!container) {
        return;
    }

    try {

        const data =
            await apiFetch(
                `/api/posts/${postId}/comments`
            );

        const comments =
            Array.isArray(data?.comments)
                ? data.comments
                : [];

        if (!comments.length) {

            container.innerHTML =
                `<p class="muted">
                    No comments yet.
                 </p>`;

            return;
        }


        container.innerHTML =
            comments
                .map(
                    (comment) => `
                        <div
                            style="
                                padding:12px 0;
                                border-bottom:1px solid var(--border);
                            "
                        >
                            <strong>
                                ${escapeHTML(
                                    comment.full_name ||
                                    comment.username ||
                                    "User"
                                )}
                            </strong>

                            <div
                                style="
                                    margin-top:4px;
                                    font-size:14px;
                                    line-height:1.4;
                                "
                            >
                                ${formatText(
                                    comment.text
                                )}
                            </div>

                            <div
                                class="muted"
                                style="margin-top:4px;"
                            >
                                ${formatTime(
                                    comment.created_at
                                )}
                            </div>
                        </div>
                    `
                )
                .join("");

    } catch (error) {

        container.innerHTML =
            `<p class="muted">
                Could not load comments.
             </p>`;

        console.error(
            "Comments error:",
            error
        );
    }
}


async function createComment(postId) {

    if (!requireLogin()) {
        return;
    }

    const input =
        $("#comment-input");

    if (!input) {
        return;
    }

    const text =
        input.value.trim();

    if (!text) {
        toast("Write a comment first.");
        return;
    }


    try {

        const form =
            new FormData();

        form.append(
            "text",
            text
        );

        await apiFetch(
            `/api/posts/${postId}/comments`,
            {
                method: "POST",
                body: form
            }
        );

        input.value = "";

        await loadComments(
            postId
        );

        /*
         * Refresh feed counters.
         */

        await loadFeed();

        toast(
            "Comment added."
        );

    } catch (error) {

        console.error(
            "Comment error:",
            error
        );

        toast(
            error.message ||
            "Could not add comment."
        );
    }
}


/* ============================================================
   CREATE POST
   ============================================================ */

function openCreatePost() {

    if (!requireLogin()) {
        return;
    }

    openModal(`
        <h2>Create Post</h2>

        <form id="create-post-form">

            <textarea
                id="post-caption"
                placeholder="What's on your mind?"
                rows="5"
                style="
                    width:100%;
                    padding:14px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                    border-radius:12px;
                    resize:vertical;
                    outline:none;
                    font-family:inherit;
                    margin-bottom:12px;
                "
            ></textarea>

            <input
                id="post-media"
                type="file"
                accept="image/*,video/*"
                style="
                    width:100%;
                    margin-bottom:16px;
                "
            >

            <button
                class="btn-primary"
                type="submit"
                style="width:100%;"
            >
                Publish Post
            </button>

        </form>
    `);


    const form =
        $("#create-post-form");

    if (form) {

        form.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                await createPost();
            }
        );
    }
}


async function createPost() {

    const caption =
        $("#post-caption")?.value.trim() || "";

    const file =
        $("#post-media")?.files?.[0] || null;

    if (!caption && !file) {
        toast(
            "Write something or select media."
        );
        return;
    }


    const form =
        new FormData();

    form.append(
        "caption",
        caption
    );

    if (file) {
        form.append(
            "media",
            file
        );
    }


    const button =
        $("#create-post-form .btn-primary");

    setButtonLoading(
        button,
        true,
        "Publishing..."
    );


    try {

        await apiFetch(
            "/api/posts/create",
            {
                method: "POST",
                body: form
            }
        );

        closeModal();

        await loadFeed();

        toast(
            "Post published successfully."
        );

    } catch (error) {

        console.error(
            "Create post error:",
            error
        );

        toast(
            error.message ||
            "Could not publish post."
        );

    } finally {

        setButtonLoading(
            button,
            false,
            "Publish Post"
        );
    }
}


/* ============================================================
   SEARCH PEOPLE
   ============================================================ */

async function searchPeople(query) {

    if (!query) {
        closeSearchResults();
        return;
    }


    /*
     * Your current backend does not expose a dedicated
     * search router. Therefore we try several likely
     * endpoints without breaking the application.
     */

    const candidates = [
        `/api/profile/search?q=${encodeURIComponent(query)}`,
        `/api/users/search?q=${encodeURIComponent(query)}`,
        `/api/search/users?q=${encodeURIComponent(query)}`
    ];


    let found = false;


    for (const endpoint of candidates) {

        try {

            const data =
                await apiFetch(endpoint);

            const users =
                extractUsers(data);

            SEARCH_RESULTS =
                users;

            renderSearchResults(
                users,
                query
            );

            found = true;

            break;

        } catch (error) {

            /*
             * Continue to next endpoint.
             */
        }
    }


    /*
     * If there is no search endpoint yet,
     * use the current feed's users as a fallback.
     * This allows testing profiles immediately.
     */

    if (!found) {

        const unique =
            new Map();

        CACHED_POSTS.forEach(
            (post) => {

                if (!post.user_id) {
                    return;
                }

                const key =
                    String(post.user_id);

                if (!unique.has(key)) {

                    unique.set(
                        key,
                        {
                            id: post.user_id,
                            username:
                                post.username,
                            full_name:
                                post.full_name,
                            avatar_url:
                                post.avatar_url
                        }
                    );
                }
            }
        );


        const users =
            Array.from(
                unique.values()
            ).filter(
                (user) => {

                    const text = (
                        `${user.username || ""} ` +
                        `${user.full_name || ""}`
                    ).toLowerCase();

                    return text.includes(
                        query.toLowerCase()
                    );
                }
            );


        SEARCH_RESULTS =
            users;

        renderSearchResults(
            users,
            query
        );
    }
}


function extractUsers(data) {

    if (Array.isArray(data)) {
        return data;
    }

    if (Array.isArray(data?.users)) {
        return data.users;
    }

    if (Array.isArray(data?.results)) {
        return data.results;
    }

    if (Array.isArray(data?.items)) {
        return data.items;
    }

    return [];
}


/* ============================================================
   SEARCH RESULT UI
   ============================================================ */

function renderSearchResults(
    users,
    query
) {

    closeSearchResults();


    if (!users.length) {

        const element =
            document.createElement("div");

        element.id =
            "search-results";

        element.style.cssText = `
            background:var(--bg-2);
            border:1px solid var(--border);
            border-radius:14px;
            margin-top:8px;
            padding:14px;
        `;

        element.innerHTML = `
            <p class="muted">
                No user found for
                "${escapeHTML(query)}"
            </p>
        `;


        const searchBar =
            $(".search-bar");

        if (searchBar) {
            searchBar.appendChild(
                element
            );
        }

        return;
    }


    const element =
        document.createElement("div");

    element.id =
        "search-results";

    element.style.cssText = `
        background:var(--bg-2);
        border:1px solid var(--border);
        border-radius:14px;
        margin-top:8px;
        overflow:hidden;
        position:relative;
        z-index:80;
    `;


    element.innerHTML =
        users
            .slice(0, 20)
            .map(
                (user) => {

                    const name =
                        user.full_name ||
                        user.username ||
                        "User";

                    const avatar =
                        user.avatar_url
                            ? `<img
                                src="${escapeHTML(
                                    mediaURL(user.avatar_url)
                                )}"
                                style="
                                    width:100%;
                                    height:100%;
                                    object-fit:cover;
                                    border-radius:50%;
                                "
                               >`
                            : escapeHTML(
                                getInitial(name)
                              );

                    return `
                        <button
                            type="button"
                            onclick="openUserProfile(${Number(user.id) || 0})"
                            style="
                                width:100%;
                                display:flex;
                                align-items:center;
                                gap:12px;
                                padding:12px;
                                border:0;
                                border-bottom:1px solid var(--border);
                                background:transparent;
                                color:var(--text);
                                text-align:left;
                                cursor:pointer;
                            "
                        >

                            <span
                                style="
                                    width:44px;
                                    height:44px;
                                    border-radius:50%;
                                    display:flex;
                                    align-items:center;
                                    justify-content:center;
                                    background:linear-gradient(
                                        135deg,
                                        var(--accent),
                                        var(--accent-2)
                                    );
                                    font-weight:700;
                                    overflow:hidden;
                                    flex-shrink:0;
                                "
                            >
                                ${avatar}
                            </span>

                            <span>
                                <strong>
                                    ${escapeHTML(name)}
                                </strong>

                                <small
                                    class="muted"
                                    style="display:block;"
                                >
                                    @${escapeHTML(
                                        user.username || "user"
                                    )}
                                </small>
                            </span>

                        </button>
                    `;
                }
            )
            .join("");


    const searchBar =
        $(".search-bar");

    if (searchBar) {
        searchBar.appendChild(
            element
        );
    }
}


function closeSearchResults() {

    const results =
        $("#search-results");

    if (results) {
        results.remove();
    }
}


/* ============================================================
   USER PROFILE
   ============================================================ */

async function openUserProfile(userId) {

    if (!userId) {
        toast("User profile is unavailable.");
        return;
    }

    closeSearchResults();

    CURRENT_PROFILE_ID =
        Number(userId);


    /*
     * Own profile can be displayed immediately.
     */

    if (
        CURRENT_USER &&
        Number(CURRENT_USER.id) ===
        Number(userId)
    ) {

        navigate(
            "profile"
        );

        return;
    }


    PAGE_HISTORY.push(
        CURRENT_PAGE
    );

    CURRENT_PAGE =
        "sub";


    $all(".page").forEach(
        (page) =>
            page.classList.remove("active")
    );


    const sub =
        $("#page-sub");

    if (sub) {
        sub.classList.add("active");
    }


    updatePageTitle(
        "Profile"
    );

    updateBackButton();


    const content =
        $("#sub-content");

    if (!content) {
        return;
    }


    content.innerHTML = `
        <div class="post-card">
            <p class="muted">
                Loading profile...
            </p>
        </div>
    `;


    try {

        const data =
            await apiFetch(
                `/api/profile/${Number(userId)}`
            );

        const user =
            data?.user ||
            data;


        renderUserProfile(
            user
        );


        /*
         * Load user's posts from the existing feed
         * if available.
         */

        await appendUserPosts(
            user.id
        );


    } catch (error) {

        console.error(
            "Profile error:",
            error
        );

        content.innerHTML = `
            <div class="post-card">
                <strong>
                    User not found
                </strong>

                <p class="muted"
                   style="margin-top:8px;">
                    ${escapeHTML(
                        error.message
                    )}
                </p>
            </div>
        `;
    }
}


function renderUserProfile(user) {

    const content =
        $("#sub-content");

    if (!content) {
        return;
    }


    const name =
        user.full_name ||
        user.username ||
        "User";

    const username =
        user.username ||
        "user";

    const avatar =
        user.avatar_url
            ? `<img
                src="${escapeHTML(
                    mediaURL(user.avatar_url)
                )}"
                style="
                    width:100%;
                    height:100%;
                    object-fit:cover;
                    border-radius:50%;
                "
               >`
            : escapeHTML(
                getInitial(name)
              );


    content.innerHTML = `

        <div
            style="
                background:linear-gradient(
                    135deg,
                    var(--accent),
                    var(--accent-2)
                );
                height:120px;
                margin:-16px -16px 0;
            "
        ></div>


        <div
            style="
                text-align:center;
                margin-top:-40px;
                position:relative;
            "
        >

            <div
                style="
                    width:80px;
                    height:80px;
                    border-radius:50%;
                    margin:0 auto 12px;
                    border:4px solid var(--bg);
                    background:var(--bg-3);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:30px;
                    font-weight:900;
                    overflow:hidden;
                "
            >
                ${avatar}
            </div>

            <h2>
                ${escapeHTML(name)}
            </h2>

            <p class="muted">
                @${escapeHTML(username)}
            </p>

            ${
                user.bio
                    ? `
                        <p
                            class="muted"
                            style="
                                max-width:500px;
                                margin:10px auto;
                                line-height:1.5;
                            "
                        >
                            ${formatText(
                                user.bio
                            )}
                        </p>
                      `
                    : ""
            }

            ${
                user.location
                    ? `
                        <p class="muted">
                            📍 ${escapeHTML(
                                user.location
                            )}
                        </p>
                      `
                    : ""
            }


            <div
                style="
                    display:flex;
                    justify-content:center;
                    gap:30px;
                    margin:18px 0;
                "
            >
                <div>
                    <strong id="other-post-count">
                        0
                    </strong>
                    <small
                        class="muted"
                        style="display:block;"
                    >
                        Posts
                    </small>
                </div>

                <div>
                    <strong>
                        0
                    </strong>
                    <small
                        class="muted"
                        style="display:block;"
                    >
                        Followers
                    </small>
                </div>

                <div>
                    <strong>
                        0
                    </strong>
                    <small
                        class="muted"
                        style="display:block;"
                    >
                        Following
                    </small>
                </div>
            </div>


            ${
                Number(user.id) !==
                Number(CURRENT_USER?.id)
                    ? `
                        <button
                            class="btn-primary"
                            onclick="startChatWithUser(${Number(user.id)})"
                        >
                            💬 Message
                        </button>
                      `
                    : ""
            }

        </div>


        <div
            id="other-user-posts"
            class="feed"
            style="margin-top:20px;"
        ></div>
    `;
}


async function appendUserPosts(
    userId
) {

    const container =
        $("#other-user-posts");

    if (!container) {
        return;
    }


    try {

        const data =
            await apiFetch(
                "/api/feed"
            );

        const posts =
            extractPosts(data)
                .filter(
                    (post) =>
                        Number(post.user_id) ===
                        Number(userId)
                );


        const count =
            $("#other-post-count");

        if (count) {
            count.textContent =
                String(posts.length);
        }


        if (!posts.length) {

            container.innerHTML = `
                <div class="post-card">
                    <p class="muted">
                        No posts yet.
                    </p>
                </div>
            `;

            return;
        }


        container.innerHTML =
            posts
                .map(
                    (post) =>
                        renderPost(post)
                )
                .join("");


    } catch (error) {

        console.error(
            "User posts error:",
            error
        );

        container.innerHTML = `
            <div class="post-card">
                <p class="muted">
                    Could not load posts.
                </p>
            </div>
        `;
    }
}


/* ============================================================
   CHAT
   ============================================================ */

async function loadChats() {

    const list =
        $("#chat-list");

    if (!list) {
        return;
    }


    list.innerHTML = `
        <div class="muted"
             style="padding:20px;text-align:center;">
            Loading chats...
        </div>
    `;


    try {

        const data =
            await apiFetch(
                "/api/messages"
            );

        const chats =
            Array.isArray(data?.chats)
                ? data.chats
                : [];


        CACHED_CHATS =
            chats;


        renderChatList(
            chats
        );


    } catch (error) {

        console.error(
            "Chat list error:",
            error
        );

        list.innerHTML = `
            <div class="post-card">
                <strong>
                    Chats
                </strong>

                <p class="muted"
                   style="margin-top:8px;">
                    No conversations yet.
                </p>
            </div>
        `;
    }
}


function renderChatList(chats) {

    const list =
        $("#chat-list");

    if (!list) {
        return;
    }


    if (!chats.length) {

        list.innerHTML = `
            <div
                class="post-card"
                style="text-align:center;margin-top:10px;"
            >
                <div style="font-size:42px;">
                    💬
                </div>

                <strong>
                    No chats yet
                </strong>

                <p
                    class="muted"
                    style="margin-top:8px;"
                >
                    Search for another user from Home
                    and tap Message to start a conversation.
                </p>
            </div>
        `;

        return;
    }


    list.innerHTML =
        chats
            .map(
                (chat) => {

                    const user =
                        chat.user ||
                        chat.other_user ||
                        chat.recipient ||
                        chat;

                    const name =
                        user.full_name ||
                        user.username ||
                        chat.name ||
                        "User";

                    const username =
                        user.username ||
                        "";

                    const initial =
                        getInitial(name);

                    return `
                        <div
                            class="chat-item"
                            onclick="openChat(
                                ${Number(
                                    user.id ||
                                    chat.user_id ||
                                    chat.recipient_id ||
                                    0
                                )}
                            )"
                        >

                            <div class="chat-avatar">
                                ${escapeHTML(
                                    initial
                                )}
                            </div>

                            <div class="chat-info">

                                <strong>
                                    ${escapeHTML(name)}
                                </strong>

                                <span>
                                    ${
                                        chat.last_message ||
                                        chat.message ||
                                        (
                                            username
                                                ? `@${username}`
                                                : "Conversation"
                                        )
                                    }
                                </span>

                            </div>

                        </div>
                    `;
                }
            )
            .join("");
}


/* ============================================================
   START CHAT
   ============================================================ */

async function startChatWithUser(
    userId
) {

    if (!requireLogin()) {
        return;
    }

    if (!userId) {
        toast("User unavailable.");
        return;
    }

    CURRENT_CHAT_USER =
        Number(userId);

    openChat(
        userId
    );
}


async function openChat(
    userId
) {

    if (!userId) {
        toast("Chat user unavailable.");
        return;
    }

    CURRENT_CHAT_USER =
        Number(userId);


    PAGE_HISTORY.push(
        CURRENT_PAGE
    );

    CURRENT_PAGE =
        "sub";


    $all(".page").forEach(
        (page) =>
            page.classList.remove("active")
    );


    const sub =
        $("#page-sub");

    if (sub) {
        sub.classList.add("active");
    }


    updatePageTitle(
        "Chat"
    );

    updateBackButton();


    const content =
        $("#sub-content");

    if (!content) {
        return;
    }


    content.innerHTML = `

        <div
            style="
                display:flex;
                flex-direction:column;
                min-height:calc(100vh - 150px);
            "
        >

            <div
                id="chat-header"
                style="
                    display:flex;
                    align-items:center;
                    gap:10px;
                    padding:0 0 14px;
                    border-bottom:1px solid var(--border);
                "
            >
                <div
                    class="chat-avatar"
                    style="
                        width:42px;
                        height:42px;
                        font-size:15px;
                    "
                >
                    ?
                </div>

                <div>
                    <strong>
                        Loading...
                    </strong>
                    <div class="muted">
                        @user
                    </div>
                </div>
            </div>


            <div
                id="chat-messages"
                class="chat-msgs"
                style="
                    flex:1;
                    overflow-y:auto;
                "
            >
                <p class="muted">
                    Loading conversation...
                </p>
            </div>


            <form
                id="chat-send-form"
                style="
                    display:flex;
                    gap:8px;
                    padding-top:12px;
                    border-top:1px solid var(--border);
                "
            >

                <input
                    id="chat-message-input"
                    type="text"
                    placeholder="Type a message..."
                    autocomplete="off"
                    style="
                        flex:1;
                        padding:12px;
                        border-radius:12px;
                        border:1px solid var(--border);
                        background:var(--bg-3);
                        color:var(--text);
                        outline:none;
                    "
                >

                <button
                    class="btn-primary"
                    type="submit"
                >
                    ➤
                </button>

            </form>

        </div>
    `;


    await loadChatUser(
        userId
    );

    await loadConversation(
        userId
    );


    const form =
        $("#chat-send-form");

    if (form) {

        form.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                await sendMessage(
                    userId
                );
            }
        );
    }
}


/* ============================================================
   CHAT USER
   ============================================================ */

async function loadChatUser(
    userId
) {

    const header =
        $("#chat-header");

    if (!header) {
        return;
    }


    try {

        const data =
            await apiFetch(
                `/api/profile/${Number(userId)}`
            );

        const user =
            data?.user ||
            data;


        const name =
            user.full_name ||
            user.username ||
            "User";

        header.innerHTML = `
            <div
                class="chat-avatar"
                style="
                    width:42px;
                    height:42px;
                    font-size:15px;
                "
            >
                ${escapeHTML(
                    getInitial(name)
                )}
            </div>

            <div>
                <strong>
                    ${escapeHTML(name)}
                </strong>

                <div class="muted">
                    @${escapeHTML(
                        user.username || "user"
                    )}
                </div>
            </div>
        `;

    } catch (error) {

        console.warn(
            "Could not load chat user:",
            error
        );
    }
}


/* ============================================================
   LOAD CONVERSATION
   ============================================================ */

async function loadConversation(
    userId
) {

    const container =
        $("#chat-messages");

    if (!container) {
        return;
    }


    /*
     * Current messages.py only exposes:
     *
     * GET /api/messages
     *
     * Therefore this function gracefully supports
     * future conversation endpoints without crashing.
     */

    const candidates = [
        `/api/messages/${Number(userId)}`,
        `/api/messages/user/${Number(userId)}`,
        `/api/messages?user_id=${Number(userId)}`
    ];


    for (const endpoint of candidates) {

        try {

            const data =
                await apiFetch(
                    endpoint
                );

            const messages =
                extractMessages(data);

            renderMessages(
                messages
            );

            return;

        } catch (error) {
            /*
             * Try next candidate.
             */
        }
    }


    /*
     * Current backend has no conversation route yet.
     */

    container.innerHTML = `
        <div
            style="
                text-align:center;
                padding:30px 10px;
            "
        >
            <div style="font-size:38px;">
                💬
            </div>

            <strong>
                Conversation ready
            </strong>

            <p
                class="muted"
                style="
                    margin-top:8px;
                    line-height:1.5;
                "
            >
                The current messages router exposes
                the chat list only. A conversation
                send/read endpoint is required for
                real-time messaging.
            </p>
        </div>
    `;
}


function extractMessages(
    data
) {

    if (Array.isArray(data)) {
        return data;
    }

    if (Array.isArray(data?.messages)) {
        return data.messages;
    }

    if (Array.isArray(data?.chat)) {
        return data.chat;
    }

    return [];
}


function renderMessages(
    messages
) {

    const container =
        $("#chat-messages");

    if (!container) {
        return;
    }


    if (!messages.length) {

        container.innerHTML = `
            <p
                class="muted"
                style="
                    text-align:center;
                    padding:30px 0;
                "
            >
                No messages yet.
                Start the conversation.
            </p>
        `;

        return;
    }


    container.innerHTML =
        messages
            .map(
                (message) => {

                    const senderId =
                        message.sender_id ||
                        message.user_id;

                    const mine =
                        Number(senderId) ===
                        Number(CURRENT_USER?.id);

                    return `
                        <div
                            class="msg ${mine ? "user" : "ai"}"
                        >
                            ${formatText(
                                message.text ||
                                message.content ||
                                message.message ||
                                ""
                            )}
                        </div>
                    `;
                }
            )
            .join("");


    container.scrollTop =
        container.scrollHeight;
}


/* ============================================================
   SEND MESSAGE
   ============================================================ */

async function sendMessage(
    userId
) {

    if (!requireLogin()) {
        return;
    }


    const input =
        $("#chat-message-input");

    if (!input) {
        return;
    }


    const text =
        input.value.trim();

    if (!text) {
        return;
    }


    /*
     * Future-compatible endpoint candidates.
     */

    const candidates = [
        {
            url: "/api/messages/send",
            body: {
                receiver_id: Number(userId),
                recipient_id: Number(userId),
                text
            }
        },
        {
            url: `/api/messages/${Number(userId)}`,
            body: {
                receiver_id: Number(userId),
                text
            }
        }
    ];


    let sent = false;


    for (const candidate of candidates) {

        try {

            await apiFetch(
                candidate.url,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify(
                        candidate.body
                    )
                }
            );

            sent = true;
            break;

        } catch (error) {
            /*
             * Try next endpoint.
             */
        }
    }


    if (!sent) {

        /*
         * IMPORTANT:
         * Do not pretend the message was saved.
         */

        toast(
            "Messaging endpoint is not implemented in the current backend."
        );

        return;
    }


    input.value = "";

    await loadConversation(
        userId
    );
}


/* ============================================================
   STORIES
   ============================================================ */

async function loadStories() {

    const bar =
        $("#stories-bar");

    if (!bar) {
        return;
    }


    try {

        const data =
            await apiFetch(
                "/api/stories"
            );

        const stories =
            Array.isArray(data?.stories)
                ? data.stories
                : Array.isArray(data)
                    ? data
                    : [];


        renderStories(
            stories
        );

    } catch (error) {

        /*
         * Keep My Story button visible.
         */

        console.warn(
            "Stories loading:",
            error.message
        );
    }
}


function renderStories(
    stories
) {

    const bar =
        $("#stories-bar");

    if (!bar) {
        return;
    }


    const myStory = `
        <div
            class="story-item add-story"
            id="add-story-btn"
        >
            <div
                class="story-avatar add-avatar"
            >
                +
            </div>
            <span>
                My Story
            </span>
        </div>
    `;


    bar.innerHTML =
        myStory +
        stories
            .map(
                (story) => {

                    const name =
                        story.full_name ||
                        story.username ||
                        "User";

                    return `
                        <div
                            class="story-item"
                            onclick="openStory(${Number(
                                story.id
                            ) || 0})"
                        >

                            <div
                                class="story-avatar"
                            >
                                ${escapeHTML(
                                    getInitial(name)
                                )}
                            </div>

                            <span>
                                ${escapeHTML(
                                    name
                                )}
                            </span>

                        </div>
                    `;
                }
            )
            .join("");


    const add =
        $("#add-story-btn");

    if (add) {
        add.addEventListener(
            "click",
            openCreateStory
        );
    }
}


/* ============================================================
   CREATE STORY
   ============================================================ */

function openCreateStory() {

    if (!requireLogin()) {
        return;
    }

    openModal(`
        <h2>My Story</h2>

        <form id="create-story-form">

            <textarea
                id="story-caption"
                rows="3"
                placeholder="Add a caption..."
                style="
                    width:100%;
                    padding:12px;
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
                id="story-media"
                type="file"
                accept="image/*,video/*"
                style="
                    width:100%;
                    margin-bottom:16px;
                "
            >

            <button
                type="submit"
                class="btn-primary"
                style="width:100%;"
            >
                Post Story
            </button>

        </form>
    `);


    const form =
        $("#create-story-form");

    if (form) {

        form.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                await createStory();
            }
        );
    }
}


async function createStory() {

    const file =
        $("#story-media")?.files?.[0];

    const caption =
        $("#story-caption")?.value.trim() || "";


    if (!file && !caption) {
        toast(
            "Select media or write a caption."
        );
        return;
    }


    const form =
        new FormData();

    form.append(
        "caption",
        caption
    );

    if (file) {
        form.append(
            "media",
            file
        );
    }


    try {

        await apiFetch(
            "/api/stories/create",
            {
                method: "POST",
                body: form
            }
        );

        closeModal();

        await loadStories();

        toast(
            "Story posted."
        );

    } catch (error) {

        toast(
            error.message ||
            "Story endpoint is not available."
        );
    }
}


async function openStory(
    storyId
) {

    if (!storyId) {
        return;
    }

    try {

        const data =
            await apiFetch(
                `/api/stories/${Number(storyId)}`
            );

        const story =
            data?.story ||
            data;

        openModal(`
            <h2>Story</h2>
            <p>
                ${formatText(
                    story.caption || ""
                )}
            </p>
        `);

    } catch (error) {

        toast(
            "Story could not be opened."
        );
    }
}


/* ============================================================
   DISCOVERY
   ============================================================ */

async function loadDiscovery() {

    const grid =
        $("#discovery-grid");

    if (!grid) {
        return;
    }


    grid.innerHTML = `
        <div
            class="muted"
            style="
                grid-column:1/-1;
                text-align:center;
                padding:20px;
            "
        >
            Loading Discovery...
        </div>
    `;


    try {

        const data =
            await apiFetch(
                "/api/discovery"
            );

        const cards =
            Array.isArray(data?.cards)
                ? data.cards
                : [];


        if (!cards.length) {
            renderDefaultDiscovery();
            return;
        }


        grid.innerHTML =
            cards
                .map(
                    (card) =>
                        `
                        <div
                            class="disc-card"
                            onclick="openDiscovery('${escapeHTML(
                                card.id
                            )}')"
                        >

                            <span class="icon">
                                ${escapeHTML(
                                    card.icon || "✨"
                                )}
                            </span>

                            <div class="title">
                                ${escapeHTML(
                                    card.title
                                )}
                            </div>

                            <div class="desc">
                                ${escapeHTML(
                                    card.desc || ""
                                )}
                            </div>

                        </div>
                        `
                )
                .join("");


    } catch (error) {

        console.error(
            "Discovery error:",
            error
        );

        renderDefaultDiscovery();
    }
}


function renderDefaultDiscovery() {

    const grid =
        $("#discovery-grid");

    if (!grid) {
        return;
    }


    const cards = [
        ["ai-council", "📖", "AI Council", "Education, Health, Agriculture, Research"],
        ["creative-studio", "🖼️", "Creative Studio", "Image, Video, Documents"],
        ["market", "🛍️", "Market", "Products, Services, Digital"],
        ["world-map", "🌍", "World Map", "Explore the world"],
        ["channels", "📺", "Channels", "News and media"],
        ["communities", "👥", "Communities", "Groups and communities"],
        ["videos", "▶️", "Videos", "Short videos feed"],
        ["settings", "⚙️", "Settings", "App preferences"]
    ];


    grid.innerHTML =
        cards
            .map(
                (card) => `
                    <div
                        class="disc-card"
                        onclick="openDiscovery('${card[0]}')"
                    >
                        <span class="icon">
                            ${card[1]}
                        </span>

                        <div class="title">
                            ${escapeHTML(card[2])}
                        </div>

                        <div class="desc">
                            ${escapeHTML(card[3])}
                        </div>
                    </div>
                `
            )
            .join("");
}


/* ============================================================
   DISCOVERY ROUTER
   ============================================================ */

function openDiscovery(
    id
) {

    if (!id) {
        return;
    }


    if (id === "ai-council") {
        openAICouncil();
        return;
    }

    if (id === "creative-studio") {
        openCreativeStudio();
        return;
    }

    if (id === "market") {
        openMarket();
        return;
    }

    if (id === "world-map") {
        openWorldMap();
        return;
    }

    if (id === "channels") {
        openChannels();
        return;
    }

    if (id === "communities") {
        openCommunities();
        return;
    }

    if (id === "videos") {
        openVideos();
        return;
    }

    if (id === "settings") {
        openSettings();
        return;
    }
}


/* ============================================================
   SUB PAGE HELPER
   ============================================================ */

function openSubPage(
    title,
    html
) {

    PAGE_HISTORY.push(
        CURRENT_PAGE
    );

    CURRENT_PAGE =
        "sub";


    $all(".page").forEach(
        (page) =>
            page.classList.remove("active")
    );


    const sub =
        $("#page-sub");

    if (sub) {
        sub.classList.add("active");
    }


    const content =
        $("#sub-content");

    if (content) {
        content.innerHTML =
            html;
    }


    updatePageTitle(
        title
    );

    updateBackButton();
}


/* ============================================================
   AI COUNCIL
   ============================================================ */

async function openAICouncil() {

    openSubPage(
        "AI Council",
        `
        <div class="page-h">
            AI Council
        </div>

        <div id="ai-list">
            <p class="muted">
                Loading AI Council...
            </p>
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                "/api/ai-council"
            );

        const ais =
            Array.isArray(data?.ais)
                ? data.ais
                : [];


        const list =
            $("#ai-list");

        if (!list) {
            return;
        }


        list.innerHTML =
            ais
                .map(
                    (ai) => `
                        <div
                            class="sub-item"
                            onclick="openAI('${escapeHTML(
                                ai.id
                            )}')"
                        >

                            <div class="icon">
                                ${escapeHTML(
                                    ai.icon || "🤖"
                                )}
                            </div>

                            <div class="text">

                                <strong>
                                    ${escapeHTML(
                                        ai.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        ai.desc || ""
                                    )}
                                </span>

                            </div>

                            <span>
                                →
                            </span>

                        </div>
                    `
                )
                .join("");


    } catch (error) {

        toast(
            "Could not load AI Council."
        );
    }
}


async function openAI(
    aiId
) {

    if (aiId === "education") {
        openEducationAI();
        return;
    }

    if (
        aiId === "health" ||
        aiId === "agriculture" ||
        aiId === "research"
    ) {

        openAIChat(
            aiId,
            aiId.charAt(0).toUpperCase() +
            aiId.slice(1)
        );

        return;
    }

    if (aiId === "canvas") {

        openSubPage(
            "AI Canvas",
            `
                <div class="page-h">
                    AI Canvas
                </div>

                <div class="sub-item">
                    <div class="icon">
                        📐
                    </div>

                    <div class="text">
                        <strong>
                            Workspace
                        </strong>

                        <span>
                            Documents and AI workspace.
                        </span>
                    </div>
                </div>

                <p class="muted">
                    AI Canvas is prepared for the
                    next implementation phase.
                </p>
            `
        );

        return;
    }
}


/* ============================================================
   EDUCATION AI
   ============================================================ */

async function openEducationAI() {

    openSubPage(
        "Education AI",
        `
        <div class="page-h">
            Education AI
        </div>

        <p class="muted"
           style="margin-bottom:16px;">
            Choose your country.
        </p>

        <div id="country-list">
            <p class="muted">
                Loading countries...
            </p>
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                "/api/ai-council/countries"
            );

        const countries =
            Array.isArray(data?.countries)
                ? data.countries
                : [];


        const list =
            $("#country-list");

        if (!list) {
            return;
        }


        list.innerHTML =
            countries
                .map(
                    (country) => `
                        <div
                            class="sub-item"
                            onclick="chooseEducationCountry('${escapeHTML(
                                country
                            )}')"
                        >

                            <div class="icon">
                                🌍
                            </div>

                            <div class="text">
                                <strong>
                                    ${escapeHTML(
                                        country
                                    )}
                                </strong>

                                <span>
                                    Continue
                                </span>
                            </div>

                            <span>
                                →
                            </span>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        toast(
            "Could not load countries."
        );
    }
}


function chooseEducationCountry(
    country
) {

    openSubPage(
        "Choose Level",
        `
        <div class="page-h">
            ${escapeHTML(country)}
        </div>

        <p class="muted"
           style="margin-bottom:16px;">
            Choose education level.
        </p>

        <div id="level-list">
            Loading levels...
        </div>
        `
    );


    apiFetch(
        "/api/ai-council/levels"
    )
        .then(
            (data) => {

                const levels =
                    Array.isArray(data?.levels)
                        ? data.levels
                        : [];

                const list =
                    $("#level-list");

                if (!list) {
                    return;
                }

                list.innerHTML =
                    levels
                        .map(
                            (level) => `
                                <div
                                    class="sub-item"
                                    onclick="chooseEducationLevel(
                                        '${escapeHTML(country)}',
                                        '${escapeHTML(level)}'
                                    )"
                                >

                                    <div class="icon">
                                        🎓
                                    </div>

                                    <div class="text">
                                        <strong>
                                            ${escapeHTML(
                                                level
                                            )}
                                        </strong>

                                        <span>
                                            Continue
                                        </span>
                                    </div>

                                    <span>
                                        →
                                    </span>

                                </div>
                            `
                        )
                        .join("");
            }
        )
        .catch(
            () => toast(
                "Could not load levels."
            )
        );
}


function chooseEducationLevel(
    country,
    level
) {

    openSubPage(
        "Choose Content",
        `
        <div class="page-h">
            ${escapeHTML(level)}
        </div>

        <p class="muted"
           style="margin-bottom:16px;">
            ${escapeHTML(country)} ·
            ${escapeHTML(level)}
        </p>

        <div id="content-type-list">
            Loading content types...
        </div>
        `
    );


    apiFetch(
        "/api/ai-council/content-types"
    )
        .then(
            (data) => {

                const types =
                    Array.isArray(data?.content_types)
                        ? data.content_types
                        : [];

                const list =
                    $("#content-type-list");

                if (!list) {
                    return;
                }


                list.innerHTML =
                    types
                        .map(
                            (content) => `
                                <div
                                    class="sub-item"
                                    onclick="openEducationChat(
                                        '${escapeHTML(country)}',
                                        '${escapeHTML(level)}',
                                        '${escapeHTML(content)}'
                                    )"
                                >

                                    <div class="icon">
                                        📚
                                    </div>

                                    <div class="text">
                                        <strong>
                                            ${escapeHTML(
                                                content
                                            )}
                                        </strong>

                                        <span>
                                            Open AI assistant
                                        </span>
                                    </div>

                                    <span>
                                        →
                                    </span>

                                </div>
                            `
                        )
                        .join("");
            }
        )
        .catch(
            () => toast(
                "Could not load content types."
            )
        );
}


function openEducationChat(
    country,
    level,
    content
) {

    openSubPage(
        "AI Chat",
        `
        <div class="page-h">
            Education AI
        </div>

        <div
            class="post-card"
            style="margin-bottom:12px;"
        >
            <strong>
                ${escapeHTML(content)} assistant
            </strong>

            <p
                class="muted"
                style="
                    margin-top:8px;
                    line-height:1.5;
                "
            >
                Hello! I'm your
                ${escapeHTML(content)}
                assistant for
                ${escapeHTML(level)}
                curriculum in
                ${escapeHTML(country)}.
                Ask me anything about a subject or topic.
            </p>
        </div>

        <div
            id="education-chat-messages"
            class="chat-msgs"
        ></div>

        <form
            id="education-chat-form"
            style="
                display:flex;
                gap:8px;
                margin-top:12px;
            "
        >
            <input
                id="education-chat-input"
                type="text"
                placeholder="Ask a question..."
                style="
                    flex:1;
                    padding:12px;
                    border-radius:12px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                    outline:none;
                "
            >

            <button
                class="btn-primary"
                type="submit"
            >
                ➤
            </button>
        </form>
        `
    );


    const form =
        $("#education-chat-form");

    if (form) {

        form.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                await askEducationAI(
                    country,
                    level,
                    content
                );
            }
        );
    }
}


async function askEducationAI(
    country,
    level,
    content
) {

    const input =
        $("#education-chat-input");

    const messages =
        $("#education-chat-messages");

    if (!input || !messages) {
        return;
    }


    const question =
        input.value.trim();

    if (!question) {
        return;
    }


    messages.innerHTML += `
        <div class="msg user">
            ${formatText(question)}
        </div>
    `;

    input.value = "";


    try {

        const query =
            new URLSearchParams({
                ai: "education",
                country,
                level,
                content,
                q: question
            });


        const data =
            await apiFetch(
                `/api/ai-council/chat?${query.toString()}`
            );


        messages.innerHTML += `
            <div class="msg ai">
                ${formatText(
                    data?.reply ||
                    "AI response unavailable."
                )}
            </div>
        `;


        messages.scrollTop =
            messages.scrollHeight;

    } catch (error) {

        messages.innerHTML += `
            <div class="msg ai">
                ${escapeHTML(
                    error.message ||
                    "AI request failed."
                )}
            </div>
        `;
    }
}


function openAIChat(
    ai,
    title
) {

    openSubPage(
        `${title} AI`,
        `
        <div class="page-h">
            ${escapeHTML(title)} AI
        </div>

        <div
            id="generic-ai-messages"
            class="chat-msgs"
        >
            <div class="msg ai">
                Hello! I'm your
                ${escapeHTML(title)}
                assistant.
                Ask me a question.
            </div>
        </div>

        <form
            id="generic-ai-form"
            style="
                display:flex;
                gap:8px;
                margin-top:12px;
            "
        >
            <input
                id="generic-ai-input"
                type="text"
                placeholder="Ask a question..."
                style="
                    flex:1;
                    padding:12px;
                    border-radius:12px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                    outline:none;
                "
            >

            <button
                class="btn-primary"
                type="submit"
            >
                ➤
            </button>
        </form>
        `
    );


    const form =
        $("#generic-ai-form");

    if (form) {

        form.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                const input =
                    $("#generic-ai-input");

                const messages =
                    $("#generic-ai-messages");

                if (!input || !messages) {
                    return;
                }

                const question =
                    input.value.trim();

                if (!question) {
                    return;
                }

                messages.innerHTML += `
                    <div class="msg user">
                        ${formatText(question)}
                    </div>
                `;

                input.value = "";


                try {

                    const params =
                        new URLSearchParams({
                            ai,
                            q: question
                        });


                    const data =
                        await apiFetch(
                            `/api/ai-council/chat?${params.toString()}`
                        );


                    messages.innerHTML += `
                        <div class="msg ai">
                            ${formatText(
                                data?.reply ||
                                "No response."
                            )}
                        </div>
                    `;

                } catch (error) {

                    messages.innerHTML += `
                        <div class="msg ai">
                            ${escapeHTML(
                                error.message
                            )}
                        </div>
                    `;
                }
            }
        );
    }
}


/* ============================================================
   CREATIVE STUDIO
   ============================================================ */

async function openCreativeStudio() {

    openSubPage(
        "Creative Studio",
        `
        <div class="page-h">
            Creative Studio
        </div>

        <div id="studio-tools">
            Loading tools...
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                "/api/studio"
            );

        const tools =
            Array.isArray(data?.tools)
                ? data.tools
                : [];


        const container =
            $("#studio-tools");

        if (!container) {
            return;
        }


        container.innerHTML =
            tools
                .map(
                    (tool) => `
                        <div
                            class="sub-item"
                            onclick="openStudioTool('${escapeHTML(
                                tool.id
                            )}','${escapeHTML(
                                tool.title
                            )}')"
                        >

                            <div class="icon">
                                ${escapeHTML(
                                    tool.icon || "✨"
                                )}
                            </div>

                            <div class="text">

                                <strong>
                                    ${escapeHTML(
                                        tool.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        tool.desc || ""
                                    )}
                                </span>

                            </div>

                            <span>
                                →
                            </span>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        toast(
            "Could not load Studio."
        );
    }
}


function openStudioTool(
    id,
    title
) {

    openSubPage(
        title,
        `
        <div class="page-h">
            ${escapeHTML(title)}
        </div>

        <div class="post-card">

            <div
                style="
                    font-size:48px;
                    text-align:center;
                    margin-bottom:16px;
                "
            >
                ✨
            </div>

            <strong>
                ${escapeHTML(title)}
            </strong>

            <p
                class="muted"
                style="
                    margin-top:8px;
                    line-height:1.5;
                "
            >
                This Creative Studio module is
                prepared for the next implementation
                phase.
            </p>

        </div>
        `
    );
}


/* ============================================================
   MARKET
   ============================================================ */

async function openMarket() {

    openSubPage(
        "Market",
        `
        <div class="page-h">
            Market
        </div>

        <div id="market-categories">
            Loading categories...
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                "/api/market/categories"
            );

        const categories =
            Array.isArray(data?.categories)
                ? data.categories
                : [];


        const container =
            $("#market-categories");

        if (!container) {
            return;
        }


        container.innerHTML =
            categories
                .map(
                    (category) => `
                        <div
                            class="sub-item"
                            onclick="openMarketCategory('${escapeHTML(
                                category.id
                            )}','${escapeHTML(
                                category.title
                            )}')"
                        >

                            <div class="icon">
                                ${
                                    category.id === "products"
                                        ? "🛍️"
                                        : category.id === "services"
                                            ? "🛠️"
                                            : category.id === "digital"
                                                ? "💾"
                                                : "💼"
                                }
                            </div>

                            <div class="text">
                                <strong>
                                    ${escapeHTML(
                                        category.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        category.desc || ""
                                    )}
                                </span>
                            </div>

                            <span>
                                →
                            </span>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        toast(
            "Could not load Market."
        );
    }
}


async function openMarketCategory(
    category,
    title
) {

    openSubPage(
        title,
        `
        <div class="page-h">
            ${escapeHTML(title)}
        </div>

        <div id="market-items">
            Loading...
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                `/api/market/items?category=${encodeURIComponent(
                    category
                )}`
            );

        const items =
            Array.isArray(data?.items)
                ? data.items
                : [];


        const container =
            $("#market-items");

        if (!container) {
            return;
        }


        if (!items.length) {

            container.innerHTML = `
                <div class="post-card"
                     style="text-align:center;">

                    <div style="font-size:40px;">
                        🛍️
                    </div>

                    <strong>
                        No items yet
                    </strong>

                    <p
                        class="muted"
                        style="margin-top:8px;"
                    >
                        Market data will be available
                        when the marketplace module
                        is connected.
                    </p>

                </div>
            `;

            return;
        }


        container.innerHTML =
            items
                .map(
                    (item) => `
                        <div class="sub-item">

                            <div class="icon">
                                🛍️
                            </div>

                            <div class="text">
                                <strong>
                                    ${escapeHTML(
                                        item.name ||
                                        "Item"
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        item.description ||
                                        ""
                                    )}
                                </span>
                            </div>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        toast(
            "Could not load Market items."
        );
    }
}


/* ============================================================
   WORLD MAP
   ============================================================ */

async function openWorldMap() {

    openSubPage(
        "World Map",
        `
        <div class="page-h">
            🌍 World Map
        </div>

        <div id="world-countries">
            Loading countries...
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                "/api/world-map/countries"
            );

        const countries =
            Array.isArray(data?.countries)
                ? data.countries
                : [];


        const container =
            $("#world-countries");

        if (!container) {
            return;
        }


        container.innerHTML =
            countries
                .map(
                    (country) => `
                        <div
                            class="sub-item"
                            onclick="openCountry(
                                '${escapeHTML(
                                    country.name
                                )}'
                            )"
                        >

                            <div class="icon">
                                🌍
                            </div>

                            <div class="text">

                                <strong>
                                    ${escapeHTML(
                                        country.name
                                    )}
                                </strong>

                                <span>
                                    Users:
                                    ${Number(
                                        country.users
                                    ) || 0}
                                    · Posts:
                                    ${Number(
                                        country.posts
                                    ) || 0}
                                </span>

                            </div>

                            <span>
                                →
                            </span>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        toast(
            "Could not load World Map."
        );
    }
}


function openCountry(
    country
) {

    openSubPage(
        country,
        `
        <div class="page-h">
            🌍 ${escapeHTML(country)}
        </div>

        <div class="post-card">

            <strong>
                ${escapeHTML(country)}
            </strong>

            <p
                class="muted"
                style="margin-top:8px;line-height:1.5;"
            >
                Country users, posts, trending content
                and local communities will appear here
                as the World Map backend develops.
            </p>

        </div>
        `
    );
}


/* ============================================================
   CHANNELS
   ============================================================ */

async function openChannels() {

    openSubPage(
        "Channels",
        `
        <div class="page-h">
            📺 Channels
        </div>

        <div id="channels-list">
            Loading...
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                "/api/channels"
            );

        const channels =
            Array.isArray(data?.channels)
                ? data.channels
                : [];


        const container =
            $("#channels-list");

        if (!container) {
            return;
        }


        container.innerHTML =
            channels
                .map(
                    (channel) => `
                        <div
                            class="sub-item"
                            onclick="openChannel('${escapeHTML(
                                channel.id
                            )}')"
                        >

                            <div class="icon">
                                📺
                            </div>

                            <div class="text">

                                <strong>
                                    ${escapeHTML(
                                        channel.name
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        channel.desc || ""
                                    )}
                                </span>

                            </div>

                            <span>
                                →
                            </span>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        toast(
            "Could not load channels."
        );
    }
}


function openChannel(
    channelId
) {

    openSubPage(
        "Channel",
        `
        <div class="page-h">
            📺 Channel
        </div>

        <div class="post-card">

            <div style="font-size:40px;">
                📺
            </div>

            <h3 style="margin-top:10px;">
                Channel content
            </h3>

            <p
                class="muted"
                style="margin-top:8px;"
            >
                Live updates, articles, videos,
                subscriptions and notifications
                will be connected in the next phase.
            </p>

        </div>
        `
    );
}


/* ============================================================
   COMMUNITIES
   ============================================================ */

async function openCommunities() {

    openSubPage(
        "Communities",
        `
        <div class="page-h">
            👥 Communities
        </div>

        <div id="community-categories">
            Loading...
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                "/api/communities/categories"
            );

        const categories =
            Array.isArray(data?.categories)
                ? data.categories
                : [];


        const container =
            $("#community-categories");

        if (!container) {
            return;
        }


        container.innerHTML =
            categories
                .map(
                    (category) => `
                        <div
                            class="sub-item"
                            onclick="openCommunityCategory(
                                '${escapeHTML(
                                    category.id
                                )}',
                                '${escapeHTML(
                                    category.title
                                )}'
                            )"
                        >

                            <div class="icon">
                                👥
                            </div>

                            <div class="text">

                                <strong>
                                    ${escapeHTML(
                                        category.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        category.desc || ""
                                    )}
                                </span>

                            </div>

                            <span>
                                →
                            </span>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        toast(
            "Could not load communities."
        );
    }
}


function openCommunityCategory(
    id,
    title
) {

    openSubPage(
        title,
        `
        <div class="page-h">
            👥 ${escapeHTML(title)}
        </div>

        <div class="post-card">

            <strong>
                ${escapeHTML(title)} Community
            </strong>

            <p
                class="muted"
                style="
                    margin-top:8px;
                    line-height:1.5;
                "
            >
                Community posts, members, Join,
                Leave and Create Community will be
                connected in the community backend phase.
            </p>

            <button
                class="btn-primary"
                style="
                    margin-top:16px;
                    width:100%;
                "
                onclick="toast('Community backend coming soon.')"
            >
                Join Community
            </button>

        </div>
        `
    );
}


/* ============================================================
   VIDEOS
   ============================================================ */

async function openVideos() {

    openSubPage(
        "Videos",
        `
        <div class="page-h">
            ▶️ Videos
        </div>

        <div id="video-feed">
            Loading videos...
        </div>
        `
    );


    try {

        const data =
            await apiFetch(
                "/api/videos"
            );

        const videos =
            Array.isArray(data?.videos)
                ? data.videos
                : Array.isArray(data)
                    ? data
                    : [];


        const container =
            $("#video-feed");

        if (!container) {
            return;
        }


        if (!videos.length) {

            container.innerHTML = `
                <div class="post-card"
                     style="text-align:center;">

                    <div style="font-size:42px;">
                        ▶️
                    </div>

                    <strong>
                        No videos yet
                    </strong>

                    <p
                        class="muted"
                        style="margin-top:8px;"
                    >
                        Video feed is ready for
                        backend content.
                    </p>

                </div>
            `;

            return;
        }


        container.innerHTML =
            videos
                .map(
                    (video) => `
                        <div class="post-card">

                            <video
                                class="post-media"
                                controls
                                playsinline
                                loop
                                src="${escapeHTML(
                                    mediaURL(
                                        video.media_url ||
                                        video.url ||
                                        ""
                                    )
                                )}"
                            ></video>

                            <strong>
                                ${escapeHTML(
                                    video.username ||
                                    video.full_name ||
                                    "User"
                                )}
                            </strong>

                            <p class="post-caption">
                                ${formatText(
                                    video.caption || ""
                                )}
                            </p>

                        </div>
                    `
                )
                .join("");

    } catch (error) {

        console.warn(
            "Video endpoint:",
            error.message
        );

        const container =
            $("#video-feed");

        if (container) {

            container.innerHTML = `
                <div class="post-card">
                    <strong>
                        Videos
                    </strong>

                    <p
                        class="muted"
                        style="margin-top:8px;"
                    >
                        Video module is ready.
                    </p>
                </div>
            `;
        }
    }
}


/* ============================================================
   PROFILE
   ============================================================ */

async function loadMyProfile() {

    if (!CURRENT_USER) {

        await loadCurrentUser();

        if (!CURRENT_USER) {
            showAuth();
            return;
        }
    }


    updateOwnProfileUI();


    const profilePosts =
        $("#profile-posts");

    if (!profilePosts) {
        return;
    }


    try {

        const data =
            await apiFetch(
                "/api/feed"
            );

        const posts =
            extractPosts(data)
                .filter(
                    (post) =>
                        Number(post.user_id) ===
                        Number(CURRENT_USER.id)
                );


        const postCount =
            $("#stat-posts");

        if (postCount) {
            postCount.textContent =
                String(posts.length);
        }


        profilePosts.innerHTML =
            posts.length
                ? posts
                    .map(
                        (post) =>
                            renderPost(post)
                    )
                    .join("")
                : `
                    <div class="post-card"
                         style="text-align:center;">
                        <strong>
                            No posts yet
                        </strong>

                        <p
                            class="muted"
                            style="margin-top:8px;"
                        >
                            Your posts will appear here.
                        </p>
                    </div>
                  `;

    } catch (error) {

        console.error(
            "Profile posts error:",
            error
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


    openModal(`
        <h2>Edit Profile</h2>

        <form id="edit-profile-form">

            <input
                id="edit-fullname"
                type="text"
                value="${escapeHTML(
                    CURRENT_USER.full_name || ""
                )}"
                placeholder="Full Name"
                style="
                    width:100%;
                    padding:12px;
                    margin-bottom:10px;
                    border-radius:10px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                    outline:none;
                "
            >

            <textarea
                id="edit-bio"
                rows="4"
                placeholder="Bio"
                style="
                    width:100%;
                    padding:12px;
                    margin-bottom:10px;
                    border-radius:10px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                    outline:none;
                    font-family:inherit;
                "
            >${escapeHTML(
                CURRENT_USER.bio || ""
            )}</textarea>

            <input
                id="edit-location"
                type="text"
                value="${escapeHTML(
                    CURRENT_USER.location || ""
                )}"
                placeholder="Location"
                style="
                    width:100%;
                    padding:12px;
                    margin-bottom:16px;
                    border-radius:10px;
                    border:1px solid var(--border);
                    background:var(--bg-3);
                    color:var(--text);
                    outline:none;
                "
            >

            <button
                class="btn-primary"
                type="submit"
                style="width:100%;"
            >
                Save Changes
            </button>

        </form>
    `);


    const form =
        $("#edit-profile-form");

    if (form) {

        form.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                await updateProfile();
            }
        );
    }
}


async function updateProfile() {

    const fullName =
        $("#edit-fullname")?.value.trim();

    const bio =
        $("#edit-bio")?.value.trim();

    const location =
        $("#edit-location")?.value.trim();


    try {

        /*
         * Current profile.py accepts query parameters.
         * Therefore PATCH is sent using URLSearchParams.
         */

        const params =
            new URLSearchParams();

        params.append(
            "full_name",
            fullName || ""
        );

        params.append(
            "bio",
            bio || ""
        );

        params.append(
            "location",
            location || ""
        );


        const data =
            await apiFetch(
                `/api/profile?${params.toString()}`,
                {
                    method: "PATCH"
                }
            );


        const user =
            data?.user ||
            data;


        if (user?.id) {
            saveCurrentUser(user);
        } else {

            CURRENT_USER.full_name =
                fullName || "";

            CURRENT_USER.bio =
                bio || "";

            CURRENT_USER.location =
                location || "";

            saveCurrentUser(
                CURRENT_USER
            );
        }


        updateOwnProfileUI();

        closeModal();

        toast(
            "Profile updated."
        );

    } catch (error) {

        console.error(
            "Profile update error:",
            error
        );

        toast(
            error.message ||
            "Could not update profile."
        );
    }
}


/* ============================================================
   USER MANUAL
   ============================================================ */

async function showUserManual() {

    let manual;

    try {

        manual =
            await apiFetch(
                "/api/user-manual"
            );

    } catch (error) {

        manual = {
            app: APP_NAME,
            tagline: APP_VERSION,
            founder: FOUNDER,
            company: COMPANY,
            version: APP_VERSION
        };
    }


    openModal(`
        <h2>
            ${escapeHTML(
                manual.app || APP_NAME
            )}
        </h2>

        <p class="muted">
            ${escapeHTML(
                manual.tagline || "Connect beyond"
            )}
        </p>


        <div class="manual-section">

            <h3>
                About MSAFIRI
            </h3>

            <p>
                ${escapeHTML(
                    manual.about ||
                    `${APP_NAME} is a social, communication and AI application.`
                )}
            </p>

        </div>


        <div class="manual-section">

            <h3>
                Founder & Company
            </h3>

            <p>
                Founder:
                ${escapeHTML(
                    manual.founder ||
                    FOUNDER
                )}
            </p>

            <p>
                Company:
                ${escapeHTML(
                    manual.company ||
                    COMPANY
                )}
            </p>

        </div>


        <div class="manual-section">

            <h3>
                Sections of the App
            </h3>

            <ul>

                <li>
                    Home — Feed, Stories, Posts
                </li>

                <li>
                    Discovery — AI Council, Studio,
                    Market, World Map, Channels,
                    Communities, Videos, Settings
                </li>

                <li>
                    Chats — Messaging
                </li>

                <li>
                    Profile — Your profile
                </li>

            </ul>

        </div>


        <div class="manual-section">

            <h3>
                How to Use MSAFIRI
            </h3>

            <ul>

                <li>
                    Register → Fill details →
                    Create Account
                </li>

                <li>
                    Home → + → Create Post
                </li>

                <li>
                    My Story → Select media →
                    Post Story
                </li>

                <li>
                    Search people → Open profile →
                    Message
                </li>

                <li>
                    Discovery → AI Council →
                    Choose AI
                </li>

            </ul>

        </div>


        <div class="manual-section">

            <h3>
                Support
            </h3>

            <p>
                ${escapeHTML(
                    manual.support ||
                    `Contact ${COMPANY}`
                )}
            </p>

        </div>


        <button
            class="btn-primary"
            style="width:100%;"
            onclick="downloadUserManual()"
        >
            📥 Download User Manual
        </button>
    `);
}


function downloadUserManual() {

    const text = `
${APP_NAME}
${APP_VERSION}

${APP_TAGLINE_PLACEHOLDER()}

Founder:
${FOUNDER}

Company:
${COMPANY}

==================================================
ABOUT MSAFIRI
==================================================

MSAFIRI GLOBAL MEDIA is a social, communication,
and AI platform.

==================================================
SECTIONS OF THE APP
==================================================

Home
- Feed
- Stories
- Posts

Discovery
- AI Council
- Creative Studio
- Market
- World Map
- Channels
- Communities
- Videos
- Settings

Chats
- Messaging
- Conversations

Profile
- Profile information
- Posts

==================================================
HOW TO USE
==================================================

Create Account:
Register → Fill details → Create Account

Create Post:
Home → + → Caption → Photo/Video → Publish

Share Story:
My Story → Select media → Post Story

Chat:
Search people → Open profile → Message

Explore AI:
Discovery → AI Council → Choose AI

==================================================
FOUNDER
==================================================

${FOUNDER}

==================================================
COMPANY
==================================================

${COMPANY}

==================================================
VERSION
==================================================

${APP_VERSION}

==================================================
`;

    const blob =
        new Blob(
            [text],
            {
                type: "text/plain;charset=utf-8"
            }
        );

    const url =
        URL.createObjectURL(blob);

    const anchor =
        document.createElement("a");

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
        "User Manual downloaded."
    );
}


function APP_TAGLINE_PLACEHOLDER() {
    return "Connect beyond — Media V0.0.1";
}


/* ============================================================
   SETTINGS
   ============================================================ */

async function openSettings() {

    openModal(`
        <h2>
            Settings
        </h2>

        <div class="sub-item"
             onclick="showUserManual()">

            <div class="icon">
                📖
            </div>

            <div class="text">
                <strong>
                    User Manual
                </strong>

                <span>
                    Learn how to use MSAFIRI
                </span>
            </div>

            <span>
                →
            </span>

        </div>


        <div class="sub-item"
             onclick="toggleTheme()">

            <div class="icon">
                🌓
            </div>

            <div class="text">
                <strong>
                    Toggle Theme
                </strong>

                <span>
                    Light / Dark
                </span>
            </div>

            <span>
                →
            </span>

        </div>


        <div class="sub-item">

            <div class="icon">
                ℹ️
            </div>

            <div class="text">
                <strong>
                    Version
                </strong>

                <span>
                    ${escapeHTML(
                        APP_VERSION
                    )}
                </span>
            </div>

        </div>


        <div class="sub-item"
             onclick="logout()">

            <div class="icon">
                🚪
            </div>

            <div class="text">
                <strong>
                    Logout
                </strong>

                <span>
                    Sign out of your account
                </span>
            </div>

        </div>
    `);
}


/* ============================================================
   THEME
   ============================================================ */

function initializeTheme() {

    const saved =
        localStorage.getItem(
            THEME_KEY
        );

    if (saved === "light") {
        applyLightTheme();
    } else {
        applyDarkTheme();
    }
}


function toggleTheme() {

    const current =
        localStorage.getItem(
            THEME_KEY
        ) || "dark";

    if (current === "dark") {

        localStorage.setItem(
            THEME_KEY,
            "light"
        );

        applyLightTheme();

        toast(
            "Light theme enabled."
        );

    } else {

        localStorage.setItem(
            THEME_KEY,
            "dark"
        );

        applyDarkTheme();

        toast(
            "Dark theme enabled."
        );
    }
}


function applyLightTheme() {

    const root =
        document.documentElement;

    root.style.setProperty(
        "--bg",
        "#f4f7ff"
    );

    root.style.setProperty(
        "--bg-2",
        "#ffffff"
    );

    root.style.setProperty(
        "--bg-3",
        "#e9edfa"
    );

    root.style.setProperty(
        "--text",
        "#111827"
    );

    root.style.setProperty(
        "--text-2",
        "#64748b"
    );

    root.style.setProperty(
        "--border",
        "#d9def0"
    );
}


function applyDarkTheme() {

    const root =
        document.documentElement;

    root.style.setProperty(
        "--bg",
        "#0a0e27"
    );

    root.style.setProperty(
        "--bg-2",
        "#131837"
    );

    root.style.setProperty(
        "--bg-3",
        "#1c2350"
    );

    root.style.setProperty(
        "--text",
        "#ffffff"
    );

    root.style.setProperty(
        "--text-2",
        "#a0a8c8"
    );

    root.style.setProperty(
        "--border",
        "#2a3260"
    );
}


/* ============================================================
   LOGOUT
   ============================================================ */

async function logout() {

    try {

        if (TOKEN) {

            /*
             * Logout endpoint may or may not exist.
             * Failure here should never prevent local logout.
             */

            try {

                await apiFetch(
                    "/api/auth/logout",
                    {
                        method: "POST"
                    }
                );

            } catch (error) {
                console.warn(
                    "Server logout unavailable:",
                    error.message
                );
            }
        }

    } finally {

        TOKEN = null;

        CURRENT_USER = null;

        CACHED_POSTS = [];

        CACHED_CHATS = [];

        PAGE_HISTORY = [];

        localStorage.removeItem(
            TOKEN_KEY
        );

        localStorage.removeItem(
            USER_KEY
        );


        closeModal();

        showAuth();

        switchAuthTab(
            "login"
        );

        toast(
            "Logged out."
        );
    }
}


/* ============================================================
   MODAL
   ============================================================ */

function openModal(
    html
) {

    const modal =
        $("#modal");

    const body =
        $("#modal-body");

    if (!modal || !body) {
        return;
    }

    body.innerHTML =
        html;

    modal.classList.remove(
        "hidden"
    );
}


function closeModal() {

    const modal =
        $("#modal");

    const body =
        $("#modal-body");

    if (modal) {
        modal.classList.add(
            "hidden"
        );
    }

    if (body) {
        body.innerHTML = "";
    }
}


/* ============================================================
   DROPDOWN
   ============================================================ */

function toggleDotsMenu() {

    const menu =
        $("#dots-menu");

    if (!menu) {
        return;
    }

    menu.classList.toggle(
        "hidden"
    );
}


function closeDotsMenu() {

    const menu =
        $("#dots-menu");

    if (menu) {
        menu.classList.add(
            "hidden"
        );
    }
}


/* ============================================================
   TOAST
   ============================================================ */

function toast(
    message
) {

    const old =
        document.querySelector(
            ".toast"
        );

    if (old) {
        old.remove();
    }


    const element =
        document.createElement("div");

    element.className =
        "toast";

    element.textContent =
        message || "Done";


    document.body.appendChild(
        element
    );


    setTimeout(
        () => {

            if (element) {
                element.remove();
            }

        },
        3000
    );
}


/* ============================================================
   BUTTON LOADING
   ============================================================ */

function setButtonLoading(
    button,
    loading,
    text
) {

    if (!button) {
        return;
    }


    if (loading) {

        if (!button.dataset.originalText) {
            button.dataset.originalText =
                button.textContent;
        }

        button.disabled =
            true;

        button.textContent =
            text || "Loading...";

    } else {

        button.disabled =
            false;

        button.textContent =
            button.dataset.originalText ||
            text ||
            "Submit";
    }
}


/* ============================================================
   LOGIN REQUIREMENT
   ============================================================ */

function requireLogin() {

    if (TOKEN) {
        return true;
    }

    showAuth();

    toast(
        "Please login first."
    );

    return false;
}


/* ============================================================
   MEDIA URL
   ============================================================ */

function mediaURL(
    url
) {

    if (!url) {
        return "";
    }


    if (
        url.startsWith("http://") ||
        url.startsWith("https://") ||
        url.startsWith("data:")
    ) {
        return url;
    }


    if (url.startsWith("/")) {
        return `${API}${url}`;
    }


    return `${API}/${url}`;
}


/* ============================================================
   INITIAL
   ============================================================ */

function getInitial(
    name
) {

    const value =
        String(name || "M")
            .trim();

    if (!value) {
        return "M";
    }

    return value
        .charAt(0)
        .toUpperCase();
}


/* ============================================================
   TIME
   ============================================================ */

function formatTime(
    value
) {

    if (!value) {
        return "";
    }


    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "";
    }


    const now =
        Date.now();

    const diff =
        Math.max(
            0,
            now - date.getTime()
        );


    const seconds =
        Math.floor(
            diff / 1000
        );

    if (seconds < 60) {
        return "now";
    }


    const minutes =
        Math.floor(
            seconds / 60
        );

    if (minutes < 60) {
        return `${minutes}m`;
    }


    const hours =
        Math.floor(
            minutes / 60
        );

    if (hours < 24) {
        return `${hours}h`;
    }


    const days =
        Math.floor(
            hours / 24
        );

    if (days < 7) {
        return `${days}d`;
    }


    return date.toLocaleDateString();
}


/* ============================================================
   TEXT FORMAT
   ============================================================ */

function formatText(
    value
) {

    const safe =
        escapeHTML(
            value || ""
        );

    return safe
        .replace(
            /\n/g,
            "<br>"
        );
}


/* ============================================================
   GLOBAL ERROR PROTECTION
   ============================================================ */

window.addEventListener(
    "error",
    (event) => {

        console.error(
            "Global JavaScript error:",
            event.error ||
            event.message
        );
    }
);


window.addEventListener(
    "unhandledrejection",
    (event) => {

        console.error(
            "Unhandled Promise rejection:",
            event.reason
        );
    }
);


/* ============================================================
   GLOBAL FUNCTIONS
   ------------------------------------------------------------
   Functions used by inline onclick handlers must be exposed
   on window.
   ============================================================ */

window.navigate = navigate;
window.goBack = goBack;

window.toggleLike = toggleLike;
window.toggleSave = toggleSave;
window.sharePost = sharePost;

window.openComments = openComments;
window.openCreatePost = openCreatePost;
window.openCreateStory = openCreateStory;

window.openUserProfile = openUserProfile;
window.startChatWithUser = startChatWithUser;
window.openChat = openChat;

window.openDiscovery = openDiscovery;
window.openAICouncil = openAICouncil;
window.openAI = openAI;

window.chooseEducationCountry =
    chooseEducationCountry;

window.chooseEducationLevel =
    chooseEducationLevel;

window.openEducationChat =
    openEducationChat;

window.openCreativeStudio =
    openCreativeStudio;

window.openStudioTool =
    openStudioTool;

window.openMarket =
    openMarket;

window.openMarketCategory =
    openMarketCategory;

window.openWorldMap =
    openWorldMap;

window.openCountry =
    openCountry;

window.openChannels =
    openChannels;

window.openChannel =
    openChannel;

window.openCommunities =
    openCommunities;

window.openCommunityCategory =
    openCommunityCategory;

window.openVideos =
    openVideos;

window.openSettings =
    openSettings;

window.showUserManual =
    showUserManual;

window.downloadUserManual =
    downloadUserManual;

window.toggleTheme =
    toggleTheme;

window.logout =
    logout;

window.toast =
    toast;

window.closeModal =
    closeModal;

window.loadFeed =
    loadFeed;


/* ============================================================
   END
   ============================================================ */
