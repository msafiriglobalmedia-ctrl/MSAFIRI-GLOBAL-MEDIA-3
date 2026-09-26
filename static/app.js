// ============================================
// MSAFIRI GLOBAL MEDIA — App Logic
// ============================================

const API = "";
let currentUser = null;
let currentFeed = "for-you";
let navStack = [];

// ========== INIT ==========
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    document.getElementById("splash").classList.add("hidden");
    checkAuth();
  }, 3000);
});

async function checkAuth() {
  try {
    const r = await fetch(`${API}/api/auth/me`, { credentials: "include" });
    if (r.ok) {
      currentUser = await r.json();
      showApp();
    } else {
      showAuth();
    }
  } catch {
    showAuth();
  }
}

function showAuth() {
  document.getElementById("auth-screen").classList.remove("hidden");
  document.getElementById("app").classList.add("hidden");
}

function showApp() {
  document.getElementById("auth-screen").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  loadHome();
  loadDiscovery();
  loadProfile();
}

// ========== AUTH ==========
document.querySelectorAll(".auth-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    const target = tab.dataset.tab;
    document.getElementById("login-form").classList.toggle("hidden", target !== "login");
    document.getElementById("register-form").classList.toggle("hidden", target !== "register");
  });
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;
  try {
    const r = await fetch(`${API}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username, password })
    });
    if (r.ok) {
      const data = await r.json();
      if (data.access_token) localStorage.setItem("token", data.access_token);
      await checkAuth();
    } else {
      toast("Login failed");
    }
  } catch { toast("Network error"); }
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    username: document.getElementById("reg-username").value,
    email: document.getElementById("reg-email").value,
    full_name: document.getElementById("reg-fullname").value,
    password: document.getElementById("reg-password").value,
  };
  try {
    const r = await fetch(`${API}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body)
    });
    if (r.ok) {
      toast("Account created! Please login.");
      document.querySelector('[data-tab="login"]').click();
    } else {
      toast("Registration failed");
    }
  } catch { toast("Network error"); }
});

// ========== NAVIGATION ==========
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const nav = btn.dataset.nav;
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.getElementById(`page-${nav}`).classList.add("active");
    document.getElementById("page-title").textContent =
      { home: "MSAFIRI", discovery: "Discovery", chats: "Chats", profile: "Profile" }[nav];
    navStack = [];
    if (nav === "chats") loadChats();
    if (nav === "profile") loadProfile();
  });
});

// Back button
document.getElementById("back-btn").addEventListener("click", () => {
  if (navStack.length > 0) {
    const prev = navStack.pop();
    prev();
  }
});

function showSubPage(title, renderFn) {
  navStack.push(() => {
    document.getElementById("page-sub").classList.remove("active");
    document.querySelector(".page.active").classList.add("active");
    document.getElementById("back-btn").classList.add("hidden");
    document.getElementById("page-title").textContent = "MSAFIRI";
  });
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.getElementById("page-sub").classList.add("active");
  document.getElementById("page-title").textContent = title;
  document.getElementById("back-btn").classList.remove("hidden");
  renderFn(document.getElementById("sub-content"));
}

// ========== HOME ==========
async function loadHome() {
  await loadStories();
  await loadFeed();
}

document.querySelectorAll(".feed-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".feed-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    currentFeed = tab.dataset.feed;
    loadFeed();
  });
});

async function loadStories() {
  try {
    const r = await fetch(`${API}/api/stories`);
    const data = await r.json();
    const bar = document.getElementById("stories-bar");
    bar.querySelectorAll(".story-item:not(.add-story)").forEach(el => el.remove());
    (data.stories || []).forEach(s => {
      const el = document.createElement("div");
      el.className = "story-item";
      el.innerHTML = `<div class="story-avatar">${(s.user_id || "U").toString().charAt(0)}</div><span>User</span>`;
      bar.appendChild(el);
    });
  } catch {}
}

async function loadFeed() {
  const feed = document.getElementById("feed");
  feed.innerHTML = `<p class="muted" style="text-align:center;padding:20px;">Loading...</p>`;
  try {
    const r = await fetch(`${API}/api/feed?type=${currentFeed}`);
    const data = await r.json();
    if (!data.posts || data.posts.length === 0) {
      feed.innerHTML = `<p class="muted" style="text-align:center;padding:40px 20px;">
        No posts yet. Be the first to share!</p>`;
      return;
    }
    feed.innerHTML = "";
    data.posts.forEach(p => feed.appendChild(renderPost(p)));
  } catch {
    feed.innerHTML = `<p class="muted" style="text-align:center;padding:20px;">Failed to load feed</p>`;
  }
}

function renderPost(p) {
  const el = document.createElement("div");
  el.className = "post-card";
  el.innerHTML = `
    <div class="post-header">
      <div class="post-avatar">${(p.user_id || "U").toString().charAt(0)}</div>
      <div class="post-user">
        <strong>User ${p.user_id || ""}</strong>
        <span>${timeAgo(p.created_at)}</span>
      </div>
    </div>
    ${p.caption ? `<p class="post-caption">${escape(p.caption)}</p>` : ""}
    ${p.media_url ? `<img class="post-media" src="${p.media_url}" alt="">` : ""}
    <div class="post-actions">
      <button onclick="toggleLike(this)">❤️ ${p.likes || 0}</button>
      <button>💬 ${p.comments || 0}</button>
      <button>↗️ Share</button>
      <button>🔖 Save</button>
    </div>
  `;
  return el;
}

window.toggleLike = function(btn) {
  btn.classList.toggle("liked");
};

// ========== DISCOVERY ==========
async function loadDiscovery() {
  try {
    const r = await fetch(`${API}/api/discovery`);
    const data = await r.json();
    const grid = document.getElementById("discovery-grid");
    grid.innerHTML = "";
    data.cards.forEach(card => {
      const el = document.createElement("div");
      el.className = "disc-card";
      el.innerHTML = `<span class="icon">${card.icon}</span>
        <div class="title">${card.title}</div>
        <div class="desc">${card.desc}</div>`;
      el.addEventListener("click", () => handleDiscoveryCard(card.id, card.title));
      grid.appendChild(el);
    });
  } catch {}
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
    "settings": showSettings,
  };
  (handlers[id] || (() => toast("Coming soon")))(title);
}

// ========== AI COUNCIL ==========
async function showAICouncil() {
  showSubPage("AI Council", async (c) => {
    c.innerHTML = `<h2>AI Council</h2><p class="muted" style="margin-bottom:16px;">Choose an AI assistant</p>`;
    const r = await fetch(`${API}/api/ai-council`);
    const data = await r.json();
    data.ais.forEach(ai => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">${ai.icon}</span>
        <div class="text"><strong>${ai.title}</strong><span>${ai.desc}</span></div>`;
      el.addEventListener("click", () => {
        if (ai.id === "education") showEducationAICountries();
        else showAIChat(ai.id);
      });
      c.appendChild(el);
    });
  });
}

async function showEducationAICountries() {
  showSubPage("Education AI", async (c) => {
    c.innerHTML = `<h2>Step 1 — Choose Country</h2><p class="muted" style="margin-bottom:16px;">Select your country</p>`;
    const r = await fetch(`${API}/api/ai-council/countries`);
    const data = await r.json();
    data.countries.forEach(country => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">🌍</span><div class="text"><strong>${country}</strong></div>`;
      el.addEventListener("click", () => showEducationAILevels(country));
      c.appendChild(el);
    });
  });
}

async function showEducationAILevels(country) {
  showSubPage(`Education — ${country}`, async (c) => {
    c.innerHTML = `<h2>Step 2 — Choose Level</h2><p class="muted" style="margin-bottom:16px;">${country}</p>`;
    const r = await fetch(`${API}/api/ai-council/levels`);
    const data = await r.json();
    data.levels.forEach(level => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">🎓</span><div class="text"><strong>${level}</strong></div>`;
      el.addEventListener("click", () => showEducationAIContent(country, level));
      c.appendChild(el);
    });
  });
}

async function showEducationAIContent(country, level) {
  showSubPage(`Education — ${level}`, async (c) => {
    c.innerHTML = `<h2>Step 3 — Choose Content</h2><p class="muted" style="margin-bottom:16px;">${country} • ${level}</p>`;
    const r = await fetch(`${API}/api/ai-council/content-types`);
    const data = await r.json();
    data.content_types.forEach(ct => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">📄</span><div class="text"><strong>${ct}</strong></div>`;
      el.addEventListener("click", () => showAIChat("education", { country, level, content: ct }));
      c.appendChild(el);
    });
  });
}

function showAIChat(ai, ctx = {}) {
  showSubPage("AI Chat", (c) => {
    c.innerHTML = `
      <h2>${ai.charAt(0).toUpperCase() + ai.slice(1)} AI</h2>
      <div id="chat-msgs" class="chat-msgs">
        <div class="msg ai">Hello! I'm your ${ctx.content || ""} assistant for ${ctx.level || ""} curriculum in ${ctx.country || ""}. Ask me anything.</div>
      </div>
      <div class="search-bar" style="display:flex;gap:8px;margin-top:12px;">
        <input type="text" id="ai-input" placeholder="Ask a question..." style="flex:1;">
        <button class="btn-primary" id="ai-send" style="padding:12px 20px;">Send</button>
      </div>
    `;
    const send = async () => {
      const input = document.getElementById("ai-input");
      const q = input.value.trim();
      if (!q) return;
      const msgs = document.getElementById("chat-msgs");
      msgs.innerHTML += `<div class="msg user">${escape(q)}</div>`;
      input.value = "";
      msgs.scrollTop = msgs.scrollHeight;
      try {
        const params = new URLSearchParams({ ai, ...ctx, q });
        const r = await fetch(`${API}/api/ai-council/chat?${params}`);
        const data = await r.json();
        msgs.innerHTML += `<div class="msg ai">${escape(data.reply)}</div>`;
        msgs.scrollTop = msgs.scrollHeight;
      } catch {
        msgs.innerHTML += `<div class="msg ai">Error reaching AI.</div>`;
      }
    };
    document.getElementById("ai-send").addEventListener("click", send);
    document.getElementById("ai-input").addEventListener("keypress", e => { if (e.key === "Enter") send(); });
  });
}

// ========== STUDIO / MARKET / MAP / CHANNELS / COMMUNITIES / VIDEOS ==========
async function showStudio() {
  showSubPage("Creative Studio", async (c) => {
    c.innerHTML = `<h2>Creative Studio</h2><p class="muted" style="margin-bottom:16px;">Canva-style tools</p>`;
    const r = await fetch(`${API}/api/studio`);
    const data = await r.json();
    data.tools.forEach(t => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">${t.icon}</span><div class="text"><strong>${t.title}</strong><span>${t.desc}</span></div>`;
      el.addEventListener("click", () => toast(`${t.title} coming soon`));
      c.appendChild(el);
    });
  });
}

async function showMarket() {
  showSubPage("Market", async (c) => {
    c.innerHTML = `<h2>Market</h2><p class="muted" style="margin-bottom:16px;">Buy and sell</p>`;
    const r = await fetch(`${API}/api/market/categories`);
    const data = await r.json();
    data.categories.forEach(cat => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">🛍️</span><div class="text"><strong>${cat.title}</strong><span>${cat.desc}</span></div>`;
      el.addEventListener("click", () => toast(`${cat.title} — coming soon`));
      c.appendChild(el);
    });
  });
}

async function showWorldMap() {
  showSubPage("World Map", async (c) => {
    c.innerHTML = `<h2>World Map</h2><p class="muted" style="margin-bottom:16px;">Explore the world</p>`;
    const r = await fetch(`${API}/api/world-map/countries`);
    const data = await r.json();
    data.countries.forEach(co => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">🌍</span><div class="text"><strong>${co.name}</strong><span>${co.users} users • ${co.posts} posts</span></div>`;
      el.addEventListener("click", () => toast(`${co.name} — coming soon`));
      c.appendChild(el);
    });
  });
}

async function showChannels() {
  showSubPage("Channels", async (c) => {
    c.innerHTML = `<h2>Channels</h2><p class="muted" style="margin-bottom:16px;">News and media</p>`;
    const r = await fetch(`${API}/api/channels`);
    const data = await r.json();
    data.channels.forEach(ch => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">📺</span><div class="text"><strong>${ch.name}</strong><span>${ch.desc}</span></div>`;
      el.addEventListener("click", () => toast(`${ch.name} — coming soon`));
      c.appendChild(el);
    });
  });
}

async function showCommunities() {
  showSubPage("Communities", async (c) => {
    c.innerHTML = `<h2>Communities</h2><p class="muted" style="margin-bottom:16px;">Join groups</p>`;
    const r = await fetch(`${API}/api/communities/categories`);
    const data = await r.json();
    data.categories.forEach(cat => {
      const el = document.createElement("div");
      el.className = "sub-item";
      el.innerHTML = `<span class="icon">👥</span><div class="text"><strong>${cat.title}</strong><span>${cat.desc}</span></div>`;
      el.addEventListener("click", () => toast(`${cat.title} — coming soon`));
      c.appendChild(el);
    });
  });
}

async function showVideos() {
  showSubPage("Videos", async (c) => {
    c.innerHTML = `<h2>Videos</h2><p class="muted" style="margin-bottom:16px;">Short video feed</p>
      <div class="sub-item"><span class="icon">▶️</span><div class="text"><strong>Coming soon</strong><span>TikTok-style feed</span></div></div>`;
  });
}

// ========== SETTINGS ==========
function showSettings() {
  showSubPage("Settings", (c) => {
    c.innerHTML = `
      <h2>Settings</h2>
      <div class="sub-item" id="s-manual"><span class="icon">📖</span><div class="text"><strong>User Manual</strong><span>How to use the app</span></div></div>
      <div class="sub-item" id="s-theme"><span class="icon">🌓</span><div class="text"><strong>Theme</strong><span>Light / Dark</span></div></div>
      <div class="sub-item"><span class="icon">ℹ️</span><div class="text"><strong>Version</strong><span>MSAFIRI MEDIA V0.0.1</span></div></div>
      <div class="sub-item" id="s-logout"><span class="icon">🚪</span><div class="text"><strong>Logout</strong><span>Sign out of your account</span></div></div>
    `;
    document.getElementById("s-manual").addEventListener("click", showUserManual);
    document.getElementById("s-theme").addEventListener("click", toggleTheme);
    document.getElementById("s-logout").addEventListener("click", logout);
  });
}

// ========== USER MANUAL ==========
async function showUserManual() {
  showSubPage("User Manual", async (c) => {
    const r = await fetch(`${API}/api/user-manual`);
    const m = await r.json();
    c.innerHTML = `
      <div style="text-align:center;margin-bottom:20px;">
        <div class="auth-logo" style="margin:0 auto 12px;">M</div>
        <h2>${m.app}</h2>
        <p class="muted">${m.tagline}</p>
        <p class="muted" style="margin-top:4px;">Founder: ${m.founder}</p>
        <p class="muted">${m.company}</p>
        <p class="muted">Version: ${m.version}</p>
      </div>
      <div class="manual-section"><h3>About</h3><p>${m.about}</p></div>
      <div class="manual-section"><h3>Sections</h3><ul>
        ${Object.entries(m.sections).map(([k,v]) => `<li><strong>${k}:</strong> ${v}</li>`).join("")}
      </ul></div>
      <div class="manual-section"><h3>How to Use</h3><ul>
        ${Object.entries(m.how_to_use).map(([k,v]) => `<li><strong>${k.replace("_"," ")}:</strong> ${v}</li>`).join("")}
      </ul></div>
      <div class="manual-section"><h3>Support</h3><p>${m.support}</p></div>
      <button class="btn-primary" id="dl-manual" style="width:100%;margin-top:16px;">📥 Download User Manual</button>
    `;
    document.getElementById("dl-manual").addEventListener("click", () => {
      const text = `MSAFIRI GLOBAL MEDIA\n${m.tagline}\n\nFounder: ${m.founder}\nCompany: ${m.company}\nVersion: ${m.version}\n\nABOUT\n${m.about}\n\nSECTIONS\n${Object.entries(m.sections).map(([k,v])=>`- ${k}: ${v}`).join("\n")}\n\nHOW TO USE\n${Object.entries(m.how_to_use).map(([k,v])=>`- ${k}: ${v}`).join("\n")}\n\nSUPPORT\n${m.support}\n`;
      const blob = new Blob([text], { type: "text/plain" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "MSAFIRI-UserManual.txt";
      a.click();
      toast("Downloaded!");
    });
  });
}

// ========== DOTS MENU ==========
document.getElementById("dots-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  document.getElementById("dots-menu").classList.toggle("hidden");
});
document.addEventListener("click", () => {
  document.getElementById("dots-menu").classList.add("hidden");
});
document.querySelectorAll("#dots-menu button").forEach(btn => {
  btn.addEventListener("click", () => {
    const a = btn.dataset.action;
    if (a === "manual") showUserManual();
    if (a === "settings") showSettings();
    if (a === "logout") logout();
    document.getElementById("dots-menu").classList.add("hidden");
  });
});

// ========== CHATS ==========
async function loadChats() {
  const list = document.getElementById("chat-list");
  try {
    const r = await fetch(`${API}/api/messages`);
    if (!r.ok) { list.innerHTML = `<p class="muted" style="padding:20px;text-align:center;">No chats yet</p>`; return; }
    const data = await r.json();
    if (!data.messages || data.messages.length === 0) {
      list.innerHTML = `<p class="muted" style="padding:20px;text-align:center;">No chats yet</p>`;
      return;
    }
    list.innerHTML = "";
  } catch {
    list.innerHTML = `<p class="muted" style="padding:20px;text-align:center;">No chats yet</p>`;
  }
}

// ========== PROFILE ==========
async function loadProfile() {
  try {
    const r = await fetch(`${API}/api/auth/me`);
    if (!r.ok) return;
    const u = await r.json();
    document.getElementById("profile-name").textContent = u.full_name || u.username || "User";
    document.getElementById("profile-username").textContent = "@" + (u.username || "user");
    document.getElementById("profile-bio").textContent = u.bio || "Welcome to Msafiri";
    document.getElementById("profile-avatar").textContent = (u.full_name || u.username || "U").charAt(0).toUpperCase();
  } catch {}
}

// ========== UTILS ==========
function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}

function escape(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

function timeAgo(iso) {
  if (!iso) return "now";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return s + "s";
  if (s < 3600) return Math.floor(s / 60) + "m";
  if (s < 86400) return Math.floor(s / 3600) + "h";
  return Math.floor(s / 86400) + "d";
}

function toggleTheme() {
  document.body.style.filter = document.body.style.filter ? "" : "invert(1) hue-rotate(180deg)";
  toast("Theme toggled");
}

function logout() {
  fetch(`${API}/api/auth/logout`, { method: "POST" });
  localStorage.removeItem("token");
  currentUser = null;
  location.reload();
}
