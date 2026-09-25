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
