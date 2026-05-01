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

    status.textContent = "Running evaluation...";
    output.textContent = "";
    setButtonLoading(button, true, "Evaluating...");

    try {
        const response = await fetch("/api/evaluate/run", {
            method: "POST",
            body: formData
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            status.textContent = data.detail || "Evaluation failed.";
            output.textContent = JSON.stringify(data, null, 2);
            return;
        }

        status.textContent = `Complete: ${data.passed}/${data.total} passed.`;
        output.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
        status.textContent = `Request failed: ${error.message}`;
    } finally {
        setButtonLoading(button, false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    $("eval-form").addEventListener("submit", runEvaluation);
});