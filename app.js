/* ============================================================
   MSAFIRI GLOBAL MEDIA - APP.JS
   Part 1/3 — Core, Auth, Feed, Posts
   ============================================================ */

'use strict';

const API = window.location.origin;
let TOKEN = null;
let CURRENT_USER = null;
let CURRENT_VIEW = 'home';
let CACHED_POSTS = [];
let CACHED_CHATS = [];
let CACHED_VIDEOS = [];

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ============ DOM HELPER ============
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'dataset') Object.assign(node.dataset, v);
    else if (k.startsWith('on') && typeof v === 'function') {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (v !== null && v !== undefined && v !== false) {
      node.setAttribute(k, v);
    }
  }
  for (const c of children) {
    if (c == null || c === false) continue;
    if (typeof c === 'string') node.appendChild(document.createTextNode(c));
    else if (c instanceof Node) node.appendChild(c);
  }
  return node;
}

function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function initials(name) {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const s = Math.floor((now - d) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return Math.floor(s / 60) + 'm';
  if (s < 86400) return Math.floor(s / 3600) + 'h';
  if (s < 604800) return Math.floor(s / 86400) + 'd';
  if (s < 2592000) return Math.floor(s / 604800) + 'w';
  return d.toLocaleDateString();
}

// ============ API CLIENT ============
async function api(path, opts = {}) {
  const headers = opts.headers || {};
  if (!(opts.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  if (TOKEN) headers['Authorization'] = `Bearer ${TOKEN}`;

  let res;
  try {
    res = await fetch(API + path, { ...opts, headers });
  } catch (networkErr) {
    console.warn('[MSAFIRI] Network error, retrying in 2s...');
    await new Promise(r => setTimeout(r, 2000));
    res = await fetch(API + path, { ...opts, headers });
  }

  let data = null;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    try { data = await res.json(); } catch (_) { data = null; }
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    if (res.status === 401 && TOKEN && !path.includes('/login') && !path.includes('/register')) {
      console.warn('[MSAFIRI] Session expired');
      TOKEN = null;
      CURRENT_USER = null;
      localStorage.removeItem('msafiri_token');
      showAuth();
    }
    const msg = (data && data.detail) || (data && data.message) || (typeof data === 'string' ? data : `HTTP ${res.status}`);
    const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    err.status = res.status;
    throw err;
  }
  return data;
}

// ============ TOAST ============
function toast(message, type = 'info', duration = 3000) {
  const container = $('#toastContainer');
  if (!container) return;
  const t = el('div', { class: `toast ${type}` });
  const icons = {
    success: '<polyline points="20 6 9 17 4 12"/>',
    error: '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
    info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  };
  t.innerHTML = `<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icons[type] || icons.info}</svg><span>${esc(message)}</span>`;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transition = 'opacity .3s';
    setTimeout(() => t.remove(), 300);
  }, duration);
}

// ============ THEME ============
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('msafiri_theme', theme);
}
function initTheme() {
  const saved = localStorage.getItem('msafiri_theme') || 'dark';
  applyTheme(saved);
}
function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = cur === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  if (CURRENT_USER) {
    api('/api/profile', { method: 'PATCH', body: JSON.stringify({ theme: next }) }).catch(() => {});
  }
}

// ============ SESSION ============
function saveSession(token) {
  TOKEN = token;
  localStorage.setItem('msafiri_token', token);
  localStorage.setItem('msafiri_token_time', Date.now().toString());
  try { sessionStorage.setItem('msafiri_token', token); } catch(e) {}
}
function getSavedToken() {
  let t = localStorage.getItem('msafiri_token');
  if (!t) {
    try { t = sessionStorage.getItem('msafiri_token'); } catch(e) {}
  }
  return t;
}

// ============ AUTH ============
async function register(name, email, password, username) {
  return api('/api/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password, username: username || null }),
  });
}
async function login(email, password) {
  return api('/api/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}
async function logout() {
  try { await api('/api/logout', { method: 'POST' }); } catch (_) {}
  TOKEN = null;
  CURRENT_USER = null;
  localStorage.removeItem('msafiri_token');
  localStorage.removeItem('msafiri_token_time');
  try { sessionStorage.removeItem('msafiri_token'); } catch(e) {}
  showAuth();
}
async function loadMe() {
  const data = await api('/api/me');
  CURRENT_USER = data.user;
  return CURRENT_USER;
}

// ============ SCREENS ============
function showAuth() {
  const sp = $('#splashScreen');
  if (sp) sp.classList.add('fade-out');
  $('#authScreen').classList.remove('hidden');
  $('#appScreen').classList.add('hidden');
}
function showApp() {
  const sp = $('#splashScreen');
  if (sp) sp.classList.add('fade-out');
  $('#authScreen').classList.add('hidden');
  $('#appScreen').classList.remove('hidden');
}

// ============ AVATAR ============
function avatarEl(user, size = 40) {
  const wrap = el('div', {
    style: `width:${size}px;height:${size}px;border-radius:50%;overflow:hidden;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:${Math.round(size*0.4)}px;flex-shrink:0;`
  });
  if (user && user.avatar) {
    wrap.appendChild(el('img', { src: user.avatar, style: 'width:100%;height:100%;object-fit:cover;' }));
  } else {
    wrap.textContent = initials(user && user.name);
  }
  return wrap;
}

// ============ AUTH UI BINDINGS ============
function bindAuthUI() {
  $$('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const t = tab.dataset.tab;
      $$('.auth-tab').forEach(x => x.classList.toggle('active', x === tab));
      $('#loginForm').classList.toggle('hidden', t !== 'login');
      $('#registerForm').classList.toggle('hidden', t !== 'register');
      $('#loginError').classList.add('hidden');
      $('#registerError').classList.add('hidden');
    });
  });

  $$('.password-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const inp = $('#' + btn.dataset.target);
      if (!inp) return;
      inp.type = inp.type === 'password' ? 'text' : 'password';
    });
  });

  $('#loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = $('#loginBtn');
    const errEl = $('#loginError');
    errEl.classList.add('hidden');
    btn.disabled = true;
    btn.innerHTML = '<div class="loader"></div>';
    try {
      const email = $('#loginEmail').value.trim();
      const password = $('#loginPassword').value;
      const res = await login(email, password);
      saveSession(res.token);
      CURRENT_USER = res.user;
      toast('Welcome back!', 'success');
      await startApp();
    } catch (err) {
      errEl.textContent = err.message || 'Login failed';
      errEl.classList.remove('hidden');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>Login</span>';
    }
  });

  $('#registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = $('#registerBtn');
    const errEl = $('#registerError');
    errEl.classList.add('hidden');
    btn.disabled = true;
    btn.innerHTML = '<div class="loader"></div>';
    try {
      const name = $('#regName').value.trim();
      const username = $('#regUsername').value.trim() || null;
      const email = $('#regEmail').value.trim();
      const password = $('#regPassword').value;
      const res = await register(name, email, password, username);
      saveSession(res.token);
      CURRENT_USER = res.user;
      toast('Account created!', 'success');
      await startApp();
    } catch (err) {
      errEl.textContent = err.message || 'Registration failed';
      errEl.classList.remove('hidden');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>Create Account</span>';
    }
  });

  const logoutBtn = $('#logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      if (confirm('Logout from MSAFIRI?')) logout();
    });
  }
  const themeBtn = $('#themeToggle');
  if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
}

// ============ POST RENDERER ============
function renderPost(post) {
  const card = el('article', { class: 'post-card', dataset: { postId: post.id } });
  const header = el('div', { class: 'post-header' });
  const userInfo = el('div', {
    style: 'display:flex;align-items:center;gap:10px;cursor:pointer;',
    onclick: () => openProfile(post.user.id),
  });
  userInfo.appendChild(avatarEl(post.user, 40));
  const names = el('div');
  names.appendChild(el('div', { style: 'font-weight:600;font-size:14px;' }, post.user.name));
  const uname = post.user.username ? '@' + post.user.username + ' · ' : '';
  names.appendChild(el('div', { style: 'font-size:12px;color:var(--text-3);' }, uname + timeAgo(post.created_at)));
  userInfo.appendChild(names);
  header.appendChild(userInfo);

  if (CURRENT_USER && post.user.id === CURRENT_USER.id) {
    const menuBtn = el('button', { class: 'btn-icon', style: 'width:32px;height:32px;' });
    menuBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>';
    menuBtn.addEventListener('click', (e) => { e.stopPropagation(); openPostMenu(post); });
    header.appendChild(menuBtn);
  }
  card.appendChild(header);

  if (post.caption) {
    card.appendChild(el('div', {
      style: 'padding:0 16px 12px;font-size:14px;line-height:1.5;white-space:pre-wrap;word-break:break-word;',
    }, post.caption));
  }

  if (post.media) {
    const mediaWrap = el('div', { style: 'background:#000;display:flex;justify-content:center;' });
    if (post.media_type === 'video') {
      mediaWrap.appendChild(el('video', {
        src: post.media, controls: true, playsinline: true,
        style: 'max-width:100%;max-height:70vh;display:block;',
      }));
    } else {
      mediaWrap.appendChild(el('img', {
        src: post.media,
        style: 'max-width:100%;max-height:70vh;display:block;object-fit:contain;',
        loading: 'lazy',
      }));
    }
    card.appendChild(mediaWrap);
  }

  const actions = el('div', { style: 'display:flex;align-items:center;gap:2px;padding:8px 8px 12px;' });
  actions.appendChild(makeActionBtn(post.liked, 'like', post.likes_count || 0, post.liked ? 'var(--danger)' : null, () => toggleLike(post)));
  actions.appendChild(makeActionBtn(false, 'comment', post.comments_count || 0, null, () => openComments(post)));
  actions.appendChild(makeActionBtn(false, 'reshare', post.reshares_count || 0, null, () => toggleReshare(post)));
  actions.appendChild(makeActionBtn(post.saved, 'save', null, post.saved ? 'var(--accent)' : null, () => toggleSave(post)));
  card.appendChild(actions);
  return card;
}

function makeActionBtn(filled, kind, count, color, onClick) {
  const btn = el('button', {
    class: 'btn-icon',
    style: `flex:1;height:36px;gap:6px;padding:0 8px;border-radius:8px;color:${color || 'var(--text-2)'};display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;`,
  });
  const icons = {
    like: '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
    comment: '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
    reshare: '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
    save: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
  };
  const fillStyle = filled ? 'fill:currentColor;' : '';
  btn.innerHTML = `<svg class="icon icon-sm" viewBox="0 0 24 24" style="${fillStyle}">${icons[kind]}</svg>${count != null ? `<span>${count > 0 ? count : ''}</span>` : ''}`;
  btn.addEventListener('click', (e) => { e.stopPropagation(); onClick(); });
  return btn;
}

// ============ ACTIONS (LIKE/SAVE/RESHARE) ============
async function toggleLike(post) {
  try {
    if (post.liked) {
      await api(`/api/posts/${post.id}/like`, { method: 'DELETE' });
      post.liked = false;
      post.likes_count = Math.max(0, (post.likes_count || 0) - 1);
    } else {
      await api(`/api/posts/${post.id}/like`, { method: 'POST' });
      post.liked = true;
      post.likes_count = (post.likes_count || 0) + 1;
    }
    updatePostCard(post);
  } catch (err) { toast(err.message, 'error'); }
}
async function toggleSave(post) {
  try {
    if (post.saved) {
      await api(`/api/posts/${post.id}/save`, { method: 'DELETE' });
      post.saved = false;
      toast('Removed', 'info');
    } else {
      await api(`/api/posts/${post.id}/save`, { method: 'POST' });
      post.saved = true;
      toast('Saved', 'success');
    }
    updatePostCard(post);
  } catch (err) { toast(err.message, 'error'); }
}
async function toggleReshare(post) {
  try {
    await api(`/api/posts/${post.id}/reshare`, { method: 'POST' });
    post.reshares_count = (post.reshares_count || 0) + 1;
    toast('Reshared', 'success');
    updatePostCard(post);
  } catch (err) { toast(err.message, 'error'); }
}
function updatePostCard(post) {
  const old = document.querySelector(`[data-post-id="${post.id}"]`);
  if (!old) return;
  old.replaceWith(renderPost(post));
}

// ============ POST MENU ============
function openPostMenu(post) {
  const items = [];
  if (CURRENT_USER && post.user.id === CURRENT_USER.id) {
    items.push({
      label: 'Delete Post', danger: true, onClick: async () => {
        if (!confirm('Delete this post?')) return;
        try {
          await api(`/api/posts/${post.id}`, { method: 'DELETE' });
          toast('Deleted', 'success');
          CACHED_POSTS = CACHED_POSTS.filter(p => p.id !== post.id);
          renderFeed();
        } catch (err) { toast(err.message, 'error'); }
      }
    });
  }
  items.push({
    label: 'Copy Link', onClick: () => {
      const url = `${API}/?post=${post.id}`;
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(() => toast('Copied', 'success'));
      else toast(url, 'info');
    }
  });
  openSheet('Post Options', items);
}

// ============ SHEET ============
function openSheet(title, items, contentNode = null) {
  const container = $('#modalContainer');
  container.innerHTML = '';
  const overlay = el('div', {
    class: 'modal-overlay',
    onclick: (e) => { if (e.target === overlay) closeModal(); }
  });
  const content = el('div', { class: 'modal-content' });
  content.appendChild(el('div', { class: 'modal-handle' }));

  if (title) {
    const h = el('div', { class: 'modal-header' });
    h.appendChild(el('h3', {}, title));
    const cb = el('button', { class: 'btn-icon', onclick: closeModal });
    cb.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    h.appendChild(cb);
    content.appendChild(h);
  }

  const body = el('div', { class: 'modal-body', style: 'padding:8px 0;' });
  if (contentNode) body.appendChild(contentNode);
  if (items) {
    for (const item of items) {
      const btn = el('button', {
        style: `display:block;width:100%;text-align:left;padding:14px 20px;font-size:15px;background:none;color:${item.danger ? 'var(--danger)' : 'var(--text)'};`,
        onclick: () => { closeModal(); item.onClick && item.onClick(); }
      }, item.label);
      body.appendChild(btn);
    }
  }
  content.appendChild(body);
  overlay.appendChild(content);
  container.appendChild(overlay);
}

function closeModal() {
  $('#modalContainer').innerHTML = '';
}

// ============ FEED ============
async function loadFeed(feedType = 'all') {
  const main = $('#appMain');
  main.innerHTML = '<div class="center-loader"><div class="loader loader-lg"></div></div>';
  try {
    const data = await api('/api/posts?feed=' + encodeURIComponent(feedType) + '&limit=30');
    CACHED_POSTS = data.posts || [];
    renderFeed(feedType);
  } catch (err) {
    main.innerHTML = `<div class="empty-state"><p class="empty-state-title">Failed to load feed</p><p class="empty-state-text">${esc(err.message)}</p></div>`;
  }
}

function renderFeed(feedType = 'all') {
  const main = $('#appMain');
  main.innerHTML = '';

  // Search bar
  const searchWrap = el('div', { class: 'home-search' });
  const searchIconWrap = el('div', { style: 'position:relative;' });
  searchIconWrap.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24" style="position:absolute;left:14px;top:12px;color:var(--text-3);pointer-events:none;"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>';
  const searchInput = el('input', {
    type: 'text', class: 'home-search-input', placeholder: 'Search people...',
    onkeydown: (e) => {
      if (e.key === 'Enter') {
        const q = e.target.value.trim();
        if (q) {
          switchView('search');
          openSearchWithQuery(q);
        }
      }
    }
  });
  searchIconWrap.appendChild(searchInput);
  searchWrap.appendChild(searchIconWrap);
  main.appendChild(searchWrap);

  // Feed tabs
  const tabs = el('div', { class: 'feed-tabs' });
  ['all', 'following'].forEach(f => {
    const active = f === feedType;
    const t = el('button', {
      class: 'feed-tab' + (active ? ' active' : ''),
      onclick: () => loadFeed(f),
    }, f === 'all' ? 'For You' : 'Following');
    tabs.appendChild(t);
  });
  main.appendChild(tabs);

  // Stories bar
  const storiesBar = el('div', { class: 'stories-bar', id: 'storiesBar' });
  main.appendChild(storiesBar);

  const addStoryBtn = el('div', {
    class: 'add-story-btn',
    onclick: () => openCreateStory(),
  });
  addStoryBtn.appendChild(el('div', { class: 'add-story-circle' }, '+'));
  addStoryBtn.appendChild(el('div', { style: 'font-size:11px;color:var(--text-2);font-weight:600;' }, 'My Story'));
  storiesBar.appendChild(addStoryBtn);

  if (typeof loadStories === 'function') {
    loadStories(storiesBar);
  }

  // Posts
  if (CACHED_POSTS.length === 0) {
    main.appendChild(el('div', { class: 'empty-state' },
      el('p', { class: 'empty-state-title' }, 'No posts yet'),
      el('p', { class: 'empty-state-text' }, 'Be the first to share something!')));
    return;
  }
  for (const p of CACHED_POSTS) main.appendChild(renderPost(p));
}

// ============ START APP ============
async function startApp() {
  showApp();
  await loadFeed('all');
}


/* ============================================================
   APP.JS — PART 2/3
   Post Creator, Comments, Profile, Chat, Story
   ============================================================ */

// ============ POST CREATOR ============
function openCreatePost() {
  const container = $('#modalContainer');
  container.innerHTML = '';
  const overlay = el('div', { class: 'modal-overlay', onclick: (e) => { if (e.target === overlay) closeModal(); } });
  const content = el('div', { class: 'modal-content' });
  const h = el('div', { class: 'modal-header' });
  h.appendChild(el('h3', {}, 'Create Post'));
  const closeBtn = el('button', { class: 'btn-icon', onclick: closeModal });
  closeBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  h.appendChild(closeBtn);
  content.appendChild(h);
  const body = el('div', { class: 'modal-body' });
  const textarea = el('textarea', {
    placeholder: "What's on your mind?", rows: 5,
    style: 'width:100%;background:var(--bg-3);border:1px solid var(--border);border-radius:var(--radius);padding:12px;font-size:15px;color:var(--text);resize:none;font-family:inherit;',
    maxlength: 2000,
  });
  body.appendChild(textarea);

  const preview = el('div', { style: 'margin-top:12px;display:none;position:relative;border-radius:var(--radius);overflow:hidden;background:#000;' });
  body.appendChild(preview);

  let selectedFile = null;
  let previewURL = null;

  const fileInput = el('input', { type: 'file', style: 'display:none' });
  fileInput.addEventListener('change', () => {
    const f = fileInput.files && fileInput.files[0];
    if (!f) return;
    const maxMB = f.type.startsWith('video/') ? 50 : 5;
    if (f.size > maxMB * 1024 * 1024) {
      toast(`File too large. Max ${maxMB} MB.`, 'error');
      fileInput.value = '';
      return;
    }
    selectedFile = f;
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = URL.createObjectURL(f);
    preview.innerHTML = '';
    preview.style.display = 'block';
    if (f.type.startsWith('video/')) {
      preview.appendChild(el('video', { src: previewURL, controls: true, playsinline: true, style: 'width:100%;max-height:300px;display:block;' }));
    } else if (f.type.startsWith('image/')) {
      preview.appendChild(el('img', { src: previewURL, style: 'width:100%;max-height:300px;display:block;object-fit:contain;' }));
    }
    const rm = el('button', {
      style: 'position:absolute;top:8px;right:8px;width:32px;height:32px;border-radius:50%;background:rgba(0,0,0,0.7);color:white;display:flex;align-items:center;justify-content:center;',
      onclick: () => {
        selectedFile = null;
        if (previewURL) URL.revokeObjectURL(previewURL);
        previewURL = null;
        fileInput.value = '';
        preview.style.display = 'none';
      }
    });
    rm.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    preview.appendChild(rm);
  });
  body.appendChild(fileInput);

  const mediaActions = el('div', { style: 'display:flex;gap:6px;margin-top:12px;' });
  const photoBtn = el('button', { class: 'btn btn-secondary', style: 'flex:1;padding:10px 6px;font-size:12px;', onclick: () => { fileInput.accept = 'image/*'; fileInput.click(); } });
  photoBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg><span>Photo</span>';
  mediaActions.appendChild(photoBtn);
  const videoBtn = el('button', { class: 'btn btn-secondary', style: 'flex:1;padding:10px 6px;font-size:12px;', onclick: () => { fileInput.accept = 'video/*'; fileInput.click(); } });
  videoBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg><span>Video</span>';
  mediaActions.appendChild(videoBtn);
  const fileBtn = el('button', { class: 'btn btn-secondary', style: 'flex:1;padding:10px 6px;font-size:12px;', onclick: () => { fileInput.accept = '*/*'; fileInput.click(); } });
  fileBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg><span>File</span>';
  mediaActions.appendChild(fileBtn);
  body.appendChild(mediaActions);

  const postBtn = el('button', {
    class: 'btn btn-primary',
    style: 'margin-top:10px;',
    onclick: async () => {
      const caption = textarea.value.trim();
      if (!caption && !selectedFile) { toast('Add text or media', 'error'); return; }
      postBtn.disabled = true;
      postBtn.innerHTML = '<div class="loader"></div>';
      try {
        const fd = new FormData();
        fd.append('caption', caption);
        if (selectedFile) fd.append('file', selectedFile);
        await api('/api/posts', { method: 'POST', body: fd });
        toast('Posted!', 'success');
        closeModal();
        loadFeed('all');
      } catch (err) {
        toast(err.message, 'error');
        postBtn.disabled = false;
        postBtn.innerHTML = '<span>Post</span>';
      }
    },
  }, el('span', {}, 'Post'));
  body.appendChild(postBtn);
  content.appendChild(body);
  overlay.appendChild(content);
  container.appendChild(overlay);
}

// ============ COMMENTS ============
async function openComments(post) {
  const container = $('#modalContainer');
  container.innerHTML = '';
  const overlay = el('div', { class: 'modal-overlay', onclick: (e) => { if (e.target === overlay) closeModal(); } });
  const content = el('div', { class: 'modal-content', style: 'height:85vh;display:flex;flex-direction:column;' });
  const h = el('div', { class: 'modal-header' });
  h.appendChild(el('h3', {}, `Comments (${post.comments_count || 0})`));
  const closeBtn = el('button', { class: 'btn-icon', onclick: closeModal });
  closeBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  h.appendChild(closeBtn);
  content.appendChild(h);
  const list = el('div', { style: 'flex:1;overflow-y:auto;padding:12px 16px;' });
  list.innerHTML = '<div class="center-loader"><div class="loader" style="margin:0 auto;"></div></div>';
  content.appendChild(list);
  const form = el('form', {
    style: 'display:flex;gap:8px;padding:12px;border-top:1px solid var(--border);background:var(--bg-2);',
    onsubmit: async (e) => {
      e.preventDefault();
      const inp = form.querySelector('input');
      const text = inp.value.trim();
      if (!text) return;
      const submitBtn = form.querySelector('button');
      submitBtn.disabled = true;
      try {
        const res = await api(`/api/posts/${post.id}/comments`, { method: 'POST', body: JSON.stringify({ text }) });
        inp.value = '';
        post.comments_count = (post.comments_count || 0) + 1;
        renderSingleComment(res.comment, list);
        updatePostCard(post);
      } catch (err) { toast(err.message, 'error'); }
      submitBtn.disabled = false;
    },
  });
  const inp = el('input', {
    type: 'text', placeholder: 'Add a comment...', maxlength: 2000,
    style: 'flex:1;padding:10px 14px;background:var(--bg-3);border:1px solid var(--border);border-radius:20px;font-size:14px;color:var(--text);',
  });
  form.appendChild(inp);
  const sendBtn = el('button', { type: 'submit', class: 'btn-icon', style: 'background:var(--accent);color:white;width:40px;height:40px;border-radius:50%;' });
  sendBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
  form.appendChild(sendBtn);
  content.appendChild(form);
  overlay.appendChild(content);
  container.appendChild(overlay);

  try {
    const data = await api(`/api/posts/${post.id}/comments`);
    list.innerHTML = '';
    if (!data.comments || data.comments.length === 0) {
      list.innerHTML = '<div class="empty-state"><p class="empty-state-text">No comments yet. Be the first!</p></div>';
    } else {
      for (const c of data.comments) renderSingleComment(c, list);
    }
  } catch (err) {
    list.innerHTML = `<div class="empty-state"><p class="empty-state-text" style="color:var(--danger);">${esc(err.message)}</p></div>`;
  }
}

function renderSingleComment(c, list) {
  const row = el('div', { style: 'display:flex;gap:10px;margin-bottom:16px;' });
  row.appendChild(avatarEl(c.user, 36));
  const right = el('div', { style: 'flex:1;min-width:0;' });
  right.appendChild(el('div', { style: 'font-size:13px;font-weight:600;' }, c.user.name));
  right.appendChild(el('div', { style: 'font-size:14px;line-height:1.4;word-break:break-word;margin-top:2px;' }, c.text));
  right.appendChild(el('div', { style: 'font-size:11px;color:var(--text-3);margin-top:4px;' }, timeAgo(c.created_at)));
  row.appendChild(right);
  list.appendChild(row);
  list.scrollTop = list.scrollHeight;
}

// ============ PROFILE ============
async function openProfile(userId) {
  const main = $('#appMain');
  main.innerHTML = '<div class="center-loader"><div class="loader loader-lg"></div></div>';
  switchView('profile');
  try {
    const data = await api(`/api/users/${userId}`);
    const u = data.user;
    main.innerHTML = '';

    const cover = el('div', { style: 'height:120px;background:linear-gradient(135deg,var(--accent),var(--accent-2));' });
    main.appendChild(cover);

    const info = el('div', { style: 'padding:0 16px 16px;margin-top:-50px;position:relative;' });
    const av = avatarEl(u, 100);
    av.style.border = '4px solid var(--bg)';
    info.appendChild(av);

    info.appendChild(el('div', { style: 'font-size:20px;font-weight:700;margin-top:8px;' }, u.name));
    if (u.username) info.appendChild(el('div', { style: 'font-size:14px;color:var(--text-2);' }, '@' + u.username));
    if (u.bio) info.appendChild(el('div', { style: 'font-size:14px;line-height:1.5;margin-top:12px;' }, u.bio));
    if (u.location) info.appendChild(el('div', { style: 'font-size:13px;color:var(--text-2);margin-top:8px;' }, '📍 ' + u.location));

    const stats = el('div', { style: 'display:flex;gap:24px;margin-top:16px;' });
    [
      { label: 'Posts', value: u.posts_count || 0 },
      { label: 'Followers', value: u.followers_count || 0 },
      { label: 'Following', value: u.following_count || 0 },
    ].forEach(s => {
      const box = el('div');
      box.appendChild(el('div', { style: 'font-weight:700;font-size:16px;' }, String(s.value)));
      box.appendChild(el('div', { style: 'font-size:12px;color:var(--text-3);' }, s.label));
      stats.appendChild(box);
    });
    info.appendChild(stats);

    const actions = el('div', { style: 'display:flex;gap:8px;margin-top:16px;' });
    if (CURRENT_USER && u.id === CURRENT_USER.id) {
      const editBtn = el('button', { class: 'btn btn-secondary', style: 'flex:1;', onclick: () => openEditProfile() }, 'Edit Profile');
      actions.appendChild(editBtn);
    } else {
      const followBtn = el('button', {
        class: 'btn ' + (u.is_following ? 'btn-secondary' : 'btn-primary'),
        style: 'flex:1;',
        onclick: async () => {
          try {
            if (u.is_following) {
              await api(`/api/users/${u.id}/follow`, { method: 'DELETE' });
              u.is_following = false;
              u.followers_count = Math.max(0, (u.followers_count || 1) - 1);
            } else {
              await api(`/api/users/${u.id}/follow`, { method: 'POST' });
              u.is_following = true;
              u.followers_count = (u.followers_count || 0) + 1;
            }
            openProfile(u.id);
          } catch (err) { toast(err.message, 'error'); }
        }
      }, el('span', {}, u.is_following ? 'Following' : 'Follow'));
      actions.appendChild(followBtn);

      const msgBtn = el('button', { class: 'btn btn-secondary', style: 'flex:0 0 auto;width:auto;padding:14px;' });
      msgBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
      msgBtn.addEventListener('click', () => openChatWith(u));
      actions.appendChild(msgBtn);
    }
    info.appendChild(actions);
    main.appendChild(info);

    main.appendChild(el('div', { style: 'padding:12px 16px;border-top:1px solid var(--border);font-weight:600;font-size:14px;' }, 'Posts'));
    const postsWrap = el('div');
    main.appendChild(postsWrap);

    try {
      const pdata = await api(`/api/users/${u.id}/posts`);
      if (!pdata.posts || pdata.posts.length === 0) {
        postsWrap.innerHTML = '<div class="empty-state"><p class="empty-state-text">No posts yet</p></div>';
      } else {
        for (const p of pdata.posts) postsWrap.appendChild(renderPost(p));
      }
    } catch (err) {
      postsWrap.innerHTML = `<div class="empty-state"><p class="empty-state-text" style="color:var(--danger);">${esc(err.message)}</p></div>`;
    }
  } catch (err) {
    main.innerHTML = `<div class="empty-state"><p class="empty-state-text" style="color:var(--danger);">${esc(err.message)}</p></div>`;
  }
}

// ============ EDIT PROFILE ============
function openEditProfile() {
  const container = $('#modalContainer');
  container.innerHTML = '';
  const overlay = el('div', { class: 'modal-overlay', onclick: (e) => { if (e.target === overlay) closeModal(); } });
  const content = el('div', { class: 'modal-content' });
  const h = el('div', { class: 'modal-header' });
  h.appendChild(el('h3', {}, 'Edit Profile'));
  const cb = el('button', { class: 'btn-icon', onclick: closeModal });
  cb.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  h.appendChild(cb);
  content.appendChild(h);
  const body = el('div', { class: 'modal-body' });

  const avatarSection = el('div', { style: 'text-align:center;margin-bottom:20px;' });
  const avatarPreview = el('div', {
    style: 'width:100px;height:100px;margin:0 auto;border-radius:50%;overflow:hidden;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:40px;position:relative;cursor:pointer;border:3px solid var(--border);',
    onclick: () => avatarInput.click(),
  });
  function setAvatarPreview(src) {
    avatarPreview.innerHTML = '';
    if (src) {
      avatarPreview.appendChild(el('img', { src, style: 'width:100%;height:100%;object-fit:cover;' }));
    } else {
      avatarPreview.textContent = initials(CURRENT_USER.name);
    }
  }
  setAvatarPreview(CURRENT_USER.avatar);

  const cameraBadge = el('div', { style: 'position:absolute;bottom:0;right:0;background:var(--accent);width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid var(--bg);' });
  cameraBadge.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24" style="stroke:white;"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>';
  avatarPreview.appendChild(cameraBadge);
  avatarSection.appendChild(avatarPreview);

  const changePhotoText = el('div', { style: 'margin-top:10px;color:var(--accent);font-size:14px;font-weight:600;cursor:pointer;', onclick: () => avatarInput.click() }, 'Change Profile Picture');
  avatarSection.appendChild(changePhotoText);

  const avatarInput = el('input', { type: 'file', accept: 'image/*', style: 'display:none' });
  avatarInput.addEventListener('change', async () => {
    const f = avatarInput.files && avatarInput.files[0];
    if (!f) return;
    if (f.size > 2 * 1024 * 1024) { toast('Avatar too large (max 2 MB)', 'error'); avatarInput.value = ''; return; }
    if (!f.type.startsWith('image/')) { toast('Avatar must be an image', 'error'); avatarInput.value = ''; return; }
    const reader = new FileReader();
    reader.onload = (ev) => setAvatarPreview(ev.target.result);
    reader.readAsDataURL(f);
    const fd = new FormData();
    fd.append('file', f);
    changePhotoText.textContent = 'Uploading...';
    changePhotoText.style.color = 'var(--text-3)';
    try {
      const res = await api('/api/profile/avatar', { method: 'POST', body: fd });
      toast('Profile picture updated!', 'success');
      CURRENT_USER.avatar = res.avatar;
      changePhotoText.textContent = 'Change Profile Picture';
      changePhotoText.style.color = 'var(--accent)';
    } catch (err) {
      toast(err.message, 'error');
      setAvatarPreview(CURRENT_USER.avatar);
      changePhotoText.textContent = 'Change Profile Picture';
      changePhotoText.style.color = 'var(--accent)';
    }
  });
  avatarSection.appendChild(avatarInput);
  body.appendChild(avatarSection);

  const fields = [
    { key: 'name', label: 'Name', value: CURRENT_USER.name || '' },
    { key: 'username', label: 'Username', value: CURRENT_USER.username || '' },
    { key: 'bio', label: 'Bio', value: CURRENT_USER.bio || '', multiline: true },
    { key: 'location', label: 'Location', value: CURRENT_USER.location || '' },
  ];
  const inputs = {};
  for (const f of fields) {
    const wrap = el('div', { class: 'field', style: 'margin-bottom:12px;' });
    wrap.appendChild(el('label', {}, f.label));
    const inpWrap = el('div', { class: 'input-wrap no-icon' });
    const inp = f.multiline
      ? el('textarea', { rows: 3, style: 'padding:12px;resize:none;' })
      : el('input', { type: 'text' });
    inp.value = f.value;
    inpWrap.appendChild(inp);
    wrap.appendChild(inpWrap);
    body.appendChild(wrap);
    inputs[f.key] = inp;
  }

  const saveBtn = el('button', {
    class: 'btn btn-primary',
    style: 'margin-top:8px;',
    onclick: async () => {
      saveBtn.disabled = true;
      saveBtn.innerHTML = '<div class="loader"></div>';
      try {
        await api('/api/profile', {
          method: 'PATCH',
          body: JSON.stringify({
            name: inputs.name.value.trim(),
            username: inputs.username.value.trim() || null,
            bio: inputs.bio.value.trim(),
            location: inputs.location.value.trim(),
          }),
        });
        toast('Profile saved', 'success');
        await loadMe();
        closeModal();
        openProfile(CURRENT_USER.id);
      } catch (err) {
        toast(err.message, 'error');
        saveBtn.disabled = false;
        saveBtn.innerHTML = 'Save Changes';
      }
    }
  }, el('span', {}, 'Save Changes'));
  body.appendChild(saveBtn);
  content.appendChild(body);
  overlay.appendChild(content);
  container.appendChild(overlay);
}

// ============ CHAT LIST ============
async function openChats() {
  const main = $('#appMain');
  main.innerHTML = '<div class="center-loader"><div class="loader loader-lg"></div></div>';
  switchView('chats');
  try {
    const data = await api('/api/messages');
    CACHED_CHATS = data.chats || [];
    renderChatList();
  } catch (err) {
    main.innerHTML = `<div class="empty-state"><p class="empty-state-text" style="color:var(--danger);">${esc(err.message)}</p></div>`;
  }
}

function renderChatList() {
  const main = $('#appMain');
  main.innerHTML = '';
  const header = el('div', { style: 'padding:16px;border-bottom:1px solid var(--border);' });
  header.appendChild(el('h2', { style: 'font-size:20px;font-weight:700;' }, 'Chats'));
  main.appendChild(header);

  if (CACHED_CHATS.length === 0) {
    main.appendChild(el('div', { class: 'empty-state' },
      el('p', { class: 'empty-state-title' }, 'No conversations yet'),
      el('p', { class: 'empty-state-text' }, 'Start a chat from someone\'s profile')));
    return;
  }

  for (const c of CACHED_CHATS) {
    const row = el('div', {
      class: 'chat-list-item',
      onclick: () => openChat(c.other_id, c.name, c.avatar, c.username),
    });
    row.appendChild(avatarEl({ name: c.name, avatar: c.avatar }, 48));
    const info = el('div', { class: 'chat-list-item-info' });
    info.appendChild(el('div', { class: 'chat-list-item-name' }, c.name));
    if (c.last_text) {
      info.appendChild(el('div', { class: 'chat-list-item-preview' }, c.last_text));
    }
    row.appendChild(info);
    if (c.last_at) {
      row.appendChild(el('div', { class: 'chat-list-item-time' }, timeAgo(c.last_at)));
    }
    main.appendChild(row);
  }
}

// ============ OPEN CHAT (WhatsApp-style) ============
async function openChat(otherId, name, avatar, username) {
  const main = $('#appMain');
  main.innerHTML = '';
  switchView('chats');

  // Chat header
  const header = el('div', { class: 'chat-header' });
  const backBtn = el('button', { class: 'btn-icon', onclick: () => openChats() });
  backBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg>';
  header.appendChild(backBtn);

  const info = el('div', { class: 'chat-header-info', onclick: () => openProfile(otherId) });
  info.appendChild(avatarEl({ name, avatar }, 36));
  const infoText = el('div', { style: 'min-width:0;' });
  infoText.appendChild(el('div', { class: 'chat-header-name' }, name));
  infoText.appendChild(el('div', { class: 'chat-header-status', id: 'chatStatus' }, 'online'));
  info.appendChild(infoText);
  header.appendChild(info);

  const voiceBtn = el('button', { class: 'btn-icon', title: 'Voice call' });
  voiceBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>';
  voiceBtn.addEventListener('click', () => startCall(otherId, 'audio', name));
  header.appendChild(voiceBtn);

  const videoBtn = el('button', { class: 'btn-icon', title: 'Video call' });
  videoBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>';
  videoBtn.addEventListener('click', () => startCall(otherId, 'video', name));
  header.appendChild(videoBtn);

  const menuBtn = el('button', { class: 'btn-icon' });
  menuBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>';
  menuBtn.addEventListener('click', () => openChatMenu(otherId, name));
  header.appendChild(menuBtn);
  main.appendChild(header);

  // Messages area
  const msgsWrap = el('div', { class: 'chat-messages', id: 'msgsWrap' });
  main.appendChild(msgsWrap);

  // Load wallpaper
  try {
    const s = await api(`/api/chats/${otherId}/settings`);
    if (s.settings && s.settings.wallpaper) {
      msgsWrap.style.backgroundImage = `linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url(${s.settings.wallpaper})`;
    }
  } catch (_) {}

  // Composer
  const composer = el('div', { class: 'chat-composer' });
  const plusBtn = el('button', { class: 'chat-plus-btn' });
  plusBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
  plusBtn.addEventListener('click', () => openChatAttach(otherId));
  composer.appendChild(plusBtn);

  const inputWrap = el('div', { class: 'chat-input-wrap' });
  const typingIndicator = el('div', { class: 'chat-typing-indicator', id: 'typingIndicator' }, 'typing...');
  inputWrap.appendChild(typingIndicator);
  const msgInput = el('input', {
    type: 'text', class: 'chat-input', placeholder: 'Type text here', id: 'chatMsgInput',
  });
  inputWrap.appendChild(msgInput);
  composer.appendChild(inputWrap);

  const sendBtn = el('button', { class: 'chat-send-btn', style: 'display:none;', id: 'chatSendBtn' });
  sendBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
  composer.appendChild(sendBtn);

  const micBtn = el('button', { class: 'chat-mic-btn', id: 'chatMicBtn' });
  micBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
  composer.appendChild(micBtn);
  main.appendChild(composer);

  // Mic recording state
  let isRecording = false;
  let mediaRecorder = null;
  let audioChunks = [];
  let recordingLabel = null;

  // Typing indicator
  let typingTimer = null;
  function showTyping() {
    if (typingIndicator) typingIndicator.classList.add('show');
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
      if (typingIndicator) typingIndicator.classList.remove('show');
    }, 2000);
  }

  // Toggle send/mic based on input
  msgInput.addEventListener('input', () => {
    const hasText = msgInput.value.trim().length > 0;
    sendBtn.style.display = hasText ? 'flex' : 'none';
    micBtn.style.display = hasText ? 'none' : 'flex';
    if (hasText) showTyping();
  });

  // Send text
  async function sendText() {
    const text = msgInput.value.trim();
    if (!text) return;
    msgInput.value = '';
    sendBtn.style.display = 'none';
    micBtn.style.display = 'flex';
    try {
      const res = await api('/api/messages', {
        method: 'POST',
        body: JSON.stringify({ receiver_id: otherId, text }),
      });
      appendMessage(res.message);
    } catch (err) { toast(err.message, 'error'); }
  }
  sendBtn.addEventListener('click', sendText);
  msgInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendText(); });

  // Mic — long press to record
  micBtn.addEventListener('mousedown', startRecording);
  micBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); }, { passive: false });
  micBtn.addEventListener('mouseup', stopRecording);
  micBtn.addEventListener('mouseleave', stopRecording);
  micBtn.addEventListener('touchend', stopRecording);
  micBtn.addEventListener('touchcancel', stopRecording);

  async function startRecording() {
    if (isRecording) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      toast('Recording not supported', 'error');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];
      mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        if (blob.size < 500) return;
        if (blob.size > 15 * 1024 * 1024) { toast('Voice too large (max 15 MB)', 'error'); return; }
        const fd = new FormData();
        fd.append('receiver_id', otherId);
        fd.append('duration_seconds', '0');
        fd.append('file', blob, 'voice.webm');
        try {
          const res = await api('/api/messages/voice', { method: 'POST', body: fd });
          appendMessage(res.message);
        } catch (err) { toast(err.message, 'error'); }
      };
      mediaRecorder.start();
      isRecording = true;
      micBtn.classList.add('recording');
      // Recording label
      const inputWrap = msgInput.parentElement;
      recordingLabel = el('div', { class: 'chat-recording-label' }, 'recording audio...');
      inputWrap.appendChild(recordingLabel);
      msgInput.disabled = true;
      msgInput.placeholder = '';
    } catch (err) {
      toast('Mic permission denied', 'error');
    }
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    try { mediaRecorder.stop(); } catch(_) {}
    micBtn.classList.remove('recording');
    if (recordingLabel) { recordingLabel.remove(); recordingLabel = null; }
    msgInput.disabled = false;
    msgInput.placeholder = 'Type text here';
  }

  // Load messages
  try {
    const data = await api(`/api/messages/${otherId}`);
    if (!data.messages || data.messages.length === 0) {
      msgsWrap.innerHTML = '<div class="empty-state"><p class="empty-state-text">No messages yet. Say hi!</p></div>';
    } else {
      for (const m of data.messages) appendMessage(m);
    }
  } catch (err) {
    msgsWrap.innerHTML = `<div class="empty-state"><p class="empty-state-text" style="color:var(--danger);">${esc(err.message)}</p></div>`;
  }
}

function appendMessage(m) {
  const msgsWrap = $('#msgsWrap');
  if (!msgsWrap) return;
  const mine = CURRENT_USER && m.sender_id === CURRENT_USER.id;
  const wrap = el('div', { class: `chat-bubble-wrap ${mine ? 'mine' : 'theirs'}` });
  const bubble = el('div', { class: `chat-bubble ${mine ? 'mine' : 'theirs'}` });

  if (m.media && m.media_type === 'voice') {
    bubble.appendChild(el('audio', { src: m.media, controls: true, style: 'max-width:220px;' }));
  } else if (m.media && m.media_type === 'image') {
    bubble.appendChild(el('img', { src: m.media, class: 'chat-bubble-media' }));
    if (m.text) bubble.appendChild(el('div', { class: 'chat-bubble-text' }, m.text));
  } else if (m.media && m.media_type === 'video') {
    bubble.appendChild(el('video', { src: m.media, controls: true, class: 'chat-bubble-media', style: 'max-width:220px;' }));
    if (m.text) bubble.appendChild(el('div', { class: 'chat-bubble-text' }, m.text));
  } else if (m.media) {
    const a = el('a', { href: m.media, download: 'file', class: 'chat-bubble-file' }, '📎 Download file');
    bubble.appendChild(a);
    if (m.text) bubble.appendChild(el('div', { class: 'chat-bubble-text', style: 'margin-top:4px;' }, m.text));
  } else {
    bubble.appendChild(el('div', { class: 'chat-bubble-text' }, m.text || ''));
  }

  bubble.appendChild(el('div', { class: 'chat-bubble-time' }, timeAgo(m.created_at)));
  wrap.appendChild(bubble);
  msgsWrap.appendChild(wrap);
  msgsWrap.scrollTop = msgsWrap.scrollHeight;
}

function openChatAttach(otherId) {
  const items = [
    { label: '📷 Photo', onClick: () => pickChatFile(otherId, 'image/*') },
    { label: '🎥 Video', onClick: () => pickChatFile(otherId, 'video/*') },
    { label: '📄 Document', onClick: () => pickChatFile(otherId, '*/*') },
    { label: '🎙️ Voice Note', onClick: () => recordVoice(otherId) },
  ];
  openSheet('Attach', items);
}

function pickChatFile(otherId, accept) {
  const inp = el('input', { type: 'file', accept, style: 'display:none' });
  inp.addEventListener('change', async () => {
    const f = inp.files && inp.files[0];
    if (!f) return;
    let maxMB = 25;
    if (f.type.startsWith('video/')) maxMB = 50;
    else if (f.type.startsWith('image/')) maxMB = 10;
    if (f.size > maxMB * 1024 * 1024) {
      toast('File too large. Max ' + maxMB + ' MB', 'error');
      inp.value = '';
      return;
    }
    const fd = new FormData();
    fd.append('receiver_id', otherId);
    fd.append('text', '');
    fd.append('file', f);
    try {
      const res = await api('/api/messages/file', { method: 'POST', body: fd });
      appendMessage(res.message);
    } catch (err) { toast(err.message, 'error'); }
  });
  document.body.appendChild(inp);
  inp.click();
  setTimeout(() => inp.remove(), 1000);
}

async function recordVoice(otherId) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    toast('Recording not supported on this browser', 'error');
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(chunks, { type: 'audio/webm' });
      if (blob.size > 15 * 1024 * 1024) { toast('Voice too large (max 15 MB)', 'error'); return; }
      const fd = new FormData();
      fd.append('receiver_id', otherId);
      fd.append('duration_seconds', '0');
      fd.append('file', blob, 'voice.webm');
      try {
        const res = await api('/api/messages/voice', { method: 'POST', body: fd });
        appendMessage(res.message);
      } catch (err) { toast(err.message, 'error'); }
    };
    recorder.start();
    const maxTimer = setTimeout(() => recorder.stop(), 30000);
    const container = $('#modalContainer');
    container.innerHTML = '';
    const overlay = el('div', { class: 'modal-overlay', onclick: () => { clearTimeout(maxTimer); if (recorder.state !== 'inactive') recorder.stop(); closeModal(); } });
    const content = el('div', { class: 'modal-content', style: 'text-align:center;padding:32px 20px;' });
    content.appendChild(el('div', { style: 'font-size:20px;font-weight:700;margin-bottom:16px;' }, '🎙️ Recording...'));
    content.appendChild(el('div', { style: 'color:var(--text-2);font-size:14px;margin-bottom:24px;' }, 'Tap stop when done (max 30s)'));
    const stopBtn = el('button', {
      class: 'btn btn-danger',
      style: 'max-width:200px;margin:0 auto;',
      onclick: () => { clearTimeout(maxTimer); if (recorder.state !== 'inactive') recorder.stop(); closeModal(); }
    }, 'Stop & Send');
    content.appendChild(stopBtn);
    overlay.appendChild(content);
    container.appendChild(overlay);
  } catch (err) {
    toast('Mic permission denied', 'error');
  }
}

function openChatMenu(otherId, name) {
  const items = [
    { label: 'View Profile', onClick: () => openProfile(otherId) },
    { label: 'Chat Wallpaper', onClick: () => pickWallpaper(otherId) },
    { label: 'Clear Chat', danger: true, onClick: async () => {
      if (!confirm('Clear all messages in this chat?')) return;
      try {
        await api(`/api/chats/${otherId}`, { method: 'DELETE' });
        toast('Chat cleared', 'success');
        openChat(otherId, name);
      } catch (err) { toast(err.message, 'error'); }
    }},
    { label: 'Block User', danger: true, onClick: async () => {
      if (!confirm('Block ' + name + '?')) return;
      try {
        await api(`/api/users/${otherId}/block`, { method: 'POST' });
        toast('Blocked', 'success');
        openChats();
      } catch (err) { toast(err.message, 'error'); }
    }},
  ];
  openSheet('Chat Options', items);
}

function pickWallpaper(otherId) {
  const inp = el('input', { type: 'file', accept: 'image/*', style: 'display:none' });
  inp.addEventListener('change', async () => {
    const f = inp.files && inp.files[0];
    if (!f) return;
    if (f.size > 1024 * 1024) { toast('Max 1 MB', 'error'); return; }
    const fd = new FormData();
    fd.append('file', f);
    try {
      await api(`/api/chats/${otherId}/wallpaper`, { method: 'POST', body: fd });
      toast('Wallpaper set', 'success');
      const msgsWrap = $('#msgsWrap');
      if (msgsWrap) {
        const reader = new FileReader();
        reader.onload = () => { msgsWrap.style.backgroundImage = `linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url(${reader.result})`; };
        reader.readAsDataURL(f);
      }
    } catch (err) { toast(err.message, 'error'); }
  });
  document.body.appendChild(inp);
  inp.click();
  setTimeout(() => inp.remove(), 1000);
}

async function openChatWith(user) {
  openChat(user.id, user.name, user.avatar, user.username);
}

async function startCall(otherId, type, name) {
  try {
    toast('Starting ' + type + ' call...', 'info');
    const res = await api('/api/calls/token', {
      method: 'POST',
      body: JSON.stringify({ receiver_id: otherId, call_type: type }),
    });
    toast('LiveKit ready: room ' + res.room_name, 'success');
    alert('Call token created!\nRoom: ' + res.room_name + '\n\nNote: Full LiveKit client SDK integration needed for call UI.');
  } catch (err) { toast(err.message, 'error'); }
}

// ============ STORIES ============
async function loadStories(storiesBar) {
  try {
    const data = await api('/api/statuses');
    const groups = data.groups || [];
    if (groups.length === 0) {
      storiesBar.appendChild(el('div', { style: 'display:flex;align-items:center;color:var(--text-3);font-size:13px;padding:0 8px;' }, 'No stories yet'));
      return;
    }
    for (const g of groups) {
      const isMe = CURRENT_USER && g.user.id === CURRENT_USER.id;
      const storyItem = el('div', { class: 'story-item', onclick: () => openStoryViewer(g) });
      const ring = el('div', { class: 'story-ring' });
      const inner = el('div', { class: 'story-ring-inner' });
      if (g.user.avatar) {
        inner.appendChild(el('img', { src: g.user.avatar, style: 'width:100%;height:100%;object-fit:cover;' }));
      } else {
        inner.textContent = initials(g.user.name);
        inner.style.color = 'white';
        inner.style.fontWeight = '700';
        inner.style.fontSize = '24px';
        inner.style.background = 'linear-gradient(135deg,#3b82f6,#8b5cf6)';
      }
      ring.appendChild(inner);
      storyItem.appendChild(ring);
      const label = isMe ? 'My Story' : g.user.name.split(' ')[0];
      storyItem.appendChild(el('div', { class: 'story-item-name' }, label));
      storiesBar.appendChild(storyItem);
    }
  } catch (err) {
    console.warn('Stories load failed:', err.message);
  }
}

function openStoryViewer(group) {
  const container = $('#modalContainer');
  container.innerHTML = '';
  const overlay = el('div', { class: 'story-viewer' });

  let idx = 0;
  const total = group.statuses.length;
  let progressTimer = null;
  let currentProgressBar = null;
  let isPaused = false;
  const STORY_DURATION = 5000;

  function clearTimer() {
    if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
  }

  function render() {
    clearTimer();
    overlay.innerHTML = '';
    isPaused = false;
    const s = group.statuses[idx];

    // Progress bars
    const progressWrap = el('div', { class: 'story-progress-wrap' });
    const bars = [];
    for (let i = 0; i < total; i++) {
      const bar = el('div', { class: 'story-progress-bar' });
      const fill = el('div', { class: 'story-progress-fill', style: `width:${i < idx ? '100%' : '0%'};` });
      bar.appendChild(fill);
      progressWrap.appendChild(bar);
      bars.push(fill);
    }
    overlay.appendChild(progressWrap);
    currentProgressBar = bars[idx];

    // Header
    const header = el('div', { class: 'story-header' });
    if (group.user.avatar) {
      header.appendChild(el('img', { src: group.user.avatar, class: 'story-avatar' }));
    } else {
      header.appendChild(el('div', {
        style: 'width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:14px;border:2px solid white;',
      }, initials(group.user.name)));
    }
    const info = el('div', { class: 'story-info' });
    info.appendChild(el('div', { class: 'story-name' }, group.user.name));
    info.appendChild(el('div', { class: 'story-time' }, timeAgo(s.created_at)));
    header.appendChild(info);

    if (CURRENT_USER && group.user.id === CURRENT_USER.id) {
      const delBtn = el('button', {
        class: 'story-btn',
        onclick: async (e) => {
          e.stopPropagation();
          if (!confirm('Delete this story?')) return;
          try {
            await api(`/api/statuses/${s.id}`, { method: 'DELETE' });
            toast('Deleted', 'success');
            clearTimer();
            closeModal();
            loadFeed('all');
          } catch (err) { toast(err.message, 'error'); }
        }
      });
      delBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/></svg>';
      header.appendChild(delBtn);
    }

    const closeBtn = el('button', { class: 'story-btn', onclick: () => { clearTimer(); closeModal(); } });
    closeBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    header.appendChild(closeBtn);
    overlay.appendChild(header);

    // Content
    const content = el('div', { class: 'story-content' });

    if (s.media_type === 'video') {
      const video = el('video', {
        src: s.media, autoplay: true, playsinline: true, muted: true, loop: false,
      });
      content.appendChild(video);
      video.addEventListener('loadedmetadata', () => {
        if (video.duration && video.duration < 60) startProgress(video.duration * 1000);
        else startProgress(STORY_DURATION);
      });
      setTimeout(() => { if (!video.duration) startProgress(STORY_DURATION); }, 500);
      setTimeout(() => { video.play().catch(() => {}); }, 100);
    } else if (s.media) {
      content.appendChild(el('img', { src: s.media }));
      startProgress(STORY_DURATION);
    } else {
      startProgress(STORY_DURATION);
    }

    if (s.text) {
      content.appendChild(el('div', { class: 'story-caption' }, s.text));
    }

    overlay.appendChild(content);

    // Tap zones
    const tapLeft = el('div', { class: 'story-tap-left' });
    const tapRight = el('div', { class: 'story-tap-right' });
    tapLeft.onclick = () => { clearTimer(); if (idx > 0) { idx--; render(); } else closeModal(); };
    tapRight.onclick = () => { clearTimer(); if (idx < total - 1) { idx++; render(); } else closeModal(); };
    overlay.appendChild(tapLeft);
    overlay.appendChild(tapRight);

    // Long press pause
    let holdTimer = null;
    function startHold() {
      holdTimer = setTimeout(() => {
        isPaused = true;
        const v = overlay.querySelector('video');
        if (v) v.pause();
      }, 200);
    }
    function endHold() {
      clearTimeout(holdTimer);
      if (isPaused) {
        isPaused = false;
        const v = overlay.querySelector('video');
        if (v) v.play().catch(() => {});
      }
    }
    overlay.addEventListener('mousedown', startHold);
    overlay.addEventListener('touchstart', startHold, { passive: true });
    overlay.addEventListener('mouseup', endHold);
    overlay.addEventListener('touchend', endHold);
    overlay.addEventListener('mouseleave', endHold);
    overlay.addEventListener('touchcancel', endHold);

    container.appendChild(overlay);
  }

  function startProgress(durationMs) {
    let elapsed = 0;
    clearTimer();
    progressTimer = setInterval(() => {
      if (isPaused) return;
      elapsed += 50;
      const pct = Math.min(100, (elapsed / durationMs) * 100);
      if (currentProgressBar) currentProgressBar.style.width = pct + '%';
      if (pct >= 100) {
        clearTimer();
        if (idx < total - 1) { idx++; render(); }
        else closeModal();
      }
    }, 50);
  }

  render();
}

function openCreateStory() {
  const container = $('#modalContainer');
  container.innerHTML = '';
  const overlay = el('div', { class: 'modal-overlay', onclick: (e) => { if (e.target === overlay) closeModal(); } });
  const content = el('div', { class: 'modal-content' });

  const h = el('div', { class: 'modal-header' });
  h.appendChild(el('h3', {}, 'Create Story'));
  const cb = el('button', { class: 'btn-icon', onclick: closeModal });
  cb.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  h.appendChild(cb);
  content.appendChild(h);

  const body = el('div', { class: 'modal-body' });

  const preview = el('div', {
    style: 'width:100%;height:300px;background:var(--bg-3);border-radius:var(--radius);display:flex;align-items:center;justify-content:center;overflow:hidden;margin-bottom:12px;position:relative;',
  }, el('div', { style: 'color:var(--text-3);font-size:14px;' }, 'No media selected'));
  body.appendChild(preview);

  const fileInput = el('input', { type: 'file', style: 'display:none' });
  let selectedFile = null;
  let previewURL = null;

  fileInput.addEventListener('change', () => {
    const f = fileInput.files && fileInput.files[0];
    if (!f) return;
    let maxMB = 10;
    if (f.type.startsWith('video/')) maxMB = 50;
    if (f.size > maxMB * 1024 * 1024) {
      toast('File too large. Max ' + maxMB + ' MB', 'error');
      fileInput.value = '';
      return;
    }
    selectedFile = f;
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = URL.createObjectURL(f);
    preview.innerHTML = '';
    if (f.type.startsWith('video/')) {
      preview.appendChild(el('video', { src: previewURL, controls: true, playsinline: true, style: 'width:100%;height:100%;object-fit:contain;' }));
    } else if (f.type.startsWith('image/')) {
      preview.appendChild(el('img', { src: previewURL, style: 'width:100%;height:100%;object-fit:contain;' }));
    }
  });
  body.appendChild(fileInput);

  const mediaRow = el('div', { style: 'display:flex;gap:6px;margin-bottom:12px;' });
  const photoBtn = el('button', { class: 'btn btn-secondary', style: 'flex:1;padding:10px 6px;font-size:12px;', onclick: () => { fileInput.accept = 'image/*'; fileInput.click(); } });
  photoBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg><span>Photo</span>';
  mediaRow.appendChild(photoBtn);
  const videoBtn = el('button', { class: 'btn btn-secondary', style: 'flex:1;padding:10px 6px;font-size:12px;', onclick: () => { fileInput.accept = 'video/*'; fileInput.click(); } });
  videoBtn.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg><span>Video</span>';
  mediaRow.appendChild(videoBtn);
  body.appendChild(mediaRow);

  const textInput = el('textarea', {
    placeholder: 'Add a caption (optional)...', rows: 3, maxlength: 500,
    style: 'width:100%;background:var(--bg-3);border:1px solid var(--border);border-radius:var(--radius);padding:12px;font-size:14px;color:var(--text);resize:none;font-family:inherit;margin-bottom:12px;',
  });
  body.appendChild(textInput);

  const postBtn = el('button', {
    class: 'btn btn-primary',
    onclick: async () => {
      const text = textInput.value.trim();
      if (!text && !selectedFile) { toast('Add text or media', 'error'); return; }
      postBtn.disabled = true;
      postBtn.innerHTML = '<div class="loader"></div>';
      try {
        const fd = new FormData();
        fd.append('text', text);
        if (selectedFile) fd.append('file', selectedFile);
        await api('/api/statuses', { method: 'POST', body: fd });
        toast('Story posted!', 'success');
        closeModal();
        loadFeed('all');
      } catch (err) {
        toast(err.message, 'error');
        postBtn.disabled = false;
        postBtn.innerHTML = '<span>Post Story</span>';
      }
    }
  }, el('span', {}, 'Post Story'));
  body.appendChild(postBtn);

  content.appendChild(body);
  overlay.appendChild(content);
  container.appendChild(overlay);
}


/* ============================================================
   APP.JS — PART 3/3
   Search, Discovery, Video, User Manual, Init
   ============================================================ */

// ============ SEARCH ============
async function openSearch() {
  openSearchWithQuery('');
}

async function openSearchWithQuery(initialQuery) {
  const main = $('#appMain');
  switchView('home');
  main.innerHTML = '';

  const header = el('div', { style: 'padding:12px 16px;background:var(--bg-2);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:4;' });
  const backBtn = el('button', { class: 'btn-icon', style: 'position:absolute;left:8px;top:12px;', onclick: () => loadFeed('all') });
  backBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg>';
  header.appendChild(backBtn);
  const inputWrap = el('div', { class: 'input-wrap', style: 'margin-left:44px;' });
  const searchIcon = el('div');
  searchIcon.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>';
  inputWrap.appendChild(searchIcon.firstChild);
  const inp = el('input', { type: 'text', placeholder: 'Search people...', value: initialQuery || '', style: 'padding-left:42px;' });
  inputWrap.appendChild(inp);
  header.appendChild(inputWrap);
  main.appendChild(header);

  const results = el('div');
  main.appendChild(results);

  async function doSearch(q) {
    if (!q) { results.innerHTML = ''; return; }
    results.innerHTML = '<div class="center-loader"><div class="loader"></div></div>';
    try {
      const data = await api('/api/search?q=' + encodeURIComponent(q));
      results.innerHTML = '';
      if (!data.users || data.users.length === 0) {
        results.innerHTML = '<div class="empty-state"><p class="empty-state-title">No users found</p></div>';
        return;
      }
      for (const u of data.users) {
        const row = el('div', {
          style: 'display:flex;align-items:center;gap:12px;padding:12px 16px;cursor:pointer;border-bottom:1px solid var(--border);',
          onclick: () => openProfile(u.id),
        });
        row.appendChild(avatarEl(u, 44));
        const info = el('div');
        info.appendChild(el('div', { style: 'font-weight:600;font-size:14px;' }, u.name));
        if (u.username) info.appendChild(el('div', { style: 'font-size:12px;color:var(--text-3);' }, '@' + u.username));
        row.appendChild(info);
        results.appendChild(row);
      }
    } catch (err) {
      results.innerHTML = `<div class="empty-state"><p class="empty-state-text" style="color:var(--danger);">${esc(err.message)}</p></div>`;
    }
  }

  let timer;
  inp.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => doSearch(inp.value.trim()), 400);
  });
  if (initialQuery) doSearch(initialQuery);
  inp.focus();
}

// ============ DISCOVERY ============
async function openDiscovery() {
  const main = $('#appMain');
  main.innerHTML = '';
  switchView('discovery');

  const header = el('div', { class: 'discovery-header' });
  header.appendChild(el('h2', { class: 'discovery-title' }, 'Discover'));
  header.appendChild(el('p', { class: 'discovery-subtitle' }, 'AI, Studio, Market and more'));
  main.appendChild(header);

  const items = [
    { key: 'ai', icon: 'book', label: 'AI Council', desc: 'Education, Health, Agriculture, Research', color: '#3b82f6' },
    { key: 'studio', icon: 'image', label: 'Creative Studio', desc: 'Image, Video, Documents', color: '#8b5cf6' },
    { key: 'market', icon: 'shopping-bag', label: 'Market', desc: 'Products, Services, Digital', color: '#10b981' },
    { key: 'map', icon: 'globe', label: 'World Map', desc: 'Explore the world', color: '#f59e0b' },
    { key: 'channels', icon: 'tv', label: 'Channels', desc: 'BBC, CNN, Aljazeera and more', color: '#ef4444' },
    { key: 'communities', icon: 'users', label: 'Communities', desc: 'Join groups and communities', color: '#06b6d4' },
    { key: 'videos', icon: 'play', label: 'Videos', desc: 'Short videos feed', color: '#ec4899' },
    { key: 'settings', icon: 'settings', label: 'Settings', desc: 'App preferences', color: '#64748b' },
  ];

  const icons = {
    book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
    'shopping-bag': '<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>',
    globe: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    tv: '<rect x="2" y="7" width="20" height="15" rx="2"/><polyline points="17 2 12 7 7 2"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    play: '<polygon points="5 3 19 12 5 21 5 3"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  };

  const grid = el('div', { class: 'discovery-grid' });
  for (const item of items) {
    const card = el('div', { class: 'discovery-card', onclick: () => openDiscoveryItem(item.key) });
    const iconWrap = el('div', { class: 'discovery-card-icon', style: `background:${item.color};` });
    iconWrap.innerHTML = `<svg viewBox="0 0 24 24" style="width:26px;height:26px;stroke:white;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;">${icons[item.icon]}</svg>`;
    card.appendChild(iconWrap);
    card.appendChild(el('div', { class: 'discovery-card-label' }, item.label));
    card.appendChild(el('div', { class: 'discovery-card-desc' }, item.desc));
    grid.appendChild(card);
  }
  main.appendChild(grid);
}

function openDiscoveryItem(key) {
  if (key === 'ai') openAICouncil();
  else if (key === 'studio') openStudio();
  else if (key === 'market') openMarket();
  else if (key === 'map') openWorldMap();
  else if (key === 'channels') openChannels();
  else if (key === 'communities') openCommunities();
  else if (key === 'videos') openVideos();
  else if (key === 'settings') openSettings();
}

// ============ DISCOVERY SUB-PAGE HEADER ============
function subPageHeader(title, backFn) {
  const header = el('div', { class: 'discovery-back' });
  const back = el('button', { class: 'discovery-back-btn', onclick: backFn || openDiscovery });
  back.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg>';
  header.appendChild(back);
  header.appendChild(el('div', { class: 'discovery-back-title' }, title));
  return header;
}

// ============ AI COUNCIL ============
function openAICouncil() {
  const main = $('#appMain');
  main.innerHTML = '';
  switchView('discovery');
  main.appendChild(subPageHeader('AI Council'));

  const list = el('div', { class: 'ai-list' });

  const ais = [
    { key: 'edu', icon: 'book', label: 'Education AI', desc: 'Study notes, syllabus, past papers', color: '#3b82f6' },
    { key: 'health', icon: 'heart', label: 'Health AI', desc: 'General health information', color: '#10b981' },
    { key: 'agri', icon: 'leaf', label: 'Agriculture AI', desc: 'Crops, soil, farming', color: '#84cc16' },
    { key: 'research', icon: 'search', label: 'Research AI', desc: 'Methodology, citations', color: '#8b5cf6' },
    { key: 'canvas', icon: 'layout', label: 'AI Canvas', desc: 'Workspace with documents', color: '#f59e0b' },
  ];

  const icons = {
    book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    heart: '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
    leaf: '<path d="M6 21V11a6 6 0 0 1 6-6h6l-3 3 3 3h-6a6 6 0 0 0-6 6"/>',
    search: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    layout: '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/>',
  };

  for (const a of ais) {
    const item = el('div', { class: 'ai-list-item', onclick: () => openAISub(a.key, a.label) });
    const iconWrap = el('div', { class: 'ai-list-icon', style: `background:${a.color};` });
    iconWrap.innerHTML = `<svg viewBox="0 0 24 24" style="width:26px;height:26px;stroke:white;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;">${icons[a.icon]}</svg>`;
    item.appendChild(iconWrap);
    const text = el('div', { class: 'ai-list-text' });
    text.appendChild(el('div', { class: 'ai-list-title' }, a.label));
    text.appendChild(el('div', { class: 'ai-list-desc' }, a.desc));
    item.appendChild(text);
    const arrow = el('div', { class: 'ai-list-arrow' });
    arrow.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>';
    item.appendChild(arrow);
    list.appendChild(item);
  }
  main.appendChild(list);
}

function openAISub(key, label) {
  if (key === 'edu') openEduAI();
  else openAIChatPlaceholder(label);
}

function openAIChatPlaceholder(label) {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader(label, openAICouncil));
  main.appendChild(el('div', { class: 'empty-state' },
    el('p', { class: 'empty-state-title' }, label),
    el('p', { class: 'empty-state-text' }, 'Coming soon — AI chat integration in Phase 6.')));
}

// ============ EDUCATION AI ============
function openEduAI() {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('Education AI', openAICouncil));

  const stepLabel = el('div', { style: 'padding:16px 16px 8px;font-weight:700;font-size:15px;' }, 'Step 1 — Choose country');
  main.appendChild(stepLabel);

  const countries = [
    'Tanzania', 'Kenya', 'Uganda', 'Rwanda', 'Burundi', 'South Africa',
    'Nigeria', 'Ghana', 'UK', 'USA', 'Canada', 'Australia', 'India',
    'China', 'Japan', 'Germany', 'France', 'Brazil'
  ];
  const grid = el('div', { class: 'selector-grid' });
  for (const c of countries) {
    grid.appendChild(el('div', {
      class: 'selector-item',
      onclick: () => openEduLevel(c),
    }, c));
  }
  main.appendChild(grid);
}

function openEduLevel(country) {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('Education AI — ' + country, openEduAI));

  main.appendChild(el('div', { style: 'padding:16px 16px 8px;font-weight:700;font-size:15px;' }, 'Step 2 — Choose level'));

  const levels = ['Nursery', 'Primary', 'Secondary', 'High School', 'Certificate', 'Diploma', 'Degree', 'Master', 'PhD'];
  const grid = el('div', { class: 'selector-grid' });
  for (const l of levels) {
    grid.appendChild(el('div', {
      class: 'selector-item',
      onclick: () => openEduContent(country, l),
    }, l));
  }
  main.appendChild(grid);
}

function openEduContent(country, level) {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader(level + ' — ' + country, () => openEduLevel(country)));

  main.appendChild(el('div', { style: 'padding:16px 16px 8px;font-weight:700;font-size:15px;' }, 'Step 3 — Choose content'));

  const types = [
    { key: 'notes', label: 'Notes' },
    { key: 'books', label: 'Books' },
    { key: 'papers', label: 'Past Papers' },
    { key: 'schemes', label: 'Marking Schemes' },
  ];
  const grid = el('div', { class: 'selector-grid' });
  for (const t of types) {
    grid.appendChild(el('div', {
      class: 'selector-item',
      onclick: () => openEduChat(country, level, t.label),
    }, t.label));
  }
  main.appendChild(grid);
}

function openEduChat(country, level, type) {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('Edu AI — ' + level + ' ' + country, () => openEduContent(country, level)));

  const chatContainer = el('div', { class: 'ai-chat-container' });
  const msgs = el('div', { class: 'ai-chat-messages', id: 'aiChatMsgs' });
  msgs.appendChild(el('div', { class: 'ai-chat-msg ai' },
    `Hello! I'm your ${type} assistant for ${level} curriculum in ${country}. Ask me anything about a subject or topic.`));
  chatContainer.appendChild(msgs);

  const inputWrap = el('div', { class: 'ai-chat-input-wrap' });
  const inp = el('input', { type: 'text', class: 'ai-chat-input', placeholder: 'Ask about a topic...' });
  const send = el('button', { class: 'chat-send-btn' });
  send.innerHTML = '<svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
  send.addEventListener('click', () => {
    const q = inp.value.trim();
    if (!q) return;
    inp.value = '';
    msgs.appendChild(el('div', { class: 'ai-chat-msg user' }, q));
    msgs.appendChild(el('div', { class: 'ai-chat-msg ai' }, 'AI responses will be available in Phase 6. This is a placeholder.'));
    msgs.scrollTop = msgs.scrollHeight;
  });
  inputWrap.appendChild(inp);
  inputWrap.appendChild(send);
  chatContainer.appendChild(inputWrap);
  main.appendChild(chatContainer);
}

// ============ STUDIO ============
function openStudio() {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('Creative Studio'));
  main.appendChild(el('div', { class: 'empty-state' },
    el('p', { class: 'empty-state-title' }, 'Creative Studio'),
    el('p', { class: 'empty-state-text' }, 'Image, Video, Documents — coming in Phase 7.')));
}

// ============ MARKET ============
function openMarket() {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('Market'));

  const searchWrap = el('div', { style: 'padding:12px 16px;' });
  const inp = el('input', {
    type: 'text', placeholder: 'Search products...',
    style: 'width:100%;padding:12px 16px;background:var(--bg-3);border:1.5px solid var(--border);border-radius:24px;font-size:14px;color:var(--text);',
  });
  searchWrap.appendChild(inp);
  main.appendChild(searchWrap);

  main.appendChild(el('div', { class: 'empty-state' },
    el('p', { class: 'empty-state-title' }, 'No products yet'),
    el('p', { class: 'empty-state-text' }, 'Market functionality — coming in Phase 8.')));
}

// ============ WORLD MAP ============
function openWorldMap() {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('World Map'));
  main.appendChild(el('div', { class: 'empty-state' },
    el('p', { class: 'empty-state-title' }, 'World Map'),
    el('p', { class: 'empty-state-text' }, 'Coming soon.')));
}

// ============ CHANNELS ============
function openChannels() {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('Channels'));

  const channels = [
    { name: 'BBC News', desc: 'Global news from UK', color: '#dc2626', text: 'BBC' },
    { name: 'CNN', desc: 'Cable News Network', color: '#b91c1c', text: 'CNN' },
    { name: 'Al Jazeera', desc: 'Qatar-based news', color: '#d97706', text: 'AJ' },
    { name: 'ITV News', desc: 'UK broadcaster', color: '#0ea5e9', text: 'ITV' },
    { name: 'Msafiri Global Media', desc: 'Our own channel', color: '#3b82f6', text: 'M' },
  ];

  for (const ch of channels) {
    const item = el('div', { class: 'channel-item', onclick: () => toast(ch.name + ' — coming soon', 'info') });
    const logo = el('div', { class: 'channel-logo', style: `background:${ch.color};` }, ch.text);
    item.appendChild(logo);
    const info = el('div', { class: 'channel-info' });
    info.appendChild(el('div', { class: 'channel-name' }, ch.name));
    info.appendChild(el('div', { class: 'channel-desc' }, ch.desc));
    item.appendChild(info);
    main.appendChild(item);
  }
}

// ============ COMMUNITIES ============
function openCommunities() {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('Communities'));
  main.appendChild(el('div', { class: 'empty-state' },
    el('p', { class: 'empty-state-title' }, 'Communities'),
    el('p', { class: 'empty-state-text' }, 'Join groups — coming soon.')));
}

// ============ SETTINGS ============
function openSettings() {
  const main = $('#appMain');
  main.innerHTML = '';
  main.appendChild(subPageHeader('Settings'));

  const list = el('div', { class: 'ai-list' });
  const items = [
    { label: 'User Manual', icon: '📖', fn: () => openUserManual() },
    { label: 'Toggle Theme', icon: '🌓', fn: () => toggleTheme() },
    { label: 'Version', icon: 'ℹ️', fn: () => toast('MSAFIRI MEDIA V0.0.1', 'info') },
    { label: 'Logout', icon: '🚪', fn: () => logout() },
  ];
  for (const it of items) {
    const row = el('div', { class: 'ai-list-item', onclick: it.fn });
    row.appendChild(el('div', { style: 'font-size:24px;' }, it.icon));
    row.appendChild(el('div', { class: 'ai-list-text', style: 'margin-left:14px;' }, it.label));
    list.appendChild(row);
  }
  main.appendChild(list);
}

// ============ VIDEO FEED ============
async function openVideos() {
  const main = $('#appMain');
  main.innerHTML = '';
  switchView('discovery');

  const container = el('div', { class: 'video-feed-container', id: 'videoFeedContainer' });
  main.appendChild(container);
  container.innerHTML = '<div class="center-loader" style="height:100%;"><div class="loader loader-lg"></div></div>';

  try {
    const data = await api('/api/videos?limit=30');
    CACHED_VIDEOS = data.videos || [];

    if (CACHED_VIDEOS.length === 0) {
      container.innerHTML = `<div class="empty-state" style="height:100%;color:white;">
        <p class="empty-state-title" style="color:white;">No videos yet</p>
        <p class="empty-state-text" style="color:rgba(255,255,255,0.7);">Be the first to share a video!</p>
      </div>`;
      return;
    }

    window._videoIndex = 0;
    renderVideoFeed();
  } catch (err) {
    container.innerHTML = `<div class="empty-state" style="height:100%;color:white;"><p class="empty-state-text">${esc(err.message)}</p></div>`;
  }
}

function renderVideoFeed() {
  const container = $('#videoFeedContainer');
  if (!container) return;
  container.innerHTML = '';

  const video = CACHED_VIDEOS[window._videoIndex];
  if (!video) return;

  const videoEl = el('video', {
    src: video.media, autoplay: true, playsinline: true, loop: true,
    class: 'video-feed-video',
  });
  videoEl.addEventListener('click', () => {
    if (videoEl.paused) videoEl.play().catch(() => {});
    else videoEl.pause();
  });
  container.appendChild(videoEl);
  setTimeout(() => { videoEl.play().catch(() => { videoEl.muted = true; videoEl.play().catch(() => {}); }); }, 100);

  // Actions
  const actions = el('div', { class: 'video-feed-actions' });

  const likeBtn = el('div', { class: 'video-feed-action' });
  likeBtn.innerHTML = `<svg viewBox="0 0 24 24" style="fill:${video.liked ? 'var(--danger)' : 'none'};stroke:${video.liked ? 'var(--danger)' : 'white'};"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg><span>${video.likes_count || 0}</span>`;
  likeBtn.addEventListener('click', async () => {
    try {
      if (video.liked) {
        await api(`/api/posts/${video.id}/like`, { method: 'DELETE' });
        video.liked = false;
        video.likes_count = Math.max(0, (video.likes_count || 0) - 1);
      } else {
        await api(`/api/posts/${video.id}/like`, { method: 'POST' });
        video.liked = true;
        video.likes_count = (video.likes_count || 0) + 1;
      }
      renderVideoFeed();
    } catch (err) { toast(err.message, 'error'); }
  });
  actions.appendChild(likeBtn);

  const commentBtn = el('div', { class: 'video-feed-action' });
  commentBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg><span>${video.comments_count || 0}</span>`;
  commentBtn.addEventListener('click', () => { videoEl.pause(); openComments(video); });
  actions.appendChild(commentBtn);

  const shareBtn = el('div', { class: 'video-feed-action' });
  shareBtn.innerHTML = `<svg viewBox="0 0 24 24"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg><span>Share</span>`;
  shareBtn.addEventListener('click', async () => {
    const url = `${API}/?video=${video.id}`;
    if (navigator.share) { try { await navigator.share({ title: 'MSAFIRI Video', url }); } catch(_){} }
    else if (navigator.clipboard) navigator.clipboard.writeText(url).then(() => toast('Link copied', 'success'));
  });
  actions.appendChild(shareBtn);

  const muteBtn = el('div', { class: 'video-feed-action' });
  muteBtn.innerHTML = '<svg viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>';
  muteBtn.addEventListener('click', () => {
    videoEl.muted = !videoEl.muted;
    muteBtn.innerHTML = videoEl.muted
      ? '<svg viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>'
      : '<svg viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>';
  });
  actions.appendChild(muteBtn);
  container.appendChild(actions);

  // Info
  const info = el('div', { class: 'video-feed-info' });
  const userRow = el('div', { class: 'video-feed-user', onclick: () => openProfile(video.user.id) });
  userRow.appendChild(avatarEl(video.user, 40));
  userRow.appendChild(el('span', { class: 'video-feed-username' }, video.user.name));
  info.appendChild(userRow);
  if (video.caption) info.appendChild(el('div', { class: 'video-feed-caption' }, video.caption));
  info.appendChild(el('div', { class: 'video-feed-time' }, timeAgo(video.created_at)));
  container.appendChild(info);

  // Swipe
  let startY = 0;
  container.addEventListener('touchstart', (e) => { startY = e.touches[0].clientY; }, { passive: true });
  container.addEventListener('touchend', (e) => {
    const diff = startY - e.changedTouches[0].clientY;
    if (Math.abs(diff) > 80) {
      if (diff > 0 && window._videoIndex < CACHED_VIDEOS.length - 1) { window._videoIndex++; renderVideoFeed(); }
      else if (diff < 0 && window._videoIndex > 0) { window._videoIndex--; renderVideoFeed(); }
    }
  }, { passive: true });
}

// ============ USER MANUAL ============
function openUserManual() {
  const container = $('#modalContainer');
  container.innerHTML = '';
  const overlay = el('div', { class: 'modal-overlay', onclick: (e) => { if (e.target === overlay) closeModal(); } });
  const content = el('div', { class: 'modal-content', style: 'max-height:95vh;' });

  const h = el('div', { class: 'modal-header' });
  h.appendChild(el('h3', {}, 'User Manual'));
  const cb = el('button', { class: 'btn-icon', onclick: closeModal });
  cb.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  h.appendChild(cb);
  content.appendChild(h);

  const body = el('div', { class: 'modal-body' });
  body.innerHTML = `
    <div class="manual-container">
      <div class="manual-header">
        <div class="manual-logo">M</div>
        <div class="manual-title">MSAFIRI GLOBAL MEDIA</div>
        <div class="manual-subtitle">Connect beyond — Media V0.0.1</div>
      </div>

      <div class="manual-section">
        <h4>About MSAFIRI</h4>
        <p>MSAFIRI GLOBAL MEDIA is a social, communication, and AI platform that connects people across the world. It was founded by <strong>MSAFIRI WILLIAM MUNGA</strong> under the company <strong>ZetroLink Technology Limited</strong>.</p>
        <p>Version: <strong>Media V0.0.1</strong></p>
      </div>

      <div class="manual-section">
        <h4>Sections of the App</h4>
        <ul>
          <li><strong>Home</strong> — See posts from people you follow, discover new content, post photos/videos/files, share stories.</li>
          <li><strong>Discovery</strong> — Access AI Council (Education, Health, Agriculture, Research), Creative Studio, Market, World Map, Channels, Communities.</li>
          <li><strong>Chats</strong> — WhatsApp-style messaging with voice notes, photos, videos, files.</li>
          <li><strong>Profile</strong> — Your personal profile — posts, followers, following, bio, avatar.</li>
        </ul>
      </div>

      <div class="manual-section">
        <h4>How to Use MSAFIRI</h4>
        <ul>
          <li><strong>Create account:</strong> Tap Register, fill name/email/password, tap Create Account.</li>
          <li><strong>Post content:</strong> Tap Create (+) on Home, write caption, choose Photo/Video/File, tap Post.</li>
          <li><strong>Share story:</strong> Tap "+ My Story" on Home, pick media, add caption, tap Post Story.</li>
          <li><strong>Chat with someone:</strong> Go to their profile, tap Message icon, type or record.</li>
          <li><strong>Explore AI:</strong> Go to Discovery → AI Council → choose an AI.</li>
        </ul>
      </div>

      <div class="manual-section">
        <h4>Support</h4>
        <p>For help, contact ZetroLink Technology Limited.</p>
      </div>

      <button class="manual-download-btn" onclick="downloadManual()">
        <svg class="icon" viewBox="0 0 24 24" style="width:20px;height:20px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Download User Manual
      </button>
    </div>
  `;

  content.appendChild(body);
  overlay.appendChild(content);
  container.appendChild(overlay);
}

window.downloadManual = function() {
  const text = `MSAFIRI GLOBAL MEDIA — USER MANUAL
Version: Media V0.0.1
Founded by: MSAFIRI WILLIAM MUNGA
Company: ZetroLink Technology Limited

SECTIONS:
1. Home — Feed, stories, search, posts
2. Discovery — AI Council, Studio, Market, World Map, Channels, Communities
3. Chats — Messaging, voice notes, media sharing
4. Profile — Personal profile, followers, posts

HOW TO USE:
- Register: Tap Register, fill details, tap Create Account
- Post: Tap Create (+), write caption, choose media, tap Post
- Story: Tap "+ My Story", pick media, tap Post Story
- Chat: Go to profile, tap Message icon
- AI: Discovery → AI Council → Choose an AI

© ZetroLink Technology Limited
`;
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'MSAFIRI-UserManual.txt';
  a.click();
  URL.revokeObjectURL(url);
  toast('Downloading manual...', 'success');
};

// ============ 3-DOTS MENU ============
function openThreeDotsMenu() {
  const items = [
    { label: 'User Manual', icon: '📖', onClick: () => openUserManual() },
    { label: 'Toggle Theme', icon: '🌓', onClick: () => toggleTheme() },
    { label: 'Version — Media V0.0.1', icon: 'ℹ️', onClick: () => toast('MSAFIRI MEDIA V0.0.1', 'info') },
    { label: 'Logout', icon: '🚪', danger: true, onClick: () => {
      if (confirm('Logout from MSAFIRI?')) logout();
    }},
  ];

  const container = $('#modalContainer');
  container.innerHTML = '';
  const overlay = el('div', { class: 'modal-overlay', onclick: (e) => { if (e.target === overlay) closeModal(); } });
  const content = el('div', { class: 'modal-content' });
  content.appendChild(el('div', { class: 'modal-handle' }));
  const h = el('div', { class: 'modal-header' });
  h.appendChild(el('h3', {}, 'Menu'));
  const cb = el('button', { class: 'btn-icon', onclick: closeModal });
  cb.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  h.appendChild(cb);
  content.appendChild(h);

  const body = el('div', { style: 'padding:8px 0;' });
  for (const it of items) {
    const row = el('div', {
      class: 'dots-menu-item' + (it.danger ? ' danger' : ''),
      onclick: () => { closeModal(); it.onClick(); }
    });
    row.appendChild(el('div', { class: 'dots-menu-icon', style: 'font-size:20px;' }, it.icon));
    row.appendChild(el('div', {}, it.label));
    body.appendChild(row);
  }
  content.appendChild(body);
  overlay.appendChild(content);
  container.appendChild(overlay);
}

// ============ NAVIGATION ============
function switchView(view) {
  CURRENT_VIEW = view;
  $$('.nav-item').forEach(n => {
    n.classList.toggle('active', n.dataset.view === view);
  });
}

function handleNav(view) {
  if (view === 'home') loadFeed('all');
  else if (view === 'discovery') openDiscovery();
  else if (view === 'chats') openChats();
  else if (view === 'profile') {
    if (CURRENT_USER) openProfile(CURRENT_USER.id);
  }
}

// ============ INIT ============
async function init() {
  try {
    initTheme();
    bindAuthUI();

    // Bottom nav
    $$('.nav-item').forEach(item => {
      item.addEventListener('click', () => handleNav(item.dataset.view));
    });

    // 3-dots menu
    const dotsBtn = $('#threeDotsBtn');
    if (dotsBtn) dotsBtn.addEventListener('click', openThreeDotsMenu);

    TOKEN = getSavedToken();

    if (TOKEN) {
      try {
        await loadMe();
        // Wait for splash (6 seconds total)
        const splash = $('#splashScreen');
        const splashTime = splash ? 6000 : 500;
        setTimeout(async () => {
          await startApp();
        }, splashTime);
        return;
      } catch (err) {
        console.warn('[MSAFIRI] Auto-login failed:', err.message);
        TOKEN = null;
        CURRENT_USER = null;
        localStorage.removeItem('msafiri_token');
        try { sessionStorage.removeItem('msafiri_token'); } catch(e) {}
      }
    }

    const splash = $('#splashScreen');
    const splashTime = splash ? 6000 : 500;
    setTimeout(() => showAuth(), splashTime);

  } catch (err) {
    console.error('[MSAFIRI] FATAL:', err);
    setTimeout(() => showAuth(), 500);
  }
}

// ============ KEEP ALIVE PING ============
setInterval(() => {
  if (TOKEN) {
    api('/api/me').catch(() => {});
  }
}, 5 * 60 * 1000);

// ============ VISIBILITY RESUME ============
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && TOKEN && !CURRENT_USER) {
    init();
  }
});

// ============ DOM CONTENT LOADED ============
document.addEventListener('DOMContentLoaded', init);
