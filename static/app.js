const state = {
  user: null,
  meta: null,
  cases: [],
  dashboard: null,
  selectedCaseId: null,
  currentDetail: { comments: [], subtasks: [] },
};

const palette = ["#5cc0ff", "#57d9bc", "#ffbf69", "#8f8cff", "#ff7f96", "#53a4ff", "#89f0dd"];
const page = document.body.dataset.page;

function roleCanWrite() {
  return state.user && ["Admin", "Editor"].includes(state.user.role);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = "Request failed.";
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch (error) {}
    throw new Error(message);
  }
  if (response.headers.get("Content-Type")?.includes("application/json")) {
    return response.json();
  }
  return response;
}

function $(id) {
  return document.getElementById(id);
}

function setActiveNav() {
  document.querySelectorAll(".nav-link").forEach((link) => {
    const href = link.getAttribute("href");
    if ((page === "dashboard" && href === "/dashboard.html") ||
        (page === "cases" && href === "/cases.html") ||
        (page === "analytics" && href === "/analytics.html") ||
        (page === "settings" && href === "/settings.html")) {
      link.classList.add("active");
    }
  });
}

function bindLogout() {
  const button = $("logoutBtn");
  if (!button) return;
  button.addEventListener("click", async () => {
    await api("/api/logout", { method: "POST", body: "{}" });
    window.location.href = "/";
  });
}

function fillUserBadge() {
  const badge = $("userBadge");
  if (badge && state.user) {
    badge.textContent = `${state.user.full_name} | ${state.user.role}`;
  }
}

function setSelectOptions(select, values, includeAll = true) {
  if (!select) return;
  const options = values.map((value) => `<option value="${value}">${value}</option>`).join("");
  select.innerHTML = includeAll ? `<option value="">All</option>${options}` : options;
}

function buildQueryFromForm(form) {
  const params = new URLSearchParams();
  if (!form) return "";
  for (const [key, value] of new FormData(form).entries()) {
    if (String(value).trim()) {
      params.set(key, value);
    }
  }
  return params.toString();
}

function metricCard(label, value) {
  return `<article class="metric-card"><span class="muted">${label}</span><strong>${value}</strong></article>`;
}

function renderMetrics(target, summary) {
  if (!target || !summary) return;
  target.innerHTML = [
    metricCard("Total Cases", summary.total_cases),
    metricCard("Open Cases", summary.open_cases),
    metricCard("Overdue", summary.overdue_cases),
    metricCard("Due in 7 Days", summary.due_within_7_days),
  ].join("");
}

function renderDonut(targetId, data) {
  const target = $(targetId);
  if (!target) return;
  const total = data.reduce((sum, item) => sum + item.value, 0);
  if (!total) {
    target.innerHTML = `<p class="muted">No data available.</p>`;
    return;
  }

  let cursor = 0;
  const stops = data.map((item, index) => {
    const start = Math.round((cursor / total) * 100);
    cursor += item.value;
    const end = Math.round((cursor / total) * 100);
    return `${palette[index % palette.length]} ${start}% ${end}%`;
  });

  target.innerHTML = `
    <div class="donut-shell" style="background: conic-gradient(${stops.join(", ")});">
      <div class="donut-center"><strong>${total}</strong><div class="muted">cases</div></div>
    </div>
    <div class="chart-legend">
      ${data.map((item, index) => `
        <div class="legend-item">
          <span><span class="swatch" style="background:${palette[index % palette.length]}"></span>${item.label}</span>
          <strong>${item.value}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function renderBars(targetId, data, gradient = false) {
  const target = $(targetId);
  if (!target) return;
  const max = Math.max(...data.map((item) => item.value), 0);
  if (!max) {
    target.innerHTML = `<p class="muted">No data available.</p>`;
    return;
  }

  const wrapClass = gradient ? "timeline-bars" : "chart-bars";
  const rowClass = gradient ? "timeline-row" : "bar-row";
  const trackClass = gradient ? "timeline-track" : "bar-track";
  const fillClass = gradient ? "timeline-fill" : "bar-fill";

  target.innerHTML = `
    <div class="${wrapClass}">
      ${data.map((item, index) => `
        <div class="${rowClass}">
          <span>${item.label}</span>
          <div class="${trackClass}">
            <div class="${fillClass}" style="width:${(item.value / max) * 100}%; background:${gradient ? `linear-gradient(90deg, ${palette[index % palette.length]}, #d6fff5)` : palette[index % palette.length]}"></div>
          </div>
          <strong>${item.value}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function statusBadge(status) {
  const map = {
    "Resolved": "rgba(87, 217, 188, 0.15)",
    "Dropped": "rgba(255, 127, 150, 0.14)",
    "In-progress": "rgba(92, 192, 255, 0.15)",
    "New": "rgba(255, 191, 105, 0.15)",
    "Impasse": "rgba(143, 140, 255, 0.16)",
    "Hold": "rgba(255, 255, 255, 0.08)",
  };
  return `<span class="badge" style="background:${map[status] || "rgba(255,255,255,0.08)"}">${status}</span>`;
}

function renderCasesTable() {
  const tableBody = $("casesTableBody");
  if (!tableBody) return;
  if (!state.cases.length) {
    tableBody.innerHTML = `<tr><td colspan="9" class="muted">No cases match the current filters.</td></tr>`;
    return;
  }

  tableBody.innerHTML = state.cases.map((item) => `
    <tr data-id="${item.id}" class="${item.id === state.selectedCaseId ? "active-row" : ""}">
      <td>${item.case_id}</td>
      <td>${item.applicant}</td>
      <td>${item.complainant}</td>
      <td>${item.respondent}</td>
      <td>${item.case_type}</td>
      <td>${statusBadge(item.status)}</td>
      <td>${item.assignee || "-"}</td>
      <td>${item.due_date || "-"}</td>
      <td>${item.priority}</td>
    </tr>
  `).join("");

  tableBody.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => loadCaseDetail(Number(row.dataset.id)));
  });
}

function renderComments(comments) {
  const target = $("commentsList");
  if (!target) return;
  target.innerHTML = comments.length ? comments.map((comment) => `
    <article class="feed-card">
      <div>
        <p>${comment.body}</p>
        <small class="muted">${comment.author_name} | ${comment.created_at.replace("T", " ")}</small>
      </div>
    </article>
  `).join("") : `<p class="muted">No comments yet.</p>`;
}

function renderSubtasks(subtasks) {
  const target = $("subtasksList");
  if (!target) return;
  target.innerHTML = subtasks.length ? subtasks.map((task) => `
    <article class="subtask-item">
      <div>
        <p><strong>${task.title}</strong></p>
        <small class="muted">${task.assignee || "Unassigned"}${task.due_date ? ` | due ${task.due_date}` : ""}</small>
      </div>
      <label><input type="checkbox" data-subtask="${task.id}" ${task.is_done ? "checked" : ""}>Done</label>
    </article>
  `).join("") : `<p class="muted">No subtasks yet.</p>`;

  target.querySelectorAll("input[data-subtask]").forEach((checkbox) => {
    checkbox.disabled = !roleCanWrite();
    checkbox.addEventListener("change", async () => {
      const task = state.currentDetail.subtasks.find((item) => item.id === Number(checkbox.dataset.subtask));
      if (!task) return;
      try {
        const result = await api(`/api/cases/${state.selectedCaseId}/subtasks/${task.id}`, {
          method: "PUT",
          body: JSON.stringify({
            title: task.title,
            due_date: task.due_date || "",
            assignee: task.assignee || "",
            is_done: checkbox.checked,
          }),
        });
        state.currentDetail = result;
        renderSubtasks(result.subtasks);
      } catch (error) {
        checkbox.checked = !checkbox.checked;
        alert(error.message);
      }
    });
  });
}

function fillCaseForm(item) {
  const caseForm = $("caseForm");
  const detailHint = $("detailHint");
  if (!caseForm) return;

  const values = item || {
    id: "",
    case_id: "",
    applicant: "",
    complainant: "",
    respondent: "",
    summary: "",
    case_type: state.meta.case_types[0],
    status: "New",
    created_date: new Date().toISOString().slice(0, 10),
    start_date: "",
    documents_link: "",
    due_date: "",
    completed_date: "",
    assignee: "",
    priority: "Medium",
  };

  for (const [key, value] of Object.entries(values)) {
    if (caseForm.elements[key]) {
      caseForm.elements[key].value = value || "";
    }
  }

  if (detailHint) {
    detailHint.textContent = item ? `Viewing ${item.case_id}` : "Create a new case.";
  }
  renderComments(state.currentDetail.comments);
  renderSubtasks(state.currentDetail.subtasks);
}

async function loadCaseDetail(caseId) {
  const result = await api(`/api/cases/${caseId}`);
  state.selectedCaseId = caseId;
  state.currentDetail = result;
  fillCaseForm(result.case);
  renderCasesTable();
}

function applyCasesPermissions() {
  const caseForm = $("caseForm");
  const commentForm = $("commentForm");
  const subtaskForm = $("subtaskForm");
  const saveMessage = $("caseFormMessage");
  const newCaseBtn = $("newCaseBtn");
  const writeEnabled = roleCanWrite();

  if (caseForm) {
    [...caseForm.elements].forEach((field) => {
      if (field.type !== "hidden") field.disabled = !writeEnabled;
    });
  }
  if (commentForm) {
    [...commentForm.elements].forEach((field) => { field.disabled = !writeEnabled; });
  }
  if (subtaskForm) {
    [...subtaskForm.elements].forEach((field) => { field.disabled = !writeEnabled; });
  }
  if (newCaseBtn) newCaseBtn.disabled = !writeEnabled;
  if (saveMessage && !writeEnabled) {
    saveMessage.textContent = "Viewer role has read-only access.";
  }
}

async function loadCaseList(query, selectFirst = true) {
  const casesPayload = await api(`/api/cases${query ? `?${query}` : ""}`);
  state.cases = casesPayload.cases;
  renderCasesTable();
  if (page === "cases") {
    if (selectFirst && state.cases.length) {
      await loadCaseDetail(state.cases[0].id);
    } else if (!state.cases.length) {
      state.selectedCaseId = null;
      state.currentDetail = { comments: [], subtasks: [] };
      fillCaseForm(null);
    }
  }
}

async function loadDashboard(query) {
  state.dashboard = await api(`/api/dashboard${query ? `?${query}` : ""}`);
  renderMetrics($("metricGrid"), state.dashboard.summary);
  renderDonut("statusChart", state.dashboard.by_status);
  renderBars("typeChart", state.dashboard.by_type);
  renderBars("assigneeChart", state.dashboard.by_assignee);
  renderBars("priorityChart", state.dashboard.by_priority);
  renderBars("timelineChart", state.dashboard.by_start_month, true);

  const recentList = $("recentCasesList");
  if (recentList) {
    const recent = (state.cases || []).slice(0, 5);
    recentList.innerHTML = recent.length ? recent.map((item) => `
      <article class="feed-card">
        <div>
          <p><strong>${item.case_id}</strong> ${statusBadge(item.status)}</p>
          <small class="muted">${item.applicant} vs ${item.respondent}</small>
        </div>
      </article>
    `).join("") : `<p class="muted">No cases available.</p>`;
  }
}

function bindFilterForm() {
  const filtersForm = $("filtersForm");
  const clearBtn = $("clearFiltersBtn");
  if (!filtersForm) return;

  filtersForm.addEventListener("input", async () => {
    const query = buildQueryFromForm(filtersForm);
    if (page === "cases") {
      await loadCaseList(query, true);
    } else if (page === "analytics") {
      await loadDashboard(query);
    }
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", async () => {
      filtersForm.reset();
      setSelectOptions(filtersForm.elements.case_type, state.meta.case_types);
      setSelectOptions(filtersForm.elements.status, state.meta.statuses);
      setSelectOptions(filtersForm.elements.priority, state.meta.priorities);
      const query = buildQueryFromForm(filtersForm);
      if (page === "cases") {
        await loadCaseList(query, true);
      } else if (page === "analytics") {
        await loadDashboard(query);
      }
    });
  }

  setSelectOptions(filtersForm.elements.case_type, state.meta.case_types);
  setSelectOptions(filtersForm.elements.status, state.meta.statuses);
  setSelectOptions(filtersForm.elements.priority, state.meta.priorities);
}

function bindCasePage() {
  const caseForm = $("caseForm");
  const commentForm = $("commentForm");
  const subtaskForm = $("subtaskForm");
  const newCaseBtn = $("newCaseBtn");
  if (!caseForm) return;

  setSelectOptions(caseForm.elements.case_type, state.meta.case_types, false);
  setSelectOptions(caseForm.elements.status, state.meta.statuses, false);
  setSelectOptions(caseForm.elements.priority, state.meta.priorities, false);
  applyCasesPermissions();

  if (newCaseBtn) {
    newCaseBtn.addEventListener("click", () => {
      state.selectedCaseId = null;
      state.currentDetail = { comments: [], subtasks: [] };
      fillCaseForm(null);
      renderCasesTable();
    });
  }

  caseForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!roleCanWrite()) return;
    const payload = Object.fromEntries(new FormData(caseForm).entries());
    const id = payload.id;
    delete payload.id;
    try {
      const result = await api(id ? `/api/cases/${id}` : "/api/cases", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      state.selectedCaseId = result.case.id;
      state.currentDetail = result;
      const message = $("caseFormMessage");
      if (message) message.textContent = `Saved ${result.case.case_id}`;
      await loadCaseList(buildQueryFromForm($("filtersForm")), false);
      fillCaseForm(result.case);
    } catch (error) {
      const message = $("caseFormMessage");
      if (message) message.textContent = error.message;
    }
  });

  commentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.selectedCaseId || !roleCanWrite()) return;
    const body = commentForm.elements.body.value.trim();
    if (!body) return;
    try {
      const result = await api(`/api/cases/${state.selectedCaseId}/comments`, {
        method: "POST",
        body: JSON.stringify({ body }),
      });
      commentForm.reset();
      state.currentDetail = result;
      renderComments(result.comments);
    } catch (error) {
      alert(error.message);
    }
  });

  subtaskForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.selectedCaseId || !roleCanWrite()) return;
    const payload = Object.fromEntries(new FormData(subtaskForm).entries());
    if (!payload.title.trim()) return;
    try {
      const result = await api(`/api/cases/${state.selectedCaseId}/subtasks`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      subtaskForm.reset();
      state.currentDetail = result;
      renderSubtasks(result.subtasks);
    } catch (error) {
      alert(error.message);
    }
  });
}

function bindAnalyticsPage() {
  const exportBtn = $("exportBtn");
  if (!exportBtn) return;
  exportBtn.addEventListener("click", () => {
    const query = buildQueryFromForm($("filtersForm"));
    window.location.href = `/api/export.csv${query ? `?${query}` : ""}`;
  });
}

function renderSettingsPage() {
  const usersList = $("usersList");
  const settingsMeta = $("settingsMeta");
  if (settingsMeta) {
    settingsMeta.innerHTML = `
      <article class="feed-card"><div><p><strong>Database</strong></p><small class="muted">SQLite-backed live sync via the application server</small></div></article>
      <article class="feed-card"><div><p><strong>Authentication</strong></p><small class="muted">Credential login with Admin, Editor, and Viewer roles</small></div></article>
      <article class="feed-card"><div><p><strong>Users in system</strong></p><small class="muted">${state.meta.users.length} accounts available</small></div></article>
    `;
  }
  if (usersList) {
    usersList.innerHTML = state.meta.users.map((user) => `
      <article class="feed-card">
        <div>
          <p><strong>${user.full_name}</strong></p>
          <small class="muted">${user.username} | ${user.role}</small>
        </div>
      </article>
    `).join("");
  }
}

async function initLoginPage() {
  const loginForm = $("loginForm");
  const loginError = $("loginError");
  const sessionNotice = $("sessionNotice");
  const sessionUserText = $("sessionUserText");
  const continueBtn = $("continueBtn");
  const signOutBtn = $("signOutBtn");
  const session = await api("/api/session");
  if (session.user && sessionNotice && sessionUserText) {
    sessionNotice.classList.remove("hidden");
    sessionUserText.textContent = `${session.user.full_name} | ${session.user.role}`;
    if (continueBtn) {
      continueBtn.addEventListener("click", () => {
        window.location.href = "/dashboard.html";
      });
    }
    if (signOutBtn) {
      signOutBtn.addEventListener("click", async () => {
        await api("/api/logout", { method: "POST", body: "{}" });
        window.location.reload();
      });
    }
  }

  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (loginError) loginError.textContent = "";
      try {
        await api("/api/login", {
          method: "POST",
          body: JSON.stringify(Object.fromEntries(new FormData(loginForm).entries())),
        });
        window.location.href = "/dashboard.html";
      } catch (error) {
        if (loginError) loginError.textContent = error.message;
      }
    });
  }
}

async function initAppPage() {
  const session = await api("/api/session");
  if (!session.user) {
    window.location.href = "/";
    return;
  }

  state.user = session.user;
  state.meta = await api("/api/meta");
  fillUserBadge();
  bindLogout();
  setActiveNav();

  if (page === "dashboard") {
    await loadCaseList("", false);
    await loadDashboard("");
  }

  if (page === "cases") {
    bindFilterForm();
    bindCasePage();
    await loadCaseList("", true);
  }

  if (page === "analytics") {
    bindFilterForm();
    bindAnalyticsPage();
    await loadDashboard("");
  }

  if (page === "settings") {
    renderSettingsPage();
  }
}

(async function bootstrap() {
  try {
    if (page === "login") {
      await initLoginPage();
      return;
    }
    await initAppPage();
  } catch (error) {
    console.error(error);
    const loginError = $("loginError");
    if (loginError) loginError.textContent = error.message;
  }
})();
