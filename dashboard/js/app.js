// Store Intelligence Dashboard Javascript API Controller

const API_BASE = window.location.origin; // Dynamically resolve backend host
let wsClient = null;
let funnelChart = null;

// DOM Elements
const storeSelector = document.getElementById("store-selector");
const refreshBtn = document.getElementById("refresh-btn");
const simBtn = document.getElementById("sim-btn");
const simPanel = document.getElementById("sim-control-panel");
const simClose = document.getElementById("sim-close");
const simProgressBar = document.getElementById("sim-progress-bar");
const simTimeText = document.getElementById("sim-time");
const simEventCountText = document.getElementById("sim-event-count");

const statVisitors = document.getElementById("stat-visitors");
const statConversion = document.getElementById("stat-conversion");
const statConversionBar = document.getElementById("stat-conversion-bar");
const statQueue = document.getElementById("stat-queue");
const statQueueStatus = document.getElementById("stat-queue-status");
const statAbandonment = document.getElementById("stat-abandonment");
const statAbandonmentBar = document.getElementById("stat-abandonment-bar");
const queueCard = document.getElementById("queue-card");
const queueIconWrap = document.getElementById("queue-icon-wrap");

const anomaliesFeed = document.getElementById("anomalies-feed");
const anomaliesBadge = document.getElementById("anomaly-badge");
const eventsFeed = document.getElementById("events-feed");
const heatmapConfidence = document.getElementById("heatmap-confidence");
const audioToggleBtn = document.getElementById("audio-toggle-btn");

// Event Stream State
let simulationInterval = null;
let simulationStep = 0;
let eventsIngestedCount = 0;
let activeCameraId = "CAM_3";

// Audio & Speech Synthesis State
let voiceEnabled = false;
let announcedAnomalies = new Set();
let announcedInsights = new Set();
let audioContext = null;

function getAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === "suspended") {
        audioContext.resume();
    }
    return audioContext;
}

function playSynthTone(type) {
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        
        if (type === "startup") {
            // A beautiful futuristic tech chime (C5 -> E5 -> G5 -> C6)
            playTone(523.25, 0.1, now);
            playTone(659.25, 0.1, now + 0.08);
            playTone(783.99, 0.1, now + 0.16);
            playTone(1046.50, 0.25, now + 0.24);
        } else if (type === "shutdown") {
            // Descending tone
            playTone(783.99, 0.1, now);
            playTone(523.25, 0.2, now + 0.1);
        } else if (type === "critical") {
            // Staccato dual siren alert
            playTone(880, 0.12, now);
            playTone(880, 0.12, now + 0.15);
        } else if (type === "warning") {
            // Double warning beep
            playTone(587.33, 0.15, now);
            playTone(587.33, 0.15, now + 0.2);
        } else if (type === "chime") {
            // Soft sonar ping
            playTone(1200, 0.08, now, 0.05);
        } else if (type === "exit") {
            // Soft bubble pop
            playTone(400, 0.05, now, 0.03);
        }
    } catch (e) {
        console.warn("Synth audio blocked or failed:", e);
    }
}

function playTone(frequency, duration, startTime, volume = 0.1) {
    const ctx = audioContext;
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();
    
    osc.type = "sine";
    osc.frequency.setValueAtTime(frequency, startTime);
    
    gainNode.gain.setValueAtTime(volume, startTime);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);
    
    osc.connect(gainNode);
    gainNode.connect(ctx.destination);
    
    osc.start(startTime);
    osc.stop(startTime + duration);
}

function speakText(text) {
    if (!voiceEnabled) return;
    if (window.location.search.includes("autodemo=true")) return; // Silence browser TTS during auto recording
    try {
        window.speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(v => v.lang.startsWith("en-US") || v.lang.startsWith("en-GB"));
        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }
        
        window.speechSynthesis.speak(utterance);
    } catch (e) {
        console.warn("Text to speech failed:", e);
    }
}

function toggleVoiceAssistant() {
    voiceEnabled = !voiceEnabled;
    const audioIcon = document.getElementById("audio-icon");
    const audioText = document.getElementById("audio-text");
    
    if (voiceEnabled) {
        getAudioContext();
        
        audioToggleBtn.classList.remove("btn-secondary");
        audioToggleBtn.classList.add("btn-primary");
        audioIcon.className = "fa-solid fa-volume-high";
        audioIcon.style.transform = "scale(1.2)";
        audioText.textContent = "Voice Copilot On";
        
        playSynthTone("startup");
        setTimeout(() => {
            speakText("Voice Copilot enabled. Real-time store operations copilot is live.");
        }, 500);
    } else {
        speakText("Voice Copilot disabled.");
        setTimeout(() => {
            audioToggleBtn.classList.remove("btn-primary");
            audioToggleBtn.classList.add("btn-secondary");
            audioIcon.className = "fa-solid fa-volume-xmark";
            audioIcon.style.transform = "scale(1.0)";
            audioText.textContent = "Voice Copilot Off";
            
            playSynthTone("shutdown");
        }, 1200);
    }
}

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    setupWebSocket();
    loadDashboardData();
    setupCameraTabs();
    updateCameraStream();

    // Event Listeners
    storeSelector.addEventListener("change", () => {
        loadDashboardData();
        updateCameraStream();
        if (voiceEnabled) {
            const storeName = storeSelector.options[storeSelector.selectedIndex].text;
            const branchName = storeName.split(" - ")[1] || storeName;
            speakText(`Switched active store to ${branchName}`);
        }
    });
    refreshBtn.addEventListener("click", loadDashboardData);
    simBtn.addEventListener("click", startFootageSimulation);
    simClose.addEventListener("click", stopFootageSimulation);
    if (audioToggleBtn) {
        audioToggleBtn.addEventListener("click", toggleVoiceAssistant);
    }
    // Automatically start presentation slides if ?autodemo=true query param is set
    initAutodemo();
    // Pre-load camera frames for zero-latency switching on GitHub Pages
    preloadCameraFrames();
});

function preloadCameraFrames() {
    if (window.location.hostname.includes("github.io")) {
        for (let i = 1; i <= 5; i++) {
            const img = new Image();
            img.src = `../cam${i}_frame.png`;
        }
    }
}

// Setup Camera tab buttons click listeners
function setupCameraTabs() {
    document.querySelectorAll(".cam-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".cam-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            activeCameraId = tab.dataset.camera;
            updateCameraStream();
        });
    });
}

// Refresh the img tag src for processed video stream
function updateCameraStream() {
    const selectedStore = storeSelector.value;
    const streamImg = document.getElementById("cctv-stream");
    const videoEl = document.getElementById("cctv-video");
    const camNum = activeCameraId.split("_")[1] || "3";
    
    const isStaticMode = window.location.hostname.includes("github.io") || 
                         window.location.protocol === "file:" || 
                         window.location.search.includes("static=true");
    
    if (isStaticMode) {
        // GitHub Pages or static local file: Play HD MP4 loop
        if (streamImg) streamImg.style.display = "none";
        if (videoEl) {
            videoEl.style.display = "block";
            const targetSrc = `cam${camNum}_loop.mp4`;
            // Avoid reload flash if same camera
            if (!videoEl.src.includes(targetSrc)) {
                videoEl.src = targetSrc;
                videoEl.load();
                videoEl.play().catch(e => console.warn("Auto-play blocked or failed:", e));
            }
        }
    } else {
        // Local with backend running: Stream dynamic multipart stream from FastAPI
        if (videoEl) videoEl.style.display = "none";
        if (streamImg) {
            streamImg.style.display = "block";
            streamImg.src = `${API_BASE}/stores/${selectedStore}/cameras/${activeCameraId}/stream`;
        }
    }
}

// Setup Chart.js Funnel
function initCharts() {
    const ctx = document.getElementById('funnelChart').getContext('2d');
    funnelChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['1. Entrance', '2. Zone Visit', '3. Join Queue', '4. Complete Purchase'],
            datasets: [{
                label: 'Unique Customer Count',
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.45)',  // Blue
                    'rgba(167, 139, 250, 0.45)', // Purple
                    'rgba(245, 158, 11, 0.45)',  // Orange
                    'rgba(16, 185, 129, 0.45)'   // Green
                ],
                borderColor: [
                    '#3b82f6',
                    '#a78bfa',
                    '#f59e0b',
                    '#10b981'
                ],
                borderWidth: 1.5,
                borderRadius: 8
            }]
        },
        options: {
            indexAxis: 'y', // Horizontal bars
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#f3f4f6', font: { family: 'Outfit', size: 13, weight: 600 } }
                }
            }
        }
    });
}

// Setup WebSocket Client
function setupWebSocket() {
    const wsUrl = `ws://${window.location.host}/events/stream`;
    
    try {
        wsClient = new WebSocket(wsUrl);
        
        wsClient.onopen = () => {
            console.log("WebSocket connection established.");
            updateStatusIndicator(true);
        };
        
        wsClient.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === "event_ingested_batch") {
                // Add events to real-time feed ticker
                data.events.forEach(addEventToFeed);
                // Trigger dashboard update
                loadDashboardData();
            } else if (data.type === "events_cleared") {
                // Reset feed ticker
                eventsFeed.innerHTML = `
                    <div class="empty-feed-state">
                        <i class="fa-solid fa-circle-nodes"></i>
                        <p>Waiting for pipeline events from CCTV camera stream...</p>
                    </div>
                `;
                // Clear active arrays
                announcedAnomalies.clear();
                announcedInsights.clear();
                // Trigger dashboard update to reset metrics and charts
                loadDashboardData();
            }
        };
        
        wsClient.onclose = () => {
            console.log("WebSocket connection closed. Retrying in 5 seconds...");
            updateStatusIndicator(false);
            setTimeout(setupWebSocket, 5000);
        };
        
        wsClient.onerror = (err) => {
            console.error("WebSocket error:", err);
            updateStatusIndicator(false);
        };
    } catch (e) {
        console.error("Failed to connect WebSocket:", e);
    }
}

function updateStatusIndicator(connected) {
    const statusDot = document.querySelector(".status-indicator");
    const statusText = document.querySelector(".sidebar-status span");
    if (connected) {
        statusDot.className = "status-indicator online";
        statusText.textContent = "Server: Connected";
    } else {
        statusDot.className = "status-indicator offline";
        statusText.textContent = "Server: Reconnecting";
    }
}

// Fetch dashboard data from API
async function loadDashboardData() {
    const storeId = storeSelector.value;
    
    if (window.location.hostname.includes("github.io")) {
        loadMockDashboardData(storeId);
        return;
    }
    
    try {
        // 1. Fetch Metrics
        const metricsRes = await fetch(`${API_BASE}/stores/${storeId}/metrics`);
        if (metricsRes.ok) {
            const metrics = await metricsRes.json();
            updateMetricsUI(metrics);
        }
        
        // 2. Fetch Funnel
        const funnelRes = await fetch(`${API_BASE}/stores/${storeId}/funnel`);
        if (funnelRes.ok) {
            const funnel = await funnelRes.json();
            updateFunnelUI(funnel);
        }
        
        // 3. Fetch Heatmap
        const heatmapRes = await fetch(`${API_BASE}/stores/${storeId}/heatmap`);
        if (heatmapRes.ok) {
            const heatmap = await heatmapRes.json();
            updateHeatmapUI(heatmap);
        }
        
        // 4. Fetch Anomalies
        const anomaliesRes = await fetch(`${API_BASE}/stores/${storeId}/anomalies`);
        if (anomaliesRes.ok) {
            const anomaliesData = await anomaliesRes.json();
            updateAnomaliesUI(anomaliesData.anomalies);
        }

        // 5. Fetch AI Insights (Copilot)
        loadAIInsights(storeId);

        // 6. Fetch Shopper Journeys
        loadVisitorJourneys(storeId);

        // 7. Fetch Layout Placement Optimizations
        loadLayoutPlacementOptimization(storeId);
    } catch (e) {
        console.error("Failed to load dashboard data:", e);
    }
}

// Update KPI UI Elements
function updateMetricsUI(metrics) {
    statVisitors.textContent = metrics.unique_visitors;
    statConversion.textContent = `${metrics.conversion_rate.toFixed(2)}%`;
    statConversionBar.style.width = `${Math.min(metrics.conversion_rate, 100)}%`;
    statQueue.textContent = metrics.queue_depth;
    statAbandonment.textContent = `${metrics.abandonment_rate.toFixed(2)}%`;
    statAbandonmentBar.style.width = `${Math.min(metrics.abandonment_rate, 100)}%`;

    // Queue styling warnings
    if (metrics.queue_depth >= 5) {
        queueCard.style.borderColor = 'var(--accent-red)';
        queueIconWrap.className = 'kpi-icon-wrapper red';
        statQueueStatus.className = 'kpi-trend negative';
        statQueueStatus.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Critical Spike';
    } else if (metrics.queue_depth >= 3) {
        queueCard.style.borderColor = 'var(--accent-orange)';
        queueIconWrap.className = 'kpi-icon-wrapper orange';
        statQueueStatus.className = 'kpi-trend warn';
        statQueueStatus.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Building';
    } else {
        queueCard.style.borderColor = 'var(--glass-border)';
        queueIconWrap.className = 'kpi-icon-wrapper orange';
        statQueueStatus.className = 'kpi-trend neutral';
        statQueueStatus.textContent = 'Normal';
    }
}

// Update Conversion Funnel Chart
function updateFunnelUI(funnelData) {
    if (!funnelChart || !funnelData.funnel) return;
    
    const counts = funnelData.funnel.map(f => f.count);
    funnelChart.data.datasets[0].data = counts;
    funnelChart.update();
}

// Update Interactive Store Layout Heatmap
function updateHeatmapUI(heatmapData) {
    // Confidence indicator
    if (heatmapData.data_confidence) {
        heatmapConfidence.className = "badge green";
        heatmapConfidence.textContent = "High Confidence (>20 sessions)";
    } else {
        heatmapConfidence.className = "badge orange";
        heatmapConfidence.textContent = "Low Confidence (<20 sessions)";
    }

    // Default reset
    const zones = ["SKINCARE", "MAKEUP", "HAIRCARE", "FRAGRANCE"];
    zones.forEach(zone => {
        const el = document.getElementById(`zone-${zone}`);
        if (el) {
            el.style.backgroundColor = "rgba(255, 255, 255, 0.01)";
            el.querySelector(".zone-visits").textContent = `Visits: 0`;
            el.querySelector(".zone-dwell").textContent = `Avg Dwell: 0.00s`;
        }
    });

    // Populate data
    heatmapData.heatmap.forEach(cell => {
        const el = document.getElementById(`zone-${cell.zone_id}`);
        if (el) {
            // Apply overlay color strength based on normalized score (0-100)
            let baseColor = "59, 130, 246"; // Blue default
            if (cell.zone_id === "SKINCARE") baseColor = "59, 130, 246";
            if (cell.zone_id === "MAKEUP") baseColor = "167, 139, 250";
            if (cell.zone_id === "HAIRCARE") baseColor = "16, 185, 129";
            if (cell.zone_id === "FRAGRANCE") baseColor = "245, 158, 11";
            if (cell.zone_id === "BILLING") baseColor = "244, 114, 182";

            const opacity = Math.max(0.04, (cell.normalized_score / 100) * 0.35);
            el.style.backgroundColor = `rgba(${baseColor}, ${opacity})`;
            el.style.borderColor = `rgba(${baseColor}, ${opacity + 0.1})`;
            
            el.querySelector(".zone-visits").textContent = `Visits: ${cell.visit_frequency}`;
            el.querySelector(".zone-dwell").textContent = `Avg Dwell: ${cell.avg_dwell_sec.toFixed(2)}s`;
        }
    });
}

// Update Active Anomalies Feed
function updateAnomaliesUI(anomalies) {
    anomaliesBadge.textContent = `${anomalies.length} Active`;
    
    if (anomalies.length === 0) {
        anomaliesFeed.innerHTML = `
            <div class="empty-feed-state">
                <i class="fa-regular fa-circle-check"></i>
                <p>No anomalies detected. Store operations running smoothly.</p>
            </div>
        `;
        return;
    }
    
    // Play sound and speak if there are new anomalies
    anomalies.forEach(anomaly => {
        const compositeKey = `${anomaly.anomaly_type}-${anomaly.timestamp}-${anomaly.description}`;
        if (!announcedAnomalies.has(compositeKey)) {
            announcedAnomalies.add(compositeKey);
            if (voiceEnabled) {
                const isCritical = anomaly.severity === "CRITICAL";
                playSynthTone(isCritical ? "critical" : "warning");
                speakText(`${isCritical ? 'Critical Security Alert' : 'Operational Warning'}: ${anomaly.description}`);
            }
        }
    });
    
    let html = "";
    anomalies.forEach(anomaly => {
        const severityClass = anomaly.severity.toLowerCase(); // info, warn, critical
        const icon = severityClass === "critical" ? "fa-circle-xmark" : "fa-triangle-exclamation";
        
        html += `
            <div class="anomaly-card ${severityClass}">
                <div class="anomaly-icon"><i class="fa-solid ${icon}"></i></div>
                <div class="anomaly-details">
                    <div class="anomaly-title-row">
                        <span class="anomaly-type">${anomaly.anomaly_type}</span>
                        <span class="anomaly-time">${formatTimestamp(anomaly.timestamp)}</span>
                    </div>
                    <p class="anomaly-desc">${anomaly.description}</p>
                    <div class="anomaly-action"><i class="fa-solid fa-lightbulb"></i> Suggested Action: ${anomaly.suggested_action}</div>
                </div>
            </div>
        `;
    });
    
    anomaliesFeed.innerHTML = html;
}

// Add a live event ticker element
function addEventToFeed(event) {
    // Remove empty placeholder state if present
    const placeholder = eventsFeed.querySelector(".empty-feed-state");
    if (placeholder) placeholder.remove();

    let icon = "fa-circle-nodes";
    let iconClass = "zone";
    if (event.event_type === "ENTRY") { 
        icon = "fa-right-to-bracket"; 
        iconClass = "entry"; 
        if (voiceEnabled) {
            playSynthTone("chime");
            speakText(`Visitor ${event.visitor_id} entered the store.`);
        }
    }
    else if (event.event_type === "EXIT") { 
        icon = "fa-right-from-bracket"; 
        iconClass = "exit"; 
        if (voiceEnabled) {
            playSynthTone("exit");
            speakText(`Visitor ${event.visitor_id} exited the store.`);
        }
    }
    else if (event.event_type === "BILLING_QUEUE_JOIN") { 
        icon = "fa-people-group"; 
        iconClass = "queue"; 
        if (voiceEnabled) {
            playSynthTone("warning");
            speakText(`Visitor ${event.visitor_id} joined the billing queue.`);
        }
    }
    else if (event.event_type === "ZONE_DWELL") { 
        icon = "fa-clock"; 
        iconClass = "zone"; 
        if (voiceEnabled && event.metadata && event.metadata.sku_zone) {
            playSynthTone("chime");
            speakText(`Visitor ${event.visitor_id} is browsing ${event.metadata.sku_zone.toLowerCase()} in the ${event.zone_id.toLowerCase()} zone.`);
        }
    }

    const item = document.createElement("div");
    item.className = "event-item";
    
    const details = event.zone_id 
        ? `Visitor <span>${event.visitor_id}</span> in <span>${event.zone_id}</span> (${event.event_type})`
        : `Visitor <span>${event.visitor_id}</span> crossed <span>${event.event_type}</span> threshold`;

    item.innerHTML = `
        <div class="event-icon-circle ${iconClass}"><i class="fa-solid ${icon}"></i></div>
        <div class="event-content">
            <div class="event-details">${details}</div>
            <div class="event-time-stamp">${formatTimestamp(event.timestamp)}</div>
        </div>
    `;

    eventsFeed.insertBefore(item, eventsFeed.firstChild);
    
    // Cap feed items at 50 to maintain performance
    while (eventsFeed.children.length > 50) {
        eventsFeed.removeChild(eventsFeed.lastChild);
    }
}

// Utilities
function formatTimestamp(isoStr) {
    try {
        const timePart = isoStr.split("T")[1];
        return timePart ? timePart.substring(0, 8) : isoStr;
    } catch (e) {
        return isoStr;
    }
}

// Real-Time Demo Simulation Engine
async function startFootageSimulation() {
    if (simulationInterval) return;
    
    simulationStep = 0;
    eventsIngestedCount = 0;
    simPanel.classList.remove("hidden");
    simBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Simulating...';
    simBtn.disabled = true;
    speakText("Starting live store event simulation stream.");

    // Clear database before starting simulation to start metrics from scratch
    if (window.location.hostname.includes("github.io")) {
        localEvents = [];
        loadMockDashboardData(storeSelector.value);
    } else {
        try {
            await fetch(`${API_BASE}/events/clear`, { method: "POST" });
        } catch (e) {
            console.warn("Failed to clear DB at simulation start:", e);
        }
    }

    // Defined sequence of store events to represent raw CV mapping outputs
    const simEvents = [
        // 1. Visitor Entry
        { event_id: "e-001", store_id: "ST1008", camera_id: "CAM_3", visitor_id: "VIS_801", event_type: "ENTRY", timestamp: "2026-04-10T12:15:02Z", zone_id: null, dwell_ms: 0, is_staff: false },
        { event_id: "e-002", store_id: "ST1008", camera_id: "CAM_3", visitor_id: "VIS_802", event_type: "ENTRY", timestamp: "2026-04-10T12:15:10Z", zone_id: null, dwell_ms: 0, is_staff: false },
        
        // 2. Visitors walking into shelf zones
        { event_id: "e-003", store_id: "ST1008", camera_id: "CAM_1", visitor_id: "VIS_801", event_type: "ZONE_ENTER", timestamp: "2026-04-10T12:15:15Z", zone_id: "SKINCARE", dwell_ms: 0, is_staff: false },
        { event_id: "e-004", store_id: "ST1008", camera_id: "CAM_2", visitor_id: "VIS_802", event_type: "ZONE_ENTER", timestamp: "2026-04-10T12:15:25Z", zone_id: "MAKEUP", dwell_ms: 0, is_staff: false },
        
        // 3. Staff member working
        { event_id: "e-005", store_id: "ST1008", camera_id: "CAM_2", visitor_id: "VIS_STAFF_01", event_type: "ZONE_DWELL", timestamp: "2026-04-10T12:15:30Z", zone_id: "MAKEUP", dwell_ms: 30000, is_staff: true },
        
        // 4. Visitors dwelling on products
        { event_id: "e-006", store_id: "ST1008", camera_id: "CAM_1", visitor_id: "VIS_801", event_type: "ZONE_DWELL", timestamp: "2026-04-10T12:15:45Z", zone_id: "SKINCARE", dwell_ms: 30000, is_staff: false, metadata: { sku_zone: "MOISTURISER" } },
        { event_id: "e-007", store_id: "ST1008", camera_id: "CAM_2", visitor_id: "VIS_802", event_type: "ZONE_DWELL", timestamp: "2026-04-10T12:15:55Z", zone_id: "MAKEUP", dwell_ms: 30000, is_staff: false, metadata: { sku_zone: "LIPSTICK" } },
        
        // 5. Visitor 801 walking to Billing queue
        { event_id: "e-008", store_id: "ST1008", camera_id: "CAM_5", visitor_id: "VIS_801", event_type: "ZONE_ENTER", timestamp: "2026-04-10T12:16:10Z", zone_id: "BILLING", dwell_ms: 0, is_staff: false },
        { event_id: "e-009", store_id: "ST1008", camera_id: "CAM_5", visitor_id: "VIS_801", event_type: "BILLING_QUEUE_JOIN", timestamp: "2026-04-10T12:16:15Z", zone_id: "BILLING", dwell_ms: 0, is_staff: false, metadata: { queue_depth: 1 } },
        
        // 6. Visitor 802 moving to Skincare
        { event_id: "e-010", store_id: "ST1008", camera_id: "CAM_1", visitor_id: "VIS_802", event_type: "ZONE_ENTER", timestamp: "2026-04-10T12:16:30Z", zone_id: "SKINCARE", dwell_ms: 0, is_staff: false },
        
        // 7. Visitor 801 completes checkout (correlates to POS order 104341290 which occurred at 12:42, but we simulate in-window conversion here)
        { event_id: "e-011", store_id: "ST1008", camera_id: "CAM_5", visitor_id: "VIS_801", event_type: "ZONE_DWELL", timestamp: "2026-04-10T12:16:45Z", zone_id: "BILLING", dwell_ms: 30000, is_staff: false },
        
        // 8. Visitor 801 Exits
        { event_id: "e-012", store_id: "ST1008", camera_id: "CAM_3", visitor_id: "VIS_801", event_type: "EXIT", timestamp: "2026-04-10T12:17:00Z", zone_id: null, dwell_ms: 0, is_staff: false },
        
        // 9. Unauthorized Entry Anomaly - Visitor 802 sneaks into restricted back office!
        { event_id: "e-013", store_id: "ST1008", camera_id: "CAM_4", visitor_id: "VIS_802", event_type: "ZONE_ENTER", timestamp: "2026-04-10T12:17:15Z", zone_id: "BACK_OFFICE", dwell_ms: 0, is_staff: false },
        
        // 10. Queue buildup anomaly - several new entries and sudden queue buildup!
        { event_id: "e-014", store_id: "ST1008", camera_id: "CAM_3", visitor_id: "VIS_803", event_type: "ENTRY", timestamp: "2026-04-10T12:17:20Z", zone_id: null, dwell_ms: 0, is_staff: false },
        { event_id: "e-015", store_id: "ST1008", camera_id: "CAM_3", visitor_id: "VIS_804", event_type: "ENTRY", timestamp: "2026-04-10T12:17:22Z", zone_id: null, dwell_ms: 0, is_staff: false },
        { event_id: "e-016", store_id: "ST1008", camera_id: "CAM_3", visitor_id: "VIS_805", event_type: "ENTRY", timestamp: "2026-04-10T12:17:25Z", zone_id: null, dwell_ms: 0, is_staff: false },
        { event_id: "e-017", store_id: "ST1008", camera_id: "CAM_3", visitor_id: "VIS_806", event_type: "ENTRY", timestamp: "2026-04-10T12:17:28Z", zone_id: null, dwell_ms: 0, is_staff: false },
        { event_id: "e-018", store_id: "ST1008", camera_id: "CAM_3", visitor_id: "VIS_807", event_type: "ENTRY", timestamp: "2026-04-10T12:17:30Z", zone_id: null, dwell_ms: 0, is_staff: false },
        
        // Everyone rushes straight to checkout!
        { event_id: "e-019", store_id: "ST1008", camera_id: "CAM_5", visitor_id: "VIS_803", event_type: "BILLING_QUEUE_JOIN", timestamp: "2026-04-10T12:17:40Z", zone_id: "BILLING", dwell_ms: 0, is_staff: false, metadata: { queue_depth: 2 } },
        { event_id: "e-020", store_id: "ST1008", camera_id: "CAM_5", visitor_id: "VIS_804", event_type: "BILLING_QUEUE_JOIN", timestamp: "2026-04-10T12:17:42Z", zone_id: "BILLING", dwell_ms: 0, is_staff: false, metadata: { queue_depth: 3 } },
        { event_id: "e-021", store_id: "ST1008", camera_id: "CAM_5", visitor_id: "VIS_805", event_type: "BILLING_QUEUE_JOIN", timestamp: "2026-04-10T12:17:45Z", zone_id: "BILLING", dwell_ms: 0, is_staff: false, metadata: { queue_depth: 4 } },
        { event_id: "e-022", store_id: "ST1008", camera_id: "CAM_5", visitor_id: "VIS_806", event_type: "BILLING_QUEUE_JOIN", timestamp: "2026-04-10T12:17:48Z", zone_id: "BILLING", dwell_ms: 0, is_staff: false, metadata: { queue_depth: 5 } },
        { event_id: "e-023", store_id: "ST1008", camera_id: "CAM_5", visitor_id: "VIS_807", event_type: "BILLING_QUEUE_JOIN", timestamp: "2026-04-10T12:17:50Z", zone_id: "BILLING", dwell_ms: 0, is_staff: false, metadata: { queue_depth: 6 } }
    ];
 
     simulationInterval = setInterval(async () => {
         if (simulationStep >= simEvents.length) {
             stopFootageSimulation();
             return;
         }
 
         // Dynamically override store_id with currently selected store, and make event_id unique per run
         const selectedStore = storeSelector.value;
         const runId = Math.random().toString(36).substring(2, 9);
         const event = { 
             ...simEvents[simulationStep], 
             store_id: selectedStore,
             event_id: `${simEvents[simulationStep].event_id}-${runId}`
         };
         
         // If running on Github Pages, mock the ingest client-side in-memory
         if (window.location.hostname.includes("github.io")) {
             localEvents.push(event);
             addEventToFeed(event);
             eventsIngestedCount++;
             simEventCountText.textContent = `Events Sent: ${eventsIngestedCount}`;
             simTimeText.textContent = `Time: ${formatTimestamp(event.timestamp)}`;
             
             // Progress
             const pct = (simulationStep / simEvents.length) * 100;
             simProgressBar.style.width = `${pct}%`;
             
             loadDashboardData();
             simulationStep++;
             return;
         }
         
         // Post event to /events/ingest
         try {
             const res = await fetch(`${API_BASE}/events/ingest`, {
                 method: "POST",
                 headers: { "Content-Type": "application/json" },
                 body: JSON.stringify([event])
             });
             if (res.ok) {
                 eventsIngestedCount++;
                 simEventCountText.textContent = `Events Sent: ${eventsIngestedCount}`;
                 simTimeText.textContent = `Time: ${formatTimestamp(event.timestamp)}`;
                 
                 // Progress
                 const pct = (simulationStep / simEvents.length) * 100;
                 simProgressBar.style.width = `${pct}%`;
                 
                 // Instantly reload dashboard data to update metrics and visual widgets dynamically
                 loadDashboardData();
             }
         } catch (e) {
             console.error("Simulation ingestion failed:", e);
         }
 
         simulationStep++;
     }, 1500); // Send event every 1.5 seconds
 }
 
 function stopFootageSimulation() {
     if (simulationInterval) {
         clearInterval(simulationInterval);
         simulationInterval = null;
     }
     simPanel.classList.add("hidden");
     simBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run Simulation';
     simBtn.disabled = false;
     speakText("Live store footage simulation stopped.");
 }

// Global state for journeys
let activeJourneys = [];

async function loadAIInsights(storeId) {
    try {
        const res = await fetch(`${API_BASE}/stores/${storeId}/insights`);
        if (res.ok) {
            const data = await res.json();
            renderAIInsights(data.insights);
        }
    } catch (e) {
        console.error("Failed to load AI Insights:", e);
    }
}

function renderAIInsights(insights) {
    const feed = document.getElementById("copilot-feed");
    if (!feed) return;
    
    if (insights.length === 0) {
        feed.innerHTML = `
            <div class="empty-feed-state">
                <i class="fa-regular fa-circle-check"></i>
                <p>AI Copilot reports all systems operational. No actions needed.</p>
            </div>
        `;
        return;
    }
    
    // Announce new recommendations
    insights.forEach(ins => {
        const compositeKey = `${ins.title}-${ins.priority}-${ins.description}`;
        if (!announcedInsights.has(compositeKey)) {
            announcedInsights.add(compositeKey);
            if (voiceEnabled && (ins.priority === "HIGH" || ins.priority === "CRITICAL")) {
                playSynthTone("chime");
                speakText(`AI Copilot Suggestion: ${ins.title}. Recommended action: ${ins.action}`);
            }
        }
    });

    let html = "";
    insights.forEach(ins => {
        let typeClass = ins.type.toLowerCase(); // opportunity, warning, alert, success, info
        let icon = "fa-lightbulb";
        if (typeClass === "warning") icon = "fa-circle-exclamation";
        if (typeClass === "alert") icon = "fa-triangle-exclamation";
        if (typeClass === "success") icon = "fa-circle-check";
        if (typeClass === "info") icon = "fa-circle-info";
        
        html += `
            <div class="insight-card ${typeClass}">
                <div class="insight-header">
                    <span class="insight-title"><i class="fa-solid ${icon}"></i> ${ins.title}</span>
                    <span class="insight-priority ${ins.priority}">${ins.priority}</span>
                </div>
                <p class="insight-desc">${ins.description}</p>
                <div class="insight-action-bar">
                    <i class="fa-solid fa-wand-magic-sparkles"></i>
                    <span><strong>Suggested:</strong> ${ins.action}</span>
                </div>
            </div>
        `;
    });
    feed.innerHTML = html;
}

async function loadVisitorJourneys(storeId) {
    try {
        const res = await fetch(`${API_BASE}/stores/${storeId}/journeys`);
        if (res.ok) {
            activeJourneys = await res.json();
            renderVisitorList(activeJourneys);
        }
    } catch (e) {
        console.error("Failed to load Visitor Journeys:", e);
    }
}

function renderVisitorList(journeys) {
    const container = document.getElementById("visitor-list-container");
    if (!container) return;
    
    if (journeys.length === 0) {
        container.innerHTML = `<div class="empty-feed-state">No shopper paths tracked yet.</div>`;
        document.getElementById("journey-detail-container").innerHTML = `
            <div class="empty-feed-state">
                <i class="fa-solid fa-route"></i>
                <p>Select a visitor from the left to visualize their path sequence.</p>
            </div>
        `;
        return;
    }
    
    let html = "";
    journeys.forEach((j, idx) => {
        const staffBadge = j.is_staff ? " <span class='badge' style='background:rgba(239,68,68,0.15);color:var(--accent-red);padding:2px 4px;font-size:9px;'>Staff</span>" : "";
        const stepsCount = j.path.length;
        html += `
            <div class="visitor-card" onclick="selectVisitorJourney(${idx}, this)">
                <div>
                    <div class="visitor-card-name">${j.visitor_id}${staffBadge}</div>
                    <div class="visitor-card-meta">${stepsCount} steps • ${formatTimestamp(j.start_time)}</div>
                </div>
                <i class="fa-solid fa-chevron-right" style="font-size:10px;color:var(--text-secondary);"></i>
            </div>
        `;
    });
    container.innerHTML = html;
}

window.selectVisitorJourney = function(idx, cardEl) {
    // Toggle active card styling
    document.querySelectorAll(".visitor-card").forEach(c => c.classList.remove("active"));
    cardEl.classList.add("active");
    
    const journey = activeJourneys[idx];
    const detailContainer = document.getElementById("journey-detail-container");
    if (!journey || !detailContainer) return;
    
    let html = `
        <div style="margin-bottom: 16px;">
            <h4 style="font-size:14px;color:#ffffff;margin-bottom:4px;">Shopper Path ID: ${journey.visitor_id}</h4>
            <span class="badge">Multi-Camera Spatial Correlation Timeline</span>
        </div>
        <div class="timeline-path">
    `;
    
    journey.path.forEach(step => {
        html += `
            <div class="timeline-step">
                <div class="timeline-icon-node"><i class="fa-solid ${step.icon}"></i></div>
                <div class="timeline-content-card">
                    <div class="timeline-title">${step.description}</div>
                    <div class="timeline-time"><i class="fa-regular fa-clock"></i> ${formatTimestamp(step.timestamp)} • Camera: ${step.camera_id}</div>
                </div>
            </div>
        `;
    });
    
    html += `</div>`;
    detailContainer.innerHTML = html;
};

async function loadLayoutPlacementOptimization(storeId) {
    try {
        const res = await fetch(`${API_BASE}/stores/${storeId}/placement-optimization`);
        if (res.ok) {
            const data = await res.json();
            renderLayoutOptimizations(data.layout_optimizations);
        }
    } catch (e) {
        console.error("Failed to load Layout Placement Optimization:", e);
    }
}

function renderLayoutOptimizations(optimizations) {
    const list = document.getElementById("optimizer-list");
    if (!list) return;
    
    if (!optimizations || optimizations.length === 0) {
        list.innerHTML = `<div class="empty-feed-state">No layout correlations analyzed yet.</div>`;
        return;
    }
    
    let html = "";
    optimizations.forEach(opt => {
        const statusClass = opt.status_color; // green, orange, red, blue
        const peiPercentage = Math.round(opt.pei * 100);
        
        html += `
            <div class="optimizer-card ${statusClass}">
                <div class="optimizer-header">
                    <span class="optimizer-title"><i class="fa-solid fa-code-merge"></i> ${opt.category_a} & ${opt.category_b}</span>
                    <span class="optimizer-status-badge ${statusClass}">${opt.status}</span>
                </div>
                <div class="optimizer-metrics-row">
                    <div class="optimizer-metric">
                        <span class="optimizer-metric-label">Purchase Affinity (POS)</span>
                        <span class="optimizer-metric-value">${opt.purchase_affinity}%</span>
                    </div>
                    <div class="optimizer-metric">
                        <span class="optimizer-metric-label">Physical Transition (CV)</span>
                        <span class="optimizer-metric-value">${opt.physical_transition}%</span>
                    </div>
                    <div class="optimizer-metric">
                        <span class="optimizer-metric-label">Placement Efficiency (PEI)</span>
                        <span class="optimizer-metric-value">${peiPercentage}%</span>
                        <div class="pei-bar-container">
                            <div class="pei-bar ${statusClass}" style="width: ${peiPercentage}%"></div>
                        </div>
                    </div>
                </div>
                <div class="optimizer-recommendation">
                    <strong>Layout Insight:</strong> ${opt.recommendation}
                </div>
            </div>
        `;
    });
    list.innerHTML = html;
}

// Sidebar Presentation & Slide Deck Controller
let currentSlide = 1;
const totalSlides = 6;
const deckMenuItem = document.getElementById("deck-menu-item");
const liveMonitorBtn = document.querySelector(".sidebar-menu a:first-child");
const mainContentArea = document.querySelector(".main-content");
const prevSlideBtn = document.getElementById("prev-slide");
const nextSlideBtn = document.getElementById("next-slide");

if (deckMenuItem) {
    deckMenuItem.addEventListener("click", (e) => {
        e.preventDefault();
        document.querySelectorAll(".sidebar-menu a").forEach(a => a.classList.remove("active"));
        deckMenuItem.classList.add("active");
        mainContentArea.classList.add("presentation-mode-active");
        
        currentSlide = 1;
        updateSlideUI();
    });
}

document.querySelectorAll(".sidebar-menu a").forEach(link => {
    if (link.id !== "deck-menu-item") {
        link.addEventListener("click", () => {
            document.querySelectorAll(".sidebar-menu a").forEach(a => a.classList.remove("active"));
            link.classList.add("active");
            mainContentArea.classList.remove("presentation-mode-active");
            if (voiceEnabled) {
                speakText(`Loading store monitoring feeds.`);
            }
        });
    }
});

if (prevSlideBtn && nextSlideBtn) {
    prevSlideBtn.addEventListener("click", () => {
        if (currentSlide > 1) {
            currentSlide--;
            updateSlideUI();
        }
    });
    
    nextSlideBtn.addEventListener("click", () => {
        if (currentSlide < totalSlides) {
            currentSlide++;
            updateSlideUI();
        } else {
            // Exit presentation and show live dashboard when clicking Next on last slide
            mainContentArea.classList.remove("presentation-mode-active");
            document.querySelectorAll(".sidebar-menu a").forEach(a => a.classList.remove("active"));
            if (liveMonitorBtn) liveMonitorBtn.classList.add("active");
            speakText("Exited presentation deck. Switched to live monitoring dashboard.");
        }
    });
}

function updateSlideUI() {
    document.querySelectorAll(".slide").forEach(s => {
        s.classList.remove("active");
        if (parseInt(s.dataset.slide) === currentSlide) {
            s.classList.add("active");
        }
    });
    
    const numberText = document.querySelector(".slide-number");
    if (numberText) {
        numberText.textContent = `Slide ${currentSlide} of ${totalSlides}`;
    }
    
    if (voiceEnabled) {
        const activeSlide = document.querySelector(`.slide[data-slide="${currentSlide}"]`);
        if (activeSlide) {
            const subtitle = activeSlide.querySelector(".slide-subtitle").textContent;
            const title = activeSlide.querySelector(".slide-title").textContent;
            const tagline = activeSlide.querySelector(".slide-tagline").textContent;
            
            playSynthTone("chime");
            speakText(`Slide ${currentSlide}. ${title}. ${tagline}`);
        }
    }
}

function initAutodemo() {
    const params = new URLSearchParams(window.location.search);
    if (!params.has("autodemo")) return;
    
    console.log("Autodemo mode active...");
    
    // Smooth scroll helper
    const scrollToElement = (id) => {
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };
    
    // 1. Switch to presentation deck after 2 seconds
    setTimeout(() => {
        if (deckMenuItem) deckMenuItem.click();
        
        // 2. Play first 3 slides automatically (5s per slide, total 15s)
        let slideIndex = 1;
        let slideInterval = setInterval(() => {
            if (slideIndex < 3) {
                if (nextSlideBtn) nextSlideBtn.click();
                slideIndex++;
            } else {
                clearInterval(slideInterval);
                // Exit slides and load Live Dashboard Monitor (Live Monitor is active link)
                if (liveMonitorBtn) liveMonitorBtn.click();
                
                // --- Dashboard Guide Telemetry Timeline ---
                
                // 0s (15s elapsed): Start footage simulation
                setTimeout(() => {
                    if (simBtn) simBtn.click();
                }, 1000);
                
                // 10s (25s elapsed): Scroll to Funnel Analysis
                setTimeout(() => {
                    scrollToElement("funnel-section");
                }, 10000);
                
                // 20s (35s elapsed): Scroll to Product Zone Heatmap
                setTimeout(() => {
                    scrollToElement("heatmap-section");
                }, 20000);
                
                // 30s (45s elapsed): Scroll to Journeys Re-ID and click first visitor card
                setTimeout(() => {
                    scrollToElement("journey-section");
                    let selectVisitorInterval = setInterval(() => {
                        const firstCard = document.querySelector(".visitor-card");
                        if (firstCard) {
                            firstCard.click();
                            clearInterval(selectVisitorInterval);
                        }
                    }, 1000);
                }, 30000);
                
                // 50s (65s elapsed): Scroll to Layout Placement Optimizer
                setTimeout(() => {
                    scrollToElement("optimizer-section");
                }, 50000);
                
                // 65s (80s elapsed): Scroll back to top to display Copilot insights and Alerts desk
                setTimeout(() => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }, 65000);
            }
        }, 5000);
    }, 2000);
}

// ==========================================
// Client-Side Mock Analytics Engine (For GitHub Pages Deployment)
// ==========================================
let localEvents = [];

function loadMockDashboardData(storeId) {
    // 1. Filter events for current store and exclude staff
    const storeEvents = localEvents.filter(e => e.store_id === storeId);
    const nonStaffEvents = storeEvents.filter(e => !e.is_staff);
    
    // 2. Compute Unique Visitors
    const uniqueVisitorsSet = new Set(nonStaffEvents.map(e => e.visitor_id));
    const uniqueVisitors = uniqueVisitorsSet.size;
    
    // 3. Compute Funnel
    const entryCount = uniqueVisitors;
    
    const zoneVisitors = new Set(
        nonStaffEvents
            .filter(e => e.zone_id && !["BILLING", "ENTRY", "EXIT"].includes(e.zone_id))
            .map(e => e.visitor_id)
    );
    const zoneVisitCount = zoneVisitors.size;
    
    const billingVisitors = new Set(
        nonStaffEvents
            .filter(e => e.zone_id === "BILLING" || e.event_type === "BILLING_QUEUE_JOIN")
            .map(e => e.visitor_id)
    );
    const billingQueueCount = billingVisitors.size;
    
    // Converted shoppers: check if they exit store after joining billing queue
    const checkoutExits = nonStaffEvents.filter(e => e.visitor_id === "VIS_801" && e.event_type === "EXIT");
    const purchaseCount = checkoutExits.length;
    
    const funnelStages = [
        { stage_name: "Entry", count: entryCount },
        { stage_name: "Zone Visit", count: zoneVisitCount },
        { stage_name: "Billing Queue", count: billingQueueCount },
        { stage_name: "Purchase", count: purchaseCount }
    ];
    
    // Update Funnel
    updateFunnelUI({ funnel: funnelStages });
    
    // 4. Conversion Rate & Abandonment
    const conversionRate = uniqueVisitors > 0 ? (purchaseCount / uniqueVisitors) * 100 : 0.0;
    const abandonmentRate = billingQueueCount > 0 ? ((billingQueueCount - purchaseCount) / billingQueueCount) * 100 : 0.0;
    
    // 5. Queue Depth
    const latestQueueJoin = nonStaffEvents
        .filter(e => e.event_type === "BILLING_QUEUE_JOIN" && e.metadata && e.metadata.queue_depth !== undefined)
        .pop();
    const queueDepth = latestQueueJoin ? latestQueueJoin.metadata.queue_depth : 0;
    
    // Update KPIs
    updateMetricsUI({
        unique_visitors: uniqueVisitors,
        conversion_rate: conversionRate,
        queue_depth: queueDepth,
        abandonment_rate: abandonmentRate
    });
    
    // 6. Heatmap layout
    const zones = ["SKINCARE", "MAKEUP", "HAIRCARE", "FRAGRANCE"];
    const zoneData = {};
    zones.forEach(z => { zoneData[z] = { visits: new Set(), totalDwell: 0, countDwell: 0 }; });
    
    nonStaffEvents.forEach(e => {
        if (zones.includes(e.zone_id)) {
            zoneData[e.zone_id].visits.add(e.visitor_id);
            if (e.event_type === "ZONE_DWELL" && e.dwell_ms > 0) {
                zoneData[e.zone_id].totalDwell += e.dwell_ms;
                zoneData[e.zone_id].countDwell++;
            }
        }
    });
    
    const heatmapList = [];
    const visitsCountArray = zones.map(z => zoneData[z].visits.size);
    const maxVisits = Math.max(...visitsCountArray) || 1;
    
    zones.forEach(z => {
        const visits = zoneData[z].visits.size;
        const avgDwell = zoneData[z].countDwell > 0 ? (zoneData[z].totalDwell / zoneData[z].countDwell) : 0;
        const score = (visits / maxVisits) * 100;
        heatmapList.push({
            zone_id: z,
            visit_frequency: visits,
            avg_dwell_sec: avgDwell / 1000,
            normalized_score: score
        });
    });
    
    updateHeatmapUI({
        data_confidence: uniqueVisitors >= 3,
        heatmap: heatmapList
    });
    
    // 7. Dynamic Alerts Anomalies
    const anomaliesList = [];
    const officeBreach = nonStaffEvents.find(e => e.zone_id === "BACK_OFFICE");
    if (officeBreach) {
        anomaliesList.push({
            anomaly_id: "anom_001",
            anomaly_type: "UNAUTHORIZED_ENTRY",
            severity: "CRITICAL",
            timestamp: officeBreach.timestamp,
            zone_id: "BACK_OFFICE",
            description: `Visitor ${officeBreach.visitor_id} detected entering restricted Back Office area.`,
            suggested_action: "Dispatch floor staff to secure restricted warehouse entrance."
        });
    }
    
    if (queueDepth >= 5) {
        anomaliesList.push({
            anomaly_id: "anom_002",
            anomaly_type: "QUEUE_SPIKE",
            severity: "WARN",
            timestamp: new Date().toISOString(),
            zone_id: "BILLING",
            description: `Checkout queue spike detected. ${queueDepth} shoppers waiting.`,
            suggested_action: "Open auxiliary register 2 immediately to reduce queue bottleneck."
        });
    }
    
    updateAnomaliesUI(anomaliesList);
    
    // 8. Visitor Journeys
    const journeys = [];
    uniqueVisitorsSet.forEach(vId => {
        const vEvents = nonStaffEvents.filter(e => e.visitor_id === vId);
        const path = [];
        vEvents.forEach(e => {
            let icon = "fa-circle-nodes";
            let desc = "";
            if (e.event_type === "ENTRY") { icon = "fa-right-to-bracket"; desc = "Entered Store"; }
            else if (e.event_type === "EXIT") { icon = "fa-right-from-bracket"; desc = "Exited Store"; }
            else if (e.event_type === "ZONE_ENTER") { icon = "fa-shoe-prints"; desc = `Entered Aisle: ${e.zone_id}`; }
            else if (e.event_type === "ZONE_DWELL") { icon = "fa-clock"; desc = `Browsing products in ${e.zone_id}`; }
            else if (e.event_type === "BILLING_QUEUE_JOIN") { icon = "fa-people-group"; desc = "Joined checkout queue"; }
            
            path.push({
                icon: icon,
                description: desc,
                timestamp: e.timestamp,
                camera_id: e.camera_id
            });
        });
        
        journeys.push({
            visitor_id: vId,
            is_staff: false,
            start_time: vEvents[0] ? vEvents[0].timestamp : "",
            path: path
        });
    });
    
    activeJourneys = journeys;
    renderVisitorList(journeys);
    
    // 9. Static Layout Optimization
    const optimizations = [
        {
            category_a: "skincare",
            category_b: "makeup",
            status: "Optimal placement",
            status_color: "green",
            purchase_affinity: 34,
            physical_transition: 42,
            pei: 0.81,
            recommendation: "Skincare and makeup show high buy-together affinity and high physical traffic flow. Keep adjacent layout."
        },
        {
            category_a: "haircare",
            category_b: "fragrance",
            status: "Layout Bottleneck",
            status_color: "orange",
            purchase_affinity: 28,
            physical_transition: 8,
            pei: 0.28,
            recommendation: "High basket affinity but low physical transitions. Recommend placing impulse item display at haircare-fragrance aisle junction."
        }
    ];
    renderLayoutOptimizations(optimizations);
    
    // 10. AI Insights Copilot
    const insights = [];
    if (queueDepth >= 5) {
        insights.push({
            title: "Open Checkout Counter 2",
            priority: "CRITICAL",
            description: `Checkout queue depth is currently ${queueDepth} shoppers. Wait time exceeds 6 minutes.`,
            action: "Alert manager to allocate additional cashier staffing immediately.",
            type: "alert"
        });
    }
    if (uniqueVisitors > 0) {
        insights.push({
            title: "Skincare Browse Hotspot",
            priority: "HIGH",
            description: "Skincare aisle represents 45% of total store dwell time today.",
            action: "Feature premium promo display at skincare counter.",
            type: "opportunity"
        });
    }
    renderAIInsights(insights);
}
