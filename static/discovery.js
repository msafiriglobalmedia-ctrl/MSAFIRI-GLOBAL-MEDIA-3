/* ============================================================
   MSAFIRI GLOBAL MEDIA — Discovery + Continuous Navigation
   Version: Media V0.0.1
   Purpose: AI Council, Studio, Market, World Map, Channels,
            Communities, Videos, Settings
   ============================================================ */

// ------------------------------------------------------------
// 1. NAVIGATION STACK (Continuous Navigation)
// ------------------------------------------------------------
let navStack = [];
let originalDiscoveryHTML = "";

/**
 * Push a page to the navigation stack
 */
function pushNav(pageFunction, title) {
    navStack.push({ pageFunction, title });
}

/**
 * Go back to the previous page
 */
function goBack() {
    navStack.pop(); // Remove current page
    if (navStack.length > 0) {
        const prev = navStack[navStack.length - 1];
        prev.pageFunction();
    } else {
        loadDiscoveryHome();
    }
}

/**
 * Render a page header with back button
 */
function pageHeader(title) {
    return `
        <div class="page-header">
            <i class="fas fa-arrow-left back-btn" onclick="goBack()"></i>
            <h2>${title}</h2>
        </div>
    `;
}

// ------------------------------------------------------------
// 2. MAIN DISCOVERY PAGE
// ------------------------------------------------------------

/**
 * Load Discovery home (grid of 8 cards)
 */
function loadDiscovery() {
    navStack = [];
    const container = document.getElementById("page-discovery");
    if (!container) return;

    container.classList.add("active");
    container.innerHTML = originalDiscoveryHTML || getDiscoveryGridHTML();
}

/**
 * Get Discovery grid HTML
 */
function getDiscoveryGridHTML() {
    return `
        <h2 style="margin-bottom: 15px;">Discovery</h2>
        <div class="discovery-grid">
            <div class="discovery-card" onclick="openAICouncil()">
                <i class="fas fa-book"></i>
                <h3>AI Council</h3>
                <p>Education, Health, Agriculture, Research</p>
            </div>
            <div class="discovery-card" onclick="openStudio()">
                <i class="fas fa-image"></i>
                <h3>Creative Studio</h3>
                <p>Image, Video, Documents</p>
            </div>
            <div class="discovery-card" onclick="openMarket()">
                <i class="fas fa-shopping-bag"></i>
                <h3>Market</h3>
                <p>Products, Services, Digital</p>
            </div>
            <div class="discovery-card" onclick="openWorldMap()">
                <i class="fas fa-globe"></i>
                <h3>World Map</h3>
                <p>Explore the world</p>
            </div>
            <div class="discovery-card" onclick="openChannels()">
                <i class="fas fa-tv"></i>
                <h3>Channels</h3>
                <p>BBC, CNN, Al Jazeera</p>
            </div>
            <div class="discovery-card" onclick="openCommunities()">
                <i class="fas fa-users"></i>
                <h3>Communities</h3>
                <p>Join groups and communities</p>
            </div>
            <div class="discovery-card" onclick="openVideos()">
                <i class="fas fa-play"></i>
                <h3>Videos</h3>
                <p>Short videos feed</p>
            </div>
            <div class="discovery-card" onclick="openSettings()">
                <i class="fas fa-cog"></i>
                <h3>Settings</h3>
                <p>App preferences</p>
            </div>
        </div>
    `;
}

// ------------------------------------------------------------
// 3. AI COUNCIL
// ------------------------------------------------------------

function openAICouncil() {
    pushNav(openAICouncil, "AI Council");
    const container = document.getElementById("page-discovery");
    container.innerHTML = `
        ${pageHeader("AI Council")}
        <div class="discovery-grid">
            <div class="discovery-card" onclick="openEducationAI()">
                <i class="fas fa-book"></i>
                <h3>Education AI</h3>
                <p>Study notes, syllabus, past papers</p>
            </div>
            <div class="discovery-card" onclick="openHealthAI()">
                <i class="fas fa-heart"></i>
                <h3>Health AI</h3>
                <p>General health information</p>
            </div>
            <div class="discovery-card" onclick="openAgricultureAI()">
                <i class="fas fa-leaf"></i>
                <h3>Agriculture AI</h3>
                <p>Crops, soil, farming</p>
            </div>
            <div class="discovery-card" onclick="openResearchAI()">
                <i class="fas fa-search"></i>
                <h3>Research AI</h3>
                <p>Methodology, citations</p>
            </div>
            <div class="discovery-card" onclick="openAICanvas()">
                <i class="fas fa-drafting-compass"></i>
                <h3>AI Canvas</h3>
                <p>Workspace with documents</p>
            </div>
        </div>
    `;
}

// ------------------------------------------------------------
// 4. EDUCATION AI — Continuous Navigation
// ------------------------------------------------------------

function openEducationAI() {
    pushNav(openEducationAI, "Education AI");
    const countries = [
        "Tanzania", "Kenya", "Uganda", "Rwanda", "Burundi",
        "South Africa", "Nigeria", "Ghana", "UK", "USA",
        "Canada", "Australia", "India", "China", "Japan",
        "Germany", "France", "Brazil"
    ];

    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Education AI — Choose Country")}
        <div class="list">
            ${countries.map(c => `
                <div class="list-item" onclick="chooseLevel('${c}')">
                    <i class="fas fa-flag"></i> ${c}
                </div>
            `).join("")}
        </div>
    `;
}

function chooseLevel(country) {
    pushNav(() => chooseLevel(country), `Level — ${country}`);
    const levels = [
        "Nursery", "Primary", "Secondary", "High School",
        "Certificate", "Diploma", "Degree", "Master", "PhD"
    ];

    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader(`Choose Level — ${country}`)}
        <div class="list">
            ${levels.map(l => `
                <div class="list-item" onclick="chooseContent('${country}', '${l}')">
                    <i class="fas fa-graduation-cap"></i> ${l}
                </div>
            `).join("")}
        </div>
    `;
}

function chooseContent(country, level) {
    pushNav(() => chooseContent(country, level), `Content — ${level}`);
    const contentTypes = ["Notes", "Books", "Past Papers", "Marking Schemes"];

    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader(`Choose Content — ${level} in ${country}`)}
        <div class="list">
            ${contentTypes.map(c => `
                <div class="list-item" onclick="startAIChat('${country}', '${level}', '${c}')">
                    <i class="fas fa-file-alt"></i> ${c}
                </div>
            `).join("")}
        </div>
    `;
}

function startAIChat(country, level, contentType) {
    pushNav(() => startAIChat(country, level, contentType), "AI Chat");

    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader(`${contentType} Assistant`)}
        <div class="ai-chat">
            <div class="chat-messages" id="ai-messages">
                <div class="ai-message">
                    <p>Hello! I'm your <strong>${contentType}</strong> assistant for 
                    <strong>${level}</strong> curriculum in <strong>${country}</strong>. 
                    Ask me anything about a subject or topic.</p>
                </div>
            </div>
            <div class="chat-input">
                <input type="text" id="ai-input" placeholder="Ask a question..." 
                       onkeypress="if(event.key==='Enter') sendAIMessage('${country}', '${level}', '${contentType}')">
                <button onclick="sendAIMessage('${country}', '${level}', '${contentType}')">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        </div>
    `;
}

function sendAIMessage(country, level, contentType) {
    const input = document.getElementById("ai-input");
    const msg = input.value.trim();
    if (!msg) return;

    const messages = document.getElementById("ai-messages");
    messages.innerHTML += `<div class="user-message"><p>${msg}</p></div>`;
    input.value = "";
    messages.scrollTop = messages.scrollHeight;

    // TODO: Connect to Gemini API (Phase 6)
    setTimeout(() => {
        messages.innerHTML += `
            <div class="ai-message">
                <p>AI response coming soon (Phase 6 — Gemini integration). 
                You asked about <strong>${msg}</strong> in ${contentType} for ${level} (${country}).</p>
            </div>
        `;
        messages.scrollTop = messages.scrollHeight;
    }, 800);
}

function openHealthAI() {
    pushNav(openHealthAI, "Health AI");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Health AI")}
        <div class="placeholder-content">
            <i class="fas fa-heart" style="font-size:60px; color:var(--primary);"></i>
            <p>Health AI — Coming in Phase 6</p>
        </div>
    `;
}

function openAgricultureAI() {
    pushNav(openAgricultureAI, "Agriculture AI");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Agriculture AI")}
        <div class="placeholder-content">
            <i class="fas fa-leaf" style="font-size:60px; color:var(--primary);"></i>
            <p>Agriculture AI — Coming in Phase 6</p>
        </div>
    `;
}

function openResearchAI() {
    pushNav(openResearchAI, "Research AI");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Research AI")}
        <div class="placeholder-content">
            <i class="fas fa-search" style="font-size:60px; color:var(--primary);"></i>
            <p>Research AI — Coming in Phase 6</p>
        </div>
    `;
}

function openAICanvas() {
    pushNav(openAICanvas, "AI Canvas");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("AI Canvas")}
        <div class="placeholder-content">
            <i class="fas fa-drafting-compass" style="font-size:60px; color:var(--primary);"></i>
            <p>AI Canvas — Workspace with documents (Phase 6)</p>
        </div>
    `;
}

// ------------------------------------------------------------
// 5. CREATIVE STUDIO
// ------------------------------------------------------------

function openStudio() {
    pushNav(openStudio, "Creative Studio");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Creative Studio")}
        <div class="discovery-grid">
            <div class="discovery-card" onclick="openStudioTool('Image Creator')">
                <i class="fas fa-image"></i>
                <h3>Image Creator</h3>
                <p>Posters, covers, thumbnails</p>
            </div>
            <div class="discovery-card" onclick="openStudioTool('Video Creator')">
                <i class="fas fa-video"></i>
                <h3>Video Creator</h3>
                <p>Short videos, editing</p>
            </div>
            <div class="discovery-card" onclick="openStudioTool('Document Creator')">
                <i class="fas fa-file-alt"></i>
                <h3>Document Creator</h3>
                <p>Documents, resources</p>
            </div>
            <div class="discovery-card" onclick="openStudioTool('Design Assistant')">
                <i class="fas fa-magic"></i>
                <h3>Design Assistant</h3>
                <p>AI-assisted creative ideas</p>
            </div>
        </div>
    `;
}

function openStudioTool(tool) {
    pushNav(() => openStudioTool(tool), tool);
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader(tool)}
        <div class="placeholder-content">
            <i class="fas fa-tools" style="font-size:60px; color:var(--primary);"></i>
            <p>${tool} — Coming in Phase 7 (Canva-style editor)</p>
        </div>
    `;
}

// ------------------------------------------------------------
// 6. MARKET
// ------------------------------------------------------------

function openMarket() {
    pushNav(openMarket, "Market");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("MSAFIRI MARKET")}
        <div class="search-bar-container">
            <i class="fas fa-search"></i>
            <input type="text" placeholder="Search products...">
        </div>
        <div class="discovery-grid">
            <div class="discovery-card" onclick="openMarketCategory('Products')">
                <i class="fas fa-box"></i>
                <h3>Products</h3>
            </div>
            <div class="discovery-card" onclick="openMarketCategory('Services')">
                <i class="fas fa-handshake"></i>
                <h3>Services</h3>
            </div>
            <div class="discovery-card" onclick="openMarketCategory('Digital')">
                <i class="fas fa-download"></i>
                <h3>Digital</h3>
            </div>
            <div class="discovery-card" onclick="openUploadProduct()">
                <i class="fas fa-plus-circle"></i>
                <h3>Upload Product</h3>
            </div>
        </div>
    `;
}

function openMarketCategory(category) {
    pushNav(() => openMarketCategory(category), category);
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader(category)}
        <div class="empty-state">
            <i class="fas fa-box-open"></i>
            <h3>No ${category.toLowerCase()} yet</h3>
            <p>Be the first to upload!</p>
        </div>
    `;
}

function openUploadProduct() {
    pushNav(openUploadProduct, "Upload Product");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Upload Product")}
        <form class="upload-form" onsubmit="event.preventDefault(); submitProduct();">
            <input type="text" id="product-name" placeholder="Product Name" required>
            <input type="file" id="product-image" accept="image/*">
            <textarea id="product-desc" placeholder="Description"></textarea>
            <input type="number" id="product-price" placeholder="Price (TZS)">
            <input type="text" id="product-location" placeholder="Location">
            <input type="text" id="product-contact" placeholder="Contact">
            <button type="submit">Publish</button>
        </form>
    `;
}

function submitProduct() {
    // TODO: Connect to backend (Phase 8)
    showToast("Product upload coming in Phase 8!");
}

// ------------------------------------------------------------
// 7. WORLD MAP
// ------------------------------------------------------------

function openWorldMap() {
    pushNav(openWorldMap, "World Map");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("World Map")}
        <div id="world-map" style="height:400px; background:var(--bg-card); border-radius:15px; display:flex; align-items:center; justify-content:center;">
            <i class="fas fa-globe" style="font-size:80px; color:var(--primary); opacity:0.3;"></i>
        </div>
        <p class="placeholder" style="margin-top:15px;">Interactive map coming soon...</p>
    `;
}

// ------------------------------------------------------------
// 8. CHANNELS
// ------------------------------------------------------------

function openChannels() {
    pushNav(openChannels, "Channels");
    const channels = [
        { name: "BBC News", color: "#c8102e" },
        { name: "CNN", color: "#cc0000" },
        { name: "Al Jazeera", color: "#f39c12" },
        { name: "ITV News", color: "#1e90ff" },
        { name: "MSAFIRI Global Media", color: "#4f46e5" }
    ];

    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Channels")}
        ${channels.map(c => `
            <div class="channel-item" onclick="openChannel('${c.name}')">
                <div class="channel-dot" style="background:${c.color}"></div>
                <span>${c.name}</span>
            </div>
        `).join("")}
    `;
}

function openChannel(name) {
    pushNav(() => openChannel(name), name);
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader(name)}
        <div class="empty-state">
            <i class="fas fa-tv"></i>
            <h3>${name}</h3>
            <p>Channel content coming soon...</p>
        </div>
    `;
}

// ------------------------------------------------------------
// 9. COMMUNITIES
// ------------------------------------------------------------

function openCommunities() {
    pushNav(openCommunities, "Communities");
    const categories = [
        "Education", "Technology", "Business", "Health",
        "Agriculture", "Entertainment", "Sports", "Religion", "Language"
    ];

    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Communities")}
        <div class="list">
            ${categories.map(c => `
                <div class="list-item" onclick="openCommunity('${c}')">
                    <i class="fas fa-users"></i> ${c}
                </div>
            `).join("")}
        </div>
    `;
}

function openCommunity(name) {
    pushNav(() => openCommunity(name), name);
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader(`${name} Community`)}
        <button class="primary-btn" style="margin-bottom:15px;" onclick="showToast('Joined ${name}!')">
            <i class="fas fa-plus"></i> Join Community
        </button>
        <div class="empty-state">
            <i class="fas fa-comments"></i>
            <h3>No posts yet</h3>
            <p>Be the first to post in ${name}.</p>
        </div>
    `;
}

// ------------------------------------------------------------
// 10. VIDEOS (TikTok-style)
// ------------------------------------------------------------

function openVideos() {
    pushNav(openVideos, "Videos");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Videos")}
        <div class="video-feed">
            <div class="video-item">
                <video autoplay loop muted playsinline>
                    <source src="/static/videos/sample.mp4" type="video/mp4">
                </video>
                <div class="video-actions">
                    <i class="fas fa-heart"></i>
                    <i class="fas fa-comment"></i>
                    <i class="fas fa-share"></i>
                </div>
            </div>
        </div>
    `;
}

// ------------------------------------------------------------
// 11. SETTINGS
// ------------------------------------------------------------

function openSettings() {
    pushNav(openSettings, "Settings");
    document.getElementById("page-discovery").innerHTML = `
        ${pageHeader("Settings")}
        <div class="list">
            <div class="list-item" onclick="openUserManual()">
                <i class="fas fa-book-open"></i> User Manual
            </div>
            <div class="list-item" onclick="toggleTheme()">
                <i class="fas fa-adjust"></i> Toggle Theme
            </div>
            <div class="list-item">
                <i class="fas fa-info-circle"></i> Version: MSAFIRI MEDIA V0.0.1
            </div>
            <div class="list-item" onclick="logout()">
                <i class="fas fa-sign-out-alt"></i> Logout
            </div>
        </div>
    `;
}

function toggleTheme() {
    document.body.classList.toggle("light-theme");
    showToast("Theme toggled!");
}

function logout() {
    localStorage.removeItem("STORAGE_TOKEN");
    localStorage.removeItem("STORAGE_USER");
    window.location.href = "/login";
}

// ------------------------------------------------------------
// 12. INITIALIZATION
// ------------------------------------------------------------

window.addEventListener("DOMContentLoaded", () => {
    // Save original Discovery HTML for reset
    const container = document.getElementById("page-discovery");
    if (container) {
        originalDiscoveryHTML = getDiscoveryGridHTML();
    }
});

// Expose functions globally
window.loadDiscovery = loadDiscovery;
window.openAICouncil = openAICouncil;
window.openEducationAI = openEducationAI;
window.chooseLevel = chooseLevel;
window.chooseContent = chooseContent;
window.startAIChat = startAIChat;
window.sendAIMessage = sendAIMessage;
window.openHealthAI = openHealthAI;
window.openAgricultureAI = openAgricultureAI;
window.openResearchAI = openResearchAI;
window.openAICanvas = openAICanvas;
window.openStudio = openStudio;
window.openStudioTool = openStudioTool;
window.openMarket = openMarket;
window.openMarketCategory = openMarketCategory;
window.openUploadProduct = openUploadProduct;
window.submitProduct = submitProduct;
window.openWorldMap = openWorldMap;
window.openChannels = openChannels;
window.openChannel = openChannel;
window.openCommunities = openCommunities;
window.openCommunity = openCommunity;
window.openVideos = openVideos;
window.openSettings = openSettings;
window.toggleTheme = toggleTheme;
window.logout = logout;
window.goBack = goBack;
window.pushNav = pushNav;
