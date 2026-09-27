// ============================================
// MSAFIRI GLOBAL MEDIA — App Logic
// Authentication/JWT FIXED VERSION
// ============================================

const API = "";
let currentUser = null;
let currentFeed = "for-you";
let navStack = [];
let authBusy = false;

// ============================================
// AUTH TOKEN HELPERS
// ============================================

function getToken() {
  return localStorage.getItem("token");
}

function saveToken(token) {
  if (token) {
    localStorage.setItem("token", token);
  }
}

function clearToken() {
  localStorage.removeItem("token");
}

function authHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getToken();

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

async function apiFetch(url, options = {}) {
  const opts = { ...options };

  opts.headers = authHeaders(opts.headers || {});

  const response = await fetch(url, opts);

  // If token is invalid/expired, clear local authentication.
  if (response.status === 401) {
    clearToken();
    currentUser = null;
  }

  return response;
}

// ============================================
// INIT
// ============================================

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    const splash = document.getElementById("splash");

    if (splash) {
      splash.classList.add("hidden");
    }

    checkAuth();
  }, 3000);
});

// ============================================
// AUTH CHECK
// ============================================

async function checkAuth() {
  const token = getToken();

  // No JWT = not authenticated
  if (!token) {
    showAuth();
    return;
  }

  try {
    const r = await apiFetch(`${API}/api/auth/me`);

    if (r.ok) {
      currentUser = await r.json();
      showApp();
      return;
    }

    clearToken();
    currentUser = null;
    showAuth();

  } catch (error) {
    console.error("Auth check error:", error);
    showAuth();
  }
}

// ============================================
// SHOW AUTH / APP
// ============================================

function showAuth() {
  const auth = document.getElementById("auth-screen");
  const app = document.getElementById("app");

  if (auth) auth.classList.remove("hidden");
  if (app) app.classList.add("hidden");
}

function showApp() {
  const auth = document.getElementById("auth-screen");
  const app = document.getElementById("app");

  if (auth) auth.classList.add("hidden");
  if (app) app.classList.remove("hidden");

  loadHome();
  loadDiscovery();
  loadProfile();
}

// ============================================
// AUTH TABS
// ============================================

document.querySelectorAll(".auth-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document
      .querySelectorAll(".auth-tab")
      .forEach(t => t.classList.remove("active"));

    tab.classList.add("active");

    const target = tab.dataset.tab;

    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

    if (loginForm) {
      loginForm.classList.toggle("hidden", target !== "login");
    }

    if (registerForm) {
      registerForm.classList.toggle("hidden", target !== "register");
    }
  });
});

// ============================================
// LOGIN
// ============================================

const loginForm = document.getElementById("login-form");

if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (authBusy) return;

    authBusy = true;

    const submitButton = loginForm.querySelector(
      'button[type="submit"]'
    );

    if (submitButton) {
      submitButton.disabled = true;
    }

    const username = document
      .getElementById("login-username")
      .value
      .trim();

    const password = document
      .getElementById("login-password")
      .value;

    if (!username || !password) {
      toast("Enter username/email and password");
      authBusy = false;

      if (submitButton) {
        submitButton.disabled = false;
      }

      return;
    }

    try {
      const r = await fetch(`${API}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          username,
          password
        })
      });

      const data = await readJSONSafe(r);

      if (!r.ok) {
        toast(
          data?.detail ||
          "Login failed. Check your username/email and password."
        );

        return;
      }

      if (!data.access_token) {
        toast("Login succeeded but no access token was returned.");
        return;
      }

      // Save JWT
      saveToken(data.access_token);

      // Save returned user if available
      if (data.user) {
        currentUser = data.user;
      }

      toast("Login successful!");

      // Verify token with backend
      await checkAuth();

    } catch (error) {
      console.error("Login error:", error);
      toast("Network error during login.");
    } finally {
      authBusy = false;

      if (submitButton) {
        submitButton.disabled = false;
      }
    }
  });
}

// ============================================
// REGISTER
// ============================================

const registerForm = document.getElementById("register-form");

if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (authBusy) return;

    authBusy = true;

    const submitButton = registerForm.querySelector(
      'button[type="submit"]'
    );

    if (submitButton) {
      submitButton.disabled = true;
    }

    const username = document
      .getElementById("reg-username")
      .value
      .trim();

    const email = document
      .getElementById("reg-email")
      .value
      .trim();

    const full_name = document
      .getElementById("reg-fullname")
      .value
      .trim();

    const password = document
      .getElementById("reg-password")
      .value;

    if (!username || !email || !password) {
      toast("Username, email and password are required.");

      authBusy = false;

      if (submitButton) {
        submitButton.disabled = false;
      }

      return;
    }

    try {
      const r = await fetch(`${API}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          username,
          email,
          full_name,
          password
        })
      });

      const data = await readJSONSafe(r);

      if (!r.ok) {
        toast(
          data?.detail ||
          "Registration failed."
        );

        return;
      }

      // Backend returns JWT immediately after registration.
      if (data.access_token) {
        saveToken(data.access_token);
      }

      if (data.user) {
        currentUser = data.user;
      }

      toast("Account created successfully!");

      // Automatically enter the app.
      await checkAuth();

    } catch (error) {
      console.error("Registration error:", error);
      toast("Network error during registration.");
    } finally {
      authBusy = false;

      if (submitButton) {
        submitButton.disabled = false;
      }
    }
  });
}

// ============================================
// SAFE JSON READER
// ============================================

async function readJSONSafe(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

// ============================================
// NAVIGATION
// ============================================

document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const nav = btn.dataset.nav;

    document
      .querySelectorAll(".nav-btn")
      .forEach(b => b.classList.remove("active"));

    btn.classList.add("active");

    document
      .querySelectorAll(".page")
      .forEach(p => p.classList.remove("active"));

    const page = document.getElementById(`page-${nav}`);

    if (page) {
      page.classList.add("active");
    }

    const titles = {
      home: "MSAFIRI",
      discovery: "Discovery",
      chats: "Chats",
      profile: "Profile"
    };

    const pageTitle = document.getElementById("page-title");

    if (pageTitle) {
      pageTitle.textContent = titles[nav] || "MSAFIRI";
    }

    navStack = [];

    if (nav === "chats") loadChats();
    if (nav === "profile") loadProfile();
  });
});

// ============================================
// BACK BUTTON
// ============================================

const backButton = document.getElementById("back-btn");

if (backButton) {
  backButton.addEventListener("click", () => {
    if (navStack.length > 0) {
      const prev = navStack.pop();
      prev();
    }
  });
}

function showSubPage(title, renderFn) {
  navStack.push(() => {
    document.getElementById("page-sub").classList.remove("active");

    const activePage = document.querySelector(".page.active");

    if (activePage) {
      activePage.classList.add("active");
    }

    document.getElementById("back-btn").classList.add("hidden");
    document.getElementById("page-title").textContent = "MSAFIRI";
  });

  document
    .querySelectorAll(".page")
    .forEach(p => p.classList.remove("active"));

  document.getElementById("page-sub").classList.add("active");

  document.getElementById("page-title").textContent = title;

  document.getElementById("back-btn").classList.remove("hidden");

  renderFn(document.getElementById("sub-content"));
}

// ============================================
// HOME
// ============================================

async function loadHome() {
  await loadStories();
  await loadFeed();
}

document.querySelectorAll(".feed-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document
      .querySelectorAll(".feed-tab")
      .forEach(t => t.classList.remove("active"));

    tab.classList.add("active");

    currentFeed = tab.dataset.feed;

    loadFeed();
  });
});

// ============================================
// STORIES
// ============================================

async function loadStories() {
  try {
    const r = await apiFetch(`${API}/api/stories`);

    if (!r.ok) return;

    const data = await r.json();

    const bar = document.getElementById("stories-bar");

    if (!bar) return;

    bar
      .querySelectorAll(".story-item:not(.add-story)")
      .forEach(el => el.remove());

    (data.stories || []).forEach(s => {
      const el = document.createElement("div");

      el.className = "story-item";

      el.innerHTML = `
        <div class="story-avatar">
          ${(s.user_id || "U").toString().charAt(0)}
        </div>
        <span>User</span>
      `;

      bar.appendChild(el);
    });

  } catch (error) {
    console.error("Stories error:", error);
  }
}

// ============================================
// FEED
// ============================================

async function loadFeed() {
  const feed = document.getElementById("feed");

  if (!feed) return;

  feed.innerHTML = `
    <p class="muted" style="text-align:center;padding:20px;">
      Loading...
    </p>
  `;

  try {
    const r = await apiFetch(
      `${API}/api/feed?type=${encodeURIComponent(currentFeed)}`
    );

    if (!r.ok) {
      feed.innerHTML = `
        <p class="muted" style="text-align:center;padding:20px;">
          Failed to load feed
        </p>
      `;
      return;
    }

    const data = await r.json();

    if (!data.posts || data.posts.length === 0) {
      feed.innerHTML = `
        <p class="muted" style="text-align:center;padding:40px 20px;">
          No posts yet. Be the first to share!
        </p>
      `;
      return;
    }

    feed.innerHTML = "";

    data.posts.forEach(p => {
      feed.appendChild(renderPost(p));
    });

  } catch (error) {
    console.error("Feed error:", error);

    feed.innerHTML = `
      <p class="muted" style="text-align:center;padding:20px;">
        Failed to load feed
      </p>
    `;
  }
}

function renderPost(p) {
  const el = document.createElement("div");

  el.className = "post-card";

  el.innerHTML = `
    <div class="post-header">
      <div class="post-avatar">
        ${(p.user_id || "U").toString().charAt(0)}
      </div>

      <div class="post-user">
        <strong>User ${p.user_id || ""}</strong>
        <span>${timeAgo(p.created_at)}</span>
      </div>
    </div>

    ${
      p.caption
        ? `<p class="post-caption">${escape(p.caption)}</p>`
        : ""
    }

    ${
      p.media_url
        ? `<img class="post-media" src="${escape(p.media_url)}" alt="">`
        : ""
    }

    <div class="post-actions">
      <button onclick="toggleLike(this)">
        ❤️ ${p.likes || 0}
      </button>

      <button>
        💬 ${p.comments || 0}
      </button>

      <button>
        ↗️ Share
      </button>

      <button>
        🔖 Save
      </button>
    </div>
  `;

  return el;
}

window.toggleLike = function(btn) {
  btn.classList.toggle("liked");
};

// ============================================
// DISCOVERY
// ============================================

async function loadDiscovery() {
  try {
    const r = await apiFetch(`${API}/api/discovery`);

    if (!r.ok) return;

    const data = await r.json();

    const grid = document.getElementById("discovery-grid");

    if (!grid) return;

    grid.innerHTML = "";

    data.cards.forEach(card => {
      const el = document.createElement("div");

      el.className = "disc-card";

      el.innerHTML = `
        <span class="icon">${card.icon}</span>
        <div class="title">${escape(card.title)}</div>
        <div class="desc">${escape(card.desc)}</div>
      `;

      el.addEventListener("click", () => {
        handleDiscoveryCard(card.id, card.title);
      });

      grid.appendChild(el);
    });

  } catch (error) {
    console.error("Discovery error:", error);
  }
}

function handleDiscoveryCard(id, title) {
  const handlers = {
    "ai-council": showAICouncil,
    "creative-studio": showStudio,
    "market": showMarket,
    "world-map": showWorldMap,
    "channels": showChannels,
    "communities": showCommunities,
    "videos": showVideos,
    "settings": showSettings
  };

  (handlers[id] || (() => toast("Coming soon")))(title);
}

// ============================================
// AI COUNCIL
// ============================================

async function showAICouncil() {
  showSubPage("AI Council", async (c) => {

    c.innerHTML = `
      <h2>AI Council</h2>
      <p class="muted" style="margin-bottom:16px;">
        Choose an AI assistant
      </p>
    `;

    const r = await apiFetch(`${API}/api/ai-council`);

    if (!r.ok) return;

    const data = await r.json();

    data.ais.forEach(ai => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">${ai.icon}</span>
        <div class="text">
          <strong>${escape(ai.title)}</strong>
          <span>${escape(ai.desc)}</span>
        </div>
      `;

      el.addEventListener("click", () => {

        if (ai.id === "education") {
          showEducationAICountries();
        } else {
          showAIChat(ai.id);
        }

      });

      c.appendChild(el);
    });
  });
}

async function showEducationAICountries() {
  showSubPage("Education AI", async (c) => {

    c.innerHTML = `
      <h2>Step 1 — Choose Country</h2>
      <p class="muted" style="margin-bottom:16px;">
        Select your country
      </p>
    `;

    const r = await apiFetch(
      `${API}/api/ai-council/countries`
    );

    if (!r.ok) return;

    const data = await r.json();

    data.countries.forEach(country => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">🌍</span>
        <div class="text">
          <strong>${escape(country)}</strong>
        </div>
      `;

      el.addEventListener("click", () => {
        showEducationAILevels(country);
      });

      c.appendChild(el);
    });
  });
}

async function showEducationAILevels(country) {
  showSubPage(`Education — ${country}`, async (c) => {

    c.innerHTML = `
      <h2>Step 2 — Choose Level</h2>
      <p class="muted" style="margin-bottom:16px;">
        ${escape(country)}
      </p>
    `;

    const r = await apiFetch(
      `${API}/api/ai-council/levels`
    );

    if (!r.ok) return;

    const data = await r.json();

    data.levels.forEach(level => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">🎓</span>
        <div class="text">
          <strong>${escape(level)}</strong>
        </div>
      `;

      el.addEventListener("click", () => {
        showEducationAIContent(country, level);
      });

      c.appendChild(el);
    });
  });
}

async function showEducationAIContent(country, level) {
  showSubPage(`Education — ${level}`, async (c) => {

    c.innerHTML = `
      <h2>Step 3 — Choose Content</h2>
      <p class="muted" style="margin-bottom:16px;">
        ${escape(country)} • ${escape(level)}
      </p>
    `;

    const r = await apiFetch(
      `${API}/api/ai-council/content-types`
    );

    if (!r.ok) return;

    const data = await r.json();

    data.content_types.forEach(ct => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">📄</span>
        <div class="text">
          <strong>${escape(ct)}</strong>
        </div>
      `;

      el.addEventListener("click", () => {
        showAIChat(
          "education",
          {
            country,
            level,
            content: ct
          }
        );
      });

      c.appendChild(el);
    });
  });
}

function showAIChat(ai, ctx = {}) {

  showSubPage("AI Chat", (c) => {

    c.innerHTML = `
      <h2>
        ${escape(ai.charAt(0).toUpperCase() + ai.slice(1))} AI
      </h2>

      <div id="chat-msgs" class="chat-msgs">
        <div class="msg ai">
          Hello! I'm your
          ${escape(ctx.content || "")}
          assistant for
          ${escape(ctx.level || "")}
          curriculum in
          ${escape(ctx.country || "")}.
          Ask me anything.
        </div>
      </div>

      <div
        class="search-bar"
        style="display:flex;gap:8px;margin-top:12px;"
      >
        <input
          type="text"
          id="ai-input"
          placeholder="Ask a question..."
          style="flex:1;"
        >

        <button
          class="btn-primary"
          id="ai-send"
          style="padding:12px 20px;"
        >
          Send
        </button>
      </div>
    `;

    const send = async () => {

      const input = document.getElementById("ai-input");

      const q = input.value.trim();

      if (!q) return;

      const msgs = document.getElementById("chat-msgs");

      msgs.innerHTML += `
        <div class="msg user">
          ${escape(q)}
        </div>
      `;

      input.value = "";

      msgs.scrollTop = msgs.scrollHeight;

      try {

        const params = new URLSearchParams({
          ai,
          ...ctx,
          q
        });

        const r = await apiFetch(
          `${API}/api/ai-council/chat?${params}`
        );

        const data = await r.json();

        msgs.innerHTML += `
          <div class="msg ai">
            ${escape(data.reply || "No response.")}
          </div>
        `;

        msgs.scrollTop = msgs.scrollHeight;

      } catch {

        msgs.innerHTML += `
          <div class="msg ai">
            Error reaching AI.
          </div>
        `;
      }
    };

    document
      .getElementById("ai-send")
      .addEventListener("click", send);

    document
      .getElementById("ai-input")
      .addEventListener("keypress", e => {
        if (e.key === "Enter") send();
      });
  });
}

// ============================================
// STUDIO
// ============================================

async function showStudio() {
  showSubPage("Creative Studio", async (c) => {

    c.innerHTML = `
      <h2>Creative Studio</h2>
      <p class="muted" style="margin-bottom:16px;">
        Canva-style tools
      </p>
    `;

    const r = await apiFetch(`${API}/api/studio`);

    if (!r.ok) return;

    const data = await r.json();

    data.tools.forEach(t => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">${t.icon}</span>
        <div class="text">
          <strong>${escape(t.title)}</strong>
          <span>${escape(t.desc)}</span>
        </div>
      `;

      el.addEventListener("click", () => {
        toast(`${t.title} coming soon`);
      });

      c.appendChild(el);
    });
  });
}

// ============================================
// MARKET
// ============================================

async function showMarket() {
  showSubPage("Market", async (c) => {

    c.innerHTML = `
      <h2>Market</h2>
      <p class="muted" style="margin-bottom:16px;">
        Buy and sell
      </p>
    `;

    const r = await apiFetch(
      `${API}/api/market/categories`
    );

    if (!r.ok) return;

    const data = await r.json();

    data.categories.forEach(cat => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">🛍️</span>
        <div class="text">
          <strong>${escape(cat.title)}</strong>
          <span>${escape(cat.desc)}</span>
        </div>
      `;

      el.addEventListener("click", () => {
        toast(`${cat.title} — coming soon`);
      });

      c.appendChild(el);
    });
  });
}

// ============================================
// WORLD MAP
// ============================================

async function showWorldMap() {
  showSubPage("World Map", async (c) => {

    c.innerHTML = `
      <h2>World Map</h2>
      <p class="muted" style="margin-bottom:16px;">
        Explore the world
      </p>
    `;

    const r = await apiFetch(
      `${API}/api/world-map/countries`
    );

    if (!r.ok) return;

    const data = await r.json();

    data.countries.forEach(co => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">🌍</span>
        <div class="text">
          <strong>${escape(co.name)}</strong>
          <span>${co.users} users • ${co.posts} posts</span>
        </div>
      `;

      el.addEventListener("click", () => {
        toast(`${co.name} — coming soon`);
      });

      c.appendChild(el);
    });
  });
}

// ============================================
// CHANNELS
// ============================================

async function showChannels() {
  showSubPage("Channels", async (c) => {

    c.innerHTML = `
      <h2>Channels</h2>
      <p class="muted" style="margin-bottom:16px;">
        News and media
      </p>
    `;

    const r = await apiFetch(`${API}/api/channels`);

    if (!r.ok) return;

    const data = await r.json();

    data.channels.forEach(ch => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">📺</span>
        <div class="text">
          <strong>${escape(ch.name)}</strong>
          <span>${escape(ch.desc)}</span>
        </div>
      `;

      el.addEventListener("click", () => {
        toast(`${ch.name} — coming soon`);
      });

      c.appendChild(el);
    });
  });
}

// ============================================
// COMMUNITIES
// ============================================

async function showCommunities() {
  showSubPage("Communities", async (c) => {

    c.innerHTML = `
      <h2>Communities</h2>
      <p class="muted" style="margin-bottom:16px;">
        Join groups
      </p>
    `;

    const r = await apiFetch(
      `${API}/api/communities/categories`
    );

    if (!r.ok) return;

    const data = await r.json();

    data.categories.forEach(cat => {

      const el = document.createElement("div");

      el.className = "sub-item";

      el.innerHTML = `
        <span class="icon">👥</span>
        <div class="text">
          <strong>${escape(cat.title)}</strong>
          <span>${escape(cat.desc)}</span>
        </div>
      `;

      el.addEventListener("click", () => {
        toast(`${cat.title} — coming soon`);
      });

      c.appendChild(el);
    });
  });
}

// ============================================
// VIDEOS
// ============================================

async function showVideos() {
  showSubPage("Videos", async (c) => {

    c.innerHTML = `
      <h2>Videos</h2>
      <p class="muted" style="margin-bottom:16px;">
        Short video feed
      </p>

      <div class="sub-item">
        <span class="icon">▶️</span>

        <div class="text">
          <strong>Coming soon</strong>
          <span>TikTok-style feed</span>
        </div>
      </div>
    `;
  });
}

// ============================================
// SETTINGS
// ============================================

function showSettings() {

  showSubPage("Settings", (c) => {

    c.innerHTML = `
      <h2>Settings</h2>

      <div class="sub-item" id="s-manual">
        <span class="icon">📖</span>
        <div class="text">
          <strong>User Manual</strong>
          <span>How to use the app</span>
        </div>
      </div>

      <div class="sub-item" id="s-theme">
        <span class="icon">🌓</span>
        <div class="text">
          <strong>Theme</strong>
          <span>Light / Dark</span>
        </div>
      </div>

      <div class="sub-item">
        <span class="icon">ℹ️</span>
        <div class="text">
          <strong>Version</strong>
          <span>MSAFIRI MEDIA V0.0.1</span>
        </div>
      </div>

      <div class="sub-item" id="s-logout">
        <span class="icon">🚪</span>
        <div class="text">
          <strong>Logout</strong>
          <span>Sign out of your account</span>
        </div>
      </div>
    `;

    document
      .getElementById("s-manual")
      .addEventListener("click", showUserManual);

    document
      .getElementById("s-theme")
      .addEventListener("click", toggleTheme);

    document
      .getElementById("s-logout")
      .addEventListener("click", logout);
  });
}

// ============================================
// USER MANUAL
// ============================================

async function showUserManual() {

  showSubPage("User Manual", async (c) => {

    try {

      const r = await apiFetch(
        `${API}/api/user-manual`
      );

      if (!r.ok) {
        c.innerHTML = `<p class="muted">Unable to load manual.</p>`;
        return;
      }

      const m = await r.json();

      c.innerHTML = `
        <div style="text-align:center;margin-bottom:20px;">

          <div
            class="auth-logo"
            style="margin:0 auto 12px;"
          >
            M
          </div>

          <h2>${escape(m.app)}</h2>

          <p class="muted">
            ${escape(m.tagline)}
          </p>

          <p class="muted" style="margin-top:4px;">
            Founder: ${escape(m.founder)}
          </p>

          <p class="muted">
            ${escape(m.company)}
          </p>

          <p class="muted">
            Version: ${escape(m.version)}
          </p>

        </div>

        <div class="manual-section">
          <h3>About</h3>
          <p>${escape(m.about)}</p>
        </div>

        <div class="manual-section">
          <h3>Sections</h3>
          <ul>
            ${Object.entries(m.sections)
              .map(([k, v]) =>
                `<li><strong>${escape(k)}:</strong> ${escape(v)}</li>`
              )
              .join("")}
          </ul>
        </div>

        <div class="manual-section">
          <h3>How to Use</h3>
          <ul>
            ${Object.entries(m.how_to_use)
              .map(([k, v]) =>
                `<li><strong>${escape(k.replace("_", " "))}:</strong> ${escape(v)}</li>`
              )
              .join("")}
          </ul>
        </div>

        <div class="manual-section">
          <h3>Support</h3>
          <p>${escape(m.support)}</p>
        </div>

        <button
          class="btn-primary"
          id="dl-manual"
          style="width:100%;margin-top:16px;"
        >
          📥 Download User Manual
        </button>
      `;

      document
        .getElementById("dl-manual")
        .addEventListener("click", () => {

          const text = `
MSAFIRI GLOBAL MEDIA
${m.tagline}

Founder: ${m.founder}
Company: ${m.company}
Version: ${m.version}

ABOUT
${m.about}

SECTIONS
${Object.entries(m.sections)
  .map(([k, v]) => `- ${k}: ${v}`)
  .join("\n")}

HOW TO USE
${Object.entries(m.how_to_use)
  .map(([k, v]) => `- ${k}: ${v}`)
  .join("\n")}

SUPPORT
${m.support}
`;

          const blob = new Blob(
            [text],
            { type: "text/plain" }
          );

          const a = document.createElement("a");

          a.href = URL.createObjectURL(blob);
          a.download = "MSAFIRI-UserManual.txt";

          a.click();

          URL.revokeObjectURL(a.href);

          toast("Downloaded!");
        });

    } catch (error) {

      console.error("Manual error:", error);

      c.innerHTML = `
        <p class="muted">
          Unable to load user manual.
        </p>
      `;
    }
  });
}

// ============================================
// DOTS MENU
// ============================================

const dotsButton = document.getElementById("dots-btn");

if (dotsButton) {

  dotsButton.addEventListener("click", (e) => {

    e.stopPropagation();

    document
      .getElementById("dots-menu")
      .classList.toggle("hidden");

  });
}

document.addEventListener("click", () => {

  const menu = document.getElementById("dots-menu");

  if (menu) {
    menu.classList.add("hidden");
  }

});

document
  .querySelectorAll("#dots-menu button")
  .forEach(btn => {

    btn.addEventListener("click", () => {

      const a = btn.dataset.action;

      if (a === "manual") showUserManual();
      if (a === "settings") showSettings();
      if (a === "logout") logout();

      document
        .getElementById("dots-menu")
        .classList.add("hidden");

    });

  });

// ============================================
// CHATS
// ============================================

async function loadChats() {

  const list = document.getElementById("chat-list");

  if (!list) return;

  try {

    const r = await apiFetch(
      `${API}/api/messages`
    );

    if (!r.ok) {

      list.innerHTML = `
        <p class="muted" style="padding:20px;text-align:center;">
          No chats yet
        </p>
      `;

      return;
    }

    const data = await r.json();

    if (!data.messages || data.messages.length === 0) {

      list.innerHTML = `
        <p class="muted" style="padding:20px;text-align:center;">
          No chats yet
        </p>
      `;

      return;
    }

    list.innerHTML = "";

    // Existing chat rendering can be added here.

  } catch (error) {

    console.error("Chats error:", error);

    list.innerHTML = `
      <p class="muted" style="padding:20px;text-align:center;">
        No chats yet
      </p>
    `;
  }
}

// ============================================
// PROFILE
// ============================================

async function loadProfile() {

  try {

    const r = await apiFetch(
      `${API}/api/auth/me`
    );

    if (!r.ok) return;

    const u = await r.json();

    currentUser = u;

    const name = document.getElementById("profile-name");
    const username = document.getElementById("profile-username");
    const bio = document.getElementById("profile-bio");
    const avatar = document.getElementById("profile-avatar");

    if (name) {
      name.textContent =
        u.full_name ||
        u.username ||
        "User";
    }

    if (username) {
      username.textContent =
        "@" + (u.username || "user");
    }

    if (bio) {
      bio.textContent =
        u.bio ||
        "Welcome to Msafiri";
    }

    if (avatar) {
      avatar.textContent =
        (
          u.full_name ||
          u.username ||
          "U"
        )
          .charAt(0)
          .toUpperCase();
    }

  } catch (error) {

    console.error("Profile error:", error);

  }
}

// ============================================
// UTILS
// ============================================

function toast(msg) {

  const t = document.createElement("div");

  t.className = "toast";

  t.textContent = msg;

  document.body.appendChild(t);

  setTimeout(() => {
    t.remove();
  }, 2500);
}

function escape(str) {

  const d = document.createElement("div");

  d.textContent = str || "";

  return d.innerHTML;
}

function timeAgo(iso) {

  if (!iso) return "now";

  const s = Math.floor(
    (Date.now() - new Date(iso).getTime()) / 1000
  );

  if (s < 60) return s + "s";

  if (s < 3600) {
    return Math.floor(s / 60) + "m";
  }

  if (s < 86400) {
    return Math.floor(s / 3600) + "h";
  }

  return Math.floor(s / 86400) + "d";
}

// ============================================
// THEME
// ============================================

function toggleTheme() {

  document.body.style.filter =
    document.body.style.filter
      ? ""
      : "invert(1) hue-rotate(180deg)";

  toast("Theme toggled");
}

// ============================================
// LOGOUT
// ============================================

async function logout() {

  try {

    await fetch(
      `${API}/api/auth/logout`,
      {
        method: "POST",
        headers: authHeaders()
      }
    );

  } catch (error) {

    console.error("Logout error:", error);

  } finally {

    clearToken();

    currentUser = null;

    location.reload();

  }
}
