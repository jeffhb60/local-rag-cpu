const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function parseJsonResponse(response) {
    const text = await response.text();

    try {
        return JSON.parse(text);
    } catch {
        return {
            detail: text || "Server returned a non-JSON response."
        };
    }
}

function setButtonLoading(button, isLoading, loadingText = "Working...") {
    if (!button) return;

    if (isLoading) {
        button.dataset.originalText = button.textContent;
        button.textContent = loadingText;
        button.disabled = true;
    } else {
        button.textContent = button.dataset.originalText || button.textContent;
        button.disabled = false;
    }
}

function setProgressBar(id, percent) {
    const progressBar = $(id);

    if (!progressBar) return;

    const safePercent = Math.max(0, Math.min(Number(percent || 0), 100));
    progressBar.style.width = `${safePercent}%`;
}

function jobPercent(job) {
    const total = Number(job.total || 0);
    const current = Number(job.current || 0);

    if (total <= 0) return 0;

    return Math.round((current / total) * 100);
}

function isFinishedJob(job) {
    return ["succeeded", "failed", "cancelled"].includes(job.status);
}