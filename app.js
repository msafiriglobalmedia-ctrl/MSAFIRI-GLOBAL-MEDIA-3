'use strict';

/* ============================================================
   MSAFIRI GLOBAL MEDIA
   Production frontend controller
   Vanilla JavaScript / FastAPI / PostgreSQL
   ============================================================ */

/* ============================================================
   SECTION A: CORE UTILITIES
   ============================================================ */

const API = Object.freeze({
  base: window.location.origin,
  auth: {
    login: '/api/auth/login',
    register: '/api/auth/register',
    me: '/api/auth/me',
    logout: '/api/auth/logout'
  },
  feed: '/api/feed',
  posts: '/api/posts',
  stories: '/api/stories',
  users: '/api/users',
  profile: '/api/profile',
  chats: '/api/chats',
  messages: '/api/messages',
  calls: '/api/calls',
  search: '/api/search',
  discovery: '/api/discovery',
  ai: '/api/ai',
  education: '/api/ai/education',
  upload: '/api/upload',
  channels: '/api/channels',
  communities: '/api/communities',
  videos: '/api/videos',
  market: '/api/market',
  worldMap: '/api/world-map',
  sessionPing: '/api/auth/ping'
});

let TOKEN = localStorage.getItem('msafiri_token') || '';
let CURRENT_USER = null;
let CURRENT_VIEW = 'home';
let CURRENT_CHAT = null;
let CURRENT_POST = null;
let CURRENT_PROFILE = null;
let CURRENT_STORY_GROUP = null;
let CURRENT_STORY_INDEX = 0;
let STORY_TIMER = null;
let STORY_VIDEO_TIMER = null;
let STORY_PAUSED = false;
let CALL_ROOM = null;
let CALL_TIMER = null;
let RINGTONE_TIMER = null;
let RINGTONE_CONTEXT = null;
let CALL_STATE = {
  active: false,
  type: null,
  otherId: null,
  name: '',
  mic: true,
  camera: true,
  speaker: true,
  answered: false
};
let CHAT_TYPING_TIMER = null;
let CHAT_RECORDING = false;
let CHAT_RECORDING_TIMER = null;
let CHAT_MEDIA_RECORDER = null;
let CHAT_MEDIA_CHUNKS = [];
let CHAT_OBJECT_URLS = [];
let LIVEKIT_SCRIPT_PROMISE = null;

const CACHE = {
  feed: new Map(),
  profiles: new Map(),
  chats: [],
  messages: new Map(),
  stories: [],
  discovery: null,
  search: new Map()
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);

  Object.entries(attrs || {}).forEach(([key, value]) => {
    if (value === null || value === undefined || value === false) return;

    if (key === 'className') {
      node.className = String(value);
    } else if (key === 'textContent') {
      node.textContent = String(value);
    } else if (key === 'htmlFor') {
      node.htmlFor = String(value);
    } else if (key === 'dataset' && typeof value === 'object') {
      Object.entries(value).forEach(([k, v]) => {
        node.dataset[k] = String(v);
      });
    } else if (key.startsWith('on') && typeof value === 'function') {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === 'style' && typeof value === 'object') {
      Object.assign(node.style, value);
    } else if (key in node && !key.startsWith('aria-')) {
      try {
        node[key] = value;
      } catch (_) {
        node.setAttribute(key, String(value));
      }
    } else {
      node.setAttribute(key, String(value));
    }
  });

  const append = child => {
    if (child === null || child === undefined || child === false) return;
    if (Array.isArray(child)) {
      child.forEach(append);
    } else if (child instanceof Node) {
      node.appendChild(child);
    } else {
      node.appendChild(document.createTextNode(String(child)));
    }
  };

  children.forEach(append);
  return node;
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function initials(name = '') {
  return String(name)
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(part => part.charAt(0).toUpperCase())
    .join('') || '?';
}

function timeAgo(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));

  if (seconds < 60) return 'now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d`;
  return date.toLocaleDateString();
}

function avatarEl(user, size = '40px') {
  const name = user?.name || user?.full_name || user?.username || 'User';
  const src = user?.avatar_url || user?.avatar || user?.profile_image;

  const wrapper = el('div', {
    className: 'avatar',
    style: {
      width: size,
      height: size,
      minWidth: size,
      borderRadius: '50%',
      overflow: 'hidden',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-3)',
      color: 'var(--text)',
      fontWeight: '700'
    }
  });

  if (src) {
    const img = el('img', {
      src,
      alt: name,
      loading: 'lazy',
      style: {
        width: '100%',
        height: '100%',
        objectFit: 'cover'
      }
    });
    img.onerror = () => {
      img.remove();
      wrapper.textContent = initials(name);
    };
    wrapper.appendChild(img);
  } else {
    wrapper.textContent = initials(name);
  }

  return wrapper;
}

function normalizeList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function absoluteUrl(url) {
  if (!url) return '';
  try {
    return new URL(url, API.base).href;
  } catch (_) {
    return String(url);
  }
}

async function api(path, opts = {}) {
  const {
    method = 'GET',
    body,
    headers = {},
    retry = true,
    timeout = 30000,
    signal
  } = opts;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  if (signal) {
    signal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  const finalHeaders = {
    Accept: 'application/json',
    ...headers
  };

  let payload = body;

  if (
    body !== undefined &&
    body !== null &&
    !(body instanceof FormData) &&
    !(body instanceof Blob)
  ) {
    finalHeaders['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  if (TOKEN) {
    finalHeaders.Authorization = `Bearer ${TOKEN}`;
  }

  try {
    const response = await fetch(absoluteUrl(path), {
      method,
      headers: finalHeaders,
      body: payload,
      credentials: 'same-origin',
      signal: controller.signal
    });

    if (response.status === 401) {
      TOKEN = '';
      localStorage.removeItem('msafiri_token');
      CURRENT_USER = null;

      if (retry && !path.includes('/auth/')) {
        showAuth();
      }

      throw new Error('Your session has expired. Please sign in again.');
    }

    const contentType = response.headers.get('content-type') || '';
    let data = null;

    if (response.status !== 204) {
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }
    }

    if (!response.ok) {
      const message =
        data?.detail ||
        data?.message ||
        data?.error ||
        (typeof data === 'string' ? data : '') ||
        `Request failed (${response.status})`;

      const error = new Error(message);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }

    if (
      retry &&
      error instanceof TypeError &&
      !String(path).includes('/auth/')
    ) {
      await new Promise(resolve => setTimeout(resolve, 700));
      return api(path, { ...opts, retry: false });
    }

    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function toast(message, type = 'info', duration = 3500) {
  let container = $('.toast-container');

  if (!container) {
    container = el('div', {
      className: 'toast-container',
      style: {
        position: 'fixed',
        right: '16px',
        bottom: '80px',
        zIndex: '10000',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }
    });
    document.body.appendChild(container);
  }

  const item = el('div', {
    className: `toast ${type}`,
    role: 'status',
    textContent: message
  });

  container.appendChild(item);

  setTimeout(() => {
    item.style.opacity = '0';
    item.style.transform = 'translateY(8px)';
    setTimeout(() => item.remove(), 250);
  }, duration);
}

function applyTheme(theme) {
  const selected = theme || localStorage.getItem('msafiri_theme') || 'dark';
  document.documentElement.dataset.theme = selected;
  document.documentElement.classList.toggle('light-theme', selected === 'light');
  document.documentElement.classList.toggle('dark-theme', selected === 'dark');
  localStorage.setItem('msafiri_theme', selected);
}

function initTheme() {
  const saved = localStorage.getItem('msafiri_theme');

  if (saved) {
    applyTheme(saved);
    return;
  }

  const prefersLight = window.matchMedia &&
    window.matchMedia('(prefers-color-scheme: light)').matches;

  applyTheme(prefersLight ? 'light' : 'dark');
}

function toggleTheme() {
  const current = localStorage.getItem('msafiri_theme') || 'dark';
  applyTheme(current === 'dark' ? 'light' : 'dark');
  toast(`Theme changed to ${current === 'dark' ? 'light' : 'dark'}.`);
}

function saveSession(token, user = null) {
  TOKEN = token || '';
  if (TOKEN) {
    localStorage.setItem('msafiri_token', TOKEN);
  } else {
    localStorage.removeItem('msafiri_token');
  }

  if (user) {
    CURRENT_USER = user;
    localStorage.setItem('msafiri_user', JSON.stringify(user));
  }
}

function getSavedToken() {
  return localStorage.getItem('msafiri_token') || '';
}

/* ============================================================
   SECTION B: AUTHENTICATION
   ============================================================ */

async function register(name, email, password, username) {
  try {
    const data = await api(API.auth.register, {
      method: 'POST',
      body: {
        name,
        email,
        password,
        username
      },
      retry: false
    });

    const token = data?.access_token || data?.token;
    const user = data?.user || data?.data?.user;

    if (token) saveSession(token, user);
    else if (user) CURRENT_USER = user;

    toast('Account created successfully.', 'success');

    if (TOKEN) {
      await loadMe();
      showApp();
      await startApp();
    } else {
      showAuth();
    }

    return data;
  } catch (error) {
    toast(error.message, 'error');
    throw error;
  }
}

async function login(email, password) {
  try {
    const data = await api(API.auth.login, {
      method: 'POST',
      body: {
        email,
        password
      },
      retry: false
    });

    const token = data?.access_token || data?.token;
    const user = data?.user || data?.data?.user;

    if (!token) {
      throw new Error('Login succeeded but no access token was returned.');
    }

    saveSession(token, user);
    await loadMe();

    toast('Welcome back.', 'success');
    showApp();
    await startApp();

    return data;
  } catch (error) {
    toast(error.message, 'error');
    throw error;
  }
}

async function logout() {
  try {
    if (TOKEN) {
      await api(API.auth.logout, {
        method: 'POST',
        timeout: 10000
      });
    }
  } catch (_) {
    /* Local logout still proceeds if server logout is unavailable. */
  }

  stopRingtone();
  hideCallScreen();

  TOKEN = '';
  CURRENT_USER = null;
  CURRENT_CHAT = null;
  CURRENT_PROFILE = null;
  localStorage.removeItem('msafiri_token');
  localStorage.removeItem('msafiri_user');

  showAuth();
  toast('You have been logged out.');
}

async function loadMe() {
  if (!TOKEN) return null;

  try {
    const data = await api(API.auth.me);
    CURRENT_USER = data?.user || data?.data || data;

    if (CURRENT_USER) {
      localStorage.setItem('msafiri_user', JSON.stringify(CURRENT_USER));
    }

    return CURRENT_USER;
  } catch (error) {
    TOKEN = '';
    localStorage.removeItem('msafiri_token');
    CURRENT_USER = null;
    throw error;
  }
}

function showAuth() {
  document.body.classList.remove('app-active');

  const auth = $('#authScreen') || $('.auth-screen') || $('[data-screen="auth"]');
  const app = $('#app') || $('.app-shell') || $('[data-app]');

  if (auth) auth.classList.remove('hidden');
  if (app) app.classList.add('hidden');

  $$('.screen').forEach(screen => {
    if (screen === auth) return;
    if (!screen.classList.contains('auth-screen')) {
      screen.classList.add('hidden');
    }
  });
}

function showApp() {
  document.body.classList.add('app-active');

  const auth = $('#authScreen') || $('.auth-screen') || $('[data-screen="auth"]');
  const app = $('#app') || $('.app-shell') || $('[data-app]');

  if (auth) auth.classList.add('hidden');
  if (app) app.classList.remove('hidden');

  $$('.bottom-nav, .app-header').forEach(node => {
    node.classList.remove('hidden');
  });
}

function bindAuthUI() {
  const loginForm = $('#loginForm') || $('[data-form="login"]');
  const registerForm = $('#registerForm') || $('[data-form="register"]');

  if (loginForm && !loginForm.dataset.bound) {
    loginForm.dataset.bound = '1';

    loginForm.addEventListener('submit', async event => {
      event.preventDefault();

      const email =
        $('[name="email"]', loginForm)?.value.trim() ||
        $('#loginEmail')?.value.trim() ||
        '';

      const password =
        $('[name="password"]', loginForm)?.value ||
        $('#loginPassword')?.value ||
        '';

      if (!email || !password) {
        toast('Enter your email and password.', 'error');
        return;
      }

      const button = $('button[type="submit"]', loginForm);
      if (button) button.disabled = true;

      try {
        await login(email, password);
      } finally {
        if (button) button.disabled = false;
      }
    });
  }

  if (registerForm && !registerForm.dataset.bound) {
    registerForm.dataset.bound = '1';

    registerForm.addEventListener('submit', async event => {
      event.preventDefault();

      const name =
        $('[name="name"]', registerForm)?.value.trim() ||
        $('#registerName')?.value.trim() ||
        '';

      const email =
        $('[name="email"]', registerForm)?.value.trim() ||
        $('#registerEmail')?.value.trim() ||
        '';

      const username =
        $('[name="username"]', registerForm)?.value.trim() ||
        $('#registerUsername')?.value.trim() ||
        '';

      const password =
        $('[name="password"]', registerForm)?.value ||
        $('#registerPassword')?.value ||
        '';

      if (!name || !email || !password) {
        toast('Complete the required registration fields.', 'error');
        return;
      }

      const button = $('button[type="submit"]', registerForm);
      if (button) button.disabled = true;

      try {
        await register(name, email, password, username);
      } finally {
        if (button) button.disabled = false;
      }
    });
  }

  $$('[data-auth-tab], .auth-tab').forEach(tab => {
    if (tab.dataset.bound) return;
    tab.dataset.bound = '1';

    tab.addEventListener('click', () => {
      const target = tab.dataset.authTab || tab.dataset.target;
      $$('[data-auth-tab], .auth-tab').forEach(item => item.classList.remove('active'));
      tab.classList.add('active');

      if (target) {
        $$('.auth-panel, [data-auth-panel]').forEach(panel => {
          panel.classList.toggle(
            'hidden',
            panel.id !== target &&
            panel.dataset.authPanel !== target
          );
        });
      }
    });
  });

  $$('[data-password-toggle], .password-toggle').forEach(button => {
    if (button.dataset.bound) return;
    button.dataset.bound = '1';

    button.addEventListener('click', () => {
      const selector = button.dataset.passwordToggle;
      const input = selector ? $(selector) : button.parentElement?.querySelector('input');

      if (!input) return;

      input.type = input.type === 'password' ? 'text' : 'password';
      button.setAttribute('aria-label', input.type === 'password' ? 'Show password' : 'Hide password');
    });
  });
}

/* ============================================================
   SECTION C: FEED & POSTS
   ============================================================ */

function makeActionBtn(icon, label, handler, active = false) {
  const button = el('button', {
    className: `btn-icon post-action ${active ? 'active' : ''}`,
    type: 'button',
    title: label,
    'aria-label': label
  });

  button.appendChild(el('span', {
    textContent: icon,
    'aria-hidden': 'true'
  }));

  if (label) {
    button.appendChild(el('span', {
      className: 'action-label',
      textContent: label
    }));
  }

  button.addEventListener('click', event => {
    event.stopPropagation();
    handler(event, button);
  });

  return button;
}

function renderPost(post) {
  const user = post.user || post.author || {};
  const name = user.name || user.full_name || user.username || 'User';
  const username = user.username ? `@${user.username}` : '';
  const caption = post.caption || post.content || '';
  const mediaUrl = post.media_url || post.image_url || post.video_url || '';
  const mediaType =
    post.media_type ||
    (post.video_url ? 'video' : post.image_url ? 'image' : '');

  const card = el('article', {
    className: 'post-card',
    dataset: {
      postId: post.id || post.post_id || ''
    }
  });

  const header = el('div', { className: 'post-header' });

  header.appendChild(avatarEl(user, '44px'));

  const identity = el('div', {
    className: 'post-author',
    style: {
      flex: '1',
      minWidth: '0'
    }
  });

  identity.appendChild(el('strong', {
    textContent: name
  }));

  identity.appendChild(el('div', {
    className: 'post-meta',
    textContent: `${username}${username ? ' · ' : ''}${timeAgo(post.created_at || post.timestamp)}`
  }));

  header.appendChild(identity);

  const menu = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '⋯',
    title: 'Post menu',
    'aria-label': 'Post menu'
  });

  menu.addEventListener('click', event => {
    event.stopPropagation();
    openPostMenu(post);
  });

  header.appendChild(menu);
  card.appendChild(header);

  if (caption) {
    card.appendChild(el('div', {
      className: 'post-caption',
      textContent: caption
    }));
  }

  if (mediaUrl) {
    const mediaWrap = el('div', {
      className: 'post-media'
    });

    if (mediaType === 'video' || /\.(mp4|webm|mov|m4v)(\?|$)/i.test(mediaUrl)) {
      const video = el('video', {
        src: absoluteUrl(mediaUrl),
        controls: true,
        playsInline: true,
        preload: 'metadata',
        style: {
          width: '100%',
          maxHeight: '600px',
          objectFit: 'cover',
          borderRadius: 'var(--radius-sm)'
        }
      });
      mediaWrap.appendChild(video);
    } else {
      const image = el('img', {
        src: absoluteUrl(mediaUrl),
        alt: caption || 'Post media',
        loading: 'lazy',
        style: {
          width: '100%',
          maxHeight: '600px',
          objectFit: 'cover',
          borderRadius: 'var(--radius-sm)'
        }
      });
      mediaWrap.appendChild(image);
    }

    card.appendChild(mediaWrap);
  }

  const actions = el('div', {
    className: 'post-actions',
    style: {
      display: 'flex',
      gap: '6px',
      alignItems: 'center',
      paddingTop: '8px'
    }
  });

  const liked = Boolean(post.liked ?? post.is_liked);
  const saved = Boolean(post.saved ?? post.is_saved);
  const reshared = Boolean(post.reshared ?? post.is_reshared);

  actions.appendChild(makeActionBtn(
    liked ? '♥' : '♡',
    String(post.likes_count ?? post.like_count ?? ''),
    () => toggleLike(post.id || post.post_id),
    liked
  ));

  actions.appendChild(makeActionBtn(
    '◯',
    String(post.comments_count ?? post.comment_count ?? ''),
    () => openComments(post)
  ));

  actions.appendChild(makeActionBtn(
    reshared ? '↻' : '⟳',
    String(post.reshares_count ?? post.reshare_count ?? ''),
    () => toggleReshare(post.id || post.post_id),
    reshared
  ));

  actions.appendChild(makeActionBtn(
    saved ? '★' : '☆',
    '',
    () => toggleSave(post.id || post.post_id),
    saved
  ));

  card.appendChild(actions);

  return card;
}

async function toggleLike(postId) {
  if (!postId) return;

  try {
    const data = await api(`${API.posts}/${encodeURIComponent(postId)}/like`, {
      method: 'POST'
    });

    updatePostCard(postId, data);
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function toggleSave(postId) {
  if (!postId) return;

  try {
    const data = await api(`${API.posts}/${encodeURIComponent(postId)}/save`, {
      method: 'POST'
    });

    updatePostCard(postId, data);
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function toggleReshare(postId) {
  if (!postId) return;

  try {
    const data = await api(`${API.posts}/${encodeURIComponent(postId)}/reshare`, {
      method: 'POST'
    });

    updatePostCard(postId, data);
  } catch (error) {
    toast(error.message, 'error');
  }
}

function updatePostCard(postId, patch = {}) {
  const card = $(`.post-card[data-post-id="${CSS.escape(String(postId))}"]`);
  if (!card) return;

  const cached = CACHE.feed.get(CURRENT_VIEW) || [];
  const index = cached.findIndex(item =>
    String(item.id || item.post_id) === String(postId)
  );

  if (index >= 0) {
    cached[index] = {
      ...cached[index],
      ...patch
    };
  }

  if (
    patch.liked !== undefined ||
    patch.is_liked !== undefined ||
    patch.likes_count !== undefined ||
    patch.like_count !== undefined ||
    patch.saved !== undefined ||
    patch.is_saved !== undefined ||
    patch.reshared !== undefined ||
    patch.is_reshared !== undefined
  ) {
    const newPost = index >= 0 ? cached[index] : {
      id: postId,
      ...patch
    };

    const replacement = renderPost(newPost);
    card.replaceWith(replacement);
  }
}

function openPostMenu(post) {
  openSheet('Post options', [
    {
      label: 'Save post',
      action: async () => {
        await toggleSave(post.id || post.post_id);
        closeModal();
      }
    },
    {
      label: 'Share post',
      action: async () => {
        const url = `${window.location.origin}/post/${post.id || post.post_id}`;

        try {
          if (navigator.share) {
            await navigator.share({
              title: 'MSAFIRI GLOBAL MEDIA',
              text: post.caption || 'Check out this post.',
              url
            });
          } else {
            await navigator.clipboard.writeText(url);
            toast('Post link copied.');
          }
        } catch (_) {
          /* User cancelled native share. */
        }

        closeModal();
      }
    },
    {
      label: 'Report post',
      danger: true,
      action: async () => {
        try {
          await api(`${API.posts}/${encodeURIComponent(post.id || post.post_id)}/report`, {
            method: 'POST'
          });
          toast('Post reported.', 'success');
          closeModal();
        } catch (error) {
          toast(error.message, 'error');
        }
      }
    }
  ]);
}

function openSheet(title, items = []) {
  closeModal();

  const overlay = el('div', {
    className: 'modal-overlay',
    role: 'dialog',
    'aria-modal': 'true'
  });

  const content = el('div', {
    className: 'modal-content'
  });

  const header = el('div', {
    className: 'modal-header'
  });

  header.appendChild(el('h3', {
    textContent: title
  }));

  const close = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '×',
    'aria-label': 'Close'
  });

  close.addEventListener('click', closeModal);
  header.appendChild(close);

  content.appendChild(header);

  const body = el('div', {
    className: 'modal-body'
  });

  items.forEach(item => {
    const button = el('button', {
      className: `dots-menu-item ${item.danger ? 'danger' : ''}`,
      type: 'button',
      textContent: item.label
    });

    button.addEventListener('click', async () => {
      if (typeof item.action === 'function') {
        await item.action();
      }
    });

    body.appendChild(button);
  });

  content.appendChild(body);
  overlay.appendChild(content);

  overlay.addEventListener('click', event => {
    if (event.target === overlay) closeModal();
  });

  document.body.appendChild(overlay);
  return overlay;
}

function closeModal() {
  $$('.modal-overlay').forEach(node => node.remove());
}

async function loadFeed(feedType = 'for-you') {
  const key = feedType || 'for-you';

  try {
    const data = await api(`${API.feed}?type=${encodeURIComponent(key)}`);
    const posts = normalizeList(data);

    CACHE.feed.set(key, posts);
    return posts;
  } catch (error) {
    toast(error.message, 'error');
    return CACHE.feed.get(key) || [];
  }
}

function renderFeed(feedType = 'for-you', posts = null) {
  const main =
    $('.app-main') ||
    $('#mainContent') ||
    $('#homeScreen') ||
    $('[data-main]');

  if (!main) return;

  const list = posts || CACHE.feed.get(feedType) || [];

  main.replaceChildren();

  const search = el('div', {
    className: 'home-search'
  });

  const searchInput = el('input', {
    className: 'home-search-input',
    type: 'search',
    placeholder: 'Search MSAFIRI GLOBAL MEDIA',
    autocomplete: 'off'
  });

  searchInput.addEventListener('keydown', event => {
    if (event.key === 'Enter' && searchInput.value.trim()) {
      openSearchWithQuery(searchInput.value.trim());
    }
  });

  search.appendChild(searchInput);
  main.appendChild(search);

  const tabs = el('div', {
    className: 'feed-tabs'
  });

  ['for-you', 'following'].forEach(type => {
    const tab = el('button', {
      className: `feed-tab ${feedType === type ? 'active' : ''}`,
      type: 'button',
      textContent: type === 'for-you' ? 'For You' : 'Following'
    });

    tab.addEventListener('click', async () => {
      if (CURRENT_VIEW !== 'home') return;
      const data = await loadFeed(type);
      renderFeed(type, data);
    });

    tabs.appendChild(tab);
  });

  main.appendChild(tabs);

  const storiesBar = el('div', {
    className: 'stories-bar'
  });

  main.appendChild(storiesBar);
  loadStories(storiesBar);

  const feedContainer = el('div', {
    className: 'feed-container'
  });

  if (!list.length) {
    feedContainer.appendChild(el('div', {
      className: 'empty-state',
      textContent: 'No posts to show yet.'
    }));
  } else {
    list.forEach(post => {
      feedContainer.appendChild(renderPost(post));
    });
  }

  main.appendChild(feedContainer);
}

async function startApp() {
  showApp();

  if (!CURRENT_USER && TOKEN) {
    try {
      await loadMe();
    } catch (_) {
      showAuth();
      return;
    }
  }

  await loadFeed('for-you');
  renderFeed('for-you');

  if (!document.title || document.title === 'Vite App') {
    document.title = 'MSAFIRI GLOBAL MEDIA';
  }
}

/* ============================================================
   SECTION D: POST CREATION & COMMENTS
   ============================================================ */

function openCreatePost() {
  closeModal();

  const overlay = el('div', {
    className: 'modal-overlay',
    role: 'dialog',
    'aria-modal': 'true'
  });

  const content = el('div', {
    className: 'modal-content'
  });

  const header = el('div', {
    className: 'modal-header'
  });

  header.appendChild(el('h3', {
    textContent: 'Create post'
  }));

  const close = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '×',
    'aria-label': 'Close'
  });

  close.addEventListener('click', closeModal);
  header.appendChild(close);
  content.appendChild(header);

  const body = el('div', {
    className: 'modal-body'
  });

  const caption = el('textarea', {
    placeholder: 'What is happening?',
    rows: '5',
    style: {
      width: '100%',
      resize: 'vertical'
    }
  });

  const fileInput = el('input', {
    type: 'file',
    accept: 'image/*,video/*,.pdf,.doc,.docx,.txt',
    hidden: true
  });

  const selected = el('div', {
    className: 'selected-file',
    textContent: 'No media selected.'
  });

  let selectedFile = null;

  fileInput.addEventListener('change', () => {
    selectedFile = fileInput.files?.[0] || null;
    selected.textContent = selectedFile
      ? selectedFile.name
      : 'No media selected.';
  });

  const actions = el('div', {
    className: 'create-media-actions'
  });

  [
    ['Photo', 'image/*'],
    ['Video', 'video/*'],
    ['File', '*/*']
  ].forEach(([label, accept]) => {
    const button = el('button', {
      className: 'btn btn-secondary',
      type: 'button',
      textContent: label
    });

    button.addEventListener('click', () => {
      fileInput.accept = accept;
      fileInput.click();
    });

    actions.appendChild(button);
  });

  const submit = el('button', {
    className: 'btn btn-primary',
    type: 'button',
    textContent: 'Post'
  });

  submit.addEventListener('click', async () => {
    submit.disabled = true;

    try {
      let mediaUrl = '';

      if (selectedFile) {
        const form = new FormData();
        form.append('file', selectedFile);

        const uploaded = await api(API.upload, {
          method: 'POST',
          body: form
        });

        mediaUrl =
          uploaded?.url ||
          uploaded?.file_url ||
          uploaded?.media_url ||
          '';
      }

      const payload = {
        caption: caption.value.trim(),
        media_url: mediaUrl,
        media_type: selectedFile
          ? selectedFile.type.startsWith('video')
            ? 'video'
            : selectedFile.type.startsWith('image')
              ? 'image'
              : 'file'
          : null
      };

      await api(API.posts, {
        method: 'POST',
        body: payload
      });

      toast('Post published.', 'success');
      closeModal();

      const data = await loadFeed(CURRENT_VIEW === 'following' ? 'following' : 'for-you');
      renderFeed(CURRENT_VIEW === 'following' ? 'following' : 'for-you', data);
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      submit.disabled = false;
    }
  });

  body.append(
    caption,
    fileInput,
    selected,
    actions,
    submit
  );

  content.appendChild(body);
  overlay.appendChild(content);

  overlay.addEventListener('click', event => {
    if (event.target === overlay) closeModal();
  });

  document.body.appendChild(overlay);
}

async function openComments(post) {
  closeModal();

  const overlay = el('div', {
    className: 'modal-overlay'
  });

  const content = el('div', {
    className: 'modal-content'
  });

  const header = el('div', {
    className: 'modal-header'
  });

  header.appendChild(el('h3', {
    textContent: 'Comments'
  }));

  const close = el('button', {
    className: 'btn-icon',
    textContent: '×',
    type: 'button'
  });

  close.addEventListener('click', closeModal);
  header.appendChild(close);
  content.appendChild(header);

  const body = el('div', {
    className: 'modal-body'
  });

  const list = el('div', {
    className: 'comments-list'
  });

  const loader = el('div', {
    className: 'loader',
    textContent: 'Loading comments...'
  });

  list.appendChild(loader);
  body.appendChild(list);

  const composer = el('div', {
    className: 'comment-composer'
  });

  const input = el('input', {
    type: 'text',
    placeholder: 'Write a comment...',
    autocomplete: 'off'
  });

  const send = el('button', {
    className: 'btn btn-primary',
    type: 'button',
    textContent: 'Send'
  });

  send.addEventListener('click', async () => {
    const text = input.value.trim();
    if (!text) return;

    send.disabled = true;

    try {
      const comment = await api(
        `${API.posts}/${encodeURIComponent(post.id || post.post_id)}/comments`,
        {
          method: 'POST',
          body: { content: text }
        }
      );

      input.value = '';
      renderSingleComment(comment?.comment || comment, list);
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      send.disabled = false;
    }
  });

  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') send.click();
  });

  composer.append(input, send);
  body.appendChild(composer);

  content.appendChild(body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);

  try {
    const data = await api(
      `${API.posts}/${encodeURIComponent(post.id || post.post_id)}/comments`
    );

    list.replaceChildren();
    normalizeList(data).forEach(comment => renderSingleComment(comment, list));
  } catch (error) {
    loader.textContent = error.message;
  }
}

function renderSingleComment(c, list) {
  if (!c || !list) return;

  const user = c.user || c.author || {};
  const row = el('div', {
    className: 'comment-item'
  });

  row.appendChild(avatarEl(user, '34px'));

  const content = el('div', {
    className: 'comment-content'
  });

  content.appendChild(el('strong', {
    textContent: user.name || user.username || 'User'
  }));

  content.appendChild(el('p', {
    textContent: c.content || c.text || ''
  }));

  content.appendChild(el('small', {
    textContent: timeAgo(c.created_at || c.timestamp)
  }));

  row.appendChild(content);
  list.appendChild(row);
}

/* ============================================================
   SECTION E: PROFILE
   ============================================================ */

async function openProfile(userId) {
  const id = userId || CURRENT_USER?.id || CURRENT_USER?.user_id;
  if (!id) return;

  switchView('profile');

  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren();

  main.appendChild(el('div', {
    className: 'loader',
    textContent: 'Loading profile...'
  }));

  try {
    let profile = CACHE.profiles.get(String(id));

    if (!profile) {
      const data = await api(`${API.users}/${encodeURIComponent(id)}`);
      profile = data?.user || data?.profile || data;
      CACHE.profiles.set(String(id), profile);
    }

    CURRENT_PROFILE = profile;

    const posts = normalizeList(
      await api(`${API.users}/${encodeURIComponent(id)}/posts`)
    );

    main.replaceChildren();

    const cover = el('div', {
      className: 'profile-cover',
      style: {
        minHeight: '150px',
        background: `var(--bg-3)`
      }
    });

    if (profile.cover_url || profile.cover) {
      cover.style.backgroundImage = `url("${absoluteUrl(profile.cover_url || profile.cover)}")`;
      cover.style.backgroundSize = 'cover';
      cover.style.backgroundPosition = 'center';
    }

    main.appendChild(cover);

    const profileHead = el('div', {
      className: 'profile-header'
    });

    profileHead.appendChild(avatarEl(profile, '88px'));

    const identity = el('div', {
      className: 'profile-identity'
    });

    identity.appendChild(el('h2', {
      textContent: profile.name || profile.username || 'User'
    }));

    if (profile.username) {
      identity.appendChild(el('div', {
        textContent: `@${profile.username}`
      }));
    }

    if (profile.bio) {
      identity.appendChild(el('p', {
        textContent: profile.bio
      }));
    }

    profileHead.appendChild(identity);

    const isMe = String(id) === String(CURRENT_USER?.id || CURRENT_USER?.user_id);

    if (!isMe) {
      const follow = el('button', {
        className: `btn ${profile.is_following ? 'btn-secondary' : 'btn-primary'}`,
        type: 'button',
        textContent: profile.is_following ? 'Following' : 'Follow'
      });

      follow.addEventListener('click', async () => {
        try {
          const data = await api(`${API.users}/${encodeURIComponent(id)}/follow`, {
            method: 'POST'
          });

          profile.is_following =
            data?.is_following ?? !profile.is_following;

          follow.textContent = profile.is_following ? 'Following' : 'Follow';
          follow.className =
            `btn ${profile.is_following ? 'btn-secondary' : 'btn-primary'}`;
        } catch (error) {
          toast(error.message, 'error');
        }
      });

      profileHead.appendChild(follow);
    } else {
      const edit = el('button', {
        className: 'btn btn-secondary',
        type: 'button',
        textContent: 'Edit profile'
      });

      edit.addEventListener('click', openEditProfile);
      profileHead.appendChild(edit);
    }

    main.appendChild(profileHead);

    const stats = el('div', {
      className: 'profile-stats'
    });

    [
      ['Posts', profile.posts_count ?? posts.length],
      ['Followers', profile.followers_count ?? 0],
      ['Following', profile.following_count ?? 0]
    ].forEach(([label, value]) => {
      const stat = el('div', { className: 'profile-stat' });
      stat.append(
        el('strong', { textContent: String(value) }),
        el('span', { textContent: label })
      );
      stats.appendChild(stat);
    });

    main.appendChild(stats);

    const postGrid = el('div', {
      className: 'profile-posts'
    });

    posts.forEach(post => postGrid.appendChild(renderPost(post)));
    main.appendChild(postGrid);
  } catch (error) {
    main.replaceChildren(el('div', {
      className: 'empty-state',
      textContent: error.message
    }));
  }
}

function openEditProfile() {
  if (!CURRENT_USER) return;

  closeModal();

  const overlay = el('div', {
    className: 'modal-overlay'
  });

  const content = el('div', {
    className: 'modal-content'
  });

  const header = el('div', {
    className: 'modal-header'
  });

  header.appendChild(el('h3', {
    textContent: 'Edit profile'
  }));

  const close = el('button', {
    className: 'btn-icon',
    textContent: '×',
    type: 'button'
  });

  close.addEventListener('click', closeModal);
  header.appendChild(close);
  content.appendChild(header);

  const body = el('div', {
    className: 'modal-body'
  });

  const name = el('input', {
    type: 'text',
    value: CURRENT_USER.name || '',
    placeholder: 'Name'
  });

  const username = el('input', {
    type: 'text',
    value: CURRENT_USER.username || '',
    placeholder: 'Username'
  });

  const bio = el('textarea', {
    placeholder: 'Bio',
    rows: '4'
  });
  bio.value = CURRENT_USER.bio || '';

  const avatarInput = el('input', {
    type: 'file',
    accept: 'image/*'
  });

  const save = el('button', {
    className: 'btn btn-primary',
    type: 'button',
    textContent: 'Save changes'
  });

  save.addEventListener('click', async () => {
    save.disabled = true;

    try {
      let avatarUrl = CURRENT_USER.avatar_url || CURRENT_USER.avatar || '';

      if (avatarInput.files?.[0]) {
        const form = new FormData();
        form.append('file', avatarInput.files[0]);

        const uploaded = await api(API.upload, {
          method: 'POST',
          body: form
        });

        avatarUrl =
          uploaded?.url ||
          uploaded?.file_url ||
          uploaded?.media_url ||
          avatarUrl;
      }

      const updated = await api(API.profile, {
        method: 'PATCH',
        body: {
          name: name.value.trim(),
          username: username.value.trim(),
          bio: bio.value.trim(),
          avatar_url: avatarUrl
        }
      });

      CURRENT_USER = updated?.user || updated;
      localStorage.setItem('msafiri_user', JSON.stringify(CURRENT_USER));

      toast('Profile updated.', 'success');
      closeModal();
      await openProfile(CURRENT_USER.id || CURRENT_USER.user_id);
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      save.disabled = false;
    }
  });

  body.append(
    avatarEl(CURRENT_USER, '72px'),
    name,
    username,
    bio,
    avatarInput,
    save
  );

  content.appendChild(body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);
}

/* ============================================================
   SECTION F: CHAT
   ============================================================ */

async function openChats() {
  switchView('chats');

  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren();

  const header = el('div', {
    className: 'chat-header'
  });

  header.appendChild(el('h2', {
    textContent: 'Chats'
  }));

  const newChat = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '+',
    title: 'New chat'
  });

  newChat.addEventListener('click', openSearch);
  header.appendChild(newChat);

  main.appendChild(header);

  const list = el('div', {
    className: 'chat-list'
  });

  main.appendChild(list);
  await renderChatList(list);
}

async function renderChatList(target = null) {
  const list = target || $('.chat-list');
  if (!list) return;

  list.replaceChildren(
    el('div', {
      className: 'loader',
      textContent: 'Loading chats...'
    })
  );

  try {
    const data = await api(API.chats);
    CACHE.chats = normalizeList(data);

    list.replaceChildren();

    if (!CACHE.chats.length) {
      list.appendChild(el('div', {
        className: 'empty-state',
        textContent: 'No conversations yet.'
      }));
      return;
    }

    CACHE.chats.forEach(chat => {
      const user = chat.user || chat.other_user || chat.recipient || {};
      const id = user.id || user.user_id || chat.other_id;

      const item = el('button', {
        className: 'chat-list-item',
        type: 'button'
      });

      item.appendChild(avatarEl(user, '48px'));

      const info = el('div', {
        style: {
          flex: '1',
          minWidth: '0',
          textAlign: 'left'
        }
      });

      info.appendChild(el('strong', {
        textContent: user.name || user.username || 'User'
      }));

      info.appendChild(el('div', {
        className: 'chat-preview',
        textContent:
          chat.last_message?.content ||
          chat.last_message ||
          'Start a conversation'
      }));

      item.appendChild(info);

      item.appendChild(el('time', {
        textContent: timeAgo(chat.last_message?.created_at || chat.updated_at)
      }));

      item.addEventListener('click', () => {
        openChat(
          id,
          user.name || user.username || 'User',
          user.avatar_url || user.avatar || '',
          user.username || ''
        );
      });

      list.appendChild(item);
    });
  } catch (error) {
    list.replaceChildren(el('div', {
      className: 'empty-state',
      textContent: error.message
    }));
  }
}

async function openChat(otherId, name = 'User', avatar = '', username = '') {
  if (!otherId) return;

  CURRENT_CHAT = {
    otherId,
    name,
    avatar,
    username
  };

  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren();

  const header = el('div', {
    className: 'chat-header'
  });

  const back = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '‹',
    title: 'Back'
  });

  back.addEventListener('click', openChats);

  const user = {
    name,
    username,
    avatar_url: avatar
  };

  header.appendChild(back);
  header.appendChild(avatarEl(user, '42px'));

  const identity = el('div', {
    style: {
      flex: '1',
      minWidth: '0'
    }
  });

  identity.appendChild(el('strong', {
    textContent: name
  }));

  identity.appendChild(el('small', {
    textContent: 'online'
  }));

  header.appendChild(identity);

  const voice = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '☎',
    title: 'Voice call'
  });

  voice.addEventListener('click', () => startCall(otherId, 'audio', name));

  const video = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '▣',
    title: 'Video call'
  });

  video.addEventListener('click', () => startCall(otherId, 'video', name));

  const menu = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '⋮',
    title: 'Chat menu'
  });

  menu.addEventListener('click', openChatMenu);

  header.append(voice, video, menu);
  main.appendChild(header);

  const messages = el('div', {
    className: 'chat-messages',
    style: {
      background: 'var(--bg-2)'
    }
  });

  main.appendChild(messages);

  const typing = el('div', {
    className: 'typing-indicator hidden',
    textContent: 'typing...'
  });

  const recording = el('div', {
    className: 'recording-indicator hidden',
    textContent: 'recording audio...'
  });

  const composer = el('div', {
    className: 'chat-composer'
  });

  const attach = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '+',
    title: 'Attach'
  });

  attach.addEventListener('click', () => openChatAttach(otherId));

  const input = el('input', {
    type: 'text',
    placeholder: 'Type text here',
    autocomplete: 'off'
  });

  const send = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '➤',
    title: 'Send'
  });

  const mic = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '🎙',
    title: 'Record voice note'
  });

  const updateComposer = () => {
    const hasText = Boolean(input.value.trim());
    send.classList.toggle('hidden', !hasText);
    mic.classList.toggle('hidden', hasText);
  };

  input.addEventListener('input', () => {
    updateComposer();
    sendTyping(otherId);
  });

  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send.click();
    }
  });

  send.addEventListener('click', async () => {
    const content = input.value.trim();
    if (!content) return;

    send.disabled = true;

    try {
      const data = await api(API.messages, {
        method: 'POST',
        body: {
          recipient_id: otherId,
          content,
          type: 'text'
        }
      });

      input.value = '';
      updateComposer();

      const message = data?.message || data;
      appendMessage(message, messages);
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      send.disabled = false;
    }
  });

  let pressTimer = null;

  mic.addEventListener('mousedown', () => {
    pressTimer = setTimeout(() => {
      recordVoice(otherId, recording, mic);
    }, 450);
  });

  mic.addEventListener('mouseup', () => {
    clearTimeout(pressTimer);
  });

  mic.addEventListener('mouseleave', () => {
    clearTimeout(pressTimer);
  });

  mic.addEventListener('touchstart', event => {
    event.preventDefault();
    pressTimer = setTimeout(() => {
      recordVoice(otherId, recording, mic);
    }, 450);
  }, { passive: false });

  mic.addEventListener('touchend', event => {
    event.preventDefault();
    clearTimeout(pressTimer);
  }, { passive: false });

  composer.append(attach, input, send, mic);
  main.append(typing, recording, composer);

  try {
    const data = await api(
      `${API.chats}/${encodeURIComponent(otherId)}/messages`
    );

    const messagesData = normalizeList(data);
    CACHE.messages.set(String(otherId), messagesData);

    messages.replaceChildren();

    messagesData.forEach(message => appendMessage(message, messages));
    messages.scrollTop = messages.scrollHeight;
  } catch (error) {
    messages.replaceChildren(el('div', {
      className: 'empty-state',
      textContent: error.message
    }));
  }
}

function appendMessage(m, container = null) {
  const target =
    container ||
    $('.chat-messages');

  if (!target || !m) return;

  const mine = String(
    m.sender_id ||
    m.sender?.id ||
    m.user_id ||
    ''
  ) === String(CURRENT_USER?.id || CURRENT_USER?.user_id || '');

  const bubble = el('div', {
    className: `chat-bubble ${mine ? 'mine' : 'theirs'}`
  });

  const type = m.type || m.message_type || 'text';
  const content = m.content || m.text || '';
  const mediaUrl = m.media_url || m.file_url || m.url || '';

  if (type === 'image' && mediaUrl) {
    bubble.appendChild(el('img', {
      src: absoluteUrl(mediaUrl),
      alt: 'Shared image',
      loading: 'lazy',
      style: {
        maxWidth: '100%',
        borderRadius: '8px'
      }
    }));
  } else if (type === 'video' && mediaUrl) {
    bubble.appendChild(el('video', {
      src: absoluteUrl(mediaUrl),
      controls: true,
      playsInline: true,
      style: {
        maxWidth: '100%',
        borderRadius: '8px'
      }
    }));
  } else if (type === 'audio' || type === 'voice') {
    if (mediaUrl) {
      bubble.appendChild(el('audio', {
        src: absoluteUrl(mediaUrl),
        controls: true
      }));
    }
  } else if (type === 'file' && mediaUrl) {
    const link = el('a', {
      href: absoluteUrl(mediaUrl),
      target: '_blank',
      rel: 'noopener noreferrer',
      textContent: m.file_name || 'Download file'
    });
    bubble.appendChild(link);
  } else {
    bubble.appendChild(el('div', {
      textContent: content
    }));
  }

  bubble.appendChild(el('small', {
    textContent: timeAgo(m.created_at || m.timestamp)
  }));

  target.appendChild(bubble);
  target.scrollTop = target.scrollHeight;
}

function sendTyping(otherId) {
  clearTimeout(CHAT_TYPING_TIMER);

  if (!otherId) return;

  api(`${API.chats}/${encodeURIComponent(otherId)}/typing`, {
    method: 'POST',
    body: { typing: true },
    timeout: 5000,
    retry: false
  }).catch(() => {});

  CHAT_TYPING_TIMER = setTimeout(() => {
    api(`${API.chats}/${encodeURIComponent(otherId)}/typing`, {
      method: 'POST',
      body: { typing: false },
      timeout: 5000,
      retry: false
    }).catch(() => {});
  }, 1500);
}

function openChatAttach(otherId) {
  openSheet('Send attachment', [
    {
      label: 'Photo',
      action: () => pickChatFile(otherId, 'image/*')
    },
    {
      label: 'Video',
      action: () => pickChatFile(otherId, 'video/*')
    },
    {
      label: 'Document',
      action: () => pickChatFile(otherId, '*/*')
    },
    {
      label: 'Voice note',
      action: () => recordVoice(otherId)
    }
  ]);
}

function pickChatFile(otherId, accept = '*/*') {
  closeModal();

  const input = el('input', {
    type: 'file',
    accept
  });

  input.addEventListener('change', async () => {
    const file = input.files?.[0];
    if (!file) return;

    try {
      const form = new FormData();
      form.append('file', file);

      const uploaded = await api(API.upload, {
        method: 'POST',
        body: form
      });

      const url =
        uploaded?.url ||
        uploaded?.file_url ||
        uploaded?.media_url;

      if (!url) throw new Error('Upload did not return a file URL.');

      const type = file.type.startsWith('image')
        ? 'image'
        : file.type.startsWith('video')
          ? 'video'
          : 'file';

      const data = await api(API.messages, {
        method: 'POST',
        body: {
          recipient_id: otherId,
          type,
          media_url: url,
          file_name: file.name
        }
      });

      appendMessage(data?.message || data);
    } catch (error) {
      toast(error.message, 'error');
    }
  });

  document.body.appendChild(input);
  input.click();

  setTimeout(() => input.remove(), 1000);
}

async function recordVoice(otherId, recordingNode = null, micButton = null) {
  if (CHAT_RECORDING) {
    stopVoiceRecording();
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    toast('Voice recording is not supported on this device.', 'error');
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true
    });

    CHAT_MEDIA_CHUNKS = [];
    CHAT_MEDIA_RECORDER = new MediaRecorder(stream);
    CHAT_RECORDING = true;

    if (recordingNode) recordingNode.classList.remove('hidden');
    if (micButton) {
      micButton.classList.add('recording');
      micButton.textContent = '■';
    }

    CHAT_MEDIA_RECORDER.addEventListener('dataavailable', event => {
      if (event.data.size > 0) CHAT_MEDIA_CHUNKS.push(event.data);
    });

    CHAT_MEDIA_RECORDER.addEventListener('stop', async () => {
      stream.getTracks().forEach(track => track.stop());

      const blob = new Blob(CHAT_MEDIA_CHUNKS, {
        type: CHAT_MEDIA_RECORDER.mimeType || 'audio/webm'
      });

      try {
        const form = new FormData();
        form.append('file', blob, `voice-${Date.now()}.webm`);

        const uploaded = await api(API.upload, {
          method: 'POST',
          body: form
        });

        const url =
          uploaded?.url ||
          uploaded?.file_url ||
          uploaded?.media_url;

        if (!url) throw new Error('Voice upload failed.');

        const data = await api(API.messages, {
          method: 'POST',
          body: {
            recipient_id: otherId,
            type: 'voice',
            media_url: url
          }
        });

        appendMessage(data?.message || data);
      } catch (error) {
        toast(error.message, 'error');
      }
    });

    CHAT_MEDIA_RECORDER.start();

    clearTimeout(CHAT_RECORDING_TIMER);
    CHAT_RECORDING_TIMER = setTimeout(() => {
      stopVoiceRecording();
    }, 60000);
  } catch (error) {
    toast(error.message || 'Microphone permission was denied.', 'error');
  }
}

function stopVoiceRecording() {
  clearTimeout(CHAT_RECORDING_TIMER);

  if (CHAT_MEDIA_RECORDER && CHAT_MEDIA_RECORDER.state !== 'inactive') {
    CHAT_MEDIA_RECORDER.stop();
  }

  CHAT_RECORDING = false;

  $('.recording-indicator')?.classList.add('hidden');

  const mic = $('.chat-composer .btn-icon:last-child');
  if (mic) {
    mic.classList.remove('recording');
    mic.textContent = '🎙';
  }
}

function openChatMenu() {
  openSheet('Chat options', [
    {
      label: 'Change wallpaper',
      action: pickWallpaper
    },
    {
      label: 'View profile',
      action: () => {
        if (CURRENT_CHAT?.otherId) openProfile(CURRENT_CHAT.otherId);
      }
    },
    {
      label: 'Clear conversation',
      danger: true,
      action: async () => {
        if (!CURRENT_CHAT?.otherId) return;

        try {
          await api(
            `${API.chats}/${encodeURIComponent(CURRENT_CHAT.otherId)}/clear`,
            { method: 'DELETE' }
          );
          toast('Conversation cleared.', 'success');
          closeModal();
          openChat(
            CURRENT_CHAT.otherId,
            CURRENT_CHAT.name,
            CURRENT_CHAT.avatar,
            CURRENT_CHAT.username
          );
        } catch (error) {
          toast(error.message, 'error');
        }
      }
    }
  ]);
}

function pickWallpaper() {
  closeModal();

  const input = el('input', {
    type: 'file',
    accept: 'image/*'
  });

  input.addEventListener('change', () => {
    const file = input.files?.[0];
    if (!file) return;

    const oldUrl = CHAT_OBJECT_URLS.pop();
    if (oldUrl) URL.revokeObjectURL(oldUrl);

    const url = URL.createObjectURL(file);
    CHAT_OBJECT_URLS.push(url);

    const messages = $('.chat-messages');

    if (messages) {
      messages.style.backgroundImage = `url("${url}")`;
      messages.style.backgroundSize = 'cover';
      messages.style.backgroundAttachment = 'fixed';
    }
  });

  document.body.appendChild(input);
  input.click();
  setTimeout(() => input.remove(), 1000);
}

async function openChatWith(user) {
  if (!user) return;

  await openChat(
    user.id || user.user_id,
    user.name || user.username || 'User',
    user.avatar_url || user.avatar || '',
    user.username || ''
  );
}

/* ============================================================
   SECTION G: STORIES
   ============================================================ */

async function loadStories(storiesBar) {
  if (!storiesBar) return;

  storiesBar.replaceChildren();

  const mine = el('button', {
    className: 'story-item',
    type: 'button'
  });

  mine.appendChild(el('div', {
    className: 'story-ring',
    textContent: '+'
  }));

  mine.appendChild(el('small', {
    textContent: 'My Story'
  }));

  mine.addEventListener('click', openCreateStory);
  storiesBar.appendChild(mine);

  try {
    const data = await api(API.stories);
    CACHE.stories = normalizeList(data);

    const groups = new Map();

    CACHE.stories.forEach(story => {
      const user = story.user || story.author || {};
      const id = user.id || user.user_id || story.user_id;

      if (!groups.has(String(id))) {
        groups.set(String(id), {
          user,
          stories: []
        });
      }

      groups.get(String(id)).stories.push(story);
    });

    groups.forEach(group => {
      const user = group.user || {};

      const item = el('button', {
        className: 'story-item',
        type: 'button'
      });

      const ring = el('div', {
        className: 'story-ring'
      });

      ring.appendChild(avatarEl(user, '56px'));

      item.appendChild(ring);
      item.appendChild(el('small', {
        textContent: user.name || user.username || 'User'
      }));

      item.addEventListener('click', () => openStoryViewer(group));
      storiesBar.appendChild(item);
    });
  } catch (error) {
    /* Stories are optional; feed remains usable. */
  }
}

function openStoryViewer(group) {
  if (!group?.stories?.length) return;

  CURRENT_STORY_GROUP = group;
  CURRENT_STORY_INDEX = 0;
  STORY_PAUSED = false;

  closeStoryViewer();

  const viewer = el('div', {
    className: 'story-viewer',
    style: {
      position: 'fixed',
      inset: '0',
      zIndex: '9999',
      background: '#000',
      display: 'flex',
      flexDirection: 'column'
    }
  });

  const progress = el('div', {
    className: 'story-progress',
    style: {
      display: 'flex',
      gap: '4px',
      padding: '12px'
    }
  });

  group.stories.forEach(() => {
    progress.appendChild(el('div', {
      style: {
        height: '3px',
        flex: '1',
        background: 'rgba(255,255,255,.35)',
        borderRadius: '3px',
        overflow: 'hidden'
      }
    }));
  });

  viewer.appendChild(progress);

  const top = el('div', {
    className: 'story-viewer-header',
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      padding: '8px 14px',
      color: '#fff'
    }
  });

  top.appendChild(avatarEl(group.user, '40px'));

  top.appendChild(el('strong', {
    textContent: group.user?.name || group.user?.username || 'User'
  }));

  const close = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '×',
    style: {
      marginLeft: 'auto',
      color: '#fff'
    }
  });

  close.addEventListener('click', closeStoryViewer);
  top.appendChild(close);
  viewer.appendChild(top);

  const stage = el('div', {
    className: 'story-stage',
    style: {
      position: 'relative',
      flex: '1',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden'
    }
  });

  viewer.appendChild(stage);

  const left = el('button', {
    className: 'story-zone story-left',
    type: 'button',
    'aria-label': 'Previous story',
    style: {
      position: 'absolute',
      inset: '0 50% 0 0',
      zIndex: '3',
      opacity: '0',
      cursor: 'pointer'
    }
  });

  const right = el('button', {
    className: 'story-zone story-right',
    type: 'button',
    'aria-label': 'Next story',
    style: {
      position: 'absolute',
      inset: '0 0 0 50%',
      zIndex: '3',
      opacity: '0',
      cursor: 'pointer'
    }
  });

  left.addEventListener('click', previousStory);
  right.addEventListener('click', nextStory);

  const pause = () => {
    STORY_PAUSED = true;
    clearTimeout(STORY_TIMER);
    clearTimeout(STORY_VIDEO_TIMER);
  };

  const resume = () => {
    STORY_PAUSED = false;
    showStory(CURRENT_STORY_INDEX);
  };

  stage.addEventListener('mousedown', pause);
  stage.addEventListener('mouseup', resume);
  stage.addEventListener('mouseleave', resume);
  stage.addEventListener('touchstart', pause, { passive: true });
  stage.addEventListener('touchend', resume, { passive: true });

  stage.append(left, right);

  document.body.appendChild(viewer);
  viewer._stage = stage;
  viewer._progress = progress;

  showStory(0);
}

function showStory(index) {
  const viewer = $('.story-viewer');
  if (!viewer || !CURRENT_STORY_GROUP) return;

  const stories = CURRENT_STORY_GROUP.stories;

  if (index < 0) index = 0;

  if (index >= stories.length) {
    closeStoryViewer();
    return;
  }

  CURRENT_STORY_INDEX = index;

  clearTimeout(STORY_TIMER);
  clearTimeout(STORY_VIDEO_TIMER);

  const story = stories[index];
  const stage = viewer._stage;
  const progress = viewer._progress;

  stage.querySelectorAll('.story-content').forEach(node => node.remove());

  Array.from(progress.children).forEach((bar, i) => {
    bar.replaceChildren();

    if (i < index) {
      bar.style.background = '#fff';
    } else if (i > index) {
      bar.style.background = 'rgba(255,255,255,.35)';
    } else {
      const fill = el('div', {
        style: {
          width: '0%',
          height: '100%',
          background: '#fff',
          transition: 'width linear'
        }
      });
      bar.appendChild(fill);
    }
  });

  const mediaUrl =
    story.media_url ||
    story.image_url ||
    story.video_url ||
    story.url;

  const content = el('div', {
    className: 'story-content',
    style: {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexDirection: 'column'
    }
  });

  if (story.caption) {
    content.appendChild(el('div', {
      className: 'story-caption',
      textContent: story.caption,
      style: {
        color: '#fff',
        position: 'absolute',
        bottom: '30px',
        zIndex: '2',
        padding: '12px',
        textAlign: 'center'
      }
    }));
  }

  if (story.media_type === 'video' || /\.(mp4|webm|mov)(\?|$)/i.test(mediaUrl || '')) {
    const video = el('video', {
      className: 'story-media',
      src: absoluteUrl(mediaUrl),
      autoplay: true,
      controls: false,
      playsInline: true,
      style: {
        maxWidth: '100%',
        maxHeight: '100%'
      }
    });

    video.addEventListener('loadedmetadata', () => {
      const duration = Math.min(
        Math.max(video.duration || 5, 1),
        15
      );

      const bar = progress.children[index]?.firstElementChild;
      if (bar) {
        bar.style.transitionDuration = `${duration}s`;
        requestAnimationFrame(() => {
          bar.style.width = '100%';
        });
      }

      STORY_VIDEO_TIMER = setTimeout(() => {
        nextStory();
      }, duration * 1000);
    });

    video.addEventListener('ended', nextStory);
    content.appendChild(video);
  } else if (mediaUrl) {
    const image = el('img', {
      className: 'story-media',
      src: absoluteUrl(mediaUrl),
      alt: story.caption || 'Story',
      style: {
        maxWidth: '100%',
        maxHeight: '100%',
        objectFit: 'contain'
      }
    });

    content.appendChild(image);

    const bar = progress.children[index]?.firstElementChild;
    if (bar) {
      bar.style.transitionDuration = '5s';
      requestAnimationFrame(() => {
        bar.style.width = '100%';
      });
    }

    STORY_TIMER = setTimeout(nextStory, 5000);
  } else {
    content.appendChild(el('div', {
      textContent: story.caption || '',
      style: {
        color: '#fff',
        fontSize: '24px',
        padding: '30px',
        textAlign: 'center'
      }
    }));

    const bar = progress.children[index]?.firstElementChild;
    if (bar) {
      bar.style.transitionDuration = '5s';
      requestAnimationFrame(() => {
        bar.style.width = '100%';
      });
    }

    STORY_TIMER = setTimeout(nextStory, 5000);
  }

  stage.prepend(content);
}

function nextStory() {
  if (STORY_PAUSED) return;

  const next = CURRENT_STORY_INDEX + 1;

  if (next >= (CURRENT_STORY_GROUP?.stories?.length || 0)) {
    closeStoryViewer();
    return;
  }

  showStory(next);
}

function previousStory() {
  if (CURRENT_STORY_INDEX <= 0) {
    showStory(0);
    return;
  }

  showStory(CURRENT_STORY_INDEX - 1);
}

function closeStoryViewer() {
  clearTimeout(STORY_TIMER);
  clearTimeout(STORY_VIDEO_TIMER);

  $('.story-viewer')?.remove();

  CURRENT_STORY_GROUP = null;
  CURRENT_STORY_INDEX = 0;
  STORY_PAUSED = false;
}

function openCreateStory() {
  closeModal();

  const overlay = el('div', {
    className: 'modal-overlay'
  });

  const content = el('div', {
    className: 'modal-content'
  });

  const header = el('div', {
    className: 'modal-header'
  });

  header.appendChild(el('h3', {
    textContent: 'Create story'
  }));

  const close = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '×'
  });

  close.addEventListener('click', closeModal);
  header.appendChild(close);
  content.appendChild(header);

  const body = el('div', {
    className: 'modal-body'
  });

  const caption = el('textarea', {
    placeholder: 'Add a caption...',
    rows: '4'
  });

  const input = el('input', {
    type: 'file',
    accept: 'image/*,video/*',
    hidden: true
  });

  const selected = el('div', {
    textContent: 'No media selected.'
  });

  let file = null;

  input.addEventListener('change', () => {
    file = input.files?.[0] || null;
    selected.textContent = file?.name || 'No media selected.';
  });

  const photo = el('button', {
    className: 'btn btn-secondary',
    type: 'button',
    textContent: 'Photo'
  });

  photo.addEventListener('click', () => {
    input.accept = 'image/*';
    input.click();
  });

  const video = el('button', {
    className: 'btn btn-secondary',
    type: 'button',
    textContent: 'Video'
  });

  video.addEventListener('click', () => {
    input.accept = 'video/*';
    input.click();
  });

  const submit = el('button', {
    className: 'btn btn-primary',
    type: 'button',
    textContent: 'Post Story'
  });

  submit.addEventListener('click', async () => {
    if (!file && !caption.value.trim()) {
      toast('Add a photo, video, or caption.', 'error');
      return;
    }

    submit.disabled = true;

    try {
      let mediaUrl = '';

      if (file) {
        const form = new FormData();
        form.append('file', file);

        const uploaded = await api(API.upload, {
          method: 'POST',
          body: form
        });

        mediaUrl =
          uploaded?.url ||
          uploaded?.file_url ||
          uploaded?.media_url ||
          '';
      }

      await api(API.stories, {
        method: 'POST',
        body: {
          media_url: mediaUrl,
          media_type: file?.type.startsWith('video') ? 'video' : 'image',
          caption: caption.value.trim()
        }
      });

      toast('Story published.', 'success');
      closeModal();

      if (CURRENT_VIEW === 'home') {
        const type = 'for-you';
        renderFeed(type, CACHE.feed.get(type) || []);
      }
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      submit.disabled = false;
    }
  });

  body.append(
    input,
    selected,
    caption,
    photo,
    video,
    submit
  );

  content.appendChild(body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);
}

/* ============================================================
   SECTION H: LIVEKIT CALLS
   ============================================================ */

function loadLiveKit() {
  if (window.LivekitClient || window.LiveKitClient) {
    return Promise.resolve(window.LivekitClient || window.LiveKitClient);
  }

  if (LIVEKIT_SCRIPT_PROMISE) return LIVEKIT_SCRIPT_PROMISE;

  LIVEKIT_SCRIPT_PROMISE = new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-livekit-sdk]');

    if (existing) {
      existing.addEventListener('load', () => {
        resolve(window.LivekitClient || window.LiveKitClient);
      });

      existing.addEventListener('error', reject);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.umd.min.js';
    script.async = true;
    script.dataset.livekitSdk = '1';

    script.addEventListener('load', () => {
      const sdk = window.LivekitClient || window.LiveKitClient;

      if (!sdk) {
        reject(new Error('LiveKit SDK failed to initialize.'));
      } else {
        resolve(sdk);
      }
    });

    script.addEventListener('error', () => {
      reject(new Error('Unable to load LiveKit.'));
    });

    document.head.appendChild(script);
  });

  return LIVEKIT_SCRIPT_PROMISE;
}

async function startCall(otherId, callType = 'audio', name = 'User') {
  if (!otherId || CALL_STATE.active) return;

  CALL_STATE = {
    active: true,
    type: callType,
    otherId,
    name,
    mic: true,
    camera: callType === 'video',
    speaker: true,
    answered: false
  };

  showCallScreen();
  startRingtone();

  try {
    const data = await api(API.calls, {
      method: 'POST',
      body: {
        recipient_id: otherId,
        type: callType
      }
    });

    stopRingtone();

    const token = data?.token || data?.access_token;
    const url = data?.url || data?.server_url || data?.ws_url;
    const roomName = data?.room_name || data?.room || data?.roomName;

    if (!token || !url || !roomName) {
      throw new Error('The call server did not return valid LiveKit credentials.');
    }

    await connectLiveKit(token, url, roomName);

    CALL_STATE.answered = true;
    updateCallStatus('Connected');
  } catch (error) {
    stopRingtone();
    updateCallStatus('Call failed');
    toast(error.message, 'error');

    setTimeout(() => {
      if (CALL_STATE.active) endCall();
    }, 1200);
  }
}

async function connectLiveKit(token, url, roomName) {
  const sdk = await loadLiveKit();

  const Room =
    sdk.Room ||
    sdk.default?.Room;

  const RoomEvent =
    sdk.RoomEvent ||
    sdk.default?.RoomEvent;

  if (!Room || !RoomEvent) {
    throw new Error('LiveKit Room API is unavailable.');
  }

  const room = new Room({
    adaptiveStream: true,
    dynacast: true
  });

  CALL_ROOM = room;

  room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
    attachRemoteTrack(track, participant);
  });

  room.on(RoomEvent.ParticipantConnected, participant => {
    updateCallStatus(`${participant.name || 'Participant'} joined`);
  });

  room.on(RoomEvent.ParticipantDisconnected, participant => {
    updateCallStatus(`${participant.name || 'Participant'} left`);
  });

  room.on(RoomEvent.Disconnected, () => {
    if (CALL_STATE.active) {
      hideCallScreen();
      stopRingtone();
    }
  });

  room.on(RoomEvent.LocalTrackPublished, publication => {
    if (publication?.track) {
      attachLocalTrack(publication.track);
    }
  });

  await room.connect(url, token);

  try {
    await room.localParticipant.setMicrophoneEnabled(CALL_STATE.mic);

    if (CALL_STATE.type === 'video') {
      await room.localParticipant.setCameraEnabled(CALL_STATE.camera);
    }
  } catch (error) {
    toast(error.message, 'error');
  }

  if (!CALL_STATE.answered) {
    startRingtone();
  }
}

function attachRemoteTrack(track, participant) {
  const container = $('.call-remote-video');
  if (!container || !track) return;

  const element = track.attach();

  if (element instanceof HTMLVideoElement) {
    element.autoplay = true;
    element.playsInline = true;
    element.style.width = '100%';
    element.style.height = '100%';
    element.style.objectFit = 'cover';
  }

  element.dataset.participantId = participant?.identity || '';
  container.appendChild(element);
}

function attachLocalTrack(track) {
  const container = $('.call-local-video');
  if (!container || !track) return;

  container.replaceChildren();

  const element = track.attach();

  if (element instanceof HTMLVideoElement) {
    element.autoplay = true;
    element.muted = true;
    element.playsInline = true;
    element.style.width = '100%';
    element.style.height = '100%';
    element.style.objectFit = 'cover';
  }

  container.appendChild(element);
}

function showCallScreen() {
  hideCallScreen();

  const overlay = el('div', {
    className: 'call-overlay',
    style: {
      position: 'fixed',
      inset: '0',
      zIndex: '10001',
      background: '#000',
      color: '#fff'
    }
  });

  const remote = el('div', {
    className: 'call-remote-video',
    style: {
      position: 'absolute',
      inset: '0',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  });

  const avatar = el('div', {
    className: 'call-avatar',
    style: {
      width: '100px',
      height: '100px',
      borderRadius: '50%',
      background: 'var(--bg-3)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '36px',
      fontWeight: '700'
    },
    textContent: initials(CALL_STATE.name)
  });

  remote.appendChild(avatar);
  overlay.appendChild(remote);

  const info = el('div', {
    className: 'call-info',
    style: {
      position: 'absolute',
      top: '30px',
      left: '0',
      right: '0',
      textAlign: 'center',
      zIndex: '4'
    }
  });

  info.appendChild(el('strong', {
    textContent: CALL_STATE.name
  }));

  info.appendChild(el('div', {
    className: 'call-status',
    textContent: 'Calling...'
  }));

  overlay.appendChild(info);

  const local = el('div', {
    className: 'call-local-video',
    style: {
      position: 'absolute',
      top: '80px',
      right: '16px',
      width: '110px',
      height: '160px',
      background: '#111',
      borderRadius: '12px',
      overflow: 'hidden',
      zIndex: '5'
    }
  });

  overlay.appendChild(local);

  const controls = el('div', {
    className: 'call-controls',
    style: {
      position: 'absolute',
      bottom: '30px',
      left: '0',
      right: '0',
      display: 'flex',
      justifyContent: 'center',
      gap: '12px',
      zIndex: '5'
    }
  });

  const mic = el('button', {
    className: 'call-control-btn',
    type: 'button',
    textContent: '🎙',
    title: 'Microphone'
  });

  mic.addEventListener('click', toggleMic);

  const camera = el('button', {
    className: 'call-control-btn',
    type: 'button',
    textContent: '▣',
    title: 'Camera'
  });

  camera.addEventListener('click', toggleCamera);

  const switchCameraButton = el('button', {
    className: 'call-control-btn',
    type: 'button',
    textContent: '↻',
    title: 'Switch camera'
  });

  switchCameraButton.addEventListener('click', switchCamera);

  const speaker = el('button', {
    className: 'call-control-btn speaker-on',
    type: 'button',
    textContent: '🔊',
    title: 'Speaker'
  });

  speaker.addEventListener('click', toggleSpeaker);

  const end = el('button', {
    className: 'call-end-btn',
    type: 'button',
    textContent: '☎',
    title: 'End call'
  });

  end.addEventListener('click', endCall);

  controls.append(
    mic,
    camera,
    switchCameraButton,
    speaker,
    end
  );

  overlay.appendChild(controls);
  document.body.appendChild(overlay);

  if (CALL_STATE.type !== 'video') {
    camera.classList.add('hidden');
    switchCameraButton.classList.add('hidden');
  }

  CALL_TIMER = setTimeout(() => {
    if (CALL_STATE.active && !CALL_STATE.answered) {
      toast('No answer.');
      endCall();
    }
  }, 30000);
}

function updateCallStatus(text) {
  const node = $('.call-status');
  if (node) node.textContent = text;
}

function hideCallScreen() {
  clearTimeout(CALL_TIMER);
  $('.call-overlay')?.remove();
}

async function toggleMic() {
  if (!CALL_ROOM?.localParticipant) return;

  try {
    CALL_STATE.mic = !CALL_STATE.mic;
    await CALL_ROOM.localParticipant.setMicrophoneEnabled(CALL_STATE.mic);

    const button = $('.call-controls .call-control-btn');
    if (button) button.textContent = CALL_STATE.mic ? '🎙' : '🔇';
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function toggleCamera() {
  if (!CALL_ROOM?.localParticipant || CALL_STATE.type !== 'video') return;

  try {
    CALL_STATE.camera = !CALL_STATE.camera;
    await CALL_ROOM.localParticipant.setCameraEnabled(CALL_STATE.camera);
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function switchCamera() {
  if (!CALL_ROOM?.localParticipant || !CALL_STATE.camera) return;

  try {
    const publication = Array.from(
      CALL_ROOM.localParticipant.videoTrackPublications.values()
    )[0];

    if (!publication?.track) return;

    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter(device => device.kind === 'videoinput');

    if (cameras.length < 2) {
      toast('Only one camera is available.');
      return;
    }

    const current = publication.track.mediaStreamTrack?.getSettings?.().deviceId;
    const index = cameras.findIndex(camera => camera.deviceId === current);
    const next = cameras[(index + 1) % cameras.length];

    if (typeof publication.track.restartTrack === 'function') {
      await publication.track.restartTrack({
        deviceId: next.deviceId
      });
    } else {
      toast('Camera switching is not supported by this LiveKit version.');
    }
  } catch (error) {
    toast(error.message, 'error');
  }
}

function toggleSpeaker() {
  CALL_STATE.speaker = !CALL_STATE.speaker;

  const volume = CALL_STATE.speaker ? '1' : '0.3';

  $$('.call-remote-video audio, .call-remote-video video').forEach(media => {
    media.volume = Number(volume);
  });

  const button = $$('.call-controls .call-control-btn')[3];

  if (button) {
    button.classList.toggle('speaker-on', CALL_STATE.speaker);
    button.classList.toggle('speaker-off', !CALL_STATE.speaker);
    button.textContent = CALL_STATE.speaker ? '🔊' : '🔉';
  }
}

async function endCall() {
  clearTimeout(CALL_TIMER);
  stopRingtone();

  try {
    if (CALL_ROOM) {
      await CALL_ROOM.disconnect();
    }
  } catch (_) {
    /* Room may already be disconnected. */
  }

  if (CALL_STATE.otherId) {
    api(API.calls, {
      method: 'DELETE',
      body: {
        recipient_id: CALL_STATE.otherId
      },
      timeout: 8000,
      retry: false
    }).catch(() => {});
  }

  CALL_ROOM = null;

  CALL_STATE = {
    active: false,
    type: null,
    otherId: null,
    name: '',
    mic: true,
    camera: true,
    speaker: true,
    answered: false
  };

  hideCallScreen();
}

function playBeep() {
  try {
    const AudioContextClass =
      window.AudioContext ||
      window.webkitAudioContext;

    if (!AudioContextClass) return;

    if (!RINGTONE_CONTEXT) {
      RINGTONE_CONTEXT = new AudioContextClass();
    }

    const oscillator = RINGTONE_CONTEXT.createOscillator();
    const gain = RINGTONE_CONTEXT.createGain();

    oscillator.frequency.value = 740;
    oscillator.type = 'sine';

    gain.gain.setValueAtTime(0.0001, RINGTONE_CONTEXT.currentTime);
    gain.gain.exponentialRampToValueAtTime(
      0.15,
      RINGTONE_CONTEXT.currentTime + 0.02
    );
    gain.gain.exponentialRampToValueAtTime(
      0.0001,
      RINGTONE_CONTEXT.currentTime + 0.22
    );

    oscillator.connect(gain);
    gain.connect(RINGTONE_CONTEXT.destination);

    oscillator.start();
    oscillator.stop(RINGTONE_CONTEXT.currentTime + 0.24);
  } catch (_) {
    /* Audio is optional. */
  }
}

function playDoubleBeep() {
  playBeep();

  setTimeout(() => {
    if (CALL_STATE.active) playBeep();
  }, 260);
}

function startRingtone() {
  stopRingtone();

  if (!CALL_STATE.active) return;

  playDoubleBeep();

  RINGTONE_TIMER = setInterval(() => {
    if (!CALL_STATE.active || CALL_STATE.answered) {
      stopRingtone();
      return;
    }

    playDoubleBeep();
  }, 2000);
}

function stopRingtone() {
  clearInterval(RINGTONE_TIMER);
  RINGTONE_TIMER = null;
}

/* ============================================================
   SECTION I: SEARCH
   ============================================================ */

async function openSearch() {
  openSearchWithQuery('');
}

async function openSearchWithQuery(q = '') {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  switchView('search');

  main.replaceChildren();

  const header = el('div', {
    className: 'sub-page-header'
  });

  const back = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '‹'
  });

  back.addEventListener('click', () => switchView('home'));

  header.append(
    back,
    el('h2', { textContent: 'Search' })
  );

  main.appendChild(header);

  const input = el('input', {
    className: 'home-search-input',
    type: 'search',
    placeholder: 'Search people, posts and channels',
    value: q
  });

  const results = el('div', {
    className: 'search-results'
  });

  main.append(input, results);

  const execute = async () => {
    const query = input.value.trim();

    if (!query) {
      results.replaceChildren();
      return;
    }

    results.replaceChildren(el('div', {
      className: 'loader',
      textContent: 'Searching...'
    }));

    try {
      const data = await api(
        `${API.search}?q=${encodeURIComponent(query)}`
      );

      CACHE.search.set(query, data);
      results.replaceChildren();

      const users = normalizeList(data?.users);
      const posts = normalizeList(data?.posts);
      const channels = normalizeList(data?.channels);

      if (users.length) {
        results.appendChild(el('h3', {
          textContent: 'People'
        }));

        users.forEach(user => {
          const item = el('button', {
            className: 'chat-list-item',
            type: 'button'
          });

          item.append(
            avatarEl(user, '44px'),
            el('span', {
              textContent: user.name || user.username || 'User'
            })
          );

          item.addEventListener('click', () => openProfile(user.id || user.user_id));
          results.appendChild(item);
        });
      }

      if (channels.length) {
        results.appendChild(el('h3', {
          textContent: 'Channels'
        }));

        channels.forEach(channel => {
          results.appendChild(el('div', {
            className: 'channel-item',
            textContent: channel.name || channel.title || 'Channel'
          }));
        });
      }

      if (posts.length) {
        results.appendChild(el('h3', {
          textContent: 'Posts'
        }));

        posts.forEach(post => {
          results.appendChild(renderPost(post));
        });
      }

      if (!users.length && !posts.length && !channels.length) {
        results.appendChild(el('div', {
          className: 'empty-state',
          textContent: 'No results found.'
        }));
      }
    } catch (error) {
      results.replaceChildren(el('div', {
        className: 'empty-state',
        textContent: error.message
      }));
    }
  };

  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') execute();
  });

  if (q) await execute();
}

/* ============================================================
   SECTION J: DISCOVERY
   ============================================================ */

function openDiscovery() {
  switchView('discovery');

  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren();

  const header = subPageHeader('Discovery', () => switchView('home'));
  main.appendChild(header);

  const grid = el('div', {
    className: 'discovery-grid'
  });

  const cards = [
    ['ai', '🤖', 'AI Council'],
    ['studio', '🎬', 'Studio'],
    ['market', '🛍', 'Market'],
    ['map', '🌍', 'World Map'],
    ['channels', '📺', 'Channels'],
    ['communities', '👥', 'Communities'],
    ['videos', '▶', 'Videos'],
    ['settings', '⚙', 'Settings']
  ];

  cards.forEach(([key, icon, title]) => {
    const card = el('button', {
      className: 'discovery-card',
      type: 'button'
    });

    card.append(
      el('div', {
        className: 'discovery-icon',
        textContent: icon
      }),
      el('strong', {
        textContent: title
      })
    );

    card.addEventListener('click', () => openDiscoveryItem(key));
    grid.appendChild(card);
  });

  main.appendChild(grid);
}

function openDiscoveryItem(key) {
  const actions = {
    ai: openAICouncil,
    studio: openStudio,
    market: openMarket,
    map: openWorldMap,
    channels: openChannels,
    communities: openCommunities,
    videos: openVideos,
    settings: openSettings
  };

  if (typeof actions[key] === 'function') {
    actions[key]();
  }
}

function subPageHeader(title, backFn) {
  const header = el('div', {
    className: 'sub-page-header',
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px'
    }
  });

  const back = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '‹',
    title: 'Back'
  });

  back.addEventListener('click', backFn);

  header.append(
    back,
    el('h2', {
      textContent: title
    })
  );

  return header;
}

function openAICouncil() {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('AI Council', openDiscovery)
  );

  const list = el('div', {
    className: 'ai-list'
  });

  [
    ['education', 'Education AI', 'Learning support across countries and levels.'],
    ['health', 'Health AI', 'General health information and education.'],
    ['agriculture', 'Agriculture AI', 'Agriculture information and practical guidance.'],
    ['research', 'Research AI', 'Research and knowledge exploration.'],
    ['canvas', 'AI Canvas', 'Creative AI workspace.']
  ].forEach(([key, title, description]) => {
    const item = el('button', {
      className: 'ai-list-item',
      type: 'button'
    });

    item.append(
      el('strong', { textContent: title }),
      el('small', { textContent: description })
    );

    item.addEventListener('click', () => {
      if (key === 'education') openEduAI();
      else openAISub(key, title);
    });

    list.appendChild(item);
  });

  main.appendChild(list);
}

function openAISub(key, title) {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader(title, openAICouncil)
  );

  const body = el('div', {
    className: 'ai-sub-page'
  });

  body.appendChild(el('p', {
    textContent:
      `Use ${title} to explore information and interact with the MSAFIRI AI service.`
  }));

  const chat = el('button', {
    className: 'btn btn-primary',
    type: 'button',
    textContent: 'Open AI Chat'
  });

  chat.addEventListener('click', () => openAIChatPlaceholder(key, title));

  body.appendChild(chat);
  main.appendChild(body);
}

function openAIChatPlaceholder(topic = 'general', title = 'AI Chat') {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader(title, () => openAISub(topic, title))
  );

  const messages = el('div', {
    className: 'chat-messages'
  });

  messages.appendChild(el('div', {
    className: 'chat-bubble theirs',
    textContent: 'Hello. How can I help you today?'
  }));

  const composer = el('div', {
    className: 'chat-composer'
  });

  const input = el('input', {
    type: 'text',
    placeholder: 'Ask the AI...'
  });

  const send = el('button', {
    className: 'btn btn-primary',
    type: 'button',
    textContent: 'Send'
  });

  const submit = async () => {
    const question = input.value.trim();
    if (!question) return;

    messages.appendChild(el('div', {
      className: 'chat-bubble mine',
      textContent: question
    }));

    input.value = '';

    try {
      const data = await api(API.ai, {
        method: 'POST',
        body: {
          topic,
          message: question
        }
      });

      const answer =
        data?.response ||
        data?.answer ||
        data?.message ||
        'No response was returned.';

      messages.appendChild(el('div', {
        className: 'chat-bubble theirs',
        textContent: answer
      }));

      messages.scrollTop = messages.scrollHeight;
    } catch (error) {
      messages.appendChild(el('div', {
        className: 'chat-bubble theirs',
        textContent: error.message
      }));
    }
  };

  send.addEventListener('click', submit);

  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') submit();
  });

  composer.append(input, send);
  main.append(messages, composer);
}

function openEduAI() {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('Education AI', openAICouncil)
  );

  const grid = el('div', {
    className: 'selector-grid'
  });

  const countries = [
    'Tanzania',
    'Kenya',
    'Uganda',
    'Rwanda',
    'Burundi',
    'South Africa',
    'Nigeria',
    'Ghana',
    'Ethiopia',
    'Egypt',
    'India',
    'United Kingdom',
    'United States',
    'Canada',
    'Australia',
    'Germany',
    'France',
    'Japan'
  ];

  countries.forEach(country => {
    const item = el('button', {
      className: 'selector-item',
      type: 'button',
      textContent: country
    });

    item.addEventListener('click', () => openEduLevel(country));
    grid.appendChild(item);
  });

  main.appendChild(grid);
}

function openEduLevel(country) {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader(`Education · ${country}`, openEduAI)
  );

  const grid = el('div', {
    className: 'selector-grid'
  });

  [
    'Pre-Primary',
    'Primary',
    'Secondary',
    'High School',
    'College',
    'University',
    'Vocational',
    'Professional',
    'Other'
  ].forEach(level => {
    const item = el('button', {
      className: 'selector-item',
      type: 'button',
      textContent: level
    });

    item.addEventListener('click', () => openEduContent(country, level));
    grid.appendChild(item);
  });

  main.appendChild(grid);
}

function openEduContent(country, level) {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader(
      `${country} · ${level}`,
      () => openEduLevel(country)
    )
  );

  const grid = el('div', {
    className: 'selector-grid'
  });

  [
    ['Lessons', 'lesson'],
    ['Questions', 'questions'],
    ['Notes', 'notes'],
    ['AI Tutor', 'chat']
  ].forEach(([title, type]) => {
    const item = el('button', {
      className: 'selector-item',
      type: 'button',
      textContent: title
    });

    item.addEventListener('click', () => {
      if (type === 'chat') {
        openEduChat(country, level);
      } else {
        openAIChatPlaceholder(
          `education:${country}:${level}:${type}`,
          title
        );
      }
    });

    grid.appendChild(item);
  });

  main.appendChild(grid);
}

function openEduChat(country, level) {
  openAIChatPlaceholder(
    `education:${country}:${level}`,
    `Education AI · ${level}`
  );
}

function openStudio() {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('Studio', openDiscovery)
  );

  const body = el('div', {
    className: 'manual-container'
  });

  body.append(
    el('h3', { textContent: 'Creator Studio' }),
    el('p', {
      textContent: 'Create and manage your posts, stories, photos and videos.'
    })
  );

  const create = el('button', {
    className: 'btn btn-primary',
    type: 'button',
    textContent: 'Create Post'
  });

  create.addEventListener('click', openCreatePost);
  body.appendChild(create);

  main.appendChild(body);
}

async function openMarket() {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('Market', openDiscovery)
  );

  const grid = el('div', {
    className: 'market-grid'
  });

  main.appendChild(grid);

  try {
    const data = await api(API.market);

    normalizeList(data).forEach(item => {
      const card = el('div', {
        className: 'market-card'
      });

      card.append(
        el('h3', {
          textContent: item.name || item.title || 'Item'
        }),
        el('p', {
          textContent: item.description || ''
        }),
        el('strong', {
          textContent: item.price !== undefined
            ? String(item.price)
            : ''
        })
      );

      grid.appendChild(card);
    });
  } catch (error) {
    grid.appendChild(el('div', {
      className: 'empty-state',
      textContent: error.message
    }));
  }
}

async function openWorldMap() {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('World Map', openDiscovery)
  );

  const body = el('div', {
    className: 'manual-container'
  });

  body.appendChild(el('h3', {
    textContent: 'World Map'
  }));

  try {
    const data = await api(API.worldMap);

    const locations = normalizeList(data);

    if (!locations.length) {
      body.appendChild(el('p', {
        textContent: 'No map locations are currently available.'
      }));
    }

    locations.forEach(location => {
      body.appendChild(el('div', {
        className: 'channel-item',
        textContent:
          location.name ||
          location.country ||
          location.title ||
          'Location'
      }));
    });
  } catch (error) {
    body.appendChild(el('p', {
      textContent: error.message
    }));
  }

  main.appendChild(body);
}

async function openChannels() {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('Channels', openDiscovery)
  );

  const list = el('div', {
    className: 'channels-list'
  });

  main.appendChild(list);

  try {
    const data = await api(API.channels);
    let channels = normalizeList(data);

    if (!channels.length) {
      channels = [
        { name: 'BBC' },
        { name: 'CNN' },
        { name: 'Aljazeera' },
        { name: 'ITV' },
        { name: 'Msafiri' }
      ];
    }

    channels.forEach(channel => {
      const item = el('button', {
        className: 'channel-item',
        type: 'button'
      });

      const logo = el('div', {
        className: 'channel-logo',
        textContent: initials(channel.name || channel.title)
      });

      item.append(
        logo,
        el('strong', {
          textContent: channel.name || channel.title || 'Channel'
        })
      );

      item.addEventListener('click', () => {
        if (channel.url) {
          window.open(absoluteUrl(channel.url), '_blank', 'noopener');
        }
      });

      list.appendChild(item);
    });
  } catch (error) {
    list.appendChild(el('div', {
      className: 'empty-state',
      textContent: error.message
    }));
  }
}

async function openCommunities() {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('Communities', openDiscovery)
  );

  const list = el('div', {
    className: 'community-list'
  });

  main.appendChild(list);

  try {
    const data = await api(API.communities);

    normalizeList(data).forEach(community => {
      const item = el('button', {
        className: 'channel-item',
        type: 'button'
      });

      item.append(
        avatarEl(community, '48px'),
        el('div', {
          style: {
            textAlign: 'left'
          }
        }, el('strong', {
          textContent: community.name || community.title || 'Community'
        }), el('small', {
          textContent: `${community.members_count ?? 0} members`
        }))
      );

      item.addEventListener('click', () => {
        if (community.id) {
          openAIChatPlaceholder(
            `community:${community.id}`,
            community.name || 'Community'
          );
        }
      });

      list.appendChild(item);
    });
  } catch (error) {
    list.appendChild(el('div', {
      className: 'empty-state',
      textContent: error.message
    }));
  }
}

async function openSettings() {
  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('Settings', openDiscovery)
  );

  const body = el('div', {
    className: 'manual-container'
  });

  const themeButton = el('button', {
    className: 'btn btn-secondary',
    type: 'button',
    textContent: 'Toggle Theme'
  });

  themeButton.addEventListener('click', toggleTheme);

  const manual = el('button', {
    className: 'btn btn-secondary',
    type: 'button',
    textContent: 'User Manual'
  });

  manual.addEventListener('click', openUserManual);

  const logoutButton = el('button', {
    className: 'btn btn-secondary',
    type: 'button',
    textContent: 'Logout'
  });

  logoutButton.addEventListener('click', logout);

  body.append(
    themeButton,
    manual,
    logoutButton
  );

  main.appendChild(body);
}

async function openVideos() {
  switchView('videos');

  const main = $('.app-main') || $('#mainContent');
  if (!main) return;

  main.replaceChildren(
    subPageHeader('Videos', openDiscovery)
  );

  const container = el('div', {
    className: 'video-feed-container'
  });

  main.appendChild(container);
  await renderVideoFeed(container);
}

async function renderVideoFeed(container = null) {
  const target = container || $('.video-feed-container');
  if (!target) return;

  try {
    const data = await api(API.videos);
    const videos = normalizeList(data);

    target.replaceChildren();

    videos.forEach(video => {
      const item = el('article', {
        className: 'video-feed-item',
        style: {
          minHeight: '80vh',
          position: 'relative',
          scrollSnapAlign: 'start'
        }
      });

      const player = el('video', {
        className: 'video-feed-video',
        src: absoluteUrl(video.video_url || video.media_url || video.url),
        controls: false,
        loop: true,
        playsInline: true,
        muted: true,
        preload: 'metadata',
        style: {
          width: '100%',
          height: '75vh',
          objectFit: 'cover'
        }
      });

      const actions = el('div', {
        className: 'video-feed-actions'
      });

      const like = el('button', {
        className: 'video-feed-action',
        type: 'button',
        textContent: `♥ ${video.likes_count ?? 0}`
      });

      like.addEventListener('click', async () => {
        try {
          const result = await api(
            `${API.videos}/${encodeURIComponent(video.id)}/like`,
            { method: 'POST' }
          );

          like.textContent = `♥ ${result?.likes_count ?? result?.count ?? 0}`;
        } catch (error) {
          toast(error.message, 'error');
        }
      });

      const comment = el('button', {
        className: 'video-feed-action',
        type: 'button',
        textContent: `◯ ${video.comments_count ?? 0}`
      });

      comment.addEventListener('click', () => {
        openComments(video);
      });

      const share = el('button', {
        className: 'video-feed-action',
        type: 'button',
        textContent: '↗ Share'
      });

      share.addEventListener('click', async () => {
        const url = video.url || `${window.location.origin}/video/${video.id}`;

        try {
          if (navigator.share) {
            await navigator.share({
              title: video.title || 'MSAFIRI video',
              url
            });
          } else {
            await navigator.clipboard.writeText(url);
            toast('Video link copied.');
          }
        } catch (_) {
          /* User cancelled share. */
        }
      });

      const mute = el('button', {
        className: 'video-feed-action',
        type: 'button',
        textContent: '🔇'
      });

      mute.addEventListener('click', () => {
        player.muted = !player.muted;
        mute.textContent = player.muted ? '🔇' : '🔊';
      });

      actions.append(like, comment, share, mute);

      const info = el('div', {
        className: 'video-feed-info'
      });

      info.append(
        el('strong', {
          textContent:
            video.user?.name ||
            video.author?.name ||
            video.title ||
            'Video'
        }),
        el('p', {
          textContent: video.caption || video.description || ''
        })
      );

      item.append(player, actions, info);
      target.appendChild(item);

      const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            player.play().catch(() => {});
          } else {
            player.pause();
          }
        });
      }, {
        threshold: 0.6
      });

      observer.observe(item);
    });

    if (!videos.length) {
      target.appendChild(el('div', {
        className: 'empty-state',
        textContent: 'No videos available.'
      }));
    }
  } catch (error) {
    target.appendChild(el('div', {
      className: 'empty-state',
      textContent: error.message
    }));
  }
}

function openUserManual() {
  closeModal();

  const overlay = el('div', {
    className: 'modal-overlay'
  });

  const content = el('div', {
    className: 'modal-content'
  });

  const header = el('div', {
    className: 'modal-header'
  });

  header.appendChild(el('h3', {
    textContent: 'User Manual'
  }));

  const close = el('button', {
    className: 'btn-icon',
    type: 'button',
    textContent: '×'
  });

  close.addEventListener('click', closeModal);
  header.appendChild(close);

  const body = el('div', {
    className: 'modal-body manual-container'
  });

  body.append(
    el('h2', {
      textContent: 'MSAFIRI GLOBAL MEDIA'
    }),
    el('p', {
      textContent: 'Social, communication and AI platform.'
    }),
    el('p', {
      textContent: 'Founder: MSAFIRI WILLIAM MUNGA'
    }),
    el('p', {
      textContent: 'Company: ZetroLink Technology Limited'
    }),
    el('p', {
      textContent: 'Version: Media V0.0.1'
    }),
    el('h3', {
      textContent: 'Getting started'
    }),
    el('p', {
      textContent:
        'Use Home to browse posts and stories, Chats for messaging and calls, Discovery for AI and other services, and Profile to manage your account.'
    })
  );

  const download = el('button', {
    className: 'btn btn-primary',
    type: 'button',
    textContent: 'Download Manual'
  });

  download.addEventListener('click', () => window.downloadManual());
  body.appendChild(download);

  content.append(header, body);
  overlay.appendChild(content);
  document.body.appendChild(overlay);
}

window.downloadManual = function downloadManual() {
  const text = [
    'MSAFIRI GLOBAL MEDIA',
    '',
    'Social, communication and AI platform.',
    '',
    'Founder: MSAFIRI WILLIAM MUNGA',
    'Company: ZetroLink Technology Limited',
    'Version: Media V0.0.1',
    '',
    'MAIN FEATURES',
    '',
    'Home',
    '- Browse For You and Following feeds.',
    '- View stories.',
    '- Create posts.',
    '- Like, comment, reshare and save posts.',
    '',
    'Chats',
    '- Send text messages.',
    '- Send photos, videos and files.',
    '- Record voice notes.',
    '- Make voice and video calls.',
    '',
    'Stories',
    '- Create photo or video stories.',
    '- Add captions.',
    '- Tap left/right to navigate.',
    '- Hold the screen to pause.',
    '',
    'Discovery',
    '- AI Council.',
    '- Education AI.',
    '- Studio.',
    '- Market.',
    '- World Map.',
    '- Channels.',
    '- Communities.',
    '- Videos.',
    '- Settings.',
    '',
    'Profile',
    '- View profile information.',
    '- Edit profile.',
    '- Upload an avatar.',
    '',
    'MSAFIRI GLOBAL MEDIA'
  ].join('\n');

  const blob = new Blob([text], {
    type: 'text/plain;charset=utf-8'
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = 'MSAFIRI-GLOBAL-MEDIA-User-Manual.txt';
  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

function openThreeDotsMenu() {
  openSheet('MSAFIRI GLOBAL MEDIA', [
    {
      label: 'User Manual',
      action: openUserManual
    },
    {
      label: 'Toggle Theme',
      action: toggleTheme
    },
    {
      label: 'Version Media V0.0.1',
      action: () => {}
    },
    {
      label: 'Logout',
      danger: true,
      action: logout
    }
  ]);
}

/* ============================================================
   SECTION K: NAVIGATION & INIT
   ============================================================ */

function switchView(view) {
  CURRENT_VIEW = view;

  $$('.nav-item').forEach(item => {
    const itemView =
      item.dataset.view ||
      item.dataset.nav ||
      item.getAttribute('data-target');

    item.classList.toggle('active', itemView === view);
  });

  if (view === 'home') {
    const posts = CACHE.feed.get('for-you') || [];
    renderFeed('for-you', posts);
  } else if (view === 'discovery') {
    openDiscovery();
  } else if (view === 'chats') {
    openChats();
  } else if (view === 'profile') {
    openProfile(CURRENT_USER?.id || CURRENT_USER?.user_id);
  }
}

function handleNav(view) {
  if (!view) return;

  switch (view) {
    case 'home':
      switchView('home');
      break;
    case 'discovery':
      switchView('discovery');
      break;
    case 'chats':
      switchView('chats');
      break;
    case 'profile':
      switchView('profile');
      break;
    default:
      switchView(view);
      break;
  }
}

function bindBottomNav() {
  $$('.nav-item').forEach(item => {
    if (item.dataset.bound) return;

    item.dataset.bound = '1';

    item.addEventListener('click', event => {
      event.preventDefault();

      const view =
        item.dataset.view ||
        item.dataset.nav ||
        item.getAttribute('data-target');

      handleNav(view);
    });
  });
}

function bindGlobalActions() {
  $$('[data-action="create-post"], #createPostButton').forEach(button => {
    if (button.dataset.bound) return;

    button.dataset.bound = '1';
    button.addEventListener('click', openCreatePost);
  });

  $$('[data-action="search"], #searchButton').forEach(button => {
    if (button.dataset.bound) return;

    button.dataset.bound = '1';
    button.addEventListener('click', openSearch);
  });

  $$('[data-action="menu"], #threeDotsButton').forEach(button => {
    if (button.dataset.bound) return;

    button.dataset.bound = '1';
    button.addEventListener('click', openThreeDotsMenu);
  });
}

function bindKeyboardShortcuts() {
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      closeModal();
      closeStoryViewer();
    }

    if (
      event.key === '/' &&
      !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)
    ) {
      event.preventDefault();
      openSearch();
    }
  });
}

function bindVisibility() {
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && TOKEN) {
      api(API.sessionPing, {
        method: 'GET',
        timeout: 10000,
        retry: false
      }).catch(() => {});
    }

    if (document.hidden && CALL_STATE.active) {
      /* Keep call alive; browser controls background execution. */
    }
  });
}

function startSessionPing() {
  setInterval(() => {
    if (!TOKEN || document.hidden) return;

    api(API.sessionPing, {
      method: 'GET',
      timeout: 10000,
      retry: false
    }).catch(() => {});
  }, 300000);
}

function hideSplashAfterDelay() {
  const splash =
    $('#splashScreen') ||
    $('.splash-screen') ||
    $('[data-splash]');

  if (!splash) return;

  setTimeout(() => {
    splash.style.opacity = '0';
    splash.style.pointerEvents = 'none';

    setTimeout(() => {
      splash.classList.add('hidden');
    }, 500);
  }, 6000);
}

function showFatalError(error) {
  let box = $('#appError');

  if (!box) {
    box = el('div', {
      id: 'appError',
      style: {
        position: 'fixed',
        left: '16px',
        right: '16px',
        bottom: '16px',
        zIndex: '20000',
        padding: '14px',
        background: 'var(--danger)',
        color: '#fff',
        borderRadius: 'var(--radius-sm)',
        boxShadow: '0 8px 30px rgba(0,0,0,.25)'
      }
    });

    document.body.appendChild(box);
  }

  box.textContent =
    `MSAFIRI GLOBAL MEDIA error: ${error?.message || error}`;
}

function bindErrorHandling() {
  window.addEventListener('error', event => {
    console.error('MSAFIRI GLOBAL MEDIA error:', event.error || event.message);
    showFatalError(event.error || new Error(event.message));
  });

  window.addEventListener('unhandledrejection', event => {
    console.error(
      'MSAFIRI GLOBAL MEDIA unhandled rejection:',
      event.reason
    );

    showFatalError(
      event.reason instanceof Error
        ? event.reason
        : new Error(String(event.reason))
    );
  });
}

async function init() {
  try {
    initTheme();
    bindAuthUI();
    bindBottomNav();
    bindGlobalActions();
    bindKeyboardShortcuts();
    bindVisibility();
    bindErrorHandling();
    hideSplashAfterDelay();
    startSessionPing();

    TOKEN = getSavedToken();

    if (!TOKEN) {
      showAuth();
      return;
    }

    const savedUser = localStorage.getItem('msafiri_user');

    if (savedUser) {
      try {
        CURRENT_USER = JSON.parse(savedUser);
      } catch (_) {
        CURRENT_USER = null;
      }
    }

    try {
      await loadMe();
      showApp();
      await startApp();
    } catch (error) {
      console.warn('Auto-login failed:', error.message);
      TOKEN = '';
      CURRENT_USER = null;
      localStorage.removeItem('msafiri_token');
      showAuth();
    }
  } catch (error) {
    console.error('Initialization failed:', error);
    showFatalError(error);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  init().catch(error => {
    console.error('DOMContentLoaded initialization failed:', error);
    showFatalError(error);
  });
});
