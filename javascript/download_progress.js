(function () {
    "use strict";

    const STATUS_URL = "/sd-webui-model-downloader/api/download_status";
    const ACTIVE_POLL_MS = 800;
    const IDLE_POLL_MS = 3000;

    let pollTimer = null;
    let inFlight = false;
    let lastActive = false;

    function formatBytes(bytes) {
        if (!bytes) return "0 B";
        const units = ["B", "KB", "MB", "GB", "TB"];
        let value = bytes;
        let unit = 0;
        while (value >= 1024 && unit < units.length - 1) {
            value /= 1024;
            unit++;
        }
        return (value >= 100 || unit === 0 ? Math.round(value) : value.toFixed(1)) + " " + units[unit];
    }

    function formatEta(seconds) {
        if (!seconds || seconds < 0) return "";
        if (seconds < 60) return Math.round(seconds) + "s";
        const minutes = Math.floor(seconds / 60);
        const remainder = Math.round(seconds % 60);
        if (minutes < 60) {
            return minutes + "m " + String(remainder).padStart(2, "0") + "s";
        }
        return Math.floor(minutes / 60) + "h " + String(minutes % 60).padStart(2, "0") + "m";
    }

    function ensureStructure(container) {
        let title = container.querySelector(".ota-progress-title");
        let detail = container.querySelector(".ota-progress-detail");
        let track = container.querySelector(".ota-progress-track");
        let fill = container.querySelector(".ota-progress-fill");
        if (!title || !detail || !track || !fill) {
            container.innerHTML =
                '<div class="ota-progress-title"></div>' +
                '<div class="ota-progress-detail"></div>' +
                '<div class="ota-progress-track"><div class="ota-progress-fill"></div></div>';
            title = container.querySelector(".ota-progress-title");
            detail = container.querySelector(".ota-progress-detail");
            track = container.querySelector(".ota-progress-track");
            fill = container.querySelector(".ota-progress-fill");
        }
        return { title: title, detail: detail, track: track, fill: fill };
    }

    function render(status) {
        const container = document.getElementById("ota_download_status");
        if (!container) return;

        if (!status || (status.phase === "idle" && !status.active)) {
            container.style.display = "none";
            return;
        }

        const el = ensureStructure(container);
        container.style.display = "block";
        container.classList.add("ota-progress");
        ["starting", "downloading", "saving", "done", "error", "cancelled"].forEach(function (phase) {
            container.classList.remove("ota-progress-" + phase);
        });
        container.classList.add("ota-progress-" + status.phase);
        el.track.style.display = "block";

        let percent = Number(status.percent) || 0;
        const total = Number(status.total) || 0;
        const downloaded = Number(status.downloaded) || 0;

        if (status.phase === "error") {
            el.title.textContent = "Download failed";
            el.detail.textContent = "See the message below.";
            percent = 100;
        } else if (status.phase === "cancelled") {
            el.title.textContent = "Download cancelled";
            el.detail.textContent = status.filename || "";
            percent = 100;
        } else if (status.phase === "done") {
            el.title.textContent = status.message || "Download complete";
            el.detail.textContent = "";
            percent = 100;
        } else if (status.phase === "starting") {
            el.title.textContent = "Starting download...";
            el.detail.textContent = status.filename || "";
            percent = 0;
        } else if (status.phase === "saving") {
            el.title.textContent = "Saving preview and metadata...";
            el.detail.textContent = status.filename || "";
            percent = 100;
        } else {
            el.title.textContent = status.filename ? "Downloading: " + status.filename : "Downloading...";
            const parts = [];
            if (total > 0) {
                parts.push(formatBytes(downloaded) + " / " + formatBytes(total) + " (" + percent.toFixed(1) + "%)");
            } else {
                parts.push(formatBytes(downloaded) + " downloaded");
            }
            if (status.speed > 0) parts.push(formatBytes(status.speed) + "/s");
            if (status.eta > 0) parts.push("ETA " + formatEta(status.eta));
            el.detail.textContent = parts.join(" • ");
        }

        if (total <= 0 && status.phase === "downloading") {
            el.fill.style.width = "100%";
            el.fill.classList.add("ota-progress-indeterminate");
        } else {
            el.fill.classList.remove("ota-progress-indeterminate");
            el.fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
        }
    }

    function schedule() {
        clearTimeout(pollTimer);
        pollTimer = setTimeout(poll, lastActive ? ACTIVE_POLL_MS : IDLE_POLL_MS);
    }

    function poll() {
        if (inFlight) return;
        clearTimeout(pollTimer);

        if (document.hidden) {
            schedule();
            return;
        }

        inFlight = true;
        fetch(STATUS_URL, { cache: "no-store" })
            .then(function (response) { return response.ok ? response.json() : null; })
            .then(function (status) {
                if (!status) return;
                lastActive = !!status.active;
                render(status);
            })
            .catch(function () {})
            .finally(function () {
                inFlight = false;
                schedule();
            });
    }

    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) poll();
    });
    window.addEventListener("pageshow", poll);

    poll();
})();
