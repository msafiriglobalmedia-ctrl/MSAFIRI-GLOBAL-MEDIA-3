/* ============================================================
   MSAFIRI GLOBAL MEDIA — User Manual Logic
   Version: Media V0.0.1
   Purpose: Open, close, and download User Manual
   ============================================================ */

// ------------------------------------------------------------
// 1. OPEN USER MANUAL
// ------------------------------------------------------------
function openUserManual() {
    const modal = document.getElementById("user-manual-modal");
    if (!modal) {
        console.error("User Manual modal not found in DOM");
        return;
    }
    modal.style.display = "flex";
    document.body.style.overflow = "hidden"; // Prevent background scroll
}

// ------------------------------------------------------------
// 2. CLOSE USER MANUAL
// ------------------------------------------------------------
function closeUserManual() {
    const modal = document.getElementById("user-manual-modal");
    if (!modal) return;
    modal.style.display = "none";
    document.body.style.overflow = ""; // Restore scroll
}

// ------------------------------------------------------------
// 3. DOWNLOAD USER MANUAL
// ------------------------------------------------------------
function downloadUserManual() {
    const manualContent = `
============================================================
        MSAFIRI GLOBAL MEDIA — USER MANUAL
============================================================
Version:        Media V0.0.1
Founder:        MSAFIRI WILLIAM MUNGA
Company:        ZetroLink Technology Limited
Year Founded:   2025
============================================================

------------------------------------------------------------
1. ABOUT MSAFIRI
------------------------------------------------------------
MSAFIRI GLOBAL MEDIA is a social, communication, and AI
app designed to connect people beyond borders. It combines
social networking, messaging, AI tools, marketplace, and
media into one platform.

------------------------------------------------------------
2. SECTIONS OF THE APP
------------------------------------------------------------
- Home:        Feed, Stories, Posts
- Discovery:   AI Council, Creative Studio, Market,
               World Map, Channels, Communities, Videos
- Chats:       Messaging (WhatsApp-style)
- Profile:     Your personal profile

------------------------------------------------------------
3. HOW TO USE MSAFIRI
------------------------------------------------------------
- Create account:   Register → Fill details → Create Account
- Post content:     Create (+) → Caption → Photo/Video → Post
- Share story:      "+ My Story" → Media → Post Story
- Chat:             Profile → Message icon → Type/Record
- Explore AI:       Discovery → AI Council → Choose AI
- Use Discovery:    Discovery → Choose any card (Market,
                    Studio, Channels, Communities, etc.)
- Edit profile:     Profile → Edit Profile → Save Changes
- Change photo:     Profile → Change Photo → Select from Gallery

------------------------------------------------------------
4. CONTINUOUS NAVIGATION
------------------------------------------------------------
Discovery features use continuous navigation — each step
leads to the next. Example (Education AI):

  AI Council → Education AI → Choose Country → Choose Level
  → Choose Content → AI Chat

Every page has a Back button (←) to return to the previous
step.

------------------------------------------------------------
5. STORIES
------------------------------------------------------------
- Stories disappear automatically after 24 hours
- Upload via "+ My Story" on Home
- Tap any story to view it
- Stories are shown in the horizontal bar on Home

------------------------------------------------------------
6. CHATS
------------------------------------------------------------
- View your conversations in the Chats tab
- Search chats using the search bar
- Start a new chat with the (+) button
- Send text, photos, videos, and voice notes (coming soon)

------------------------------------------------------------
7. AI COUNCIL
------------------------------------------------------------
Available AIs:
- Education AI  → Notes, Books, Past Papers, Marking Schemes
- Health AI     → General health information
- Agriculture AI → Crops, soil, farming
- Research AI   → Methodology, citations
- AI Canvas     → Workspace with documents

------------------------------------------------------------
8. CREATIVE STUDIO
------------------------------------------------------------
- Image Creator     → Posters, covers, thumbnails
- Video Creator     → Short videos, editing
- Document Creator  → Documents, resources
- Design Assistant  → AI-assisted creative ideas

------------------------------------------------------------
9. MARKET
------------------------------------------------------------
- Products     → Physical items
- Services     → Services offered
- Digital      → Digital products
- Upload       → Add your own product

------------------------------------------------------------
10. SETTINGS
------------------------------------------------------------
- User Manual   → Open this manual
- Toggle Theme  → Light/Dark mode
- Version       → Media V0.0.1
- Logout        → Sign out of your account

------------------------------------------------------------
11. SUPPORT
------------------------------------------------------------
For support, contact:

  ZetroLink Technology Limited
  Founder: MSAFIRI WILLIAM MUNGA

============================================================
© 2025 MSAFIRI GLOBAL MEDIA
Powered by ZetroLink Technology Limited
============================================================
    `.trim();

    // Create downloadable .txt file
    const blob = new Blob([manualContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "MSAFIRI-UserManual.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Show toast if available
    if (typeof showToast === "function") {
        showToast("User Manual downloaded!");
    }
}

// ------------------------------------------------------------
// 4. CLOSE ON ESC KEY
// ------------------------------------------------------------
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        const modal = document.getElementById("user-manual-modal");
        if (modal && modal.style.display === "flex") {
            closeUserManual();
        }
    }
});

// ------------------------------------------------------------
// 5. EXPOSE FUNCTIONS GLOBALLY
// ------------------------------------------------------------
window.openUserManual = openUserManual;
window.closeUserManual = closeUserManual;
window.downloadUserManual = downloadUserManual;
