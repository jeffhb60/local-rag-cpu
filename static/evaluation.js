let activeEvaluationPollTimer = null;

async function pollEvaluationJob(jobId) {
    const status = $("eval-status");
    const output = $("eval-output");

    if (activeEvaluationPollTimer) {
        clearInterval(activeEvaluationPollTimer);
    }

    activeEvaluationPollTimer = setInterval(async () => {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            const data = await parseJsonResponse(response);

            if (!response.ok) {
                status.textContent = data.detail || "Could not read evaluation job status.";
                clearInterval(activeEvaluationPollTimer);
                activeEvaluationPollTimer = null;
                return;
            }

            const percent = jobPercent(data);

            setProgressBar("eval-progress-bar", percent);

            status.textContent = `[${data.status}] ${percent}% — ${data.message}`;

            if (output) {
                output.textContent = JSON.stringify(data, null, 2);
            }

            if (isFinishedJob(data)) {
                clearInterval(activeEvaluationPollTimer);
                activeEvaluationPollTimer = null;

                if (data.status === "succeeded") {
                    const result = data.result || {};

                    setProgressBar("eval-progress-bar", 100);

                    status.textContent =
                        `Complete: ${result.passed ?? 0}/${result.total ?? 0} passed, ` +
                        `${result.failed ?? 0} failed.`;

                    if (output) {
                        output.textContent = JSON.stringify(result, null, 2);
                    }
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
            clearInterval(activeEvaluationPollTimer);
            activeEvaluationPollTimer = null;
        }
    }, 1000);
}

async function runEvaluation(event) {
    event.preventDefault();

    const fileInput = $("eval-file");
    const status = $("eval-status");
    const output = $("eval-output");
    const button = event.submitter;

    if (!fileInput.files.length) {
        status.textContent = "Choose a JSONL file first.";
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("top_k", Number($("eval-top-k").value));
    formData.append("retrieval_only", $("retrieval-only").checked ? "true" : "false");

    status.textContent = "Starting evaluation job...";
    output.textContent = "";
    setProgressBar("eval-progress-bar", 0);
    setButtonLoading(button, true, "Starting...");

    try {
        const response = await fetch("/api/evaluate/run/start", {
            method: "POST",
            body: formData
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            status.textContent = data.detail || "Evaluation failed.";
            output.textContent = JSON.stringify(data, null, 2);
            return;
        }

        status.textContent = `Job started: ${data.job_id}`;
        output.textContent = JSON.stringify(data, null, 2);

        pollEvaluationJob(data.job_id);
    } catch (error) {
        status.textContent = `Request failed: ${error.message}`;
        output.textContent = String(error.stack || error.message);
    } finally {
        setButtonLoading(button, false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    $("eval-form").addEventListener("submit", runEvaluation);
});