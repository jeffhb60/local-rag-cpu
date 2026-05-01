let activeReindexPollTimer = null;

async function loadDocuments() {
    const list = $("document-list");
    const status = $("reindex-status");
    const output = $("reindex-output");

    list.innerHTML = "Loading documents...";
    status.textContent = "Calling /api/documents...";
    setProgressBar("reindex-progress-bar", 0);

    if (output) {
        output.textContent = "";
    }

    try {
        const response = await fetch("/api/documents");
        const data = await parseJsonResponse(response);

        if (!response.ok) {
            list.innerHTML = "";
            status.textContent = data.detail || "Could not load documents.";

            if (output) {
                output.textContent = JSON.stringify(data, null, 2);
            }

            return;
        }

        const files = data.available_files || [];

        if (!files.length) {
            list.innerHTML = "<p>No documents found in the docs folder.</p>";
            status.textContent = "No supported files found in DOCS_DIR.";
            return;
        }

        list.innerHTML = files.map(file => `
            <label class="document-row">
                <input type="checkbox" name="selected_files" value="${escapeHtml(file.relative_path)}">
                <span>
                    <strong>${escapeHtml(file.file_name)}</strong>
                    <small>${escapeHtml(file.relative_path)} · ${file.size_bytes} bytes</small>
                </span>
            </label>
        `).join("");

        status.textContent = `${files.length} document(s) found.`;

        if (output) {
            output.textContent = JSON.stringify(
                {
                    available_files: data.available_files,
                    indexed_files: data.indexed_files,
                    chunk_count: data.chunk_count
                },
                null,
                2
            );
        }
    } catch (error) {
        list.innerHTML = "";
        status.textContent = `Request failed: ${error.message}`;

        if (output) {
            output.textContent = String(error.stack || error.message);
        }
    }
}

async function pollReindexJob(jobId) {
    const status = $("reindex-status");
    const output = $("reindex-output");

    if (activeReindexPollTimer) {
        clearInterval(activeReindexPollTimer);
    }

    activeReindexPollTimer = setInterval(async () => {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            const data = await parseJsonResponse(response);

            if (!response.ok) {
                status.textContent = data.detail || "Could not read job status.";
                clearInterval(activeReindexPollTimer);
                activeReindexPollTimer = null;
                return;
            }

            const percent = jobPercent(data);

            setProgressBar("reindex-progress-bar", percent);

            status.textContent = `[${data.status}] ${percent}% — ${data.message}`;

            if (output) {
                output.textContent = JSON.stringify(data, null, 2);
            }

            if (isFinishedJob(data)) {
                clearInterval(activeReindexPollTimer);
                activeReindexPollTimer = null;

                if (data.status === "succeeded") {
                    const result = data.result || {};

                    setProgressBar("reindex-progress-bar", 100);

                    status.textContent =
                        `Complete: ${result.files_indexed ?? 0} indexed, ` +
                        `${result.files_skipped ?? 0} skipped, ` +
                        `${result.chunks_added ?? 0} chunks.`;

                    loadDocuments();
                }

                if (data.status === "failed") {
                    status.textContent = `Failed: ${data.error}`;
                }

                if (data.status === "cancelled") {
                    status.textContent = "Cancelled.";
                }
            }
        } catch (error) {
            status.textContent = `Polling failed: ${error.message}`;
            clearInterval(activeReindexPollTimer);
            activeReindexPollTimer = null;
        }
    }, 1000);
}

async function reindexSelected(event) {
    event.preventDefault();

    const selected = Array.from(
        document.querySelectorAll("input[name='selected_files']:checked")
    );

    const status = $("reindex-status");
    const output = $("reindex-output");
    const button = event.submitter;

    if (!selected.length) {
        status.textContent = "Select at least one document.";
        return;
    }

    const formData = new FormData();

    selected.forEach(input => {
        formData.append("selected_files", input.value);
    });

    formData.append("force_rebuild", $("reindex-force").checked ? "true" : "false");

    status.textContent = "Starting selected reindex job...";
    setProgressBar("reindex-progress-bar", 0);

    if (output) {
        output.textContent = "";
    }

    setButtonLoading(button, true, "Starting...");

    try {
        const response = await fetch("/api/documents/reindex-selected/start", {
            method: "POST",
            body: formData
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            status.textContent = data.detail || "Could not start reindex job.";

            if (output) {
                output.textContent = JSON.stringify(data, null, 2);
            }

            return;
        }

        status.textContent = `Job started: ${data.job_id}`;

        if (output) {
            output.textContent = JSON.stringify(data, null, 2);
        }

        pollReindexJob(data.job_id);
    } catch (error) {
        status.textContent = `Request failed: ${error.message}`;

        if (output) {
            output.textContent = String(error.stack || error.message);
        }
    } finally {
        setButtonLoading(button, false);
    }
}

async function reindexAll() {
    const status = $("reindex-status");
    const output = $("reindex-output");
    const button = $("reindex-all-button");

    const formData = new FormData();
    formData.append("force_rebuild", $("reindex-force").checked ? "true" : "false");

    status.textContent = "Starting full reindex job...";
    setProgressBar("reindex-progress-bar", 0);

    if (output) {
        output.textContent = "";
    }

    setButtonLoading(button, true, "Starting...");

    try {
        const response = await fetch("/api/documents/reindex/start", {
            method: "POST",
            body: formData
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            status.textContent = data.detail || "Could not start full reindex job.";

            if (output) {
                output.textContent = JSON.stringify(data, null, 2);
            }

            return;
        }

        status.textContent = `Job started: ${data.job_id}`;

        if (output) {
            output.textContent = JSON.stringify(data, null, 2);
        }

        pollReindexJob(data.job_id);
    } catch (error) {
        status.textContent = `Request failed: ${error.message}`;

        if (output) {
            output.textContent = String(error.stack || error.message);
        }
    } finally {
        setButtonLoading(button, false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    $("refresh-docs-button").addEventListener("click", loadDocuments);
    $("reindex-selected-form").addEventListener("submit", reindexSelected);
    $("reindex-all-button").addEventListener("click", reindexAll);

    loadDocuments();
});