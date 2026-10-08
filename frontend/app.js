document.getElementById("chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const inputField = document.getElementById("user-input");
    const message = inputField.value.trim();

    if (!message) {
        return;
    }

    inputField.value = "";

    appendUserMessage(message);

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        if (!response.ok) {
            throw new Error("Server returned an error");
        }

        const plan = await response.json();

        appendAssistantMessage(plan);
        loadHistory();

    } catch (err) {
        appendError(
            "System",
            "Error connecting to the server."
        );
        console.error(err);
    }
});


function appendUserMessage(text) {
    const responseBox = document.getElementById("response");

    if (!responseBox) {
        return;
    }

    const msgDiv = document.createElement("div");
    msgDiv.className = "message";

    msgDiv.innerHTML = `<strong>You:</strong> ${escapeHtml(text)}`;

    responseBox.appendChild(msgDiv);
}


function appendAssistantMessage(plan) {
    const responseBox = document.getElementById("response");

    if (!responseBox) {
        return;
    }

    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant";
    msgDiv.id = `plan-msg-${plan.id}`;

    msgDiv.innerHTML = generatePlanHTML(plan);

    responseBox.appendChild(msgDiv);
}


function updateAssistantMessage(plan) {
    const msgDiv = document.getElementById(`plan-msg-${plan.id}`);

    if (msgDiv) {
        msgDiv.innerHTML = generatePlanHTML(plan);
    } else {
        appendAssistantMessage(plan);
    }

    loadHistory();
}


function generatePlanHTML(plan) {
    let html = "";

    html += `<strong>Agent State:</strong> ${escapeHtml(plan.state || "")}<br>`;
    html += `<strong>Planner:</strong> ${escapeHtml(plan.planner_source || "Unknown")}<br>`;
    html += `<strong>Intent:</strong> ${escapeHtml(plan.intent || "")}<br>`;

    if (plan.final_result) {
        html += `<strong>Final Result:</strong> ${escapeHtml(String(plan.final_result))}<br>`;
    }

    if (plan.error) {
        html += `<strong>Error:</strong> ${escapeHtml(String(plan.error))}<br>`;
    }

    if (plan.execution_trace && plan.execution_trace.length > 0) {
        html += `
            <div class="execution-trace">
                <h4>Execution Trace</h4>
                <ol>
        `;

        plan.execution_trace.forEach(step => {
            html += `<li>${escapeHtml(String(step))}</li>`;
        });

        html += `
                </ol>
            </div>
        `;
    }

    if (plan.tasks && plan.tasks.length > 0) {
        html += `<h4>Tasks</h4>`;

        plan.tasks.forEach(task => {
            html += `
                <div class="task">
                    <strong>${escapeHtml(task.description || "")}</strong><br>
                    Status: ${escapeHtml(task.status || "")}<br>
            `;

            if (task.tool_name) {
                html += `Tool: ${escapeHtml(task.tool_name)}<br>`;
            }

            if (
                task.requires_approval &&
                task.status === "PENDING"
            ) {
                html += `
                    <div class="approval-box">
                        <strong>Approval Required</strong>
                        <p>This action requires your approval.</p>

                        <div class="approval-buttons">
                            <button onclick="handleApproval(
                                '${plan.id}',
                                ${task.id},
                                'approve'
                            )">
                                Approve
                            </button>

                            <button
                                class="danger-button"
                                onclick="handleApproval(
                                    '${plan.id}',
                                    ${task.id},
                                    'reject'
                                )"
                            >
                                Reject
                            </button>
                        </div>
                    </div>
                `;
            }

            if (
                task.result !== null &&
                task.result !== undefined
            ) {
                html += `
                    Result:
                    <strong>${escapeHtml(String(task.result))}</strong><br>
                `;
            }

            if (task.error) {
                html += `
                    <strong>Error:</strong>
                    ${escapeHtml(String(task.error))}
                `;
            }

            html += `</div>`;
        });
    }

    return html;
}


async function handleApproval(planId, taskId, action) {
    try {
        const response = await fetch(`/api/${action}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                plan_id: planId,
                task_id: taskId
            })
        });

        if (!response.ok) {
            throw new Error("Approval request failed");
        }

        const plan = await response.json();

        updateAssistantMessage(plan);

    } catch (err) {
        appendError(
            "System",
            `Error performing ${action}.`
        );

        console.error(err);
    }
}


function appendError(sender, text) {
    const responseBox = document.getElementById("response");

    if (!responseBox) {
        return;
    }

    const msgDiv = document.createElement("div");

    msgDiv.className = "message";

    msgDiv.innerHTML = `
        <strong>${escapeHtml(sender)}:</strong>
        ${escapeHtml(text)}
    `;

    responseBox.appendChild(msgDiv);
}


async function loadHistory() {
    const historyList = document.getElementById("history-list");

    if (!historyList) {
        return;
    }

    try {
        const response = await fetch("/api/history?limit=20");

        if (!response.ok) {
            throw new Error("Failed to load history");
        }

        const history = await response.json();

        renderHistory(history);

    } catch (err) {
        historyList.innerHTML =
            "<p>Unable to load task history.</p>";

        console.error(err);
    }
}


function renderHistory(history) {
    const historyList = document.getElementById("history-list");

    if (!historyList) {
        return;
    }

    if (!history || history.length === 0) {
        historyList.innerHTML =
            "<p>No task history yet.</p>";
        return;
    }

    historyList.innerHTML = "";

    history.forEach(item => {
        const div = document.createElement("div");

        let stateClass = "history-pending";

        if (item.state === "COMPLETED") {
            stateClass = "history-completed";
        } else if (item.state === "FAILED") {
            stateClass = "history-failed";
        }

        div.className = `history-item ${stateClass}`;

        div.innerHTML = `
            <div class="history-header">
                <strong>${escapeHtml(item.original_request)}</strong>
                <span class="history-state">
                    ${escapeHtml(item.state)}
                </span>
            </div>

            <div>
                Planner:
                ${escapeHtml(item.planner_source || "Unknown")}
            </div>

            <div>
                Created:
                ${escapeHtml(item.created_at || "")}
            </div>
        `;

        historyList.appendChild(div);
    });
}


async function checkSystemHealth() {
    const statusElement =
        document.getElementById("system-status");

    if (!statusElement) {
        return;
    }

    try {
        const response = await fetch("/api/health");

        if (!response.ok) {
            throw new Error("Health check failed");
        }

        const data = await response.json();

        if (data.status === "healthy") {
            statusElement.textContent =
                "● System Online";

            statusElement.className =
                "system-status online";
        } else {
            statusElement.textContent =
                "● System Degraded";

            statusElement.className =
                "system-status offline";
        }

    } catch (error) {
        statusElement.textContent =
            "● System Offline";

        statusElement.className =
            "system-status offline";

        console.error(error);
    }
}


function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}


const refreshButton =
    document.getElementById("refresh-history");

if (refreshButton) {
    refreshButton.addEventListener(
        "click",
        loadHistory
    );
}


document.addEventListener(
    "DOMContentLoaded",
    () => {
        checkSystemHealth();
        loadHistory();
    }
);