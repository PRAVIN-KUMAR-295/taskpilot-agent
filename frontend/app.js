/**
 * TASKPILOT AGENT — Client-Side Application Controller
 * PS 01 – Autonomous Agents for Everyday Apps
 */

const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
  ? window.location.origin
  : "http://127.0.0.1:8000";

// Global App State
const state = {
  currentTab: "dashboard",
  tasks: [],
  schedules: [],
  reminders: [],
  memories: [],
  actions: [],
  stats: null,
  activeRun: null,
  pendingApproval: null,
  isAgentRunning: false,
  tasksViewMode: "kanban", // "kanban" or "list"
  authToken: localStorage.getItem("taskpilot_token") || null,
  user: null
};

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener("DOMContentLoaded", async () => {
  setupNavigation();
  setupCommandInputs();
  setupScenarios();
  setupTaskControls();
  setupCalendarControls();
  setupMemoryControls();
  setupModals();

  // Load initial application state
  await checkHealth();
  await refreshDashboard();
  await refreshTasks();
  await refreshCalendar();
  await refreshActivity();
  await refreshMemory();
});

// ==========================================
// NAVIGATION & TABS
// ==========================================
function setupNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      switchTab(target);
    });
  });

  // Dashboard shortcuts
  document.getElementById("btnDashViewAllTasks")?.addEventListener("click", () => switchTab("tasks"));
  document.getElementById("btnDashViewAudit")?.addEventListener("click", () => switchTab("activity"));
}

function switchTab(tabId) {
  state.currentTab = tabId;
  document.querySelectorAll(".nav-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === tabId);
  });
  document.querySelectorAll(".view-section").forEach(sec => {
    sec.classList.remove("active");
  });
  const activeSec = document.getElementById(`view${tabId.charAt(0).toUpperCase() + tabId.slice(1)}`);
  if (activeSec) {
    activeSec.classList.add("active");
  }

  // Refresh relevant data when entering tab
  if (tabId === "dashboard") refreshDashboard();
  if (tabId === "tasks") refreshTasks();
  if (tabId === "calendar") refreshCalendar();
  if (tabId === "activity") refreshActivity();
  if (tabId === "memory") refreshMemory();
}

// ==========================================
// API CLIENT
// ==========================================
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.authToken) {
    headers["Authorization"] = `Bearer ${state.authToken}`;
  }
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "API request failed");
    }
    return await res.json();
  } catch (error) {
    console.warn(`API Error [${path}]:`, error.message);
    throw error;
  }
}

async function checkHealth() {
  try {
    const health = await api("/api/health");
    const statusLabel = document.getElementById("agentStatusLabel");
    if (statusLabel) {
      statusLabel.textContent = `Agent Online (${health.aws_bedrock_configured ? "AWS Bedrock" : "Local Heuristic"})`;
    }
  } catch (e) {
    const statusLabel = document.getElementById("agentStatusLabel");
    if (statusLabel) {
      statusLabel.textContent = "Agent Running (Local Fallback)";
    }
  }
}

// ==========================================
// DASHBOARD CONTROLLER
// ==========================================
async function refreshDashboard() {
  try {
    const stats = await api("/api/stats");
    state.stats = stats;

    document.getElementById("statPendingTasks").textContent = stats.pending_tasks;
    document.getElementById("statCompletedTasks").textContent = stats.completed_tasks;
    document.getElementById("statCompletionRate").textContent = `${stats.completion_rate_percent}%`;
    document.getElementById("statUrgentTasks").textContent = stats.urgent_tasks;
    document.getElementById("statScheduledBlocks").textContent = stats.scheduled_blocks_count;
    document.getElementById("statMemoryCount").textContent = stats.active_memories_count;

    renderDashTasks(state.tasks.slice(0, 4));
    renderDashAudit(stats.recent_actions || []);
  } catch (e) {
    console.error("Failed to refresh stats:", e);
  }
}

function renderDashTasks(tasks) {
  const container = document.getElementById("dashTasksList");
  if (!container) return;
  if (!tasks || tasks.length === 0) {
    container.innerHTML = `<div class="subtle-empty">No pending tasks for today. Tell TaskPilot to generate a plan!</div>`;
    return;
  }
  container.innerHTML = tasks.map(t => `
    <div class="task-mini-item">
      <div class="mini-left">
        <span class="status-dot dot-${t.status.toLowerCase()}"></span>
        <div>
          <div class="mini-title">${escapeHtml(t.title)}</div>
          <div class="mini-meta">${t.due_date || "Today"} • ${t.estimated_duration}m • ${escapeHtml(t.category)}</div>
        </div>
      </div>
      <span class="priority-tag priority-${t.priority}">${t.priority}</span>
    </div>
  `).join("");
}

function renderDashAudit(actions) {
  const container = document.getElementById("dashAuditStream");
  if (!container) return;
  if (!actions || actions.length === 0) {
    container.innerHTML = `<div class="subtle-empty">No recent agent actions recorded.</div>`;
    return;
  }
  container.innerHTML = actions.slice(0, 4).map(a => `
    <div class="task-mini-item">
      <div class="mini-left">
        <span class="verification-badge ${a.verification_status}">✓</span>
        <div>
          <div class="mini-title">${escapeHtml(a.action_name)}</div>
          <div class="mini-meta">${escapeHtml(a.tool_name)} • ${formatTime(a.created_at)}</div>
        </div>
      </div>
      <span class="status-badge ${a.status}">${a.status}</span>
    </div>
  `).join("");
}

// ==========================================
// AGENT WORKSPACE (HERO COMPONENT)
// ==========================================
function setupCommandInputs() {
  const dashInput = document.getElementById("dashboardCommandInput");
  const dashBtn = document.getElementById("btnDashboardRun");
  if (dashBtn && dashInput) {
    dashBtn.addEventListener("click", () => {
      const val = dashInput.value.trim();
      if (!val) return;
      dashInput.value = "";
      switchTab("workspace");
      runAgentGoal(val);
    });
    dashInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        dashBtn.click();
      }
    });
  }

  // Dashboard preset chips
  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const prompt = chip.dataset.prompt;
      if (prompt) {
        switchTab("workspace");
        runAgentGoal(prompt);
      }
    });
  });

  // Workspace input
  const workInput = document.getElementById("workspaceGoalInput");
  const workBtn = document.getElementById("btnWorkspaceRun");
  if (workBtn && workInput) {
    workBtn.addEventListener("click", () => {
      const val = workInput.value.trim();
      if (!val) return;
      workInput.value = "";
      runAgentGoal(val);
    });
    workInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        workBtn.click();
      }
    });
  }

  // Approval buttons
  document.getElementById("btnApprovePlan")?.addEventListener("click", () => handlePlanApproval(true));
  document.getElementById("btnRejectPlan")?.addEventListener("click", () => handlePlanApproval(false));
}

function setupScenarios() {
  const scenarioMap = {
    "aws-friday": "Create a plan to finish my AWS project by Friday.",
    "aws-study": "Create a 7-day study plan for my AWS Solutions Architect Associate exam next week.",
    "plan-day": "Plan my day and prioritize my tasks based on my work hours.",
    "hackathon-plan": "Create a complete hackathon execution plan including app finalization, demo recording, and pitch PPT.",
    "safety-test": "Delete task 1 permanently."
  };

  document.querySelectorAll(".btn-scenario").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-scenario").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const key = btn.dataset.scenario;
      if (scenarioMap[key]) {
        runAgentGoal(scenarioMap[key]);
      }
    });
  });

  // Quick Demo Mode modal trigger
  document.getElementById("btnDemoMode")?.addEventListener("click", () => {
    switchTab("workspace");
    runAgentGoal("Create a plan to finish my AWS project by Friday.");
  });
}

/**
 * Executes a Natural Language Goal through the Autonomous Agent Orchestrator.
 */
async function runAgentGoal(goal, confirmedAction = null) {
  if (state.isAgentRunning) return;
  state.isAgentRunning = true;
  updateLiveStateBadge("EXECUTING", "running");

  // Append user message to conversation stream
  if (!confirmedAction) {
    appendChatMsg("user", goal);
    resetTimeline();
  }

  try {
    // Step 1: Animate UNDERSTANDING state on timeline
    updateStateProgressBar("UNDERSTANDING");
    appendTimelineStep("UNDERSTANDING", "Analyzing user goal and extracting intent criteria...", "in_progress");

    const payload = confirmedAction
      ? { confirmed_action: confirmedAction, goal: goal, run_id: state.activeRun }
      : { goal: goal, message: goal };

    const result = await api("/api/agent/run", {
      method: "POST",
      body: JSON.stringify(payload)
    });

    state.activeRun = result.run_id;

    // Render Timeline Steps received from backend
    renderTimelineFromRun(result.timeline || []);

    // Check if the agent paused for Human Approval
    if (result.status === "WAITING_FOR_APPROVAL" && result.actionPendingApproval) {
      state.pendingApproval = result.actionPendingApproval;
      updateStateProgressBar("CONFIRMATION");
      updateLiveStateBadge("APPROVAL REQUIRED", "waiting");
      showApprovalCard(result.actionPendingApproval, result.plan);
      appendChatMsg("assistant", `I have formulated a structured plan with ${result.plan?.tasks?.length || 0} tasks. Please review and approve execution.`);
      renderPlanVisualizer(result.plan);
    } else {
      // Completed Execution
      updateStateProgressBar("VERIFYING");
      updateStateProgressBar("COMPLETED");
      updateLiveStateBadge("COMPLETED", "completed");
      hideApprovalCard();
      appendChatMsg("assistant", result.summary || "Goal executed and verified successfully.");
      
      if (result.plan) {
        renderPlanVisualizer(result.plan);
      }
      showVerificationSummary(result);
      showToast("Agent executed and verified all actions successfully!", "success");

      // Refresh tasks, schedules, and dashboard
      await refreshTasks();
      await refreshCalendar();
      await refreshDashboard();
      await refreshActivity();
    }

  } catch (error) {
    console.error("Agent execution failed:", error);
    updateLiveStateBadge("ERROR", "failed");
    appendTimelineStep("FAILED", `Error: ${error.message}`, "failed");
    appendChatMsg("assistant", `I encountered an unexpected issue: ${error.message}. No destructive changes were made.`);
    showToast(`Agent Error: ${error.message}`, "warning");
  } finally {
    state.isAgentRunning = false;
  }
}

async function handlePlanApproval(approved) {
  if (!state.pendingApproval) return;
  const approvalData = state.pendingApproval;
  hideApprovalCard();

  if (approved) {
    appendChatMsg("user", "✓ Approved. Proceed with autonomous execution.");
    await runAgentGoal("Approved execution", approvalData);
  } else {
    appendChatMsg("user", "✕ Action rejected.");
    appendChatMsg("assistant", "Execution cancelled by user. No database mutations occurred.");
    updateLiveStateBadge("CANCELLED", "completed");
    resetTimeline();
  }
  state.pendingApproval = null;
}

// ==========================================
// WORKSPACE VISUAL RENDERING
// ==========================================
function updateLiveStateBadge(text, stateClass) {
  const badge = document.getElementById("timelineLiveState");
  if (badge) {
    badge.textContent = text;
    badge.className = `agent-live-badge ${stateClass}`;
  }
}

function updateStateProgressBar(activeState) {
  const nodes = document.querySelectorAll(".state-node");
  let found = false;
  nodes.forEach(node => {
    const s = node.dataset.state;
    if (s === activeState) {
      node.className = "state-node active";
      found = true;
    } else if (!found) {
      node.className = "state-node completed";
    } else {
      node.className = "state-node";
    }
  });
}

function resetTimeline() {
  const stream = document.getElementById("timelineStream");
  if (stream) stream.innerHTML = "";
  const planViz = document.getElementById("planVisualizer");
  if (planViz) planViz.innerHTML = "";
  hideApprovalCard();
  hideVerificationSummary();
}

function appendTimelineStep(stepName, message, statusClass, meta = {}) {
  const stream = document.getElementById("timelineStream");
  if (!stream) return;
  const card = document.createElement("div");
  card.className = `timeline-step-card ${statusClass}`;
  card.innerHTML = `
    <div class="step-card-header">
      <span class="step-name-badge">${escapeHtml(stepName)}</span>
      <span class="step-time">${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
    </div>
    <div class="step-message">${escapeHtml(message)}</div>
    ${meta.tools ? `<div class="step-tool-tag">🛠 Tools: ${escapeHtml(meta.tools.join(", "))}</div>` : ""}
  `;
  stream.appendChild(card);
  stream.scrollTop = stream.scrollHeight;
}

function renderTimelineFromRun(timeline) {
  const stream = document.getElementById("timelineStream");
  if (!stream || !timeline) return;
  stream.innerHTML = "";
  timeline.forEach(item => {
    const card = document.createElement("div");
    card.className = `timeline-step-card ${item.status || "completed"}`;
    card.innerHTML = `
      <div class="step-card-header">
        <span class="step-name-badge">${escapeHtml(item.step)}</span>
        <span class="step-time">${item.timestamp || ""}</span>
      </div>
      <div class="step-message">${escapeHtml(item.message)}</div>
      ${item.meta && item.meta.tools ? `<div class="step-tool-tag">🛠 Tools: ${escapeHtml(item.meta.tools.join(", "))}</div>` : ""}
    `;
    stream.appendChild(card);
  });
  stream.scrollTop = stream.scrollHeight;
}

function renderPlanVisualizer(plan) {
  const container = document.getElementById("planVisualizer");
  const countBadge = document.getElementById("planTasksCount");
  if (!container || !plan) return;

  const tasks = plan.tasks || [];
  if (countBadge) countBadge.textContent = `${tasks.length} Tasks Formulated`;

  container.innerHTML = tasks.map((t, idx) => `
    <div class="plan-card-item">
      <div class="plan-card-top">
        <span class="plan-card-stage">${escapeHtml(t.day_or_stage || `Step ${idx + 1}`)}</span>
        <span class="priority-tag priority-${t.priority}">${t.priority}</span>
      </div>
      <div class="plan-card-title">${escapeHtml(t.title)}</div>
      <div class="plan-card-meta">
        <span>⏱ ${t.estimated_minutes || 30} mins</span>
        ${t.dependencies && t.dependencies.length > 0 ? `<span>🔗 Depends on: ${escapeHtml(t.dependencies.join(", "))}</span>` : ""}
      </div>
    </div>
  `).join("");
}

function showApprovalCard(actionPending, plan) {
  const card = document.getElementById("humanApprovalCard");
  const title = document.getElementById("approvalCardTitle");
  const desc = document.getElementById("approvalCardDesc");
  if (!card) return;

  title.textContent = actionPending.title || "Approve Execution Plan";
  desc.textContent = actionPending.description || "The agent is waiting for your confirmation before executing mutations.";
  card.classList.remove("hidden");
}

function hideApprovalCard() {
  document.getElementById("humanApprovalCard")?.classList.add("hidden");
}

function showVerificationSummary(result) {
  const card = document.getElementById("verificationSummaryCard");
  const text = document.getElementById("verSummaryText");
  const items = document.getElementById("verSummaryItems");
  if (!card) return;

  card.classList.remove("hidden");
  text.textContent = `Autonomous execution verified: ${result.actionsSuccessful || 0} tool mutations validated in database.`;
  if (items && result.timeline) {
    const verStep = result.timeline.find(t => t.step === "VERIFYING");
    if (verStep && verStep.meta && verStep.meta.details) {
      items.innerHTML = verStep.meta.details.map(d => `
        <div style="font-size: 0.74rem; color: #a7f3d0; margin-top: 4px;">
          ✓ Verified ${d.tool_name}: ${d.details?.check || "passed"}
        </div>
      `).join("");
    }
  }
}

function hideVerificationSummary() {
  document.getElementById("verificationSummaryCard")?.classList.add("hidden");
}

function appendChatMsg(sender, text) {
  const stream = document.getElementById("workspaceChatStream");
  if (!stream) return;
  const msg = document.createElement("div");
  msg.className = `chat-msg ${sender}`;
  msg.innerHTML = `
    <div class="chat-avatar">${sender === "user" ? "ME" : "AI"}</div>
    <div class="chat-bubble">
      ${sender === "assistant" ? `<div class="chat-sender">TaskPilot Agent</div>` : ""}
      <p>${escapeHtml(text)}</p>
    </div>
  `;
  stream.appendChild(msg);
  stream.scrollTop = stream.scrollHeight;
}

// ==========================================
// TASKS PAGE CONTROLLER
// ==========================================
function setupTaskControls() {
  // View toggle
  document.getElementById("btnViewKanban")?.addEventListener("click", () => {
    state.tasksViewMode = "kanban";
    document.getElementById("btnViewKanban").classList.add("active");
    document.getElementById("btnViewList").classList.remove("active");
    document.getElementById("kanbanBoard").classList.remove("hidden");
    document.getElementById("tasksListContainer").classList.add("hidden");
  });

  document.getElementById("btnViewList")?.addEventListener("click", () => {
    state.tasksViewMode = "list";
    document.getElementById("btnViewList").classList.add("active");
    document.getElementById("btnViewKanban").classList.remove("active");
    document.getElementById("kanbanBoard").classList.add("hidden");
    document.getElementById("tasksListContainer").classList.remove("hidden");
    renderTasksTable();
  });

  // Filter inputs
  const searchInput = document.getElementById("taskSearchInput");
  const prioFilter = document.getElementById("taskPriorityFilter");
  const catFilter = document.getElementById("taskCategoryFilter");

  [searchInput, prioFilter, catFilter].forEach(el => {
    el?.addEventListener("input", () => refreshTasks());
  });

  // Task form submission
  document.getElementById("taskForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("taskInputTitle").value.trim();
    const desc = document.getElementById("taskInputDesc").value.trim();
    const prio = document.getElementById("taskInputPriority").value;
    const cat = document.getElementById("taskInputCategory").value.trim();
    const due = document.getElementById("taskInputDueDate").value.trim();
    const dur = parseInt(document.getElementById("taskInputDuration").value, 10);

    if (!title) return;

    try {
      await api("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: title,
          description: desc,
          priority: prio,
          category: cat || "General",
          due_date: due || null,
          estimated_duration: dur || 30
        })
      });
      document.getElementById("taskModal").classList.add("hidden");
      document.getElementById("taskForm").reset();
      showToast("Task created successfully!", "success");
      await refreshTasks();
      await refreshDashboard();
    } catch (err) {
      showToast(`Error creating task: ${err.message}`, "warning");
    }
  });
}

async function refreshTasks() {
  const search = document.getElementById("taskSearchInput")?.value.trim() || "";
  const priority = document.getElementById("taskPriorityFilter")?.value || "";
  const category = document.getElementById("taskCategoryFilter")?.value || "";

  let query = "/api/tasks?";
  if (search) query += `search=${encodeURIComponent(search)}&`;
  if (priority) query += `priority=${encodeURIComponent(priority)}&`;
  if (category) query += `category=${encodeURIComponent(category)}&`;

  try {
    const data = await api(query);
    state.tasks = data.tasks || [];
    renderKanban();
    if (state.tasksViewMode === "list") {
      renderTasksTable();
    }
    renderDashTasks(state.tasks.slice(0, 4));
  } catch (e) {
    console.error("Failed to load tasks:", e);
  }
}

function renderKanban() {
  const cols = {
    TODO: document.getElementById("listTodo"),
    IN_PROGRESS: document.getElementById("listProgress"),
    BLOCKED: document.getElementById("listBlocked"),
    COMPLETED: document.getElementById("listCompleted")
  };
  const counts = {
    TODO: document.getElementById("countTodo"),
    IN_PROGRESS: document.getElementById("countProgress"),
    BLOCKED: document.getElementById("countBlocked"),
    COMPLETED: document.getElementById("countCompleted")
  };

  // Clear columns
  Object.values(cols).forEach(c => { if (c) c.innerHTML = ""; });

  const buckets = { TODO: [], IN_PROGRESS: [], BLOCKED: [], COMPLETED: [] };
  state.tasks.forEach(t => {
    const s = t.status in buckets ? t.status : "TODO";
    buckets[s].push(t);
  });

  Object.entries(buckets).forEach(([status, list]) => {
    if (counts[status]) counts[status].textContent = list.length;
    const colEl = cols[status];
    if (!colEl) return;

    if (list.length === 0) {
      colEl.innerHTML = `<div class="subtle-empty">No tasks in ${status}</div>`;
      return;
    }

    colEl.innerHTML = list.map(t => `
      <div class="task-card" data-task-id="${t.id}">
        <div class="task-card-header">
          <span class="task-category">${escapeHtml(t.category)}</span>
          <span class="priority-tag priority-${t.priority}">${t.priority}</span>
        </div>
        <div class="task-card-title">${escapeHtml(t.title)}</div>
        ${t.description ? `<div class="task-card-desc">${escapeHtml(t.description)}</div>` : ""}
        <div class="task-card-meta">
          <span>⏱ ${t.estimated_duration}m</span>
          <span>📅 ${t.due_date || "Today"}</span>
        </div>
        <div class="task-card-actions">
          <button class="btn-card-ai" onclick="triggerTaskAiAction(${t.id}, 'explain')">💡 Why</button>
          <button class="btn-card-ai" onclick="triggerTaskAiAction(${t.id}, 'prioritize')">⚡ Prioritize</button>
          <button class="btn-card-ai" onclick="triggerTaskAiAction(${t.id}, 'subtasks')">🧩 Subtasks</button>
          ${t.status !== "COMPLETED" ? `<button class="btn-card-complete" onclick="completeTask(${t.id})">✓ Done</button>` : ""}
        </div>
      </div>
    `).join("");
  });
}

function renderTasksTable() {
  const tbody = document.getElementById("tasksTableBody");
  if (!tbody) return;
  if (state.tasks.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 2rem;">No matching tasks found.</td></tr>`;
    return;
  }
  tbody.innerHTML = state.tasks.map(t => `
    <tr>
      <td><span class="status-dot dot-${t.status.toLowerCase()}"></span></td>
      <td><strong>${escapeHtml(t.title)}</strong></td>
      <td><span class="priority-tag priority-${t.priority}">${t.priority}</span></td>
      <td>${escapeHtml(t.category)}</td>
      <td>${t.due_date || "Today"}</td>
      <td>${t.estimated_duration} mins</td>
      <td><span class="badge-subtle">${t.source}</span></td>
      <td>
        <button class="btn-card-ai" onclick="triggerTaskAiAction(${t.id}, 'prioritize')">Prioritize</button>
        <button class="btn-card-ai" onclick="triggerTaskAiAction(${t.id}, 'subtasks')">Subtasks</button>
        ${t.status !== "COMPLETED" ? `<button class="btn-card-complete" onclick="completeTask(${t.id})">✓</button>` : ""}
      </td>
    </tr>
  `).join("");
}

async function completeTask(taskId) {
  try {
    await api(`/api/tasks/${taskId}/complete`, { method: "POST" });
    showToast(`Task #${taskId} completed!`, "success");
    await refreshTasks();
    await refreshDashboard();
  } catch (err) {
    showToast(`Failed to complete task: ${err.message}`, "warning");
  }
}

async function triggerTaskAiAction(taskId, action) {
  try {
    const res = await api(`/api/tasks/${taskId}/ai-action`, {
      method: "POST",
      body: JSON.stringify({ action })
    });
    if (action === "explain") {
      showToast(res.explanation, "info");
      alert(`AI Importance Explanation:\n\n${res.explanation}`);
    } else {
      showToast(res.message, "success");
      await refreshTasks();
      await refreshDashboard();
    }
  } catch (err) {
    showToast(`AI action failed: ${err.message}`, "warning");
  }
}

// ==========================================
// CALENDAR & SCHEDULE CONTROLLER
// ==========================================
function setupCalendarControls() {
  document.getElementById("btnOptimizeSchedule")?.addEventListener("click", async () => {
    try {
      showToast("Optimizing focus blocks with AI...", "info");
      const res = await api("/api/agent/optimize-schedule", { method: "POST" });
      showToast(res.message || "Schedule optimized successfully!", "success");
      await refreshCalendar();
      await refreshDashboard();
    } catch (err) {
      showToast(`Schedule optimization failed: ${err.message}`, "warning");
    }
  });

  document.getElementById("btnAddScheduleBlock")?.addEventListener("click", () => {
    document.getElementById("scheduleModal").classList.remove("hidden");
  });

  document.getElementById("scheduleForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("schInputTitle").value.trim();
    const start = document.getElementById("schInputStart").value.trim();
    const end = document.getElementById("schInputEnd").value.trim();
    const type = document.getElementById("schInputType").value;
    const day = document.getElementById("schInputDay").value.trim();

    try {
      await api("/api/calendar", {
        method: "POST",
        body: JSON.stringify({
          title, start_time: start, end_time: end, session_type: type, day_of_week: day
        })
      });
      document.getElementById("scheduleModal").classList.add("hidden");
      document.getElementById("scheduleForm").reset();
      showToast("Focus block created!", "success");
      await refreshCalendar();
    } catch (err) {
      showToast(`Failed to create schedule block: ${err.message}`, "warning");
    }
  });

  document.getElementById("btnCreateReminder")?.addEventListener("click", () => {
    const title = prompt("Reminder Title (e.g. Submit hackathon PPT):");
    if (!title) return;
    const time = prompt("Reminder Time (e.g. Tomorrow at 8:00 PM):", "Tomorrow at 8:00 PM");
    if (!time) return;

    api("/api/reminders", {
      method: "POST",
      body: JSON.stringify({ title, reminder_time: time })
    }).then(() => {
      showToast("Reminder created!", "success");
      refreshCalendar();
    });
  });
}

async function refreshCalendar() {
  try {
    const data = await api("/api/calendar");
    state.schedules = data.schedules || [];
    state.reminders = data.reminders || [];

    const schCount = document.getElementById("scheduleCountBadge");
    if (schCount) schCount.textContent = `${state.schedules.length} Blocks`;

    // Render schedule blocks
    const schStream = document.getElementById("scheduleBlocksStream");
    if (schStream) {
      if (state.schedules.length === 0) {
        schStream.innerHTML = `<div class="subtle-empty">No schedule blocks planned. Click "Optimize My Schedule with AI"!</div>`;
      } else {
        schStream.innerHTML = state.schedules.map(s => `
          <div class="schedule-item-card">
            <div class="schedule-time-box">
              <span>${s.start_time}</span>
              <span style="color:var(--text-muted); font-size:0.68rem;">to ${s.end_time}</span>
            </div>
            <div class="schedule-details">
              <div class="schedule-item-title">${escapeHtml(s.title)}</div>
              <div class="schedule-type-badge">${s.session_type} • ${s.day_of_week} ${s.is_optimized ? '• <span style="color:var(--accent-cyan)">AI-Optimized</span>' : ''}</div>
            </div>
          </div>
        `).join("");
      }
    }

    // Render reminders
    const remStream = document.getElementById("remindersStream");
    if (remStream) {
      if (state.reminders.length === 0) {
        remStream.innerHTML = `<div class="subtle-empty">No active reminders configured.</div>`;
      } else {
        remStream.innerHTML = state.reminders.map(r => `
          <div class="reminder-card">
            <div class="reminder-left">
              <span>⏰</span>
              <div>
                <div class="reminder-title">${escapeHtml(r.title)}</div>
                <div class="reminder-time">${escapeHtml(r.reminder_time)} • ${r.channel}</div>
              </div>
            </div>
            <button class="btn-close-modal" title="Dismiss" onclick="cancelReminder(${r.id})">✕</button>
          </div>
        `).join("");
      }
    }

  } catch (e) {
    console.error("Failed to refresh calendar:", e);
  }
}

async function cancelReminder(reminderId) {
  try {
    await api(`/api/reminders/${reminderId}`, { method: "DELETE" });
    showToast("Reminder dismissed.", "info");
    await refreshCalendar();
  } catch (err) {
    showToast(`Failed to dismiss reminder: ${err.message}`, "warning");
  }
}

// ==========================================
// ACTIVITY LOG & AUDIT CONTROLLER
// ==========================================
function setupActivityControls() {
  document.getElementById("btnRefreshActivity")?.addEventListener("click", () => refreshActivity());
}

async function refreshActivity() {
  try {
    const data = await api("/api/agent/actions?limit=40");
    state.actions = data.actions || [];

    const tbody = document.getElementById("activityTableBody");
    if (!tbody) return;

    if (state.actions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem;">No audit records available yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = state.actions.map(a => `
      <tr>
        <td><span style="font-family:var(--font-mono); font-size:0.75rem;">${formatTime(a.created_at)}</span></td>
        <td><strong>${escapeHtml(a.action_name)}</strong></td>
        <td><span class="step-tool-tag">${escapeHtml(a.tool_name)}</span></td>
        <td><span class="status-badge ${a.status}">${a.status}</span></td>
        <td><span class="verification-badge ${a.verification_status}">${a.verification_status === 'VERIFIED' ? '✓ VERIFIED' : a.verification_status}</span></td>
        <td><span style="font-family:var(--font-mono); font-size:0.75rem;">${a.verification_details?.elapsed_ms ? a.verification_details.elapsed_ms + ' ms' : '< 5ms'}</span></td>
        <td><button class="btn-card-ai" onclick='inspectAction(${JSON.stringify(a).replace(/'/g, "&apos;")})'>Inspect</button></td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("Failed to refresh activity log:", e);
  }
}

function inspectAction(action) {
  alert(`Agent Action Audit Trail:\n\nTool: ${action.tool_name}\nAction: ${action.action_name}\nStatus: ${action.status}\nVerification: ${action.verification_status}\n\nInputs:\n${JSON.stringify(action.input_data, null, 2)}\n\nOutputs:\n${JSON.stringify(action.output_data, null, 2)}`);
}

// ==========================================
// MEMORY & USER PREFERENCES CONTROLLER
// ==========================================
function setupMemoryControls() {
  document.getElementById("btnAddMemory")?.addEventListener("click", () => {
    document.getElementById("memoryModal").classList.remove("hidden");
  });

  document.getElementById("memoryForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const key = document.getElementById("memInputKey").value.trim();
    const val = document.getElementById("memInputValue").value.trim();
    const cat = document.getElementById("memInputCategory").value;

    try {
      await api("/api/memory", {
        method: "POST",
        body: JSON.stringify({ key, value: val, category: cat })
      });
      document.getElementById("memoryModal").classList.add("hidden");
      document.getElementById("memoryForm").reset();
      showToast("Preference saved to agent memory!", "success");
      await refreshMemory();
      await refreshDashboard();
    } catch (err) {
      showToast(`Failed to save memory: ${err.message}`, "warning");
    }
  });
}

async function refreshMemory() {
  try {
    const data = await api("/api/memory");
    state.memories = data.memories || [];

    const grid = document.getElementById("memoryCardsGrid");
    if (!grid) return;

    if (state.memories.length === 0) {
      grid.innerHTML = `<div class="subtle-empty" style="grid-column: 1 / -1;">No user preferences stored yet.</div>`;
      return;
    }

    grid.innerHTML = state.memories.map(m => `
      <div class="memory-card glass-card">
        <div>
          <div class="memory-card-top">
            <span class="memory-category">${escapeHtml(m.category)}</span>
            <button class="btn-del-memory" onclick="deleteMemory(${m.id})">✕</button>
          </div>
          <div class="memory-key">${escapeHtml(m.key)}</div>
          <div class="memory-val">${escapeHtml(m.value)}</div>
        </div>
        <div style="font-size:0.68rem; color:var(--text-muted); margin-top:1rem;">
          Source: ${escapeHtml(m.source)} • Confidence: ${m.confidence * 100}%
        </div>
      </div>
    `).join("");
  } catch (e) {
    console.error("Failed to load memory:", e);
  }
}

async function deleteMemory(memoryId) {
  try {
    await api(`/api/memory/${memoryId}`, { method: "DELETE" });
    showToast("Preference removed from agent memory.", "info");
    await refreshMemory();
  } catch (err) {
    showToast(`Failed to delete memory: ${err.message}`, "warning");
  }
}

// ==========================================
// MODALS & UTILITIES
// ==========================================
function setupModals() {
  // New task modal
  document.getElementById("btnOpenNewTaskModal")?.addEventListener("click", () => {
    document.getElementById("taskModal").classList.remove("hidden");
  });
  document.getElementById("btnCloseTaskModal")?.addEventListener("click", () => {
    document.getElementById("taskModal").classList.add("hidden");
  });
  document.getElementById("btnCancelTaskModal")?.addEventListener("click", () => {
    document.getElementById("taskModal").classList.add("hidden");
  });

  // Memory modal
  document.getElementById("btnCloseMemoryModal")?.addEventListener("click", () => {
    document.getElementById("memoryModal").classList.add("hidden");
  });
  document.getElementById("btnCancelMemoryModal")?.addEventListener("click", () => {
    document.getElementById("memoryModal").classList.add("hidden");
  });

  // Schedule modal
  document.getElementById("btnCloseScheduleModal")?.addEventListener("click", () => {
    document.getElementById("scheduleModal").classList.add("hidden");
  });
  document.getElementById("btnCancelScheduleModal")?.addEventListener("click", () => {
    document.getElementById("scheduleModal").classList.add("hidden");
  });

  setupActivityControls();
}

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === "success" ? "✓" : (type === "warning" ? "⚠️" : "ℹ️")}</span>
    <div>${escapeHtml(message)}</div>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatTime(isoString) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch (e) {
    return isoString;
  }
}
