// script.js
// Talks to our Flask API and renders everything on both the landing
// page (a small live snapshot) and the dashboard page (full detail).

const API_BASE = "http://localhost:5000/api";

// Matches the Stitch design system's own chart colors from DESIGN.md
const CHART_COLORS = {
    primary: "#ffd79b",   // amber
    error: "#ffb4ab",     // red
    tertiary: "#85edff",  // cyan
    outline: "#514532",   // muted
    grid: "rgba(255,255,255,0.05)",
    text: "#9e8e78",
};

// USGS's own alert-level colors, used for the donut chart and log entries
const ALERT_COLORS = {
    green: "#a3a3a3",
    yellow: "#ffb300",
    orange: "#ff8a3d",
    red: "#ffb4ab",
    none: "#514532",
};

let charts = { timeline: null, alertDonut: null, depthScatter: null, regionBar: null, sparkline: null, landingMagnitude: null };
let currentEarthquakes = [];
let isLoadingDashboard = false;

Chart.defaults.color = CHART_COLORS.text;
Chart.defaults.font.family = "'JetBrains Mono', monospace";

// Destroys any chart already attached to this canvas — using Chart.js's
// own internal registry (Chart.getChart), not just our local `charts`
// object. This is what actually prevents "Canvas is already in use"
// errors, even if loadData() somehow runs twice back to back.
function destroyExistingChart(canvasId) {
    const existing = Chart.getChart(canvasId);
    if (existing) existing.destroy();
}

// ----------------------------------------
// PAGE ROUTER — run the right init for whichever page loaded
// ----------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("log-list")) {
        loadData(); // dashboard.html
    }
    if (document.getElementById("landing-total")) {
        loadLandingSnapshot(); // index.html
    }
});

// ----------------------------------------
// DASHBOARD PAGE
// ----------------------------------------
async function loadData() {
    if (isLoadingDashboard) return;
    isLoadingDashboard = true;
    removeErrorBanner();

    try {
        const [statsRes, quakesRes] = await Promise.all([
            fetch(`${API_BASE}/stats`),
            fetch(`${API_BASE}/earthquakes`),
        ]);
        if (!statsRes.ok || !quakesRes.ok) throw new Error("API request failed");

        const stats = await statsRes.json();
        const quakesData = await quakesRes.json();

        renderHero(stats);
        renderCharts(stats);

        currentEarthquakes = quakesData.data || [];
        renderLog(currentEarthquakes);

    } catch (error) {
        console.error("Error loading data:", error);
        showConnectionError();
    } finally {
        isLoadingDashboard = false;
    }
}

function renderHero(stats) {
    document.getElementById("strongest").textContent = stats.strongest ? stats.strongest.toFixed(1) : "--";
    document.getElementById("hero-place").textContent = stats.strongest_place || "No data yet";
    document.getElementById("total-quakes").textContent = stats.total ?? "--";
    document.getElementById("avg-magnitude").textContent = stats.avg_magnitude ? stats.avg_magnitude.toFixed(2) : "--";
    document.getElementById("tsunami-count").textContent = stats.tsunami_count ?? "--";
    document.getElementById("last-updated-time").textContent = new Date().toLocaleTimeString();
}

function renderCharts(stats) {
    renderTimelineChart(stats.by_day || []);
    renderAlertDonut(stats.by_alert || []);
    renderDepthScatter(stats.depth_vs_magnitude || []);
    renderRegionBar(stats.top_events || []);
}

function renderTimelineChart(data) {
    const ctx = document.getElementById("timelineChart");
    destroyExistingChart("timelineChart");
    charts.timeline = new Chart(ctx, {
        type: "line",
        data: {
            labels: data.map((d) => d.day),
            datasets: [{
                label: "Event Frequency",
                data: data.map((d) => d.count),
                borderColor: CHART_COLORS.primary,
                backgroundColor: "rgba(255, 215, 155, 0.1)",
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: "#131313",
                pointBorderColor: CHART_COLORS.primary,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: CHART_COLORS.grid, drawBorder: false }, ticks: { maxRotation: 45 } },
                y: { grid: { color: CHART_COLORS.grid, drawBorder: false }, beginAtZero: true },
            },
        },
    });
}

function renderAlertDonut(data) {
    const ctx = document.getElementById("alertDonutChart");
    destroyExistingChart("alertDonutChart");
    charts.alertDonut = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: data.map((d) => d.alert),
            datasets: [{
                data: data.map((d) => d.count),
                backgroundColor: data.map((d) => ALERT_COLORS[d.alert] || ALERT_COLORS.none),
                borderWidth: 0,
                hoverOffset: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "70%",
            plugins: { legend: { position: "bottom", labels: { color: "#e5e2e1", font: { size: 11 } } } },
        },
    });
}

function renderDepthScatter(data) {
    const ctx = document.getElementById("depthScatterChart");
    destroyExistingChart("depthScatterChart");
    charts.depthScatter = new Chart(ctx, {
        type: "scatter",
        data: {
            datasets: [{
                label: "Events",
                data: data.map((d) => ({ x: d.magnitude, y: d.depth })),
                backgroundColor: CHART_COLORS.tertiary,
                borderColor: "transparent",
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { title: { display: true, text: "Magnitude", color: CHART_COLORS.text }, grid: { color: CHART_COLORS.grid } },
                y: { title: { display: true, text: "Depth (km)", color: CHART_COLORS.text }, grid: { color: CHART_COLORS.grid }, reverse: true },
            },
        },
    });
}

function renderRegionBar(topEvents) {
    const ctx = document.getElementById("regionBarChart");
    destroyExistingChart("regionBarChart");
    charts.regionBar = new Chart(ctx, {
        type: "bar",
        data: {
            labels: topEvents.map((e) => truncate(e.place, 22)),
            datasets: [{
                label: "Magnitude",
                data: topEvents.map((e) => e.magnitude),
                backgroundColor: topEvents.map((e) => (e.magnitude >= 6 ? CHART_COLORS.error : e.magnitude >= 4 ? CHART_COLORS.primary : CHART_COLORS.outline)),
                borderRadius: 2,
            }],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: CHART_COLORS.grid }, beginAtZero: true },
                y: { grid: { display: false } },
            },
        },
    });
}

// ----------------------------------------
// INCIDENT LOG (matches the Stitch "pulse-*" card styles)
// ----------------------------------------
function renderLog(earthquakes) {
    const container = document.getElementById("log-list");

    if (earthquakes.length === 0) {
        container.innerHTML = '<p class="font-data-md text-data-md text-on-surface-variant p-3">No events match your search.</p>';
        return;
    }

    container.innerHTML = earthquakes.map((quake) => {
        const pulseClass = quake.magnitude >= 6 ? "pulse-alert" : quake.magnitude >= 4 ? "pulse-warning" : "pulse-normal";
        const magColor = quake.magnitude >= 6 ? "text-error border-error/20" : quake.magnitude >= 4 ? "text-primary border-primary/20" : "text-outline border-outline/20";
        const time = quake.event_time ? new Date(quake.event_time).toLocaleString() : "Unknown";
        const depth = quake.depth_km != null ? Number(quake.depth_km).toFixed(0) : "--";

        return `
            <div class="bg-surface-container-high rounded p-3 flex flex-col md:flex-row justify-between items-start md:items-center gap-3 ${pulseClass} hover:bg-surface-bright transition-colors cursor-pointer">
                <div class="flex items-center gap-4 min-w-[200px]">
                    <span class="font-data-md text-data-md bg-surface-container-lowest px-2 py-1 rounded ${magColor} border font-bold">M ${quake.magnitude != null ? Number(quake.magnitude).toFixed(1) : "--"}</span>
                    <span class="font-data-md text-data-md text-on-surface-variant">${quake.earthquake_id || ""}</span>
                </div>
                <div class="flex-grow font-body-md text-body-md font-medium">${quake.place || "Unknown location"}</div>
                <div class="flex items-center gap-6 min-w-[250px] justify-between">
                    <span class="font-data-md text-data-md text-outline">Depth: ${depth}km</span>
                    <span class="font-data-md text-data-md text-on-surface opacity-80">${time}</span>
                </div>
            </div>
        `;
    }).join("");
}

async function filterEarthquakes() {
    const search = document.getElementById("filter-search").value;
    const params = new URLSearchParams();
    if (search) params.set("search", search);

    try {
        const response = await fetch(`${API_BASE}/earthquakes?${params.toString()}`);
        const data = await response.json();
        currentEarthquakes = data.data || [];
        renderLog(currentEarthquakes);
    } catch (error) {
        console.error("Error filtering earthquakes:", error);
    }
}

// ----------------------------------------
// CSV EXPORT
// ----------------------------------------
function downloadCSV() {
    if (currentEarthquakes.length === 0) {
        alert("No data to export.");
        return;
    }

    const headers = ["ID", "Location", "Magnitude", "Depth (km)", "Alert", "Tsunami", "Time"];
    const rows = currentEarthquakes.map((q) => [
        q.earthquake_id || "",
        `"${(q.place || "").replace(/"/g, '""')}"`,
        q.magnitude ?? "",
        q.depth_km ?? "",
        q.alert || "none",
        q.tsunami ? "Yes" : "No",
        q.event_time || "",
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `earthquakes_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
}

// ----------------------------------------
// LANDING PAGE SNAPSHOT
// ----------------------------------------
async function loadLandingSnapshot() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        if (!response.ok) throw new Error("API request failed");
        const stats = await response.json();

        document.getElementById("landing-total").textContent = stats.total ?? "--";
        document.getElementById("landing-strongest").textContent = stats.strongest ? stats.strongest.toFixed(1) : "--";
        document.getElementById("landing-tsunami").textContent = stats.tsunami_count ?? "--";

        const footerTime = document.getElementById("footer-updated");
        if (footerTime) footerTime.textContent = new Date().toLocaleString();

        renderLandingSparkline(stats.by_day || []);
        renderLandingMagnitudeChart(stats.by_magnitude || []);
    } catch (error) {
        console.error("Error loading landing snapshot:", error);
        // Landing page fails quietly — the full error banner only shows on
        // the dashboard page, since the landing page is just a teaser.
    }
}

function renderLandingSparkline(data) {
    const canvas = document.getElementById("landingSparkline");
    if (!canvas) return;
    destroyExistingChart("landingSparkline");

    charts.sparkline = new Chart(canvas, {
        type: "line",
        data: {
            labels: data.map((d) => d.day),
            datasets: [{
                data: data.map((d) => d.count),
                borderColor: CHART_COLORS.primary,
                backgroundColor: "rgba(255, 215, 155, 0.08)",
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { display: false, beginAtZero: true },
            },
        },
    });
}

function renderLandingMagnitudeChart(data) {
    const canvas = document.getElementById("landingMagnitudeChart");
    if (!canvas) return;
    destroyExistingChart("landingMagnitudeChart");

    charts.landingMagnitude = new Chart(canvas, {
        type: "bar",
        data: {
            labels: data.map((d) => d.range),
            datasets: [{
                label: "Events",
                data: data.map((d) => d.count),
                backgroundColor: CHART_COLORS.primary,
                hoverBackgroundColor: CHART_COLORS.error,
                borderRadius: 4,
                barThickness: "flex",
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#1a1a1a",
                    titleColor: "#ffd79b",
                    bodyColor: "#e5e2e1",
                    padding: 10,
                    borderColor: "rgba(255,215,155,0.3)",
                    borderWidth: 1,
                },
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: "#9e8e78" } },
                y: { grid: { color: CHART_COLORS.grid }, beginAtZero: true, ticks: { color: "#9e8e78" } },
            },
        },
    });
}

// ----------------------------------------
// HELPERS
// ----------------------------------------
function truncate(str, maxLength) {
    if (!str) return "";
    return str.length > maxLength ? str.slice(0, maxLength) + "…" : str;
}

function showConnectionError() {
    if (document.getElementById("connection-error")) return;
    const main = document.querySelector("main");
    if (!main) return;

    const banner = document.createElement("div");
    banner.id = "connection-error";
    banner.className = "bg-error-container text-on-error-container rounded-lg p-4 flex items-center gap-3 font-body-md text-body-md";
    banner.innerHTML = `
        <span class="material-symbols-outlined">error</span>
        <span>Could not connect to the API. Make sure the Flask server is running at <code class="font-data-md">http://localhost:5000</code>.</span>
        <button class="ml-auto font-bold" onclick="this.parentElement.remove()">&times;</button>
    `;
    main.insertBefore(banner, main.firstChild);
}

function removeErrorBanner() {
    const existing = document.getElementById("connection-error");
    if (existing) existing.remove();
}
