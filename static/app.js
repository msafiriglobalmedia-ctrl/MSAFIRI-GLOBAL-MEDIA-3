// ============================================================
// MSAFIRI GLOBAL MEDIA — APP.JS
// Version: 6.0.0-PHASE2
// Authentication + Navigation + Feed + Stories + Discovery
// AI Council + Studio + Market + World Map + Channels
// Communities + Videos + Settings + Profile + Chats
// ============================================================

'use strict';

// ============================================================
// CONFIGURATION
// ============================================================

const API = window.location.origin;

const TOKEN_KEY = 'msafiri_access_token';
const OLD_TOKEN_KEY = 'token';

let currentUser = null;
let currentFeed = 'for-you';
let navStack = [];
let authLoading = false;


// ============================================================
// DOM HELPERS
// ============================================================

function $(selector) {
  return document.querySelector(selector);
}

function $all(selector) {
  return document.querySelectorAll(selector);
}


// ============================================================
// APP INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  initializeApp();
});


async function initializeApp() {
  try {
    setupAuthTabs();
    setupNavigation();
    setupFeedTabs();
    setupDotsMenu();
    setupBackButton();

    const splash = $('#splash');

    setTimeout(async () => {
      if (splash) {
        splash.classList.add('hidden');
      }

      await checkAuth();
    }, 3000);

  } catch (error) {
    console.error('Application initialization error:', error);
    showAuth();
  }
}


// ============================================================
// TOKEN MANAGEMENT
// ============================================================

function getToken() {
  return (
    localStorage.getItem(TOKEN_KEY) ||
    localStorage.getItem(OLD_TOKEN_KEY) ||
    null
  );
}


function saveToken(token) {
  if (!token) return;

  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(OLD_TOKEN_KEY, token);
}


function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(OLD_TOKEN_KEY);
}


// ============================================================
// AUTHENTICATED FETCH
// ============================================================

async function authFetch(url, options = {}) {
  const token = getToken();

  const headers = {
    ...(options.headers || {})
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return fetch(url, {
    ...options,
    headers
  });
}


// ============================================================
// SAFE JSON
// ============================================================

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}


// ============================================================
// AUTHENTICATION CHECK
// ============================================================

async function checkAuth() {

  if (authLoading) return;

  authLoading = true;

  try {

    const token = getToken();

    if (!token) {
      currentUser = null;
      showAuth();
      return;
    }

    const response = await authFetch(
      `${API}/api/auth/me`,
      {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      }
    );

    if (response.ok) {

      const user = await safeJson(response);

      currentUser = user;

      showApp();

    } else {

      console.warn(
        'Authentication failed:',
        response.status
      );

      removeToken();

      currentUser = null;

      showAuth();
    }

  } catch (error) {

    console.error(
      'Authentication check failed:',
      error
    );

    showAuth();

  } finally {

    authLoading = false;
  }
}


// ============================================================
// SHOW AUTH SCREEN
// ============================================================

function showAuth() {

  const authScreen = $('#auth-screen');
  const app = $('#app');

  if (authScreen) {
    authScreen.classList.remove('hidden');
  }

  if (app) {
    app.classList.add('hidden');
  }
}


// ============================================================
// SHOW MAIN APP
// ============================================================

function showApp() {

  const authScreen = $('#auth-screen');
  const app = $('#app');

  if (authScreen) {
    authScreen.classList.add('hidden');
  }

  if (app) {
    app.classList.remove('hidden');
  }

  updateCurrentUserUI();

  loadHome();
  loadDiscovery();
  loadProfile();
}


// ============================================================
// AUTH TABS
// ============================================================

function setupAuthTabs() {

  $all('.auth-tab').forEach(tab => {

    tab.addEventListener('click', () => {

      $all('.auth-tab').forEach(t => {
        t.classList.remove('active');
      });

      tab.classList.add('active');

      const target = tab.dataset.tab;

      const loginForm = $('#login-form');
      const registerForm = $('#register-form');

      if (loginForm) {
        loginForm.classList.toggle(
          'hidden',
          target !== 'login'
        );
      }

      if (registerForm) {
        registerForm.classList.toggle(
          'hidden',
          target !== 'register'
        );
      }
    });

  });
}


// ============================================================
// LOGIN
// ============================================================

const loginForm = $('#login-form');

if (loginForm) {

  loginForm.addEventListener('submit', async event => {

    event.preventDefault();

    const username = $('#login-username')?.value.trim();
    const password = $('#login-password')?.value;

    if (!username || !password) {
      toast('Please enter username and password');
      return;
    }

    const submitButton =
      loginForm.querySelector('button[type="submit"]');

    if (submitButton) {
      submitButton.disabled = true;
    }

    try {

      const response = await fetch(
        `${API}/api/auth/login`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            username,
            password
          })
        }
      );

      const data = await safeJson(response);

      if (!response.ok) {

        toast(
          data.detail ||
          'Login failed. Check your credentials.'
        );

        return;
      }

      if (!data.access_token) {

        toast(
          'Login succeeded but no access token was returned.'
        );

        console.error(
          'Login response missing access_token:',
          data
        );

        return;
      }

      saveToken(data.access_token);

      currentUser = data.user || null;

      toast('Login successful');

      showApp();

    } catch (error) {

      console.error('Login error:', error);

      toast(
        'Network error. Please check your connection.'
      );

    } finally {

      if (submitButton) {
        submitButton.disabled = false;
      }
    }

  });

}


// ============================================================
// REGISTER
// ============================================================

const registerForm = $('#register-form');

if (registerForm) {

  registerForm.addEventListener('submit', async event => {

    event.preventDefault();

    const username =
      $('#reg-username')?.value.trim();

    const email =
      $('#reg-email')?.value.trim();

    const fullName =
      $('#reg-fullname')?.value.trim();

    const password =
      $('#reg-password')?.value;

    if (!username || !email || !password) {

      toast(
        'Username, email and password are required.'
      );

      return;
    }

    const submitButton =
      registerForm.querySelector(
        'button[type="submit"]'
      );

    if (submitButton) {
      submitButton.disabled = true;
    }

    try {

      const response = await fetch(
        `${API}/api/auth/register`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            username,
            email,
            full_name: fullName || '',
            password
          })
        }
      );

      const data = await safeJson(response);

      if (!response.ok) {

        toast(
          data.detail ||
          'Registration failed.'
        );

        return;
      }

      /*
       * Backend yako inarudisha access_token
       * baada ya registration, kwa hiyo hatuhitaji
       * kumlazimisha user kufanya login tena.
       */

      if (data.access_token) {

        saveToken(data.access_token);

        currentUser = data.user || null;

        toast(
          'Account created successfully!'
        );

        showApp();

      } else {

        toast(
          'Account created. Please login.'
        );

        const loginTab =
          document.querySelector(
            '[data-tab="login"]'
          );

        if (loginTab) {
          loginTab.click();
        }
      }

    } catch (error) {

      console.error(
        'Registration error:',
        error
      );

      toast(
        'Network error. Please check your connection.'
      );

    } finally {

      if (submitButton) {
        submitButton.disabled = false;
      }
    }

  });

}


// ============================================================
// UPDATE USER UI
// ============================================================

function updateCurrentUserUI() {

  if (!currentUser) return;

  const name =
    currentUser.full_name ||
    currentUser.username ||
    'User';

  const username =
    currentUser.username ||
    'user';

  const avatarLetter =
    name.charAt(0).toUpperCase();

  const profileName = $('#profile-name');

  if (profileName) {
    profileName.textContent = name;
  }

  const profileUsername =
    $('#profile-username');

  if (profileUsername) {
    profileUsername.textContent =
      `@${username}`;
  }

  const profileBio =
    $('#profile-bio');

  if (profileBio) {
    profileBio.textContent =
      currentUser.bio ||
      'Welcome to Msafiri Global Media';
  }

  const profileAvatar =
    $('#profile-avatar');

  if (profileAvatar) {
    profileAvatar.textContent =
      avatarLetter;
  }
}


// ============================================================
// NAVIGATION
// ============================================================

function setupNavigation() {

  $all('.nav-btn').forEach(button => {

    button.addEventListener('click', () => {

      const nav = button.dataset.nav;

      $all('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
      });

      button.classList.add('active');

      $all('.page').forEach(page => {
        page.classList.remove('active');
      });

      const targetPage =
        $(`#page-${nav}`);

      if (targetPage) {
        targetPage.classList.add('active');
      }

      const titles = {
        home: 'MSAFIRI',
        discovery: 'Discovery',
        chats: 'Chats',
        profile: 'Profile'
      };

      const pageTitle =
        $('#page-title');

      if (pageTitle) {
        pageTitle.textContent =
          titles[nav] || 'MSAFIRI';
      }

      navStack = [];

      const backButton =
        $('#back-btn');

      if (backButton) {
        backButton.classList.add('hidden');
      }

      if (nav === 'home') {
        loadHome();
      }

      if (nav === 'chats') {
        loadChats();
      }

      if (nav === 'profile') {
        loadProfile();
      }

      if (nav === 'discovery') {
        loadDiscovery();
      }

    });

  });

}


// ============================================================
// BACK BUTTON
// ============================================================

function setupBackButton() {

  const button = $('#back-btn');

  if (!button) return;

  button.addEventListener('click', () => {

    if (navStack.length > 0) {

      const previous =
        navStack.pop();

      if (typeof previous === 'function') {
        previous();
      }

    }

  });

}


// ============================================================
// SUB PAGE
// ============================================================

function showSubPage(title, renderFn) {

  const subPage =
    $('#page-sub');

  const subContent =
    $('#sub-content');

  if (!subPage || !subContent) return;

  const activePage =
    document.querySelector(
      '.page.active:not(#page-sub)'
    );

  navStack.push(() => {

    subPage.classList.remove('active');

    if (activePage) {
      activePage.classList.add('active');
    }

    const backButton =
      $('#back-btn');

    if (backButton) {
      backButton.classList.add('hidden');
    }

    const pageTitle =
      $('#page-title');

    if (pageTitle) {
      pageTitle.textContent = 'MSAFIRI';
    }

  });

  $all('.page').forEach(page => {
    page.classList.remove('active');
  });

  subPage.classList.add('active');

  const pageTitle =
    $('#page-title');

  if (pageTitle) {
    pageTitle.textContent = title;
  }

  const backButton =
    $('#back-btn');

  if (backButton) {
    backButton.classList.remove('hidden');
  }

  renderFn(subContent);
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

  $all('.feed-tab').forEach(tab => {

    tab.addEventListener('click', () => {

      $all('.feed-tab').forEach(t => {
        t.classList.remove('active');
      });

      tab.classList.add('active');

      currentFeed =
        tab.dataset.feed ||
        'for-you';

      loadFeed();

    });

  });

}


// ============================================================
// STORIES
// ============================================================

async function loadStories() {

  try {

    const response =
      await fetch(
        `${API}/api/stories`
      );

    if (!response.ok) return;

    const data =
      await safeJson(response);

    const bar =
      $('#stories-bar');

    if (!bar) return;

    bar
      .querySelectorAll(
        '.story-item:not(.add-story)'
      )
      .forEach(element => {
        element.remove();
      });

    (data.stories || []).forEach(story => {

      const element =
        document.createElement('div');

      element.className =
        'story-item';

      const initial =
        String(
          story.username ||
          story.user_id ||
          'U'
        )
        .charAt(0)
        .toUpperCase();

      element.innerHTML = `
        <div class="story-avatar">
          ${escape(initial)}
        </div>
        <span>
          ${escape(
            story.username ||
            `User ${story.user_id || ''}`
          )}
        </span>
      `;

      bar.appendChild(element);

    });

  } catch (error) {

    console.error(
      'Stories loading error:',
      error
    );

  }

}


// ============================================================
// FEED
// ============================================================

async function loadFeed() {

  const feed =
    $('#feed');

  if (!feed) return;

  feed.innerHTML = `
    <p class="muted"
       style="text-align:center;padding:20px;">
      Loading...
    </p>
  `;

  try {

    const response =
      await authFetch(
        `${API}/api/feed?type=${encodeURIComponent(currentFeed)}`
      );

    if (!response.ok) {

      if (response.status === 401) {
        handleUnauthorized();
        return;
      }

      throw new Error(
        `Feed HTTP ${response.status}`
      );
    }

    const data =
      await safeJson(response);

    if (
      !data.posts ||
      data.posts.length === 0
    ) {

      feed.innerHTML = `
        <p class="muted"
           style="text-align:center;padding:40px 20px;">
          No posts yet. Be the first to share!
        </p>
      `;

      return;
    }

    feed.innerHTML = '';

    data.posts.forEach(post => {

      feed.appendChild(
        renderPost(post)
      );

    });

  } catch (error) {

    console.error(
      'Feed loading error:',
      error
    );

    feed.innerHTML = `
      <p class="muted"
         style="text-align:center;padding:20px;">
        Failed to load feed
      </p>
    `;

  }

}


// ============================================================
// RENDER POST
// ============================================================

function renderPost(post) {

  const element =
    document.createElement('div');

  element.className =
    'post-card';

  const userName =
    post.username ||
    post.full_name ||
    `User ${post.user_id || ''}`;

  const initial =
    userName
      .charAt(0)
      .toUpperCase();

  let mediaHTML = '';

  if (post.media_url) {

    const mediaType =
      post.media_type ||
      '';

    if (
      mediaType === 'video' ||
      mediaType.startsWith('video')
    ) {

      mediaHTML = `
        <video
          class="post-media"
          controls
          playsinline
          src="${escapeAttr(post.media_url)}">
        </video>
      `;

    } else {

      mediaHTML = `
        <img
          class="post-media"
          src="${escapeAttr(post.media_url)}"
          alt="Post media"
          loading="lazy">
      `;

    }

  }

  element.innerHTML = `

    <div class="post-header">

      <div class="post-avatar">
        ${escape(initial)}
      </div>

      <div class="post-user">

        <strong>
          ${escape(userName)}
        </strong>

        <span>
          ${timeAgo(post.created_at)}
        </span>

      </div>

    </div>

    ${
      post.caption
        ? `
          <p class="post-caption">
            ${escape(post.caption)}
          </p>
        `
        : ''
    }

    ${mediaHTML}

    <div class="post-actions">

      <button
        type="button"
        onclick="toggleLike(this)">
        ❤️ ${Number(post.likes || 0)}
      </button>

      <button type="button">
        💬 ${Number(post.comments || 0)}
      </button>

      <button
        type="button"
        onclick="sharePost(${Number(post.id || 0)})">
        ↗️ Share
      </button>

      <button
        type="button"
        onclick="savePost(this)">
        🔖 Save
      </button>

    </div>

  `;

  return element;
}


// ============================================================
// LIKE
// ============================================================

window.toggleLike = function(button) {

  if (!button) return;

  button.classList.toggle('liked');

};


// ============================================================
// SHARE
// ============================================================

window.sharePost = async function(postId) {

  try {

    if (
      navigator.share
    ) {

      await navigator.share({
        title: 'MSAFIRI GLOBAL MEDIA',
        text: 'Check out this post on MSAFIRI GLOBAL MEDIA',
        url: window.location.href
      });

    } else {

      await navigator.clipboard.writeText(
        window.location.href
      );

      toast('Link copied');

    }

  } catch (error) {

    console.log(
      'Share cancelled or unavailable:',
      error
    );

  }

};


// ============================================================
// SAVE
// ============================================================

window.savePost = function(button) {

  if (!button) return;

  button.classList.toggle('saved');

  toast(
    button.classList.contains('saved')
      ? 'Post saved'
      : 'Post removed from saved'
  );

};


// ============================================================
// DISCOVERY
// ============================================================

async function loadDiscovery() {

  try {

    const response =
      await fetch(
        `${API}/api/discovery`
      );

    if (!response.ok) return;

    const data =
      await safeJson(response);

    const grid =
      $('#discovery-grid');

    if (!grid) return;

    grid.innerHTML = '';

    (data.cards || []).forEach(card => {

      const element =
        document.createElement('div');

      element.className =
        'disc-card';

      element.innerHTML = `
        <span class="icon">
          ${escape(card.icon || '')}
        </span>

        <div class="title">
          ${escape(card.title || '')}
        </div>

        <div class="desc">
          ${escape(card.desc || '')}
        </div>
      `;

      element.addEventListener(
        'click',
        () => {
          handleDiscoveryCard(
            card.id,
            card.title
          );
        }
      );

      grid.appendChild(element);

    });

  } catch (error) {

    console.error(
      'Discovery loading error:',
      error
    );

  }

}


// ============================================================
// DISCOVERY HANDLER
// ============================================================

function handleDiscoveryCard(id, title) {

  const handlers = {

    'ai-council':
      showAICouncil,

    'creative-studio':
      showStudio,

    'market':
      showMarket,

    'world-map':
      showWorldMap,

    'channels':
      showChannels,

    'communities':
      showCommunities,

    'videos':
      showVideos,

    'settings':
      showSettings

  };

  const handler =
    handlers[id];

  if (handler) {

    handler(title);

  } else {

    toast('Coming soon');

  }

}


// ============================================================
// AI COUNCIL
// ============================================================

async function showAICouncil() {

  showSubPage(
    'AI Council',
    async content => {

      content.innerHTML = `
        <h2>AI Council</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          Choose an AI assistant
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/ai-council`
          );

        const data =
          await safeJson(response);

        (data.ais || []).forEach(ai => {

          const element =
            document.createElement('div');

          element.className =
            'sub-item';

          element.innerHTML = `
            <span class="icon">
              ${escape(ai.icon || '🤖')}
            </span>

            <div class="text">

              <strong>
                ${escape(ai.title || '')}
              </strong>

              <span>
                ${escape(ai.desc || '')}
              </span>

            </div>
          `;

          element.addEventListener(
            'click',
            () => {

              if (ai.id === 'education') {

                showEducationAICountries();

              } else {

                showAIChat(ai.id);

              }

            }
          );

          content.appendChild(element);

        });

      } catch (error) {

        content.innerHTML += `
          <p class="muted">
            Failed to load AI Council.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// EDUCATION AI — COUNTRIES
// ============================================================

async function showEducationAICountries() {

  showSubPage(
    'Education AI',
    async content => {

      content.innerHTML = `
        <h2>Step 1 — Choose Country</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          Select your country
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/ai-council/countries`
          );

        const data =
          await safeJson(response);

        (data.countries || []).forEach(country => {

          const element =
            document.createElement('div');

          element.className =
            'sub-item';

          element.innerHTML = `
            <span class="icon">🌍</span>

            <div class="text">
              <strong>
                ${escape(country)}
              </strong>
            </div>
          `;

          element.addEventListener(
            'click',
            () => {
              showEducationAILevels(
                country
              );
            }
          );

          content.appendChild(element);

        });

      } catch {

        content.innerHTML += `
          <p class="muted">
            Failed to load countries.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// EDUCATION AI — LEVELS
// ============================================================

async function showEducationAILevels(country) {

  showSubPage(
    `Education — ${country}`,
    async content => {

      content.innerHTML = `
        <h2>Step 2 — Choose Level</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          ${escape(country)}
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/ai-council/levels`
          );

        const data =
          await safeJson(response);

        (data.levels || []).forEach(level => {

          const element =
            document.createElement('div');

          element.className =
            'sub-item';

          element.innerHTML = `
            <span class="icon">🎓</span>

            <div class="text">
              <strong>
                ${escape(level)}
              </strong>
            </div>
          `;

          element.addEventListener(
            'click',
            () => {
              showEducationAIContent(
                country,
                level
              );
            }
          );

          content.appendChild(element);

        });

      } catch {

        content.innerHTML += `
          <p class="muted">
            Failed to load levels.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// EDUCATION AI — CONTENT TYPES
// ============================================================

async function showEducationAIContent(
  country,
  level
) {

  showSubPage(
    `Education — ${level}`,
    async content => {

      content.innerHTML = `
        <h2>Step 3 — Choose Content</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          ${escape(country)} •
          ${escape(level)}
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/ai-council/content-types`
          );

        const data =
          await safeJson(response);

        (data.content_types || []).forEach(
          contentType => {

            const element =
              document.createElement('div');

            element.className =
              'sub-item';

            element.innerHTML = `
              <span class="icon">📄</span>

              <div class="text">
                <strong>
                  ${escape(contentType)}
                </strong>
              </div>
            `;

            element.addEventListener(
              'click',
              () => {

                showAIChat(
                  'education',
                  {
                    country,
                    level,
                    content: contentType
                  }
                );

              }
            );

            content.appendChild(element);

          }
        );

      } catch {

        content.innerHTML += `
          <p class="muted">
            Failed to load content types.
          </p>
        `;

      }

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
    'AI Chat',
    content => {

      const aiName =
        ai.charAt(0).toUpperCase() +
        ai.slice(1);

      content.innerHTML = `

        <h2>
          ${escape(aiName)} AI
        </h2>

        <div
          id="chat-msgs"
          class="chat-msgs">

          <div class="msg ai">
            Hello! I'm your
            ${escape(context.content || '')}
            assistant for
            ${escape(context.level || '')}
            curriculum in
            ${escape(context.country || '')}.
            Ask me anything.
          </div>

        </div>

        <div
          class="search-bar"
          style="
            display:flex;
            gap:8px;
            margin-top:12px;
          ">

          <input
            type="text"
            id="ai-input"
            placeholder="Ask a question..."
            style="flex:1;">

          <button
            class="btn-primary"
            id="ai-send"
            style="padding:12px 20px;">
            Send
          </button>

        </div>

      `;

      const sendMessage =
        async () => {

          const input =
            $('#ai-input');

          if (!input) return;

          const question =
            input.value.trim();

          if (!question) return;

          const messages =
            $('#chat-msgs');

          if (!messages) return;

          messages.innerHTML += `
            <div class="msg user">
              ${escape(question)}
            </div>
          `;

          input.value = '';

          messages.scrollTop =
            messages.scrollHeight;

          try {

            const params =
              new URLSearchParams();

            params.set(
              'ai',
              ai
            );

            params.set(
              'country',
              context.country || 'Tanzania'
            );

            params.set(
              'level',
              context.level || 'Degree'
            );

            params.set(
              'content',
              context.content || 'Notes'
            );

            params.set(
              'q',
              question
            );

            const response =
              await fetch(
                `${API}/api/ai-council/chat?${params.toString()}`
              );

            const data =
              await safeJson(response);

            messages.innerHTML += `
              <div class="msg ai">
                ${escape(
                  data.reply ||
                  'No response available.'
                )}
              </div>
            `;

            messages.scrollTop =
              messages.scrollHeight;

          } catch {

            messages.innerHTML += `
              <div class="msg ai">
                Error reaching AI.
              </div>
            `;

          }

        };

      const sendButton =
        $('#ai-send');

      if (sendButton) {
        sendButton.addEventListener(
          'click',
          sendMessage
        );
      }

      const input =
        $('#ai-input');

      if (input) {

        input.addEventListener(
          'keypress',
          event => {

            if (
              event.key === 'Enter'
            ) {

              event.preventDefault();

              sendMessage();

            }

          }
        );

      }

    }
  );

}


// ============================================================
// CREATIVE STUDIO
// ============================================================

async function showStudio() {

  showSubPage(
    'Creative Studio',
    async content => {

      content.innerHTML = `
        <h2>Creative Studio</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          Canva-style tools
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/studio`
          );

        const data =
          await safeJson(response);

        (data.tools || []).forEach(tool => {

          const element =
            document.createElement('div');

          element.className =
            'sub-item';

          element.innerHTML = `
            <span class="icon">
              ${escape(tool.icon || '✨')}
            </span>

            <div class="text">

              <strong>
                ${escape(tool.title || '')}
              </strong>

              <span>
                ${escape(tool.desc || '')}
              </span>

            </div>
          `;

          element.addEventListener(
            'click',
            () => {
              toast(
                `${tool.title} coming soon`
              );
            }
          );

          content.appendChild(element);

        });

      } catch {

        content.innerHTML += `
          <p class="muted">
            Failed to load Creative Studio.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// MARKET
// ============================================================

async function showMarket() {

  showSubPage(
    'Market',
    async content => {

      content.innerHTML = `
        <h2>Market</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          Buy and sell
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/market/categories`
          );

        const data =
          await safeJson(response);

        (data.categories || []).forEach(category => {

          const element =
            document.createElement('div');

          element.className =
            'sub-item';

          element.innerHTML = `
            <span class="icon">🛍️</span>

            <div class="text">

              <strong>
                ${escape(category.title || '')}
              </strong>

              <span>
                ${escape(category.desc || '')}
              </span>

            </div>
          `;

          element.addEventListener(
            'click',
            () => {

              toast(
                `${category.title} — coming soon`
              );

            }
          );

          content.appendChild(element);

        });

      } catch {

        content.innerHTML += `
          <p class="muted">
            Failed to load Market.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// WORLD MAP
// ============================================================

async function showWorldMap() {

  showSubPage(
    'World Map',
    async content => {

      content.innerHTML = `
        <h2>World Map</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          Explore the world
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/world-map/countries`
          );

        const data =
          await safeJson(response);

        (data.countries || []).forEach(country => {

          const element =
            document.createElement('div');

          element.className =
            'sub-item';

          element.innerHTML = `
            <span class="icon">🌍</span>

            <div class="text">

              <strong>
                ${escape(country.name)}
              </strong>

              <span>
                ${Number(country.users || 0)}
                users •
                ${Number(country.posts || 0)}
                posts
              </span>

            </div>
          `;

          element.addEventListener(
            'click',
            () => {
              toast(
                `${country.name} — coming soon`
              );
            }
          );

          content.appendChild(element);

        });

      } catch {

        content.innerHTML += `
          <p class="muted">
            Failed to load World Map.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// CHANNELS
// ============================================================

async function showChannels() {

  showSubPage(
    'Channels',
    async content => {

      content.innerHTML = `
        <h2>Channels</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          News and media
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/channels`
          );

        const data =
          await safeJson(response);

        (data.channels || []).forEach(channel => {

          const element =
            document.createElement('div');

          element.className =
            'sub-item';

          element.innerHTML = `
            <span class="icon">📺</span>

            <div class="text">

              <strong>
                ${escape(channel.name)}
              </strong>

              <span>
                ${escape(channel.desc || '')}
              </span>

            </div>
          `;

          element.addEventListener(
            'click',
            () => {

              toast(
                `${channel.name} — coming soon`
              );

            }
          );

          content.appendChild(element);

        });

      } catch {

        content.innerHTML += `
          <p class="muted">
            Failed to load Channels.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// COMMUNITIES
// ============================================================

async function showCommunities() {

  showSubPage(
    'Communities',
    async content => {

      content.innerHTML = `
        <h2>Communities</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          Join groups
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/communities/categories`
          );

        const data =
          await safeJson(response);

        (data.categories || []).forEach(category => {

          const element =
            document.createElement('div');

          element.className =
            'sub-item';

          element.innerHTML = `
            <span class="icon">👥</span>

            <div class="text">

              <strong>
                ${escape(category.title)}
              </strong>

              <span>
                ${escape(category.desc || '')}
              </span>

            </div>
          `;

          element.addEventListener(
            'click',
            () => {

              toast(
                `${category.title} — coming soon`
              );

            }
          );

          content.appendChild(element);

        });

      } catch {

        content.innerHTML += `
          <p class="muted">
            Failed to load Communities.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// VIDEOS
// ============================================================

async function showVideos() {

  showSubPage(
    'Videos',
    content => {

      content.innerHTML = `

        <h2>Videos</h2>

        <p class="muted"
           style="margin-bottom:16px;">
          Short video feed
        </p>

        <div class="sub-item">

          <span class="icon">
            ▶️
          </span>

          <div class="text">

            <strong>
              Coming soon
            </strong>

            <span>
              TikTok-style feed
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
    'Settings',
    content => {

      content.innerHTML = `

        <h2>Settings</h2>

        <div
          class="sub-item"
          id="s-manual">

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
          id="s-theme">

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

        <div class="sub-item">

          <span class="icon">
            ℹ️
          </span>

          <div class="text">
            <strong>
              Version
            </strong>

            <span>
              MSAFIRI GLOBAL MEDIA V6.0.0-PHASE2
            </span>
          </div>

        </div>

        <div
          class="sub-item"
          id="s-logout">

          <span class="icon">
            🚪
          </span>

          <div class="text">
            <strong>
              Logout
            </strong>

            <span>
              Sign out of your account
            </span>
          </div>

        </div>

      `;

      const manual =
        $('#s-manual');

      if (manual) {
        manual.addEventListener(
          'click',
          showUserManual
        );
      }

      const theme =
        $('#s-theme');

      if (theme) {
        theme.addEventListener(
          'click',
          toggleTheme
        );
      }

      const logoutButton =
        $('#s-logout');

      if (logoutButton) {
        logoutButton.addEventListener(
          'click',
          logout
        );
      }

    }
  );

}


// ============================================================
// USER MANUAL
// ============================================================

async function showUserManual() {

  showSubPage(
    'User Manual',
    async content => {

      content.innerHTML = `
        <p class="muted">
          Loading user manual...
        </p>
      `;

      try {

        const response =
          await fetch(
            `${API}/api/user-manual`
          );

        const manual =
          await safeJson(response);

        content.innerHTML = `

          <div
            style="
              text-align:center;
              margin-bottom:20px;
            ">

            <div
              class="auth-logo"
              style="margin:0 auto 12px;">
              M
            </div>

            <h2>
              ${escape(manual.app || '')}
            </h2>

            <p class="muted">
              ${escape(manual.tagline || '')}
            </p>

            <p
              class="muted"
              style="margin-top:4px;">

              Founder:
              ${escape(manual.founder || '')}

            </p>

            <p class="muted">
              ${escape(manual.company || '')}
            </p>

            <p class="muted">
              Version:
              ${escape(manual.version || '')}
            </p>

          </div>

          <div class="manual-section">

            <h3>
              About
            </h3>

            <p>
              ${escape(manual.about || '')}
            </p>

          </div>

          <div class="manual-section">

            <h3>
              Sections
            </h3>

            <ul>

              ${Object.entries(
                manual.sections || {}
              )
                .map(
                  ([key, value]) => `
                    <li>
                      <strong>
                        ${escape(key)}:
                      </strong>
                      ${escape(value)}
                    </li>
                  `
                )
                .join('')}

            </ul>

          </div>

          <div class="manual-section">

            <h3>
              How to Use
            </h3>

            <ul>

              ${Object.entries(
                manual.how_to_use || {}
              )
                .map(
                  ([key, value]) => `
                    <li>
                      <strong>
                        ${escape(
                          key.replaceAll('_', ' ')
                        )}:
                      </strong>
                      ${escape(value)}
                    </li>
                  `
                )
                .join('')}

            </ul>

          </div>

          <div class="manual-section">

            <h3>
              Support
            </h3>

            <p>
              ${escape(manual.support || '')}
            </p>

          </div>

          <button
            class="btn-primary"
            id="dl-manual"
            style="
              width:100%;
              margin-top:16px;
            ">

            📥 Download User Manual

          </button>

        `;

        const downloadButton =
          $('#dl-manual');

        if (downloadButton) {

          downloadButton.addEventListener(
            'click',
            () => {

              const text = `MSAFIRI GLOBAL MEDIA
${manual.tagline || ''}

Founder: ${manual.founder || ''}
Company: ${manual.company || ''}
Version: ${manual.version || ''}

ABOUT
${manual.about || ''}

SECTIONS
${Object.entries(
  manual.sections || {}
)
  .map(
    ([key, value]) =>
      `- ${key}: ${value}`
  )
  .join('\n')}

HOW TO USE
${Object.entries(
  manual.how_to_use || {}
)
  .map(
    ([key, value]) =>
      `- ${key}: ${value}`
  )
  .join('\n')}

SUPPORT
${manual.support || ''}
`;

              const blob =
                new Blob(
                  [text],
                  {
                    type:
                      'text/plain;charset=utf-8'
                  }
                );

              const url =
                URL.createObjectURL(blob);

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

              URL.revokeObjectURL(url);

              toast('Downloaded!');

            }
          );

        }

      } catch (error) {

        console.error(
          'Manual error:',
          error
        );

        content.innerHTML = `
          <p class="muted">
            Failed to load User Manual.
          </p>
        `;

      }

    }
  );

}


// ============================================================
// DOTS MENU
// ============================================================

function setupDotsMenu() {

  const dotsButton =
    $('#dots-btn');

  const dotsMenu =
    $('#dots-menu');

  if (!dotsButton || !dotsMenu) {
    return;
  }

  dotsButton.addEventListener(
    'click',
    event => {

      event.stopPropagation();

      dotsMenu.classList.toggle(
        'hidden'
      );

    }
  );

  document.addEventListener(
    'click',
    () => {

      dotsMenu.classList.add(
        'hidden'
      );

    }
  );

  $all(
    '#dots-menu button'
  ).forEach(button => {

    button.addEventListener(
      'click',
      event => {

        event.stopPropagation();

        const action =
          button.dataset.action;

        if (action === 'manual') {
          showUserManual();
        }

        if (action === 'settings') {
          showSettings();
        }

        if (action === 'logout') {
          logout();
        }

        dotsMenu.classList.add(
          'hidden'
        );

      }
    );

  });

}


// ============================================================
// CHATS
// ============================================================

async function loadChats() {

  const list =
    $('#chat-list');

  if (!list) return;

  list.innerHTML = `
    <p class="muted"
       style="padding:20px;text-align:center;">
      Loading chats...
    </p>
  `;

  try {

    const response =
      await authFetch(
        `${API}/api/messages`
      );

    if (response.status === 401) {

      handleUnauthorized();

      return;
    }

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
      await safeJson(response);

    if (
      !data.messages ||
      data.messages.length === 0
    ) {

      list.innerHTML = `
        <p class="muted"
           style="padding:20px;text-align:center;">
          No chats yet
        </p>
      `;

      return;
    }

    list.innerHTML = '';

    data.messages.forEach(message => {

      const element =
        document.createElement('div');

      element.className =
        'sub-item';

      element.innerHTML = `
        <span class="icon">
          💬
        </span>

        <div class="text">

          <strong>
            ${escape(
              message.username ||
              message.sender_username ||
              'User'
            )}
          </strong>

          <span>
            ${escape(
              message.content ||
              message.text ||
              ''
            )}
          </span>

        </div>
      `;

      list.appendChild(element);

    });

  } catch (error) {

    console.error(
      'Chats loading error:',
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

    let user =
      currentUser;

    if (!user) {

      const response =
        await authFetch(
          `${API}/api/auth/me`
        );

      if (!response.ok) {

        if (
          response.status === 401
        ) {
          handleUnauthorized();
        }

        return;
      }

      user =
        await safeJson(response);

      currentUser =
        user;
    }

    updateCurrentUserUI();

  } catch (error) {

    console.error(
      'Profile loading error:',
      error
    );

  }

}


// ============================================================
// UNAUTHORIZED HANDLER
// ============================================================

function handleUnauthorized() {

  removeToken();

  currentUser = null;

  showAuth();

  toast(
    'Your session has expired. Please login again.'
  );

}


// ============================================================
// LOGOUT
// ============================================================

async function logout() {

  try {

    await authFetch(
      `${API}/api/auth/logout`,
      {
        method: 'POST'
      }
    );

  } catch (error) {

    console.log(
      'Logout request failed:',
      error
    );

  } finally {

    removeToken();

    currentUser = null;

    navStack = [];

    location.reload();

  }

}


// ============================================================
// THEME
// ============================================================

function toggleTheme() {

  const body =
    document.body;

  const isInverted =
    body.dataset.themeInverted === 'true';

  if (isInverted) {

    body.style.filter = '';

    body.dataset.themeInverted =
      'false';

    localStorage.setItem(
      'msafiri_theme',
      'normal'
    );

    toast('Light mode');

  } else {

    body.style.filter =
      'invert(1) hue-rotate(180deg)';

    body.dataset.themeInverted =
      'true';

    localStorage.setItem(
      'msafiri_theme',
      'inverted'
    );

    toast('Dark mode');

  }

}


// ============================================================
// RESTORE THEME
// ============================================================

function restoreTheme() {

  const theme =
    localStorage.getItem(
      'msafiri_theme'
    );

  if (
    theme === 'inverted'
  ) {

    document.body.style.filter =
      'invert(1) hue-rotate(180deg)';

    document.body.dataset.themeInverted =
      'true';

  }

}

restoreTheme();


// ============================================================
// TOAST
// ============================================================

function toast(message) {

  const element =
    document.createElement('div');

  element.className =
    'toast';

  element.textContent =
    String(message);

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
// HTML ESCAPING
// ============================================================

function escape(value) {

  const element =
    document.createElement('div');

  element.textContent =
    value == null
      ? ''
      : String(value);

  return element.innerHTML;

}


function escapeAttr(value) {

  return escape(value)
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

}


// ============================================================
// TIME AGO
// ============================================================

function timeAgo(iso) {

  if (!iso) {
    return 'now';
  }

  const timestamp =
    new Date(iso).getTime();

  if (
    Number.isNaN(timestamp)
  ) {
    return 'now';
  }

  const seconds =
    Math.floor(
      (Date.now() - timestamp) / 1000
    );

  if (seconds < 0) {
    return 'now';
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

  if (seconds < 604800) {
    return `${Math.floor(
      seconds / 86400
    )}d`;
  }

  return new Date(
    iso
  ).toLocaleDateString();

}


// ============================================================
// GLOBAL ERROR HANDLERS
// ============================================================

window.addEventListener(
  'unhandledrejection',
  event => {

    console.error(
      'Unhandled promise rejection:',
      event.reason
    );

  }
);


window.addEventListener(
  'error',
  event => {

    console.error(
      'Application error:',
      event.error || event.message
    );

  }
);


// ============================================================
// DEBUG HELPERS
// ============================================================

window.MSAFIRI = {

  getCurrentUser() {
    return currentUser;
  },

  getToken() {
    return getToken();
  },

  clearSession() {
    removeToken();
    currentUser = null;
    location.reload();
  },

  async checkAuth() {
    return checkAuth();
  },

  async health() {

    try {

      const response =
        await fetch(
          `${API}/api/health`
        );

      return await safeJson(
        response
      );

    } catch (error) {

      console.error(
        'Health check failed:',
        error
      );

      return null;
    }

  }

};


// ============================================================
// END OF MSAFIRI GLOBAL MEDIA APP.JS
// ============================================================
