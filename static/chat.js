function appendMessage(role, html) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;
    wrapper.innerHTML = html;
    $("chat-window").appendChild(wrapper);
    $("chat-window").scrollTop = $("chat-window").scrollHeight;
    return wrapper;
}

function normalizeSources(data) {
    if (!Array.isArray(data.retrieved_chunks)) {
        return [];
    }

    return data.retrieved_chunks.map((chunk, index) => {
        const meta = chunk.metadata || {};

        return {
            number: index + 1,
            file_name: meta.file_name || "unknown",
            page_number: meta.page_number ?? "",
            chunk_number: meta.chunk_number ?? ""
        };
    });
}

function getRuntimePayload() {
    return {
        top_k: Number($("top-k").value),
        temperature: Number($("temperature").value),
        strictness: $("strictness-mode").checked,
        system_prompt: $("system-prompt").value,
        rag_instruction_template: $("rag-template").value
    };
}

async function saveSettings() {
    const button = $("save-settings");
    const status = $("settings-status");

    const payload = {
        top_k_default: Number($("top-k").value),
        temperature_default: Number($("temperature").value),
        strictness_mode: $("strictness-mode").checked,
        system_prompt: $("system-prompt").value,
        rag_instruction_template: $("rag-template").value
    };

    status.textContent = "Saving settings...";
    setButtonLoading(button, true, "Saving...");

    try {
        const response = await fetch("/api/settings", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            status.textContent = data.detail || "Failed to save settings.";
            return;
        }

        status.textContent = "Settings saved.";
    } catch (error) {
        status.textContent = `Request failed: ${error.message}`;
    } finally {
        setButtonLoading(button, false);
    }
}

async function sendQuestion(event) {
    event.preventDefault();

    const questionInput = $("question-input");
    const question = questionInput.value.trim();
    const button = event.submitter;

    if (!question) return;

    appendMessage("user", `<strong>You</strong><p>${escapeHtml(question)}</p>`);
    questionInput.value = "";

    const assistantMessage = appendMessage(
        "assistant",
        `<strong>Assistant</strong><p>Thinking...</p>`
    );

    const payload = {
        question,
        ...getRuntimePayload()
    };

    setButtonLoading(button, true, "Sending...");

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            assistantMessage.innerHTML =
                `<strong>Assistant</strong><p>${escapeHtml(data.detail || "Query failed.")}</p>`;
            return;
        }

        const answer = data.answer || "No answer returned.";
        const sources = normalizeSources(data);

        const sourcesHtml = sources.length
            ? sources.map(source =>
                `${source.number}. ${escapeHtml(source.file_name)}, page ${escapeHtml(source.page_number)}, chunk ${escapeHtml(source.chunk_number)}`
            ).join("<br>")
            : "No sources returned.";

        assistantMessage.innerHTML = `
            <strong>Assistant</strong>
            <p>${escapeHtml(answer).replace(/\n/g, "<br>")}</p>
            <div class="sources"><strong>Sources</strong><br>${sourcesHtml}</div>
        `;
    } catch (error) {
        assistantMessage.innerHTML =
            `<strong>Assistant</strong><p>Request failed: ${escapeHtml(error.message)}</p>`;
    } finally {
        setButtonLoading(button, false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    $("save-settings").addEventListener("click", saveSettings);
    $("chat-form").addEventListener("submit", sendQuestion);
});