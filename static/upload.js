let activeUploadPollTimer = null;

async function pollUploadJob(jobId) {
    const status = $("upload-status");
    const output = $("upload-output");

    if (activeUploadPollTimer) {
        clearInterval(activeUploadPollTimer);
    }

    activeUploadPollTimer = setInterval(async () => {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            const data = await parseJsonResponse(response);

            if (!response.ok) {
                status.textContent = data.detail || "Could not read upload job status.";
                clearInterval(activeUploadPollTimer);
                activeUploadPollTimer = null;
                return;
            }

            const percent = jobPercent(data);

            setProgressBar("upload-progress-bar", percent);

            status.textContent = `[${data.status}] ${percent}% — ${data.message}`;

            if (output) {
                output.textContent = JSON.stringify(data, null, 2);
            }

            if (isFinishedJob(data)) {
                clearInterval(activeUploadPollTimer);
                activeUploadPollTimer = null;

                if (data.status === "succeeded") {
                    const result = data.result || {};

                    setProgressBar("upload-progress-bar", 100);

                    status.textContent =
                        `Complete: ${result.files_indexed ?? 0} indexed, ` +
                        `${result.files_skipped ?? 0} skipped, ` +
                        `${result.chunks_added ?? 0} chunks.`;
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
            clearInterval(activeUploadPollTimer);
            activeUploadPollTimer = null;
        }
    }, 1000);
}

async function uploadDocuments(event) {
    event.preventDefault();

    const fileInput = $("document-files");
    const status = $("upload-status");
    const output = $("upload-output");
    const button = event.submitter;

    if (!fileInput.files.length) {
        status.textContent = "Choose at least one file.";
        return;
    }

    const formData = new FormData();

    for (const file of fileInput.files) {
        formData.append("files", file);
    }

    formData.append("force_rebuild", $("upload-force").checked ? "true" : "false");

    status.textContent = "Uploading files and starting indexing job...";
    output.textContent = "";
    setProgressBar("upload-progress-bar", 0);
    setButtonLoading(button, true, "Starting...");

    try {
        const response = await fetch("/api/documents/upload/start", {
            method: "POST",
            body: formData
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            status.textContent = data.detail || "Upload failed.";
            output.textContent = JSON.stringify(data, null, 2);
            return;
        }

        status.textContent = `Job started: ${data.job_id}`;
        output.textContent = JSON.stringify(data, null, 2);

        pollUploadJob(data.job_id);
    } catch (error) {
        status.textContent = `Request failed: ${error.message}`;
        output.textContent = String(error.stack || error.message);
    } finally {
        setButtonLoading(button, false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    $("upload-form").addEventListener("submit", uploadDocuments);
});