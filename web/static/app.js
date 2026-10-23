// Security Helpers: Safe Fetch with Local Session Token
async function authFetch(url, options = {}) {
    options.headers = options.headers || {};
    if (localSessionToken && !options.headers["X-Local-Token"]) {
        options.headers["X-Local-Token"] = localSessionToken;
    }
    return fetch(url, options);
}

// Security Helpers: DOM XSS Prevention
function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function sanitizeUrl(url) {
    if (!url || typeof url !== "string") return "";
    const clean = url.trim();
    if (/^https:\/\/[a-zA-Z0-9_\-\.]+/i.test(clean) || 
        /^http:\/\/(127\.0\.0\.1|localhost)(:[0-9]+)?(\/.*)?$/i.test(clean) || 
        /^\/(static|output)\/[a-zA-Z0-9_\-\.\/]+$/i.test(clean) ||
        /^data:image\/(png|jpeg|jpg|webp);base64,[A-Za-z0-9+/=]+$/i.test(clean)) {
        return clean;
    }
    return "";
}

let localSessionToken = "";
async function initSessionAuth() {
    try {
        const res = await fetch("/api/session/token");
        const data = await res.json();
        if (data.status === "success" && data.token) {
            localSessionToken = data.token;
        }
    } catch (e) {
        console.warn("Session token handshake failed:", e);
    }
}
initSessionAuth();

// Global Wave - AI Agency OS Client Logic (100% Live Real YouTube Data & Premium SaaS Terminal)
document.addEventListener("DOMContentLoaded", () => {
    // State variables
    let currentTab = "dashboard";
    let activePersonaId = "de_engineer";
    let activeTaskId = null;
    let activeVideoData = null;
    let activeScenes = [];
    let personasData = {};
    let channelsData = [];
    let videoLibrary = [];
    let activeResolution = "1080p";
    let activeDuration = "45";
    let activeVideoType = "shorts";
    let activeOrientation = "vertical";
    let activeThumbPreset = "danger_red";

    // Chart instances
    let viewsChartInstance = null;
    let earningsChartInstance = null;

    // Header Elements
    const currentTabIcon = document.getElementById("currentTabIcon");
    const currentTabTitle = document.getElementById("currentTabTitle");
    const liveClock = document.getElementById("liveClock");
    const headerPersonaBadge = document.getElementById("headerPersonaBadge");
    const activePersonaBadgeText = document.getElementById("activePersonaBadgeText");
    const headerAuthBtn = document.getElementById("headerAuthBtn");

    // Sidebar Elements
    const sidebarNav = document.getElementById("sidebarNav");
    const sidebarYtAvatar = document.getElementById("sidebarYtAvatar");
    const sidebarYtDefault = document.getElementById("sidebarYtDefault");
    const sidebarYtTitle = document.getElementById("sidebarYtTitle");
    const sidebarYtSub = document.getElementById("sidebarYtSub");
    const sidebarYtPing = document.getElementById("sidebarYtPing");

    // Dashboard Elements
    const dashChannelCardTitle = document.getElementById("dashChannelCardTitle");
    const dashChannelCardBody = document.getElementById("dashChannelCardBody");
    const dash48hDelta = document.getElementById("dash48hDelta");
    const dashRetentionScore = document.getElementById("dashRetentionScore");
    const dashTotalVideos = document.getElementById("dashTotalVideos");
    const channelsGrid = document.getElementById("channelsGrid");
    const dashRecentVideos = document.getElementById("dashRecentVideos");

    // Studio Elements
    const studioPersonaList = document.getElementById("studioPersonaList");
    const studioTopicInput = document.getElementById("studioTopicInput");
    const studioRandomTopicBtn = document.getElementById("studioRandomTopicBtn");
    const studioGenerateBtn = document.getElementById("studioGenerateBtn");
    const studioEnableBgm = document.getElementById("studioEnableBgm");
    const studioBgmRange = document.getElementById("studioBgmRange");
    const studioBgmVal = document.getElementById("studioBgmVal");
    const studioPercent = document.getElementById("studioPercent");
    const studioProgressBar = document.getElementById("studioProgressBar");
    const studioStageMsg = document.getElementById("studioStageMsg");
    const studioVideoPlayer = document.getElementById("studioVideoPlayer");
    const studioVideoEmpty = document.getElementById("studioVideoEmpty");
    const studioActiveTitle = document.getElementById("studioActiveTitle");
    const studioDownloadBtn = document.getElementById("studioDownloadBtn");
    const studioYtUploadBtn = document.getElementById("studioYtUploadBtn");
    const studioSceneCount = document.getElementById("studioSceneCount");
    const studioScenesContainer = document.getElementById("studioScenesContainer");
    const studioVideoSelector = document.getElementById("studioVideoSelector");
    const studioVideoCountBadge = document.getElementById("studioVideoCountBadge");

    // Analytics Elements
    const analyticsChannelAvatar = document.getElementById("analyticsChannelAvatar");
    const analyticsChannelAvatarFallback = document.getElementById("analyticsChannelAvatarFallback");
    const analyticsChannelTitle = document.getElementById("analyticsChannelTitle");
    const analyticsChannelSub = document.getElementById("analyticsChannelSub");
    const anTotalViews = document.getElementById("anTotalViews");
    const anTotalLikes = document.getElementById("anTotalLikes");
    const anEarnings = document.getElementById("anEarnings");
    const anProjected = document.getElementById("anProjected");
    const analyticsTableBody = document.getElementById("analyticsTableBody");

    // Feedback Elements
    const runAiAnalysisBtn = document.getElementById("runAiAnalysisBtn");
    const feedbackDemandsList = document.getElementById("feedbackDemandsList");
    const feedbackWeaknessesList = document.getElementById("feedbackWeaknessesList");
    const dnaHumor = document.getElementById("dnaHumor");
    const dnaEnergy = document.getElementById("dnaEnergy");
    const dnaCatchphrase = document.getElementById("dnaCatchphrase");

    // YouTube Upload Pre-Modal Elements
    const ytUploadModal = document.getElementById("ytUploadModal");
    const closeYtUploadBtn = document.getElementById("closeYtUploadBtn");
    const cancelYtUploadBtn = document.getElementById("cancelYtUploadBtn");
    const confirmYtUploadBtn = document.getElementById("confirmYtUploadBtn");
    const ytConfirmBtnText = document.getElementById("ytConfirmBtnText");
    const ytUploadCustomTitle = document.getElementById("ytUploadCustomTitle");
    const ytPrivacySelect = document.getElementById("ytPrivacySelect");
    const modalChannelName = document.getElementById("modalChannelName");

    // YouTube Success Celebration Modal Elements
    const ytSuccessModal = document.getElementById("ytSuccessModal");
    const closeYtSuccessBtn = document.getElementById("closeYtSuccessBtn");
    const successModalChannel = document.getElementById("successModalChannel");
    const successModalPrivacyBadge = document.getElementById("successModalPrivacyBadge");
    const successModalVideoTitle = document.getElementById("successModalVideoTitle");
    const successModalUrlInput = document.getElementById("successModalUrlInput");
    const copyYtLinkBtn = document.getElementById("copyYtLinkBtn");
    const copyYtLinkBtnText = document.getElementById("copyYtLinkBtnText");
    const goToYtVideoBtn = document.getElementById("goToYtVideoBtn");
    const goToYtStudioBtn = document.getElementById("goToYtStudioBtn");

    // YouTube Setup & Guidance Modal Elements
    const youtubeSetupModal = document.getElementById("youtubeSetupModal");
    const closeYtSetupBtn = document.getElementById("closeYtSetupBtn");
    const diagSecretStatus = document.getElementById("diagSecretStatus");
    const diagProjectId = document.getElementById("diagProjectId");
    const diagTokenStatus = document.getElementById("diagTokenStatus");
    const linkEnableApi = document.getElementById("linkEnableApi");
    const linkConsentScreen = document.getElementById("linkConsentScreen");
    const linkCredentials = document.getElementById("linkCredentials");
    const uploadSecretInput = document.getElementById("uploadSecretInput");
    const secretUploadFeedback = document.getElementById("secretUploadFeedback");
    const btnStartInteractiveAuth = document.getElementById("btnStartInteractiveAuth");
    const authBtnLabel = document.getElementById("authBtnLabel");
    const authLiveStatusBox = document.getElementById("authLiveStatusBox");
    const authLiveStatusText = document.getElementById("authLiveStatusText");
    const onboardingStatusBadge = document.getElementById("onboardingStatusBadge");
    const guideStep1Badge = document.getElementById("guideStep1Badge");
    const guideStep2Badge = document.getElementById("guideStep2Badge");

    // Settings Elements
    const cfgPexelsKey = document.getElementById("cfgPexelsKey");
    const cfgPixabayKey = document.getElementById("cfgPixabayKey");
    const cfgOllamaHost = document.getElementById("cfgOllamaHost");
    const cfgDefaultModel = document.getElementById("cfgDefaultModel");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");

    // Live Clock Timer
    setInterval(() => {
        const now = new Date();
        if (liveClock) {
            liveClock.textContent = now.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        }
    }, 1000);

    // =========================================================================
    // 1. ROUTING / TAB NAVIGATION
    // =========================================================================
    window.switchTab = (tabName) => {
        currentTab = tabName;

        document.querySelectorAll(".nav-item").forEach(item => {
            if (item.dataset.tab === tabName) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        document.querySelectorAll(".tab-page").forEach(page => {
            page.classList.add("hidden");
        });

        const activePage = document.getElementById("tab_" + tabName);
        if (activePage) {
            activePage.classList.remove("hidden");
        }

        const tabMetadata = {
            dashboard: { title: "Dashboard (Ana Kumanda Merkezi)", icon: "fa-chart-pie" },
            jarvis: { title: "JARVIS Executive HUD (3D Kumanda Merkezi)", icon: "fa-atom" },
            studio: { title: "Üretim Stüdyosu (Gelişmiş Studio)", icon: "fa-clapperboard" },
            niche: { title: "Fırsat Nişi & Rakip Keşfi (Erkan Kolcu Stratejisi)", icon: "fa-compass" },
            thumbnails: { title: "1280x720 Yüksek CTR Thumbnail & Kapak Fabrikası", icon: "fa-images" },
            warmup: { title: "7 Günlük Kanal Güvenlik & Isıtma Protokolü", icon: "fa-shield-halved" },
            analytics: { title: "Analitik & Finans Sayfası", icon: "fa-chart-line" },
            feedback: { title: "Otonom Geri Bildirim & Persona", icon: "fa-brain" },
            settings: { title: "Sistem & Model Yapılandırması", icon: "fa-sliders" }
        };

        const meta = tabMetadata[tabName] || tabMetadata.dashboard;
        if (currentTabTitle) currentTabTitle.textContent = meta.title;
        if (currentTabIcon) currentTabIcon.innerHTML = `<i class="fa-solid ${meta.icon}"></i>`;

        if (tabName === "analytics") {
            loadAnalyticsData();
        }
    };

    if (sidebarNav) {
        sidebarNav.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-tab]");
            if (btn && btn.dataset.tab) {
                window.switchTab(btn.dataset.tab);
            }
        });
    }

    // =========================================================================
    // 2. INITIALIZATION & LIVE DATA FETCHING
    // =========================================================================
    async function initApp() {
        try {
            // Load base configuration & personas
            const res = await fetch("/api/config");
            const data = await res.json();
            personasData = data.personas || {};
            renderStudioPersonas(personasData);

            const s = data.settings || {};
            if (cfgPexelsKey) cfgPexelsKey.value = s.pexels_api_key || "";
            if (cfgPixabayKey) cfgPixabayKey.value = s.pixabay_api_key || "";
            if (cfgOllamaHost) cfgOllamaHost.value = s.ollama_host || "http://127.0.0.1:11434";
            if (cfgDefaultModel) cfgDefaultModel.value = s.default_model || "qwen3:14b";

            updatePersonaBadge("de_engineer");

            // Fetch 100% Real Live Channel Data from YouTube API v3
            await loadChannels();

            // Fetch Video Library from SQLite
            await loadVideoLibrary();

            // Fetch Autonomous AI Feedback Report
            await loadFeedbackReport("default");
        } catch (err) {
            console.error("Initialization error:", err);
        }
    }

    function updatePersonaBadge(personaId) {
        activePersonaId = personaId;
        const p = personasData[personaId];
        const personaLabel = p ? `${p.name} (${p.country ? p.country.substring(0, 2).toUpperCase() : 'AI'})` : 'The Engineer (DE)';
        if (activePersonaBadgeText) {
            activePersonaBadgeText.textContent = personaLabel;
        }
    }

    // =========================================================================
    // YOUTUBE STEP-BY-STEP SETUP WIZARD & GUIDANCE MODAL
    // =========================================================================
    let authPollingInterval = null;

    window.openYouTubeSetupModal = async () => {
        const modal = document.getElementById("youtubeSetupModal");
        if (!modal) {
            console.error("youtubeSetupModal DOM'da bulunamadı!");
            return;
        }
        modal.classList.remove("hidden");
        modal.style.display = "flex";
        modal.style.visibility = "visible";
        modal.style.opacity = "1";
        
        // Reset interactive state
        const statusBox = document.getElementById("authLiveStatusBox");
        const btnAuth = document.getElementById("btnStartInteractiveAuth");
        const btnLabel = document.getElementById("authBtnLabel");
        if (statusBox) statusBox.classList.add("hidden");
        if (btnAuth) btnAuth.disabled = false;
        if (btnLabel) btnLabel.textContent = "Google ile Kanalımı Yetkilendir (Tarayıcıda Başlat)";

        // Fetch live diagnostic data from backend
        try {
            const res = await authFetch("/api/youtube/diagnostic");
            const diag = await res.json();
            
            const secretStatus = document.getElementById("diagSecretStatus");
            const projId = document.getElementById("diagProjectId");
            const tokStatus = document.getElementById("diagTokenStatus");
            const apiLink = document.getElementById("linkEnableApi");
            const consentLink = document.getElementById("linkConsentScreen");
            const credLink = document.getElementById("linkCredentials");

            if (secretStatus) {
                secretStatus.textContent = diag.client_secret_exists ? "✅ Mevcut" : "❌ Eksik";
                secretStatus.className = diag.client_secret_exists ? "font-bold text-emerald-400" : "font-bold text-yt-red";
            }
            if (projId) {
                projId.textContent = diag.project_id || "Bilinmeyen Proje";
            }
            if (tokStatus) {
                tokStatus.textContent = diag.is_connected ? "🟢 Canlı Bağlı" : (diag.token_exists ? "⚠️ Yenilenmeli" : "⚠️ Yetki Bekliyor");
                tokStatus.className = diag.is_connected ? "font-bold text-emerald-400" : "font-bold text-amber-400";
            }
            if (apiLink && diag.urls) apiLink.href = diag.urls.enable_youtube_api;
            if (consentLink && diag.urls) consentLink.href = diag.urls.oauth_consent_screen;
            if (credLink && diag.urls) credLink.href = diag.urls.credentials_page;
        } catch (e) {
            console.error("Diagnostic fetch failed:", e);
        }
    };

    window.closeYouTubeSetupModal = () => {
        const modal = document.getElementById("youtubeSetupModal");
        if (modal) {
            modal.classList.add("hidden");
            modal.style.display = "none";
        }
        if (authPollingInterval) {
            clearInterval(authPollingInterval);
            authPollingInterval = null;
        }
    };

    const closeBtn = document.getElementById("closeYtSetupBtn");
    if (closeBtn) {
        closeBtn.addEventListener("click", window.closeYouTubeSetupModal);
    }

    // Trigger Guided OAuth Authorization
    window.runGuidedYouTubeAuth = async () => {
        try {
            if (btnStartInteractiveAuth) btnStartInteractiveAuth.disabled = true;
            if (authBtnLabel) authBtnLabel.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Onay Penceresi Açılıyor...`;
            if (authLiveStatusBox) {
                authLiveStatusBox.classList.remove("hidden");
                if (authLiveStatusText) authLiveStatusText.textContent = "Google onay penceresi açıldı. Hesabınızı seçip izin verin... Otomatik algılanıyor.";
            }

            const res = await authFetch("/api/youtube/auth", { method: "POST" });
            const data = await res.json();

            // Start polling every 2.5s for successful authentication
            if (authPollingInterval) clearInterval(authPollingInterval);
            let attempts = 0;
            authPollingInterval = setInterval(async () => {
                attempts++;
                try {
                    const cRes = await fetch("/api/channels");
                    const channels = await cRes.json();
                    if (channels && channels.length > 0 && channels[0].is_connected) {
                        clearInterval(authPollingInterval);
                        authPollingInterval = null;
                        if (authLiveStatusText) authLiveStatusText.innerHTML = `<span class="text-emerald-400 font-bold">🎉 Tebrikler! ${escapeHtml(channels[0].title)} (${escapeHtml(channels[0].custom_url)}) Başarıyla Bağlandı!</span>`;
                        if (authBtnLabel) authBtnLabel.innerHTML = `🟢 Bağlantı Tamamlandı!`;
                        await loadChannels();
                        setTimeout(() => {
                            window.closeYouTubeSetupModal();
                        }, 2000);
                    }
                } catch (err) {
                    console.error("Auth polling error:", err);
                }

                if (attempts > 60) { // 2.5 minutes timeout
                    clearInterval(authPollingInterval);
                    authPollingInterval = null;
                    if (btnStartInteractiveAuth) btnStartInteractiveAuth.disabled = false;
                    if (authBtnLabel) authBtnLabel.textContent = "Yeniden Dene";
                    if (authLiveStatusText) authLiveStatusText.textContent = "Zaman aşımı. Tarayıcı penceresinde onay verdiyseniz sayfayı yenileyin.";
                }
            }, 2500);

        } catch (e) {
            alert("Yetkilendirme başlatılamadı: " + e);
            if (btnStartInteractiveAuth) btnStartInteractiveAuth.disabled = false;
            if (authBtnLabel) authBtnLabel.textContent = "Google ile Kanalımı Yetkilendir";
        }
    };

    // Alias startYouTubeAuth to open the comprehensive guided modal
    window.startYouTubeAuth = () => {
        window.openYouTubeSetupModal();
    };

    if (headerAuthBtn) {
        headerAuthBtn.addEventListener("click", window.openYouTubeSetupModal);
    }

    // Client Secret File Upload
    if (uploadSecretInput) {
        uploadSecretInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = async (evt) => {
                try {
                    const jsonContent = JSON.parse(evt.target.result);
                    const res = await authFetch("/api/youtube/upload-secret", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(jsonContent)
                    });
                    const data = await res.json();
                    if (data.status === "success") {
                        if (secretUploadFeedback) {
                            secretUploadFeedback.textContent = "✅ client_secret.json kaydedildi!";
                            secretUploadFeedback.classList.remove("hidden");
                            setTimeout(() => { secretUploadFeedback.classList.add("hidden"); }, 3000);
                        }
                        // Refresh diagnostic info in modal
                        window.openYouTubeSetupModal();
                    } else {
                        alert("Hata: " + data.message);
                    }
                } catch (err) {
                    alert("Geçersiz JSON dosyası: " + err);
                }
            };
            reader.readAsText(file);
        });
    }

    // Fetch and bind 100% Real YouTube Channels
    async function loadChannels() {
        try {
            const res = await fetch("/api/channels");
            channelsData = await res.json();
            renderDashboardChannels(channelsData);

            if (channelsData && channelsData.length > 0) {
                const c = channelsData[0];
                const isConn = Boolean(c.is_connected);

                if (isConn) {
                    // Update Top Metric Card 1
                    if (dashChannelCardTitle) dashChannelCardTitle.textContent = `${c.title} (${c.custom_url})`;
                    if (dashChannelCardBody) {
                        dashChannelCardBody.innerHTML = `
                            <div class="flex items-center justify-between text-xs font-mono">
                                <span class="text-white font-bold">${escapeHtml(c.subscriber_count)} Canlı Abone</span>
                                <span class="text-emerald-400 flex items-center font-semibold">
                                    <i class="fa-solid fa-circle-check mr-1.5"></i> Canlı Bağlı
                                </span>
                            </div>
                        `;
                    }

                    // Update Onboarding Guidance Banner
                    if (guideStep1Badge) {
                        guideStep1Badge.textContent = "🟢 Canlı Bağlı";
                        guideStep1Badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-bold";
                    }
                    if (onboardingStatusBadge) {
                        onboardingStatusBadge.textContent = "3/3 Sistem Tamamen Hazır";
                        onboardingStatusBadge.className = "px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
                    }

                    // Update Sidebar Channel Box
                    if (sidebarYtTitle) sidebarYtTitle.textContent = c.title;
                    if (sidebarYtSub) sidebarYtSub.textContent = `${c.custom_url} • ${c.subscriber_count} Abone`;
                    if (sidebarYtPing) sidebarYtPing.className = "absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-dark-950";

                    if (c.thumbnail) {
                        if (sidebarYtAvatar) {
                            sidebarYtAvatar.src = c.thumbnail;
                            sidebarYtAvatar.classList.remove("hidden");
                        }
                        if (sidebarYtDefault) sidebarYtDefault.classList.add("hidden");

                        if (analyticsChannelAvatar) {
                            analyticsChannelAvatar.src = c.thumbnail;
                            analyticsChannelAvatar.classList.remove("hidden");
                        }
                        if (analyticsChannelAvatarFallback) analyticsChannelAvatarFallback.classList.add("hidden");
                    }

                    if (analyticsChannelTitle) analyticsChannelTitle.textContent = c.title;
                    if (analyticsChannelSub) analyticsChannelSub.textContent = `${c.custom_url} • Canlı YouTube Data API v3 İstatistikleri`;
                    if (modalChannelName) modalChannelName.textContent = `Hedef Kanal: ${c.title} (${c.custom_url})`;
                    if (successModalChannel) successModalChannel.textContent = `${c.title} (${c.custom_url})`;
                    if (headerAuthBtn) headerAuthBtn.classList.add("hidden");

                } else {
                    // Disconnected state: prominent large button
                    if (dashChannelCardTitle) dashChannelCardTitle.textContent = "Yetkilendirme Gerekli";
                    if (dashChannelCardBody) {
                        dashChannelCardBody.innerHTML = `
                            <button onclick="window.openYouTubeSetupModal()" class="action-bar-btn btn-cinematic-auth-danger w-full py-2 px-3 text-xs mt-1">
                                <i class="fa-brands fa-youtube mr-1.5"></i> 🔴 Kurulum Rehberini Aç & Yetkilendir
                            </button>
                        `;
                    }

                    // Update Onboarding Guidance Banner
                    if (guideStep1Badge) {
                        guideStep1Badge.textContent = "🔴 Bağlantı Gerekli";
                        guideStep1Badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-yt-red/15 text-yt-red border border-yt-red/30";
                    }
                    if (onboardingStatusBadge) {
                        onboardingStatusBadge.textContent = "1/3 Hazır (YouTube Bekleniyor)";
                        onboardingStatusBadge.className = "px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30";
                    }

                    if (sidebarYtTitle) sidebarYtTitle.textContent = "Kanal Bağlı Değil";
                    if (sidebarYtSub) sidebarYtSub.textContent = "Yetkilendirme Bekleniyor";
                    if (sidebarYtPing) sidebarYtPing.className = "absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-yt-red border-2 border-dark-950";
                    if (headerAuthBtn) headerAuthBtn.classList.remove("hidden");
                }
            }
        } catch (e) {
            console.error("Failed to load channels:", e);
        }
    }

    function renderDashboardChannels(channels) {
        if (!channelsGrid) return;
        channelsGrid.innerHTML = "";

        channels.forEach(ch => {
            const card = document.createElement("div");
            card.className = "glass-panel p-5 rounded-xl flex flex-col justify-between space-y-4 hover:border-cyan-400/40 transition-all";

            const isConn = ch.is_connected;
            const badgeHtml = isConn 
                ? '<span class="px-2.5 py-1 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">🟢 CANLI YAYINDA</span>'
                : '<span class="px-2.5 py-1 rounded text-[10px] font-mono font-bold bg-yt-red/10 text-yt-red border border-yt-red/30">🔴 BAĞLANTI GEREKLİ</span>';

            const safeThumb = sanitizeUrl(ch.thumbnail);
            const thumbImg = safeThumb 
                ? `<img src="${safeThumb}" class="w-full h-full object-cover rounded-lg">` 
                : '<i class="fa-brands fa-youtube text-2xl text-yt-red"></i>';

            if (isConn) {
                card.innerHTML = `
                    <div class="flex items-start justify-between">
                        <div class="flex items-center space-x-3.5">
                            <div class="w-12 h-12 rounded-lg bg-dark-950 border border-cyan-500/40 overflow-hidden flex items-center justify-center p-0.5 shadow-lg">
                                ${thumbImg}
                            </div>
                            <div>
                                <h4 class="font-display font-extrabold text-base text-white tracking-wide">${escapeHtml(ch.title)}</h4>
                                <p class="text-xs text-slate-400 font-mono">${escapeHtml(ch.custom_url)}</p>
                            </div>
                        </div>
                        ${badgeHtml}
                    </div>

                    <div class="grid grid-cols-3 gap-2 p-3 rounded-lg bg-dark-950/70 border border-slate-800/80 text-center font-mono">
                        <div>
                            <span class="block text-[10px] text-slate-400 uppercase">Canlı Abone</span>
                            <strong class="text-sm text-white">${escapeHtml(ch.subscriber_count)}</strong>
                        </div>
                        <div>
                            <span class="block text-[10px] text-slate-400 uppercase">YouTube Video</span>
                            <strong class="text-sm text-cyan-400">${escapeHtml(ch.video_count)}</strong>
                        </div>
                        <div>
                            <span class="block text-[10px] text-slate-400 uppercase">Hazır Shorts</span>
                            <strong class="text-sm text-emerald-400">${videoLibrary.length || ch.local_shorts_count || 3}</strong>
                        </div>
                    </div>

                    <div class="flex space-x-2 pt-1">
                        <button onclick="window.switchTab('studio')" class="action-bar-btn btn-cinematic-cyan flex-1 py-2 text-xs">
                            <i class="fa-solid fa-clapperboard mr-1.5"></i> Video Üret
                        </button>
                        <button onclick="window.switchTab('analytics')" class="action-bar-btn btn-cinematic-dark flex-1 py-2 text-xs">
                            <i class="fa-solid fa-chart-line mr-1.5"></i> Analitik
                        </button>
                        <button onclick="window.switchTab('feedback')" class="action-bar-btn btn-cinematic-dark px-3 py-2 text-xs" title="Persona Raporu">
                            <i class="fa-solid fa-brain text-agency-purple"></i>
                        </button>
                    </div>
                `;
            } else {
                card.innerHTML = `
                    <div class="flex items-start justify-between">
                        <div class="flex items-center space-x-3.5">
                            <div class="w-12 h-12 rounded-lg bg-dark-950 border border-yt-red/40 flex items-center justify-center text-yt-red text-2xl">
                                <i class="fa-brands fa-youtube"></i>
                            </div>
                            <div>
                                <h4 class="font-display font-extrabold text-base text-white">YouTube Kanalı Bulunamadı</h4>
                                <p class="text-xs text-slate-400 font-mono">Google Cloud OAuth Entegrasyonu</p>
                            </div>
                        </div>
                        ${badgeHtml}
                    </div>

                    <div class="p-4 rounded-lg bg-yt-red/10 border border-yt-red/20 text-center space-y-2">
                        <p class="text-xs text-red-200">YouTube Data API v3 üzerinden kanalınızı otonom bağlayın.</p>
                        <button onclick="window.openYouTubeSetupModal()" class="action-bar-btn btn-cinematic-auth-danger w-full py-2.5 text-xs font-bold">
                            <i class="fa-brands fa-youtube mr-2"></i> 🔴 Kurulum Rehberini Aç & Yetkilendir
                        </button>
                    </div>
                `;
            }

            channelsGrid.appendChild(card);
        });
    }

    // Video Library Loader & Active Studio Picker Binding
    async function loadVideoLibrary() {
        try {
            const res = await fetch("/api/videos");
            videoLibrary = await res.json();
            if (dashTotalVideos) dashTotalVideos.textContent = `${videoLibrary.length} Video`;
            if (studioVideoCountBadge) studioVideoCountBadge.textContent = `${videoLibrary.length} Video`;

            populateStudioVideoSelector(videoLibrary);
            renderDashboardRecentVideos(videoLibrary);

            if (videoLibrary && videoLibrary.length > 0) {
                // If no active video yet, load the latest video
                if (!activeTaskId || !videoLibrary.some(v => v.task_id === activeTaskId)) {
                    loadVideoIntoStudio(videoLibrary[0]);
                }
                renderAnalyticsTable(videoLibrary);
            }
        } catch (e) {
            console.error("Failed to load video library:", e);
        }
    }

    function populateStudioVideoSelector(videos) {
        if (!studioVideoSelector) return;
        studioVideoSelector.innerHTML = "";

        if (!videos || videos.length === 0) {
            studioVideoSelector.innerHTML = '<option value="">Henüz üretilmiş video yok</option>';
            return;
        }

        videos.forEach((v, idx) => {
            const opt = document.createElement("option");
            opt.value = v.task_id;
            const topic = v.topic || "Otonom Shorts";
            const dateStr = v.created_at ? v.created_at.substring(0, 10) : "";
            const isYt = Boolean(v.youtube_url);
            opt.textContent = `${idx + 1}. ${topic} [${isYt ? 'YouTube Yayında' : 'Yerel Arşiv'}] (${dateStr})`;
            if (v.task_id === activeTaskId) {
                opt.selected = true;
            }
            studioVideoSelector.appendChild(opt);
        });

        studioVideoSelector.onchange = () => {
            const selectedId = studioVideoSelector.value;
            const found = videoLibrary.find(v => v.task_id === selectedId);
            if (found) {
                loadVideoIntoStudio(found);
            }
        };
    }

    function renderDashboardRecentVideos(videos) {
        if (!dashRecentVideos) return;
        dashRecentVideos.innerHTML = "";

        videos.slice(0, 3).forEach(v => {
            const card = document.createElement("div");
            card.className = "glass-panel p-4 rounded-xl flex flex-col justify-between space-y-3 hover:border-cyan-400/40 transition-all";
            const dateStr = v.created_at ? v.created_at.substring(0, 10) : "Bugün";
            const isYt = Boolean(v.youtube_url);

            card.innerHTML = `
                <div>
                    <div class="flex justify-between items-center text-[10px] font-mono text-slate-400 mb-1.5">
                        <span class="px-2 py-0.5 rounded bg-dark-950 text-cyan-400 border border-slate-800">${escapeHtml(v.persona_id || "de_engineer")}</span>
                        <span>${escapeHtml(dateStr)}</span>
                    </div>
                    <h4 class="font-display font-bold text-sm text-white line-clamp-2">${escapeHtml(v.topic || "Otonom Shorts")}</h4>
                </div>

                <div class="flex justify-between items-center pt-2.5 border-t border-slate-800/80">
                    <span class="text-[11px] font-mono ${isYt ? 'text-emerald-400 font-bold' : 'text-slate-400'}">
                        ${isYt ? '🟢 Yayında' : '📁 Arşivde Hazır'}
                    </span>
                    <button class="action-bar-btn btn-cinematic-cyan px-3 py-1.5 text-xs" onclick="window.openVideoInStudio('${escapeHtml(v.task_id)}')">
                        İzle / Onar
                    </button>
                </div>
            `;
            dashRecentVideos.appendChild(card);
        });
    }

    window.openVideoInStudio = (taskId) => {
        const found = videoLibrary.find(v => v.task_id === taskId);
        if (found) {
            loadVideoIntoStudio(found);
            window.switchTab("studio");
        }
    };

    function loadVideoIntoStudio(video) {
        activeTaskId = video.task_id;
        activeVideoData = video;
        if (studioActiveTitle) studioActiveTitle.textContent = video.topic || "The 370 Million Dollar Rocket Disaster";
        
        if (studioVideoPlayer) {
            studioVideoPlayer.src = video.video_url;
            studioVideoPlayer.classList.remove("hidden");
            studioVideoPlayer.load();
        }
        if (studioVideoEmpty) studioVideoEmpty.classList.add("hidden");
        if (studioDownloadBtn) studioDownloadBtn.href = video.video_url;

        // Synchronize studio selector
        if (studioVideoSelector && studioVideoSelector.value !== video.task_id) {
            studioVideoSelector.value = video.task_id;
        }

        const taskData = video.task_data || {};
        activeScenes = taskData.scenes || [];
        renderStudioScenes(activeScenes);
    }

    // =========================================================================
    // 3. STUDIO CONTROLS & SCENE REPAIR
    // =========================================================================
    function renderStudioPersonas(personas) {
        if (!studioPersonaList) return;
        studioPersonaList.innerHTML = "";

        Object.keys(personas).forEach(key => {
            const p = personas[key];
            const isSelected = (key === activePersonaId);
            const card = document.createElement("div");
            card.className = `p-3 rounded-lg border cursor-pointer transition-all flex items-start space-x-2.5 ${
                isSelected 
                    ? 'bg-cyan-500/10 border-cyan-400 shadow-[0_0_15px_rgba(0,242,254,0.15)]' 
                    : 'bg-dark-950/60 border-slate-800 hover:border-slate-700'
            }`;
            card.dataset.persona = key;

            card.innerHTML = `
                <div class="w-8 h-8 rounded-lg bg-dark-900 border border-slate-700 flex items-center justify-center text-sm font-bold flex-shrink-0 text-cyan-400">
                    ${key.substring(0, 2).toUpperCase()}
                </div>
                <div class="flex-1 min-w-0">
                    <h5 class="text-xs font-bold text-white truncate">${escapeHtml(p.name)}</h5>
                    <p class="text-[10px] text-slate-400 font-mono truncate">${escapeHtml(p.country || "Global")}</p>
                </div>
            `;

            card.addEventListener("click", () => {
                document.querySelectorAll("#studioPersonaList > div").forEach(c => {
                    c.className = "p-3 rounded-lg border cursor-pointer transition-all flex items-start space-x-2.5 bg-dark-950/60 border-slate-800 hover:border-slate-700";
                });
                card.className = "p-3 rounded-lg border cursor-pointer transition-all flex items-start space-x-2.5 bg-cyan-500/10 border-cyan-400 shadow-[0_0_15px_rgba(0,242,254,0.15)]";
                updatePersonaBadge(key);
            });

            studioPersonaList.appendChild(card);
        });
    }

    // Video Type (Shorts vs Longform) Buttons
    document.querySelectorAll(".vtype-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".vtype-btn").forEach(b => {
                b.className = "vtype-btn py-2 text-xs font-bold rounded bg-dark-900 text-slate-400 border border-slate-800 flex items-center justify-center space-x-1.5";
            });
            btn.className = "vtype-btn active py-2 text-xs font-bold rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 flex items-center justify-center space-x-1.5";
            activeVideoType = btn.dataset.type || "shorts";
            activeOrientation = btn.dataset.orient || "vertical";
        });
    });

    // Resolution & Duration Buttons
    document.querySelectorAll(".res-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".res-btn").forEach(b => {
                b.className = "res-btn py-1.5 text-xs font-bold rounded bg-dark-900 text-slate-400 border border-slate-800";
            });
            btn.className = "res-btn active py-1.5 text-xs font-bold rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/40";
            activeResolution = btn.dataset.res;
        });
    });

    document.querySelectorAll(".dur-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".dur-btn").forEach(b => {
                b.className = "dur-btn py-1.5 text-[11px] font-bold rounded bg-dark-900 text-slate-400 border border-slate-800";
            });
            btn.className = "dur-btn active py-1.5 text-[11px] font-bold rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/40";
            activeDuration = btn.dataset.dur;
        });
    });

    if (studioBgmRange && studioBgmVal) {
        studioBgmRange.addEventListener("input", () => {
            studioBgmVal.textContent = studioBgmRange.value + "%";
        });
    }

    if (studioRandomTopicBtn && studioTopicInput) {
        const topics = [
            "Why Superconductors Will Make Energy Free by 2030",
            "The 370 Million Dollar Rocket Disaster That Shocked NASA",
            "The Secret German Bunker Discovered Underneath The Rhine",
            "How Quantum Radar Made Stealth Jets Completely Obsolete",
            "The Deepest Borehole on Earth and The Terrifying Noise at 12KM"
        ];
        studioRandomTopicBtn.addEventListener("click", () => {
            const rand = topics[Math.floor(Math.random() * topics.length)];
            studioTopicInput.value = rand;
        });
    }

    // Render Scene Cards for Scene Repair
    function renderStudioScenes(scenes) {
        if (!studioScenesContainer) return;
        studioScenesContainer.innerHTML = "";

        if (studioSceneCount) studioSceneCount.textContent = `${scenes.length} Sahne`;

        if (!scenes || scenes.length === 0) {
            studioScenesContainer.innerHTML = '<p class="text-xs text-slate-500 font-mono py-4 text-center">Video sahneleri yüklendiğinde burada listelenir.</p>';
            return;
        }

        scenes.forEach((sc, idx) => {
            const card = document.createElement("div");
            card.className = "p-3 rounded-lg bg-dark-950/80 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-3";
            card.id = "studioScene_" + idx;
            card.innerHTML = `
                <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-2">
                        <span class="text-xs font-mono font-bold text-cyan-400">Sahne ${idx + 1}</span>
                        <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 uppercase">${escapeHtml(sc.role || "narrative")}</span>
                    </div>
                    <p class="text-xs text-slate-200 mt-1 truncate" title="${escapeHtml(sc.text || "")}">${escapeHtml(sc.text || "")}</p>
                </div>

                <div class="flex items-center space-x-2 flex-shrink-0 w-full md:w-auto">
                    <input type="text" id="studioKw_${idx}" value="${escapeHtml(sc.visual_keyword || "")}" class="bg-dark-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white font-mono w-32 focus:border-cyan-400 outline-none">
                    <button class="action-bar-btn btn-cinematic-cyan px-3 py-1.5 text-xs font-bold" onclick="window.repairStudioScene(${idx})">
                        <i class="fa-solid fa-arrows-rotate mr-1"></i> Değiştir (6s)
                    </button>
                </div>
            `;
            studioScenesContainer.appendChild(card);
        });
    }

    window.repairStudioScene = async (sceneIdx) => {
        if (!activeTaskId) return;
        const kwInput = document.getElementById("studioKw_" + sceneIdx);
        const card = document.getElementById("studioScene_" + sceneIdx);
        if (!card) return;
        const btn = card.querySelector("button");

        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Onarılıyor...';

        try {
            const res = await fetch(`/api/tasks/${activeTaskId}/regenerate_scene`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    scene_id: sceneIdx,
                    new_keyword: kwInput ? kwInput.value.trim() : ""
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400 mr-1"></i> Onarıldı!';
                if (studioVideoPlayer) {
                    studioVideoPlayer.src = data.video_url + "?t=" + Date.now();
                    studioVideoPlayer.play();
                }
                if (studioDownloadBtn) studioDownloadBtn.href = data.video_url;

                setTimeout(() => {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa-solid fa-arrows-rotate mr-1"></i> Değiştir (6s)';
                }, 2000);
            } else {
                alert("Hata: " + data.message);
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-arrows-rotate mr-1"></i> Değiştir (6s)';
            }
        } catch (e) {
            alert("Bağlantı hatası: " + e);
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-arrows-rotate mr-1"></i> Değiştir (6s)';
        }
    };

    // Video Generation Trigger
    if (studioGenerateBtn) {
        studioGenerateBtn.addEventListener("click", async () => {
            const topic = studioTopicInput ? studioTopicInput.value.trim() : "";
            if (!topic) {
                alert("Lütfen bir video konusu veya kanca girin!");
                if (studioTopicInput) studioTopicInput.focus();
                return;
            }

            studioGenerateBtn.disabled = true;
            studioGenerateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Üretim Sürüyor...';

            const ttsEl = document.querySelector('input[name="studioTts"]:checked');
            const ttsEngine = ttsEl ? ttsEl.value : "kokoro";

            const hookStyleEl = document.getElementById("studioHookStyle");
            const humanizeEl = document.getElementById("studioHumanizeLevel");
            const rageBaitEl = document.getElementById("studioEnableRageBait");
            const teaserEl = document.getElementById("studioEnableTeaser");
            const thumbEl = document.getElementById("studioEnableThumb");
            const thumbPresetEl = document.getElementById("studioThumbPreset");

            try {
                const response = await fetch("/api/generate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        persona_id: activePersonaId,
                        topic: topic,
                        target_duration: activeDuration,
                        video_type: activeVideoType,
                        orientation: activeOrientation,
                        hook_style: hookStyleEl ? hookStyleEl.value : "danger",
                        humanize_level: humanizeEl ? humanizeEl.value : "light",
                        enable_rage_bait: rageBaitEl ? rageBaitEl.checked : false,
                        enable_teaser_splice: teaserEl ? teaserEl.checked : false,
                        generate_thumb: thumbEl ? thumbEl.checked : true,
                        thumbnail_preset: thumbPresetEl ? thumbPresetEl.value : "danger_red",
                        tts_engine: ttsEngine,
                        resolution: activeResolution,
                        enable_bgm: studioEnableBgm ? studioEnableBgm.checked : true,
                        bgm_volume: studioBgmRange ? parseInt(studioBgmRange.value) / 100 : 0.15
                    })
                });
                const data = await response.json();
                if (data.task_id) {
                    activeTaskId = data.task_id;
                    listenToTaskEvents(data.task_id);
                }
            } catch (err) {
                alert("Üretim başlatılamadı: " + err);
                studioGenerateBtn.disabled = false;
                studioGenerateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles mr-2 text-base"></i> Otonom Video Üretimini Başlat';
            }
        });
    }

    function listenToTaskEvents(taskId) {
        const evtSource = new EventSource(`/api/events/${taskId}`);

        evtSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const percent = data.percent || 0;
                const msg = data.message || "İşleniyor...";

                if (studioPercent) studioPercent.textContent = percent + "%";
                if (studioProgressBar) studioProgressBar.style.width = percent + "%";
                if (studioStageMsg) studioStageMsg.textContent = msg;

                if (data.status === "completed" || percent >= 100) {
                    evtSource.close();
                    studioGenerateBtn.disabled = false;
                    studioGenerateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles mr-2 text-base"></i> Otonom Video Üretimini Başlat';

                    if (data.video_url && studioVideoPlayer) {
                        studioVideoPlayer.src = data.video_url;
                        studioVideoPlayer.classList.remove("hidden");
                        studioVideoPlayer.load();
                        if (studioVideoEmpty) studioVideoEmpty.classList.add("hidden");
                        if (studioDownloadBtn) studioDownloadBtn.href = data.video_url;
                    }

                    const td = data.task_data || {};
                    if (td.scenes) {
                        activeScenes = td.scenes;
                        renderStudioScenes(activeScenes);
                    }

                    // Display Generated Thumbnail (Faz 5)
                    const thumbCard = document.getElementById("studioThumbCard");
                    const thumbImg = document.getElementById("studioThumbImg");
                    const thumbDl = document.getElementById("studioThumbDownloadBtn");
                    if (td.thumbnail_url && thumbCard && thumbImg) {
                        thumbCard.classList.remove("hidden");
                        thumbImg.src = td.thumbnail_url;
                        if (thumbDl) thumbDl.href = td.thumbnail_url;
                    }

                    loadVideoLibrary();
                } else if (data.status === "error") {
                    evtSource.close();
                    studioGenerateBtn.disabled = false;
                    studioGenerateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles mr-2 text-base"></i> Otonom Video Üretimini Başlat';
                    alert("Üretim Hatası: " + data.message);
                }
            } catch (e) {
                console.error("SSE parse error:", e);
            }
        };

        evtSource.onerror = () => {
            evtSource.close();
            studioGenerateBtn.disabled = false;
            studioGenerateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles mr-2 text-base"></i> Otonom Video Üretimini Başlat';
        };
    }

    // =========================================================================
    // 4. CHART.JS & REAL LIVE FINANCIAL TERMINAL
    // =========================================================================
    async function loadAnalyticsData() {
        try {
            const res = await fetch("/api/analytics/default");
            const data = await res.json();

            if (anTotalViews) anTotalViews.textContent = (data.total_views || 0).toLocaleString();
            if (anTotalLikes) anTotalLikes.textContent = (data.total_likes || 0).toLocaleString();
            if (anEarnings) anEarnings.textContent = "$" + (data.estimated_earnings || 0).toFixed(2);
            if (anProjected) anProjected.textContent = "$" + (data.projected_monthly || 0).toFixed(2) + " / Ay";

            renderAnalyticsCharts(data);
        } catch (e) {
            console.error("Failed to load analytics data:", e);
        }
    }

    function renderAnalyticsCharts(analyticsData) {
        if (viewsChartInstance) viewsChartInstance.destroy();
        if (earningsChartInstance) earningsChartInstance.destroy();

        const canvas1 = document.getElementById("viewsTrendChart");
        const canvas2 = document.getElementById("earningsChart");
        if (!canvas1 || !canvas2) return;

        const ctx1 = canvas1.getContext("2d");
        const ctx2 = canvas2.getContext("2d");

        const dailyStats = analyticsData?.daily_stats || [
            { date: "Pzt", views: 0, earnings: 0 },
            { date: "Sal", views: 0, earnings: 0 },
            { date: "Çar", views: 0, earnings: 0 },
            { date: "Per", views: 0, earnings: 0 },
            { date: "Cum", views: 0, earnings: 0 },
            { date: "Cmt", views: 0, earnings: 0 },
            { date: "Paz", views: 0, earnings: 0 }
        ];

        // Soft vertical gradient fill from neon cyan to transparent
        const gradient1 = ctx1.createLinearGradient(0, 0, 0, 240);
        gradient1.addColorStop(0, "rgba(0, 242, 254, 0.32)");
        gradient1.addColorStop(1, "rgba(0, 242, 254, 0.00)");

        // 1. Line Chart: Fiery Neon Cyan (#00f2fe), NO Gridlines
        viewsChartInstance = new Chart(ctx1, {
            type: "line",
            data: {
                labels: dailyStats.map(d => d.date),
                datasets: [{
                    label: "Canlı Shorts İzlenmesi",
                    data: dailyStats.map(d => d.views),
                    borderColor: "#00f2fe",
                    backgroundColor: gradient1,
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2.5,
                    pointBackgroundColor: "#00f2fe",
                    pointBorderColor: "#0a0f1a",
                    pointBorderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "rgba(10, 15, 26, 0.95)",
                        titleColor: "#00f2fe",
                        bodyColor: "#f1f5f9",
                        borderColor: "rgba(0, 242, 254, 0.3)",
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 11 } }
                    },
                    y: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 11 } }
                    }
                }
            }
        });

        // 2. Bar Chart: Earnings Distribution, NO Gridlines
        earningsChartInstance = new Chart(ctx2, {
            type: "bar",
            data: {
                labels: dailyStats.map(d => d.date),
                datasets: [{
                    label: "Tahmini Kazanç ($)",
                    data: dailyStats.map(d => d.earnings),
                    backgroundColor: "rgba(99, 102, 241, 0.75)",
                    hoverBackgroundColor: "#00f2fe",
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "rgba(10, 15, 26, 0.95)",
                        titleColor: "#6366f1",
                        bodyColor: "#f1f5f9",
                        borderColor: "rgba(99, 102, 241, 0.3)",
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 11 } }
                    },
                    y: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 11 } }
                    }
                }
            }
        });
    }

    function renderAnalyticsTable(videos) {
        if (!analyticsTableBody) return;
        analyticsTableBody.innerHTML = "";

        videos.forEach(v => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-800/30 transition-colors";
            const isYt = Boolean(v.youtube_url);
            tr.innerHTML = `
                <td class="py-3 text-white font-medium max-w-xs truncate">${v.topic || "Otonom Shorts"}</td>
                <td><span class="px-2 py-0.5 rounded bg-dark-950 text-cyan-400 border border-slate-800">1080p FHD</span></td>
                <td>${isYt ? '1' : '0 (Arşiv)'}</td>
                <td>${isYt ? '0' : '0'}</td>
                <td class="text-emerald-400 font-bold">$0.00</td>
                <td><span class="${isYt ? 'text-emerald-400 font-bold' : 'text-slate-500'}">${isYt ? '🟢 Yayında' : '📁 Arşivde'}</span></td>
            `;
            analyticsTableBody.appendChild(tr);
        });
    }

    // =========================================================================
    // 5. AUTONOMOUS FEEDBACK & PERSONA INTELLIGENCE
    // =========================================================================
    async function loadFeedbackReport(channelId) {
        try {
            const res = await fetch(`/api/feedback/report/${channelId}`);
            const report = await res.json();
            renderFeedbackReportUI(report);
        } catch (e) {
            console.error("Failed to load feedback report:", e);
        }
    }

    function renderFeedbackReportUI(report) {
        if (feedbackDemandsList && report.audience_demands) {
            feedbackDemandsList.innerHTML = report.audience_demands.map(d => `
                <li class="flex items-start space-x-2 p-2 rounded bg-dark-950/60 border border-slate-800/80">
                    <i class="fa-solid fa-check text-cyan-400 mt-0.5"></i>
                    <span class="text-slate-200">${d}</span>
                </li>
            `).join("");
        }

        if (feedbackWeaknessesList && report.weaknesses_to_avoid) {
            feedbackWeaknessesList.innerHTML = report.weaknesses_to_avoid.map(w => `
                <li class="flex items-start space-x-2 p-2 rounded bg-dark-950/60 border border-slate-800/80">
                    <i class="fa-solid fa-xmark text-yt-red mt-0.5"></i>
                    <span class="text-slate-300">${w}</span>
                </li>
            `).join("");
        }

        const pt = report.persona_tuning || {};
        if (dnaHumor) dnaHumor.textContent = pt.humor_level || "Hafif sarkastik, zeki";
        if (dnaEnergy) dnaEnergy.textContent = pt.energy_level || "9/10 Yüksek tempolu";
        if (dnaCatchphrase) dnaCatchphrase.textContent = pt.catchphrase || '"İşte kimsenin anlatmadığı o gerçek..."';
    }

    if (runAiAnalysisBtn) {
        runAiAnalysisBtn.addEventListener("click", async () => {
            runAiAnalysisBtn.disabled = true;
            runAiAnalysisBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Qwen 14B Analiz Ediyor...';
            try {
                const res = await fetch("/api/feedback/analyze/default", { method: "POST" });
                const data = await res.json();
                if (data.report) {
                    renderFeedbackReportUI(data.report);
                    alert("Qwen 14B izleyici analizi ve persona raporu başarıyla güncellendi!");
                }
            } catch (e) {
                alert("Hata: " + e);
            } finally {
                runAiAnalysisBtn.disabled = false;
                runAiAnalysisBtn.innerHTML = '<i class="fa-solid fa-rotate mr-1.5"></i> Zeka Analizini Başlat';
            }
        });
    }

    // =========================================================================
    // 6. YOUTUBE SHORTS UPLOAD & LUXURY CELEBRATION MODALS (No Browser Alerts!)
    // =========================================================================
    if (studioYtUploadBtn && ytUploadModal) {
        studioYtUploadBtn.addEventListener("click", () => {
            if (!activeVideoData && (!studioVideoPlayer || !studioVideoPlayer.src)) {
                alert("Lütfen önce bir video üretin veya listeden seçin!");
                return;
            }
            if (ytUploadCustomTitle) {
                const curTopic = (activeVideoData && activeVideoData.topic) ? activeVideoData.topic : (studioActiveTitle ? studioActiveTitle.textContent : "Autonomous Short");
                ytUploadCustomTitle.value = curTopic.includes("#Shorts") ? curTopic : `${curTopic} #Shorts`;
            }
            if (ytPrivacySelect) {
                ytPrivacySelect.value = "public"; // Always default to PUBLIC
            }
            ytUploadModal.classList.remove("hidden");
        });
    }

    if (closeYtUploadBtn && ytUploadModal) {
        closeYtUploadBtn.addEventListener("click", () => ytUploadModal.classList.add("hidden"));
    }
    if (cancelYtUploadBtn && ytUploadModal) {
        cancelYtUploadBtn.addEventListener("click", () => ytUploadModal.classList.add("hidden"));
    }

    // Confirm Upload Button
    if (confirmYtUploadBtn) {
        confirmYtUploadBtn.addEventListener("click", async () => {
            confirmYtUploadBtn.disabled = true;
            if (ytConfirmBtnText) ytConfirmBtnText.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Resumable Chunk Yükleniyor...';

            const chosenPrivacy = ytPrivacySelect ? ytPrivacySelect.value : "public";
            const customTitle = ytUploadCustomTitle ? ytUploadCustomTitle.value.trim() : (studioActiveTitle ? studioActiveTitle.textContent : "Autonomous Viral Short #Shorts");

            try {
                const res = await authFetch("/api/youtube/upload", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        task_id: activeTaskId,
                        video_url: studioVideoPlayer ? studioVideoPlayer.src : null,
                        title: customTitle,
                        privacy: chosenPrivacy
                    })
                });
                const data = await res.json();
                
                if (data.status === "success") {
                    // Close the pre-upload modal
                    ytUploadModal.classList.add("hidden");

                    // Show the ULTRA-LUXURY SUCCESS MODAL (No crude alert!)
                    if (successModalVideoTitle) successModalVideoTitle.textContent = data.title || customTitle;
                    if (successModalUrlInput) successModalUrlInput.value = data.url;
                    if (goToYtVideoBtn) goToYtVideoBtn.href = data.url;

                    if (successModalPrivacyBadge) {
                        if (chosenPrivacy === "public") {
                            successModalPrivacyBadge.className = "px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-bold";
                            successModalPrivacyBadge.textContent = "🟢 HERKESE AÇIK (PUBLIC)";
                        } else if (chosenPrivacy === "unlisted") {
                            successModalPrivacyBadge.className = "px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 font-bold";
                            successModalPrivacyBadge.textContent = "🟡 LİSTE DIŞI (UNLISTED)";
                        } else {
                            successModalPrivacyBadge.className = "px-2 py-0.5 rounded bg-slate-500/15 text-slate-400 border border-slate-500/30 font-bold";
                            successModalPrivacyBadge.textContent = "🔒 GİZLİ (PRIVATE)";
                        }
                    }

                    if (ytSuccessModal) {
                        ytSuccessModal.classList.remove("hidden");
                    }

                    loadChannels();
                    loadVideoLibrary();
                } else {
                    alert("Yükleme başarısız oldu: " + data.message);
                }
            } catch (err) {
                alert("Bağlantı hatası: " + err);
            } finally {
                confirmYtUploadBtn.disabled = false;
                if (ytConfirmBtnText) ytConfirmBtnText.textContent = "YouTube'a Yayınla";
            }
        });
    }

    // Success Modal Close Handlers
    if (closeYtSuccessBtn && ytSuccessModal) {
        closeYtSuccessBtn.addEventListener("click", () => ytSuccessModal.classList.add("hidden"));
    }

    // 1-Click Copy YouTube URL Button
    if (copyYtLinkBtn && successModalUrlInput) {
        copyYtLinkBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(successModalUrlInput.value).then(() => {
                if (copyYtLinkBtnText) copyYtLinkBtnText.textContent = "✓ Kopyalandı!";
                copyYtLinkBtn.classList.add("border-emerald-400", "text-emerald-400");
                setTimeout(() => {
                    if (copyYtLinkBtnText) copyYtLinkBtnText.textContent = "Linki Kopyala";
                    copyYtLinkBtn.classList.remove("border-emerald-400", "text-emerald-400");
                }, 2500);
            }).catch(() => {
                successModalUrlInput.select();
                document.execCommand("copy");
            });
        });
    }

    // =========================================================================
    // 7. SYSTEM SETTINGS
    // =========================================================================
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener("click", async () => {
            saveSettingsBtn.disabled = true;
            saveSettingsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Kaydediliyor...';
            try {
                const res = await authFetch("/api/config", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        pexels_api_key: cfgPexelsKey ? cfgPexelsKey.value.trim() : "",
                        pixabay_api_key: cfgPixabayKey ? cfgPixabayKey.value.trim() : "",
                        ollama_host: cfgOllamaHost ? cfgOllamaHost.value.trim() : "http://127.0.0.1:11434",
                        default_model: cfgDefaultModel ? cfgDefaultModel.value.trim() : "qwen3:14b"
                    })
                });
                const data = await res.json();
                if (data.status === "success") {
                    alert("Sistem ayarları başarıyla kaydedildi!");
                }
            } catch (e) {
                alert("Hata: " + e);
            } finally {
                saveSettingsBtn.disabled = false;
                saveSettingsBtn.innerHTML = '<i class="fa-solid fa-floppy-disk mr-1.5"></i> Ayarları Kaydet';
            }
        });
    }

    // =========================================================================
    // 8. TRANSCRIPT ENTEGRASYON APIS (NİŞ, THUMBNAILS, WARMUP)
    // =========================================================================

    // 8.1 Niche & Competitor Radar
    const nicheCompetitorInput = document.getElementById("nicheCompetitorInput");
    const nicheAnalyzeBtn = document.getElementById("nicheAnalyzeBtn");
    const nicheCompetitorResult = document.getElementById("nicheCompetitorResult");
    const nicheCompTitle = document.getElementById("nicheCompTitle");
    const nicheCompSubs = document.getElementById("nicheCompSubs");
    const nicheCompHook = document.getElementById("nicheCompHook");
    const nicheCompWeakness = document.getElementById("nicheCompWeakness");
    const nicheCompCounterTopics = document.getElementById("nicheCompCounterTopics");

    if (nicheAnalyzeBtn) {
        nicheAnalyzeBtn.addEventListener("click", async () => {
            const channel = nicheCompetitorInput ? nicheCompetitorInput.value.trim() : "";
            if (!channel) {
                alert("Lütfen bir kanal adı veya URL'si girin!");
                return;
            }
            nicheAnalyzeBtn.disabled = true;
            nicheAnalyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Analiz Ediliyor...';

            try {
                const res = await fetch("/api/niche/analyze", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ channel: channel })
                });
                const data = await res.json();
                if (data.status === "success" && data.analysis) {
                    const an = data.analysis;
                    if (nicheCompTitle) nicheCompTitle.textContent = an.title;
                    if (nicheCompSubs) nicheCompSubs.textContent = `${Number(an.subscribers).toLocaleString()} Abone • ${an.video_count} Video • Ort. ${Number(an.avg_views).toLocaleString()} İzlenme`;
                    
                    const intel = an.ai_intel || {};
                    if (nicheCompHook) nicheCompHook.textContent = intel.core_hook_formula || "Bilinmiyor";
                    if (nicheCompWeakness) nicheCompWeakness.textContent = intel.competitive_weakness || "Bilinmiyor";
                    
                    if (nicheCompCounterTopics) {
                        nicheCompCounterTopics.innerHTML = "";
                        (intel.recommended_counter_topics || []).forEach(top => {
                            const li = document.createElement("li");
                            li.textContent = top;
                            nicheCompCounterTopics.appendChild(li);
                        });
                    }
                    if (nicheCompetitorResult) nicheCompetitorResult.classList.remove("hidden");
                } else {
                    alert("Analiz başarısız: " + (data.message || "Bilinmeyen hata"));
                }
            } catch (e) {
                alert("Bağlantı hatası: " + e);
            } finally {
                nicheAnalyzeBtn.disabled = false;
                nicheAnalyzeBtn.innerHTML = '<i class="fa-solid fa-magnifying-glass mr-1"></i> Analiz Et';
            }
        });
    }

    const nicheKeywordInput = document.getElementById("nicheKeywordInput");
    const nicheCountrySelect = document.getElementById("nicheCountrySelect");
    const nicheDiscoverBtn = document.getElementById("nicheDiscoverBtn");
    const nicheCardsContainer = document.getElementById("nicheCardsContainer");

    if (nicheDiscoverBtn) {
        nicheDiscoverBtn.addEventListener("click", async () => {
            const kw = nicheKeywordInput ? nicheKeywordInput.value.trim() : "technology";
            const country = nicheCountrySelect ? nicheCountrySelect.value : "us";

            nicheDiscoverBtn.disabled = true;
            nicheDiscoverBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Taranıyor...';

            try {
                const res = await fetch("/api/niche/discover", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ keyword: kw, country: country })
                });
                const data = await res.json();
                if (data.status === "success" && data.niches) {
                    nicheCardsContainer.innerHTML = "";
                    data.niches.forEach(n => {
                        const card = document.createElement("div");
                        card.className = "p-4 rounded-lg bg-dark-950/80 border border-slate-800 space-y-2.5 transition-all hover:border-amber-400/50";
                        card.innerHTML = `
                            <div class="flex justify-between items-start">
                                <div>
                                    <h5 class="text-xs font-bold text-white flex items-center space-x-1.5">
                                        <span>${n.flag}</span>
                                        <span>${n.niche_name}</span>
                                    </h5>
                                    <span class="text-[10px] text-amber-400 font-mono font-bold">${n.cpm_tier} RPM • Skor: ${n.opportunity_score}/10</span>
                                </div>
                                <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">${n.competition_level}</span>
                            </div>
                            <p class="text-[11px] text-slate-300 font-mono"><span class="text-slate-500">Örnek Konu:</span> "${n.breakout_sample}"</p>
                            <p class="text-[10px] text-slate-400 font-sans">${n.why_it_works}</p>
                            <button data-niche="${escapeHtml(n.breakout_sample)}" onclick="window.useNicheTopic(this.getAttribute('data-niche'))" class="text-[11px] font-bold text-cyan-400 hover:text-cyan-300 font-mono flex items-center space-x-1 pt-1">
                                <span>Bu Konuyla Video Üret</span>
                                <i class="fa-solid fa-arrow-right text-[10px]"></i>
                            </button>
                        `;
                        nicheCardsContainer.appendChild(card);
                    });
                }
            } catch (e) {
                alert("Niş tarama hatası: " + e);
            } finally {
                nicheDiscoverBtn.disabled = false;
                nicheDiscoverBtn.innerHTML = '<i class="fa-solid fa-radar mr-1"></i> Keşfet';
            }
        });
    }

    window.useNicheTopic = function(topic) {
        if (studioTopicInput) studioTopicInput.value = topic;
        window.switchTab("studio");
    };

    // 8.2 Standalone Thumbnail Studio
    let activeStandalonePreset = "danger_red";
    document.querySelectorAll(".thumb-pre-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".thumb-pre-btn").forEach(b => {
                b.className = "thumb-pre-btn p-2.5 rounded-lg border border-slate-800 bg-dark-950 text-left text-xs font-bold text-slate-400";
            });
            btn.className = "thumb-pre-btn active p-2.5 rounded-lg border border-pink-500/40 bg-pink-500/10 text-left text-xs font-bold text-pink-400";
            activeStandalonePreset = btn.dataset.preset;
        });
    });

    const thumbTopicInput = document.getElementById("thumbTopicInput");
    const thumbGenerateStandaloneBtn = document.getElementById("thumbGenerateStandaloneBtn");
    const thumbStandaloneImg = document.getElementById("thumbStandaloneImg");
    const thumbStandaloneEmpty = document.getElementById("thumbStandaloneEmpty");
    const thumbStandaloneDownloadBtn = document.getElementById("thumbStandaloneDownloadBtn");

    if (thumbGenerateStandaloneBtn) {
        thumbGenerateStandaloneBtn.addEventListener("click", async () => {
            const topic = thumbTopicInput ? thumbTopicInput.value.trim() : "";
            if (!topic) {
                alert("Lütfen bir kapak başlığı girin!");
                return;
            }
            thumbGenerateStandaloneBtn.disabled = true;
            thumbGenerateStandaloneBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Kapak Üretiliyor...';

            try {
                const res = await fetch("/api/thumbnail/generate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        topic: topic,
                        style_preset: activeStandalonePreset
                    })
                });
                const data = await res.json();
                if (data.status === "success" && data.thumbnail_url) {
                    if (thumbStandaloneImg) {
                        thumbStandaloneImg.src = data.thumbnail_url + "?t=" + Date.now();
                        thumbStandaloneImg.classList.remove("hidden");
                    }
                    if (thumbStandaloneEmpty) thumbStandaloneEmpty.classList.add("hidden");
                    if (thumbStandaloneDownloadBtn) thumbStandaloneDownloadBtn.href = data.thumbnail_url;
                }
            } catch (e) {
                alert("Thumbnail üretilemedi: " + e);
            } finally {
                thumbGenerateStandaloneBtn.disabled = false;
                thumbGenerateStandaloneBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles mr-2"></i> Kapak Görselini Üret';
            }
        });
    }

    // 8.3 7-Day Warmup Checklist
    const warmupBadge = document.getElementById("warmupProgressBadge");
    const warmupChecks = document.querySelectorAll(".warmup-chk");

    function updateWarmupProgress() {
        const checkedList = [];
        warmupChecks.forEach((chk, i) => {
            if (chk.checked) checkedList.push(i);
        });
        localStorage.setItem("global_wave_warmup_checks", JSON.stringify(checkedList));
        if (warmupBadge) {
            warmupBadge.textContent = `${checkedList.length} / ${warmupChecks.length} Tamamlandı`;
            if (checkedList.length === warmupChecks.length) {
                warmupBadge.className = "text-xs font-mono text-emerald-400 font-bold";
            }
        }
    }

    try {
        const saved = JSON.parse(localStorage.getItem("global_wave_warmup_checks") || "[]");
        saved.forEach(idx => {
            if (warmupChecks[idx]) warmupChecks[idx].checked = true;
        });
        updateWarmupProgress();
    } catch (e) {}

    warmupChecks.forEach(chk => {
        chk.addEventListener("change", updateWarmupProgress);
    });

    // ==========================================
    // 9. JARVIS EXECUTIVE WHATSAPP & AI CONTROLLER
    // Full-Page Dedicated Experience, Real Baileys WhatsApp Daemon Sync
    // ==========================================
    function initJarvisHUD() {
        // State
        let activeChat = { id: "jarvis", name: "JARVIS Core", short_name: "JARVIS", phone: "", isAi: true };
        let allContacts = [];
        let jarvisAiFeed = [];
        let currentMessages = [];
        let lastPolledTimestamp = Math.floor(Date.now() / 1000) - 30;
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        let pollingInterval = null;

        // Elements
        const chatsListEl = document.getElementById("jarvisChatsList");
        const feedEl = document.getElementById("jarvisMessagesFeed");
        const inputEl = document.getElementById("jarvisChatInput");
        const formEl = document.getElementById("jarvisChatForm");
        const sendBtn = document.getElementById("jarvisSendBtn");
        const micBtn = document.getElementById("jarvisMicBtn");
        const aiDraftBtn = document.getElementById("jarvisAiDraftBtn");
        const activeTitleEl = document.getElementById("activeChatTitle");
        const activeSubEl = document.getElementById("activeChatSubtitle");
        const activeAvatarEl = document.getElementById("activeChatAvatar");
        const activeBadgeEl = document.getElementById("activeChatBadge");
        const backToJarvisBtn = document.getElementById("backToJarvisBtn");
        const quickBarEl = document.getElementById("jarvisQuickBar");
        const contactQuickBarEl = document.getElementById("contactQuickBar");
        const quickDraftReplyBtn = document.getElementById("quickDraftReplyBtn");
        const quickAskJarvisBtn = document.getElementById("quickAskJarvisBtn");
        const chatModeBadgeEl = document.getElementById("chatModeBadge");
        const chatTargetHintEl = document.getElementById("chatTargetHint");
        const clearBtn = document.getElementById("clearJarvisChatBtn");
        const refreshBtn = document.getElementById("chatRefreshBtn");
        const voiceCallBtn = document.getElementById("chatVoiceCallBtn");
        const deleteForMeBtn = document.getElementById("chatDeleteForMeBtn");
        const deleteForEveryoneBtn = document.getElementById("chatDeleteForEveryoneBtn");
        const searchInputEl = document.getElementById("jarvisChatSearchInput");
        const voiceToggleEl = document.getElementById("jarvisVoiceToggle");
        const contactCountBadge = document.getElementById("contactCountBadge");

        // Toast elements
        const toastEl = document.getElementById("jarvisGlobalToast");
        const toastSenderEl = document.getElementById("toastSender");
        const toastTimeEl = document.getElementById("toastTime");
        const toastBodyEl = document.getElementById("toastBody");
        const toastOpenBtn = document.getElementById("toastOpenBtn");
        const toastDismissBtn = document.getElementById("toastDismissBtn");

        if (!feedEl || !formEl) return;

        // Auto-scroll feed to bottom
        function scrollToBottom() {
            setTimeout(() => {
                if (feedEl) {
                    feedEl.scrollTop = feedEl.scrollHeight;
                }
            }, 60);
        }

        // --- Helper: Audio Chime for Inbound WhatsApp Messages ---
        function playMessageChime() {
            try {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                const ctx = new AudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "sine";
                osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
                osc.frequency.setValueAtTime(880, ctx.currentTime + 0.1); // A5
                gain.gain.setValueAtTime(0.18, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.35);
            } catch (e) {}
        }

        // --- Helper: Selective TTS Speech ---
        function speakText(text) {
            if (!voiceToggleEl || !voiceToggleEl.checked) return;
            if (!("speechSynthesis" in window)) return;
            window.speechSynthesis.cancel();
            
            // Clean markdown formatting tokens (*, _, #, `, [ ])
            let clean = text
                .replace(/[*_#`~]/g, "")
                .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
                .replace(/•/g, "")
                .trim();
            if (!clean) return;

            const utter = new SpeechSynthesisUtterance(clean);
            utter.lang = "tr-TR";
            utter.rate = 1.05;
            utter.pitch = 1.0;
            
            const voices = window.speechSynthesis.getVoices();
            const trVoice = voices.find(v => v.lang.includes("tr"));
            if (trVoice) utter.voice = trVoice;
            window.speechSynthesis.speak(utter);
        }
        window.speakJarvisText = speakText;

        // --- Show Floating Inbound WhatsApp Notification Toast ---
        let toastTimeout = null;
        function showInboundToast(senderName, time, text, contactObj) {
            if (!toastEl) return;
            playMessageChime();
            
            if (toastSenderEl) toastSenderEl.textContent = `YENİ MESAJ: ${senderName}`;
            if (toastTimeEl) toastTimeEl.textContent = time || "";
            if (toastBodyEl) toastBodyEl.textContent = text || "";

            toastEl.classList.remove("-translate-y-24", "opacity-0", "pointer-events-none");
            toastEl.classList.add("translate-y-0", "opacity-100");

            if (toastOpenBtn) {
                toastOpenBtn.onclick = () => {
                    dismissToast();
                    if (contactObj) {
                        switchChat(contactObj);
                    } else {
                        const matched = allContacts.find(c => c.name.toLowerCase().includes(senderName.toLowerCase()) || c.short_name.toLowerCase().includes(senderName.toLowerCase()));
                        if (matched) switchChat(matched);
                    }
                };
            }

            if (toastDismissBtn) {
                toastDismissBtn.onclick = dismissToast;
            }

            if (toastTimeout) clearTimeout(toastTimeout);
            toastTimeout = setTimeout(dismissToast, 9000);
        }

        function dismissToast() {
            if (!toastEl) return;
            toastEl.classList.remove("translate-y-0", "opacity-100");
            toastEl.classList.add("-translate-y-24", "opacity-0", "pointer-events-none");
        }

        // --- Append Message to Feed ---
        function appendMessage(sender, text, isUser = false, extraHtml = "", meta = {}) {
            const row = document.createElement("div");
            row.className = `flex items-start space-x-3 ${isUser ? "flex-row-reverse space-x-reverse" : ""}`;
            if (meta.messageId) row.setAttribute("data-msg-id", meta.messageId);
            if (meta.jid) row.setAttribute("data-jid", meta.jid);

            const avatarBg = isUser
                ? "bg-blue-600/20 border-blue-400/40 text-blue-300"
                : (sender === "JARVIS Core" || sender === "JARVIS" ? "bg-cyan-500/20 border-cyan-400/40 text-cyan-400" : "bg-emerald-500/20 border-emerald-400/40 text-emerald-300");

            const avatarIcon = isUser
                ? '<i class="fa-solid fa-user"></i>'
                : (sender === "JARVIS Core" || sender === "JARVIS" ? '<i class="fa-solid fa-atom"></i>' : sender.substring(0, 1).toUpperCase());

            const bubbleBg = isUser
                ? "bg-gradient-to-r from-blue-900/60 to-cyan-900/50 border border-cyan-500/30 text-slate-100 rounded-tr-sm"
                : "bg-dark-900/90 border border-slate-700/50 text-slate-200 rounded-tl-sm";

            const safeText = escapeHtml(text);
            let formatted = safeText
                .replace(/\*\*(.*?)\*\*/g, '<strong class="text-cyan-300">$1</strong>')
                .replace(/\*(.*?)\*/g, '<em class="text-slate-300">$1</em>')
                .replace(/\n/g, "<br>");

            let actionBtnHtml = "";
            if (meta.fromMe && meta.messageId) {
                actionBtnHtml = `
                    <div class="mt-1 flex items-center justify-end space-x-1 opacity-0 hover:opacity-100 transition-opacity">
                        <button onclick="window.deleteSingleMessage('${meta.jid}', '${meta.messageId}', true)" title="Herkesten Sil" class="text-[10px] text-rose-400/80 hover:text-rose-300 px-1.5 py-0.5 rounded bg-rose-950/40 border border-rose-500/30">
                            <i class="fa-solid fa-trash-can mr-1"></i>Herkesten Sil
                        </button>
                    </div>
                `;
            }

            row.innerHTML = `
                <div class="w-8 h-8 rounded-xl ${avatarBg} border flex items-center justify-center text-xs shrink-0 mt-0.5 font-bold font-mono shadow-sm">
                    ${avatarIcon}
                </div>
                <div class="${bubbleBg} rounded-2xl p-3.5 max-w-[85%] shadow-md">
                    <div class="flex items-center justify-between space-x-3 mb-1">
                        <span class="text-xs font-mono font-bold ${isUser ? "text-blue-300" : "text-cyan-400"}">${escapeHtml(sender)}</span>
                        ${meta.time ? `<span class="text-[10px] font-mono text-slate-500">${escapeHtml(meta.time)}</span>` : ""}
                    </div>
                    <div class="leading-relaxed text-sm">${formatted}</div>
                    ${extraHtml}
                    ${actionBtnHtml}
                </div>
            `;
            feedEl.appendChild(row);
            scrollToBottom();
        }

        // --- Save JARVIS Core AI chat memory ---
        function recordJarvisTurn(sender, text, isUser, extraHtml = "") {
            jarvisAiFeed.push({ sender, text, isUser, extraHtml });
            if (jarvisAiFeed.length > 50) jarvisAiFeed.shift();
        }

        // --- Load & Render Contacts Sidebar ---
        async function loadChatsList() {
            try {
                const res = await fetch("/api/jarvis/chats");
                const data = await res.json();
                if (data.status === "success" && Array.isArray(data.chats)) {
                    allContacts = data.chats;
                    renderContactsList(allContacts);
                    if (contactCountBadge) {
                        contactCountBadge.textContent = `${allContacts.length} Kişi Kayıtlı`;
                    }
                }
            } catch (err) {
                console.warn("[Jarvis] Could not load chats list:", err);
            }
        }

        function renderContactsList(contacts) {
            if (!chatsListEl) return;
            
            // Keep the pinned JARVIS tab at the very top
            const jarvisTab = document.getElementById("chatTab_jarvis");
            chatsListEl.innerHTML = "";
            if (jarvisTab) {
                jarvisTab.onclick = () => switchChat({ id: "jarvis", name: "JARVIS Core", short_name: "JARVIS", isAi: true });
                chatsListEl.appendChild(jarvisTab);
            }

            contacts.forEach(c => {
                const div = document.createElement("div");
                const isActive = activeChat.id === c.id;
                div.className = `jarvis-chat-tab p-3 hover:bg-slate-800/50 cursor-pointer transition-all flex items-center space-x-3 ${isActive ? "active bg-slate-800/90 border-l-4 border-emerald-400" : ""}`;
                div.setAttribute("data-chat-id", c.id);

                const initial = c.short_name ? c.short_name.substring(0, 1).toUpperCase() : "?";
                const unreadHtml = c.unread_count > 0
                    ? `<span class="bg-emerald-500 text-dark-950 font-bold text-[10px] px-1.5 py-0.5 rounded-full font-mono shrink-0 shadow-sm shadow-emerald-500/30 animate-pulse">${c.unread_count}</span>`
                    : "";

                div.innerHTML = `
                    <div class="w-10 h-10 rounded-xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-200 text-sm font-bold font-mono shrink-0 shadow-sm relative">
                        <span>${escapeHtml(initial)}</span>
                        ${c.unread_count > 0 ? '<span class="w-2.5 h-2.5 rounded-full bg-emerald-400 absolute -top-1 -right-1 border-2 border-dark-950"></span>' : ''}
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between">
                            <h4 class="text-xs font-bold text-slate-200 truncate font-sans">${escapeHtml(c.name)}</h4>
                            <span class="text-[10px] font-mono text-slate-500 shrink-0">${escapeHtml(c.last_time || "")}</span>
                        </div>
                        <div class="flex items-center justify-between mt-0.5">
                            <p class="text-[11px] text-slate-400 truncate max-w-[170px]">${escapeHtml(c.last_text || "Henüz mesaj yok")}</p>
                            ${unreadHtml}
                        </div>
                    </div>
                `;

                div.onclick = () => switchChat(c);
                chatsListEl.appendChild(div);
            });
        }

        // --- Filter Contacts in Sidebar ---
        if (searchInputEl) {
            searchInputEl.addEventListener("input", (e) => {
                const q = e.target.value.toLowerCase().trim();
                const filtered = allContacts.filter(c => 
                    c.name.toLowerCase().includes(q) || 
                    c.short_name.toLowerCase().includes(q) || 
                    c.phone.includes(q)
                );
                renderContactsList(filtered);
            });
        }

        // --- Switch Active Chat Tab ---
        async function switchChat(chatObj) {
            activeChat = chatObj;
            
            // Update sidebar active classes
            document.querySelectorAll(".jarvis-chat-tab").forEach(tab => {
                tab.classList.remove("active", "bg-cyan-950/40", "bg-slate-800/90", "border-l-4", "border-cyan-400", "border-emerald-400");
                if (tab.getAttribute("data-chat-id") === String(chatObj.id)) {
                    if (chatObj.id === "jarvis") {
                        tab.classList.add("active", "bg-cyan-950/40", "border-l-4", "border-cyan-400");
                    } else {
                        tab.classList.add("active", "bg-slate-800/90", "border-l-4", "border-emerald-400");
                    }
                }
            });

            feedEl.innerHTML = "";

            if (chatObj.id === "jarvis") {
                // JARVIS CORE AI TAB
                if (activeTitleEl) activeTitleEl.textContent = "JARVIS Komuta Merkezi";
                if (activeSubEl) activeSubEl.textContent = "Mücahit Hilmi • Doğrudan Yönetici Hattı";
                if (activeBadgeEl) activeBadgeEl.classList.add("hidden");
                if (backToJarvisBtn) backToJarvisBtn.classList.add("hidden");
                if (activeAvatarEl) {
                    activeAvatarEl.className = "w-8 h-8 rounded-xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-300 text-sm shrink-0 font-bold font-mono";
                    activeAvatarEl.innerHTML = '<i class="fa-solid fa-atom"></i>';
                }
                if (inputEl) inputEl.placeholder = "JARVIS ile konuşun: 'Adem'e mesaj hazırla', 'Babam ne yazmış?', 'YouTube yorumları'...";
                if (quickBarEl) quickBarEl.classList.remove("hidden");
                if (contactQuickBarEl) contactQuickBarEl.classList.add("hidden");
                if (aiDraftBtn) aiDraftBtn.classList.add("hidden");

                if (chatModeBadgeEl) {
                    chatModeBadgeEl.className = "flex items-center space-x-1 text-cyan-400 font-semibold";
                    chatModeBadgeEl.innerHTML = '<i class="fa-solid fa-atom text-[9px]"></i><span>JARVIS Asistan Hattı</span>';
                }
                if (chatTargetHintEl) {
                    chatTargetHintEl.textContent = "Mikrofonla konuşabilir veya yazabilirsiniz";
                }

                // Restore AI history
                if (jarvisAiFeed.length === 0) {
                    appendMessage("JARVIS Core", "Emrinizdeyim Efendim. Sistemler tamamen hazır. Sol taraftaki rehberden dilediğiniz kişiyle sohbet sekmesine geçebilir, mesajları herkesten silebilir veya bana yeni bir WhatsApp mesajı hazırlatabilirsiniz. Nasıl yardımcı olabilirim?");
                } else {
                    jarvisAiFeed.forEach(m => appendMessage(m.sender, m.text, m.isUser, m.extraHtml));
                }
            } else {
                // WHATSAPP CONTACT TAB (e.g. Adem, Babam, etc.)
                if (activeTitleEl) activeTitleEl.textContent = chatObj.name;
                if (activeSubEl) activeSubEl.textContent = `${chatObj.phone || ""} • Canlı WhatsApp Sohbeti (Baileys Sync)`;
                if (activeBadgeEl) activeBadgeEl.classList.remove("hidden");
                if (backToJarvisBtn) backToJarvisBtn.classList.remove("hidden");
                if (activeAvatarEl) {
                    activeAvatarEl.className = "w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center text-emerald-300 text-sm shrink-0 font-bold font-mono";
                    activeAvatarEl.textContent = chatObj.short_name ? chatObj.short_name.substring(0, 1).toUpperCase() : "?";
                }
                if (inputEl) inputEl.placeholder = `${chatObj.short_name} kişisine doğrudan WhatsApp mesajı yaz veya mikrofonla söyle...`;
                if (quickBarEl) quickBarEl.classList.add("hidden");
                if (contactQuickBarEl) contactQuickBarEl.classList.remove("hidden");
                if (aiDraftBtn) aiDraftBtn.classList.remove("hidden");

                if (chatModeBadgeEl) {
                    chatModeBadgeEl.className = "flex items-center space-x-1 text-emerald-400 font-semibold";
                    chatModeBadgeEl.innerHTML = `<i class="fa-brands fa-whatsapp text-[9px]"></i><span>WhatsApp: ${escapeHtml(chatObj.short_name)}</span>`;
                }
                if (chatTargetHintEl) {
                    chatTargetHintEl.textContent = `Bu kişiye doğrudan WhatsApp mesajı iletilir`;
                }

                // Load real message history with this contact
                await loadContactMessages(chatObj.short_name);

                // Mark as read on server
                try {
                    await fetch(`/api/jarvis/chats/${encodeURIComponent(chatObj.short_name)}/read`, { method: "POST" });
                    chatObj.unread_count = 0;
                    renderContactsList(allContacts);
                } catch(e) {}
            }
            scrollToBottom();
        }

        // Button: Back to JARVIS
        if (backToJarvisBtn) {
            backToJarvisBtn.addEventListener("click", () => {
                switchChat({ id: "jarvis", name: "JARVIS Core", short_name: "JARVIS", isAi: true });
            });
        }

        // --- Load & Render Specific Contact Messages ---
        async function loadContactMessages(contactQuery) {
            feedEl.innerHTML = `
                <div class="flex items-center justify-center py-12 text-slate-400 text-xs font-mono">
                    <i class="fa-solid fa-spinner fa-spin mr-2 text-cyan-400 text-sm"></i>
                    Canlı WhatsApp mesajları yükleniyor...
                </div>
            `;
            try {
                const res = await fetch(`/api/jarvis/chats/${encodeURIComponent(contactQuery)}/messages`);
                const data = await res.json();
                feedEl.innerHTML = "";

                if (data.status === "success" && Array.isArray(data.messages) && data.messages.length > 0) {
                    currentMessages = data.messages;
                    data.messages.forEach(m => {
                        const isMe = m.from_me === true || m.sender_jid === "me";
                        const sender = isMe ? "Mücahit Hilmi" : (m.sender_name || contactQuery);
                        appendMessage(sender, m.text, isMe, "", {
                            time: m.time,
                            messageId: m.id,
                            jid: m.chat_jid || m.sender_jid,
                            fromMe: isMe
                        });
                    });
                } else {
                    feedEl.innerHTML = `
                        <div class="text-center py-16 text-slate-400 text-xs space-y-2 font-sans">
                            <div class="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto text-xl">
                                <i class="fa-brands fa-whatsapp"></i>
                            </div>
                            <p class="font-bold text-slate-300">Henüz Mesaj Kaydı Yok</p>
                            <p class="text-slate-500 text-[11px]">Aşağıdaki giriş alanından ${escapeHtml(contactQuery)} kişisine ilk WhatsApp mesajını iletebilirsiniz.</p>
                        </div>
                    `;
                }
            } catch (err) {
                feedEl.innerHTML = `<div class="p-4 text-center text-rose-400 text-xs">Mesaj geçmişi yüklenemedi: ${escapeHtml(err.message)}</div>`;
            }
            scrollToBottom();
        }

        // --- Send Action (Form Submit) ---
        async function handleSendMessage(text) {
            if (!text || !text.trim()) return;
            const msg = text.trim();
            if (inputEl) inputEl.value = "";

            if (activeChat.id === "jarvis") {
                // SEND TO JARVIS CORE
                appendMessage("Mücahit Hilmi", msg, true);
                recordJarvisTurn("Mücahit Hilmi", msg, true);

                if (sendBtn) sendBtn.disabled = true;
                try {
                    const resp = await authFetch("/api/jarvis/chat", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ message: msg })
                    });
                    const data = await resp.json();
                    if (data.status === "success" && data.result) {
                        const reply = data.result.reply;
                        let extraHtml = "";

                        // If JARVIS generated a draft, render interactive Human-In-The-Loop confirmation card
                        if (data.result.action_taken === "draft_created" || data.result.action_taken === "draft_revised") {
                            const activeDraftId = data.result.draft ? data.result.draft.draft_id : "";
                            extraHtml = `
                                <div id="draftActionsBox" class="mt-3 pt-3 border-t border-cyan-500/30 flex items-center gap-2">
                                    <button onclick="window.confirmJarvisDraft(this, '${activeDraftId}')" class="px-3.5 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm">
                                        <i class="fa-solid fa-paper-plane text-emerald-400"></i> Onayla ve Gönder
                                    </button>
                                    <button onclick="window.cancelJarvisDraft(this, '${activeDraftId}')" class="px-3.5 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm">
                                        <i class="fa-solid fa-xmark text-rose-400"></i> İptal Et
                                    </button>
                                </div>
                            `;
                        }

                        appendMessage("JARVIS Core", reply, false, extraHtml);
                        recordJarvisTurn("JARVIS Core", reply, false, extraHtml);

                        const toSpeak = data.result.speak_text || reply;
                        speakText(toSpeak);

                        if (data.result.action_taken === "contact_saved") {
                            loadChatsList();
                        }
                    } else {
                        appendMessage("JARVIS Core", "Bir sorun oluştu efendim, lütfen tekrar deneyin.", false);
                    }
                } catch (err) {
                    appendMessage("JARVIS Core", "Bağlantı hatası: " + err.message, false);
                } finally {
                    if (sendBtn) sendBtn.disabled = false;
                }
            } else {
                // DIRECT WHATSAPP MESSAGE TO ACTIVE CONTACT
                appendMessage("Mücahit Hilmi", msg, true, "", { time: "Şimdi", fromMe: true });
                if (sendBtn) sendBtn.disabled = true;

                try {
                    const resp = await authFetch(`/api/jarvis/chats/${encodeURIComponent(activeChat.short_name)}/send`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ text: msg, confirm: true })
                    });
                    const data = await resp.json();
                    if (data.status === "success" && data.result && data.result.success) {
                        speakText("Mesaj WhatsApp üzerinden iletildi efendim.");
                        loadChatsList();
                    } else {
                        appendMessage("Sistem", `Mesaj iletilemedi: ${data.result ? data.result.error : "Bilinmeyen hata"}`, false);
                    }
                } catch (err) {
                    appendMessage("Sistem", "Gönderim hatası: " + err.message, false);
                } finally {
                    if (sendBtn) sendBtn.disabled = false;
                }
            }
            scrollToBottom();
        }

        formEl.addEventListener("submit", (e) => {
            e.preventDefault();
            const val = inputEl ? inputEl.value : "";
            handleSendMessage(val);
        });

        // --- Quick Prompts Click Handlers ---
        document.querySelectorAll(".jarvis-quick-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const text = btn.textContent.trim();
                handleSendMessage(text);
            });
        });

        // Contact Quick Actions:
        if (quickDraftReplyBtn) {
            quickDraftReplyBtn.addEventListener("click", () => {
                const targetName = activeChat.short_name;
                switchChat({ id: "jarvis", name: "JARVIS Core", short_name: "JARVIS", isAi: true });
                handleSendMessage(`${targetName} kişisine hal hatır soran samimi bir mesaj taslağı hazırla`);
            });
        }

        if (quickAskJarvisBtn) {
            quickAskJarvisBtn.addEventListener("click", () => {
                const targetName = activeChat.short_name;
                switchChat({ id: "jarvis", name: "JARVIS Core", short_name: "JARVIS", isAi: true });
                handleSendMessage(`${targetName} kişisinin son mesajlarını analiz et ve bana ne yanıt vermem gerektiğini söyle`);
            });
        }

        // --- Clear Chat ---
        if (clearBtn) {
            clearBtn.addEventListener("click", () => {
                feedEl.innerHTML = "";
                if (activeChat.id === "jarvis") {
                    jarvisAiFeed = [];
                    appendMessage("JARVIS Core", "Akış temizlendi efendim. Emrinizdeyim.", false);
                }
            });
        }

        // --- Refresh Button ---
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => {
                loadChatsList();
                if (activeChat.id !== "jarvis") {
                    loadContactMessages(activeChat.short_name);
                }
            });
        }

        // --- Voice Call Button ---
        if (voiceCallBtn) {
            voiceCallBtn.addEventListener("click", () => {
                if (activeChat.id === "jarvis" || !activeChat.phone) {
                    alert("Efendim, sesli arama yapmak için lütfen sol taraftan bir kişi (örn: Adem, Babam) seçin.");
                    return;
                }
                const cleanPhone = activeChat.phone.replace(/[^0-9]/g, "");
                const waCallUrl = `https://wa.me/${cleanPhone}`;
                window.open(waCallUrl, "_blank");
                speakText(`${activeChat.short_name} aranıyor efendim.`);
            });
        }

        // --- Delete For Everyone Button (Top Toolbar) ---
        if (deleteForEveryoneBtn) {
            deleteForEveryoneBtn.addEventListener("click", async () => {
                if (activeChat.id === "jarvis") {
                    alert("Efendim, WhatsApp mesajı silmek için lütfen önce ilgili kişinin sohbet sekmesini açın.");
                    return;
                }
                const lastOutbound = [...currentMessages].reverse().find(m => m.from_me === true || m.sender_jid === "me");
                if (!lastOutbound || !lastOutbound.id) {
                    alert("Bu sohbette herkesten silinebilecek size ait bir mesaj bulunamadı.");
                    return;
                }
                if (!confirm(`"${lastOutbound.text}" mesajı WhatsApp'ta herkesten silinsin mi?`)) return;

                const jid = lastOutbound.chat_jid || activeChat.phone;
                await window.deleteSingleMessage(jid, lastOutbound.id, true);
            });
        }

        // --- Delete For Me Button (Top Toolbar) ---
        if (deleteForMeBtn) {
            deleteForMeBtn.addEventListener("click", async () => {
                if (activeChat.id === "jarvis") {
                    feedEl.innerHTML = "";
                    jarvisAiFeed = [];
                    return;
                }
                const lastMsg = currentMessages[currentMessages.length - 1];
                if (!lastMsg) return;
                const jid = lastMsg.chat_jid || activeChat.phone;
                await window.deleteSingleMessage(jid, lastMsg.id, false);
            });
        }

        // --- Delete Single Message Implementation ---
        window.deleteSingleMessage = async function(jid, messageId, everyone = true) {
            try {
                const res = await authFetch("/api/jarvis/message/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ jid, message_id: messageId, everyone })
                });
                const data = await res.json();
                if (data.status === "success") {
                    const el = feedEl.querySelector(`[data-msg-id="${messageId}"]`);
                    if (el) {
                        el.style.opacity = "0.4";
                        el.innerHTML = `<div class="p-2 text-xs italic text-slate-500"><i class="fa-solid fa-ban mr-1"></i> Bu mesaj ${everyone ? 'herkesten' : 'bu cihazdan'} silindi.</div>`;
                    }
                    speakText(everyone ? "Mesaj herkesten silindi efendim." : "Mesaj yerel sohbetten kaldırıldı.");
                    loadChatsList();
                }
            } catch (err) {
                alert("Silme hatası: " + err.message);
            }
        };

        // --- AI Smart Reply / Draft Helper for Active Contact ---
        if (aiDraftBtn) {
            aiDraftBtn.addEventListener("click", () => {
                const prompt = window.prompt(`${activeChat.name} kişisine nasıl bir mesaj hazırlayayım efendim? (Örn: 'Halini hatrını sor', 'Kendini tanıtarak selam yaz')`, "Halini hatrını soran samimi bir selam yaz");
                if (prompt) {
                    const targetName = activeChat.short_name;
                    switchChat({ id: "jarvis", name: "JARVIS Core", short_name: "JARVIS", isAi: true });
                    handleSendMessage(`${targetName} kişisine ${prompt}`);
                }
            });
        }

        // --- Microphone Voice STT Logic ---
        if (micBtn) {
            micBtn.addEventListener("click", async () => {
                if (isRecording) {
                    if (mediaRecorder && mediaRecorder.state !== "inactive") {
                        mediaRecorder.stop();
                    }
                    isRecording = false;
                    micBtn.classList.remove("bg-rose-600", "text-white", "animate-pulse");
                    micBtn.classList.add("text-cyan-400", "bg-dark-950");
                } else {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        audioChunks = [];
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.ondataavailable = (e) => {
                            if (e.data.size > 0) audioChunks.push(e.data);
                        };
                        mediaRecorder.onstop = async () => {
                            stream.getTracks().forEach(t => t.stop());
                            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
                            const formData = new FormData();
                            formData.append("file", audioBlob, "speech.webm");

                            if (inputEl) inputEl.placeholder = "Ses analiz ediliyor (Faster-Whisper)...";
                            try {
                                const resp = await fetch("/api/jarvis/transcribe", {
                                    method: "POST",
                                    body: formData
                                });
                                const trData = await resp.json();
                                if (trData.status === "success" && trData.text) {
                                    if (inputEl) inputEl.value = trData.text;
                                    handleSendMessage(trData.text);
                                } else {
                                    if (inputEl) inputEl.placeholder = "Ses anlaşılamadı, tekrar deneyin...";
                                }
                            } catch (e) {
                                console.error("[Jarvis] STT Error:", e);
                            }
                        };
                        mediaRecorder.start();
                        isRecording = true;
                        micBtn.classList.remove("text-cyan-400", "bg-dark-950");
                        micBtn.classList.add("bg-rose-600", "text-white", "animate-pulse");
                        if (inputEl) inputEl.placeholder = "Sizi dinliyorum Sayın Hilmi...";
                    } catch (err) {
                        alert("Mikrofon erişim izni alınamadı: " + err.message);
                    }
                }
            });
        }

        // --- Live WhatsApp Inbound Message Poller (Every 3.5s) ---
        async function checkInboundMessages() {
            try {
                const res = await fetch(`/api/jarvis/inbox/check_new?since=${lastPolledTimestamp}`);
                const data = await res.json();
                if (data.status === "success") {
                    if (Array.isArray(data.new_messages) && data.new_messages.length > 0) {
                        data.new_messages.forEach(m => {
                            if (m.timestamp > lastPolledTimestamp) {
                                lastPolledTimestamp = m.timestamp;
                            }
                            showInboundToast(m.sender_name || "Bilinmeyen Kişi", m.time, m.text);

                            if (activeChat.id !== "jarvis" && (
                                (m.sender_name && m.sender_name.toLowerCase().includes(activeChat.short_name.toLowerCase())) ||
                                (m.phone && activeChat.phone && activeChat.phone.includes(m.phone))
                            )) {
                                appendMessage(m.sender_name, m.text, false, "", { time: m.time, messageId: m.id, fromMe: false });
                            }
                        });
                        if (Array.isArray(data.overview)) {
                            allContacts = data.overview;
                            renderContactsList(allContacts);
                        }
                    }
                }
            } catch(e) {}
        }

        pollingInterval = setInterval(checkInboundMessages, 3500);

        // Hardware & VRAM Telemetry Loop
        async function updateTelemetry() {
            try {
                const r = await fetch("/api/jarvis/telemetry");
                const d = await r.json();
                if (d.status === "success" && d.metrics) {
                    const el = document.getElementById("jarvisVramText");
                    if (el) {
                        el.textContent = `RAM: %${d.metrics.ram_used_pct} (%${d.metrics.swap_used_pct} Swap)`;
                    }
                }
            } catch(e) {}
        }
        updateTelemetry();
        setInterval(updateTelemetry, 10000);

        // Initial contacts load
        loadChatsList();
        switchChat({ id: "jarvis", name: "JARVIS Core", short_name: "JARVIS", isAi: true });

        // --- GLOBAL EXPORTS FOR BUTTON ONCLICK CALLS ---
        window.confirmJarvisDraft = async function(btn, draftId = "") {
            const container = btn ? btn.closest("#draftActionsBox") : null;
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Gönderiliyor...';
            }
            try {
                const res = await authFetch("/api/jarvis/draft/confirm", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ draft_id: draftId })
                });
                const data = await res.json();
                if (data.status === "success" && data.result) {
                    if (container) {
                        container.innerHTML = `
                            <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-950/70 border border-emerald-500/40 text-emerald-300 font-semibold text-xs mt-1 shadow-sm">
                                <i class="fa-solid fa-circle-check text-emerald-400"></i> Mesaj WhatsApp ile başarıyla iletildi
                            </div>
                        `;
                    }
                    appendMessage("JARVIS Core", data.result.reply, false);
                    speakText(data.result.speak_text || "Mesaj WhatsApp üzerinden başarıyla iletildi efendim.");
                    loadChatsList();
                } else {
                    if (container) {
                        container.innerHTML = `<div class="text-xs text-rose-400 mt-1">Gönderim başarısız oldu.</div>`;
                    }
                }
            } catch (err) {
                if (container) {
                    container.innerHTML = `<div class="text-xs text-rose-400 mt-1">Gönderim hatası: ${escapeHtml(err.message)}</div>`;
                }
            }
            scrollToBottom();
        };

        window.cancelJarvisDraft = async function(btn, draftId = "") {
            const container = btn ? btn.closest("#draftActionsBox") : null;
            if (btn) btn.disabled = true;
            try {
                const res = await authFetch("/api/jarvis/draft/cancel", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ draft_id: draftId })
                });
                const data = await res.json();
                if (data.status === "success" && data.result) {
                    if (container) {
                        container.innerHTML = `
                            <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-950/70 border border-rose-500/40 text-rose-300 font-semibold text-xs mt-1 shadow-sm">
                                <i class="fa-solid fa-circle-xmark text-rose-400"></i> Mesaj taslağı iptal edildi
                            </div>
                        `;
                    }
                    appendMessage("JARVIS Core", data.result.reply, false);
                    speakText(data.result.speak_text || "Mesaj gönderimi iptal edildi efendim.");
                }
            } catch (err) {
                if (container) {
                    container.innerHTML = `<div class="text-xs text-rose-400 mt-1">İptal hatası: ${escapeHtml(err.message)}</div>`;
                }
            }
            scrollToBottom();
        };
    }

    initJarvisHUD();
    // Launch Application
    initApp();
});

