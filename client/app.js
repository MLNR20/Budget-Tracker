const API_URL = "http://localhost:8000";
const SIDEBAR_KEY = "budget-tracker-sidebar-collapsed";
const VIEW_KEY = "budget-tracker-view";

// Bootstrap Icons names (without "bi-") that a card can use.
const CARD_ICONS = [
  "wallet2", "cart", "house", "car-front", "lightning-charge", "cup-hot", "heart-pulse",
  "controller", "airplane", "mortarboard", "gift", "phone", "bag", "piggy-bank",
];
const DEFAULT_ICON = CARD_ICONS[0];

const $ = (id) => document.getElementById(id);

const money = (n) =>
  Number(n).toLocaleString("en-PH", { style: "currency", currency: "PHP" });

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/* ------------------------------------------------------------------ */
/* API + session                                                       */
/* ------------------------------------------------------------------ */

// The access token lives in memory only (never localStorage), so a script injected into the
// page can't read a long-lived credential. The refresh token is an HttpOnly cookie that
// JavaScript can't read at all; it is only used by refreshSession() below.
let token = null;
let currentUser = null;

function errorMessage(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return "Something went wrong.";
}

// Ask the API for a new access token using the refresh cookie.
// Resolves to "ok", "denied" (no/expired/revoked refresh token) or "offline" (API unreachable).
// Concurrent callers share one request, because each refresh token can only be used once.
let refreshInFlight = null;

function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_URL}/auth/refresh`, { method: "POST", credentials: "include" });
        if (!res.ok) return "denied";
        const data = await res.json();
        token = data.access_token;
        return "ok";
      } catch {
        return "offline";
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

async function api(path, opts = {}, retried = false) {
  const { method = "GET", json, form, auth = true } = opts;
  const headers = {};
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = new URLSearchParams(form);
  }
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    // credentials: "include" lets the browser send/store the refresh cookie across origins.
    res = await fetch(API_URL + path, { method, headers, body, credentials: "include" });
  } catch {
    throw new Error("Can't reach the server. Is the API running?");
  }

  if (res.status === 401 && auth) {
    // The access token probably expired: get a new one and retry this request once.
    if (!retried && (await refreshSession()) === "ok") return api(path, opts, true);
    // Refresh failed too, so the session is really over.
    logout("Your session expired. Please log in again.", false);
    throw new Error("Unauthorized");
  }
  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data && data.detail));
  return data;
}

/* ------------------------------------------------------------------ */
/* Login / register                                                    */
/* ------------------------------------------------------------------ */

let authMode = "login"; // "login" | "register" | "forgot" | "reset"
let resetToken = null; // from the emailed link (#reset-password=...), only ever kept in memory

const AUTH_HEADINGS = {
  forgot: ["Forgot your password?", "Enter your email and we'll send you a link to reset it."],
  reset: ["Choose a new password", "Pick a new password for your account."],
};
const AUTH_SUBMIT_LABELS = {
  login: "Log in",
  register: "Create account",
  forgot: "Send reset link",
  reset: "Set new password",
};

function setAuthMode(mode) {
  authMode = mode;
  const login = mode === "login";
  const register = mode === "register";
  const forgot = mode === "forgot";
  const reset = mode === "reset";
  const tabs = login || register;

  $("auth-tabs").classList.toggle("hidden", !tabs);
  $("auth-heading").classList.toggle("hidden", tabs);
  if (!tabs) {
    [$("auth-heading-title").textContent, $("auth-heading-text").textContent] = AUTH_HEADINGS[mode];
  }

  $("register-fields").classList.toggle("hidden", !register);
  $("register-fields").classList.toggle("grid", register);
  $("email-field").classList.toggle("hidden", reset);
  $("password-field").classList.toggle("hidden", forgot);
  $("forgot-link").classList.toggle("hidden", !login);
  $("password-hint").classList.toggle("hidden", !(register || reset));
  $("confirm-field").classList.toggle("hidden", !reset);
  $("back-to-login").classList.toggle("hidden", tabs);
  $("password-label").textContent = reset ? "New password" : "Password";
  $("auth-submit").textContent = AUTH_SUBMIT_LABELS[mode];
  $("password").autocomplete = login ? "current-password" : "new-password";

  for (const [id, active] of [["tab-login", login], ["tab-register", register]]) {
    $(id).classList.toggle("bg-white", active);
    $(id).classList.toggle("text-slate-900", active);
    $(id).classList.toggle("text-slate-500", !active);
  }
  showAuthError("");
  showAuthInfo("");
}

function showAuthError(message) {
  $("auth-error").textContent = message;
  $("auth-error").classList.toggle("hidden", !message);
}

function showAuthInfo(message) {
  $("auth-info").textContent = message;
  $("auth-info").classList.toggle("hidden", !message);
}

function showAuthScreen(message = "") {
  $("app-view").classList.add("hidden");
  $("auth-view").classList.remove("hidden");
  $("password").value = "";
  $("confirm-password").value = "";
  showAuthError(message);
}

// Drop "#reset-password=..." from the address bar so the token doesn't linger in the URL/history.
function clearResetFromUrl() {
  history.replaceState(null, "", location.pathname + location.search);
}

// notifyServer: also revoke the refresh token server-side (skipped when the server already
// rejected it). The access token can't be revoked; it simply expires within minutes.
function logout(message = "", notifyServer = true) {
  if (notifyServer) {
    fetch(`${API_URL}/auth/logout`, { method: "POST", credentials: "include" }).catch(() => {});
  }
  token = null;
  currentUser = null;
  setAuthMode("login");
  showAuthScreen(message);
}

$("tab-login").addEventListener("click", () => setAuthMode("login"));
$("tab-register").addEventListener("click", () => setAuthMode("register"));
$("logout").addEventListener("click", () => logout());
$("forgot-link").addEventListener("click", () => setAuthMode("forgot"));
$("back-to-login").addEventListener("click", () => {
  resetToken = null;
  clearResetFromUrl();
  setAuthMode("login");
});

// "Forgot password": always shows the server's neutral answer, whether or not the email exists.
async function submitForgotPassword(email) {
  if (!email) return showAuthError("Enter your email.");
  const submit = $("auth-submit");
  submit.disabled = true;
  try {
    const result = await api("/auth/forgot-password", { method: "POST", auth: false, json: { email } });
    showAuthInfo(result.detail);
  } catch (err) {
    showAuthError(err.message);
  } finally {
    submit.disabled = false;
  }
}

// "Reset password": uses the token from the emailed link; success signs out every session.
async function submitResetPassword(password) {
  if (password.length < 8) return showAuthError("Password must be at least 8 characters.");
  if (password !== $("confirm-password").value) return showAuthError("The passwords don't match.");
  const submit = $("auth-submit");
  submit.disabled = true;
  try {
    await api("/auth/reset-password", {
      method: "POST",
      auth: false,
      json: { token: resetToken, new_password: password },
    });
    resetToken = null;
    token = null;
    setAuthMode("login");
    $("password").value = "";
    $("confirm-password").value = "";
    showAuthInfo("Password updated. Log in with your new password.");
  } catch (err) {
    showAuthError(err.message);
  } finally {
    submit.disabled = false;
  }
}

$("auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("email").value.trim();
  const password = $("password").value;
  const register = authMode === "register";

  showAuthError("");
  showAuthInfo("");
  if (authMode === "forgot") return submitForgotPassword(email);
  if (authMode === "reset") return submitResetPassword(password);

  if (!email || !password) return showAuthError("Enter your email and password.");
  if (register) {
    if (!$("first-name").value.trim() || !$("last-name").value.trim()) {
      return showAuthError("Enter your first and last name.");
    }
    if (password.length < 8) return showAuthError("Password must be at least 8 characters.");
  }

  const submit = $("auth-submit");
  submit.disabled = true;
  showAuthError("");
  try {
    if (register) {
      await api("/users", {
        method: "POST",
        auth: false,
        json: {
          first_name: $("first-name").value.trim(),
          last_name: $("last-name").value.trim(),
          email,
          password,
        },
      });
    }
    const result = await api("/auth/login", {
      method: "POST",
      auth: false,
      form: { username: email, password },
    });
    token = result.access_token; // the refresh token arrived as an HttpOnly cookie
    await enterApp();
  } catch (err) {
    showAuthError(err.message);
  } finally {
    submit.disabled = false;
  }
});

/* ------------------------------------------------------------------ */
/* Sidebar + views                                                     */
/* ------------------------------------------------------------------ */

const sidebar = $("sidebar");

function setSidebarCollapsed(collapsed) {
  sidebar.dataset.collapsed = String(collapsed);
  $("sidebar-toggle").setAttribute("aria-expanded", String(!collapsed));
  localStorage.setItem(SIDEBAR_KEY, String(collapsed));
}

$("sidebar-toggle").addEventListener("click", () => {
  setSidebarCollapsed(sidebar.dataset.collapsed !== "true");
});

const NAV_ACTIVE = ["bg-blue-50", "text-blue-600"];
const NAV_INACTIVE = ["text-slate-600", "hover:bg-slate-100"];

function showView(name) {
  localStorage.setItem(VIEW_KEY, name);
  document.querySelectorAll("[data-view]").forEach((btn) => {
    const active = btn.dataset.view === name;
    btn.classList.add(...(active ? NAV_ACTIVE : NAV_INACTIVE));
    btn.classList.remove(...(active ? NAV_INACTIVE : NAV_ACTIVE));
    $("view-" + btn.dataset.view).classList.toggle("hidden", !active);
  });
  if (name === "budgets") loadBudgets();
  if (name === "dashboard") {
    loadDashboardCards();
    // Opening the dashboard also creates anything that has come due; refresh if it did.
    catchUpRecurring().then((created) => { if (created) loadTransactions(); });
  }
  if (name === "cards") loadCardsView();
  if (name === "recurring") loadRecurring();
}

document.querySelectorAll("[data-view]").forEach((btn) =>
  btn.addEventListener("click", () => showView(btn.dataset.view))
);

async function enterApp() {
  currentUser = await api("/users/me");
  $("user-name").textContent = `${currentUser.first_name} ${currentUser.last_name}`;
  await catchUpRecurring(); // create anything that came due since the last visit, before loading
  loadTransactions(); // fire and forget: renders when the API responds

  const stored = localStorage.getItem(SIDEBAR_KEY);
  setSidebarCollapsed(stored === null ? window.innerWidth < 768 : stored === "true");

  $("auth-view").classList.add("hidden");
  $("app-view").classList.remove("hidden");
  const view = localStorage.getItem(VIEW_KEY);
  showView(["dashboard", "crud", "cards", "recurring", "budgets"].includes(view) ? view : "dashboard");
}

/* ------------------------------------------------------------------ */
/* Dashboard (transactions live in the database, via the API)         */
/* ------------------------------------------------------------------ */

let transactions = [];

function showTransactionsError(message) {
  for (const id of ["transactions-error", "crud-error"]) {
    $(id).textContent = message;
    $(id).classList.toggle("hidden", !message);
  }
}

async function loadTransactions() {
  try {
    transactions = await api("/transactions");
    showTransactionsError("");
  } catch (err) {
    transactions = [];
    if (err.message !== "Unauthorized") showTransactionsError(err.message);
  }
  renderTransactions();
  loadCharts(); // transactions changed, so the aggregates did too
}

function setInvalid(input, invalid) {
  input.classList.toggle("border-red-500", invalid);
  input.nextElementSibling.classList.toggle("hidden", !invalid);
}

function renderTransactions() {
  const listEl = $("transaction-list");
  listEl.innerHTML = "";

  let income = 0;
  let expenses = 0;

  transactions.forEach((t) => {
    const amount = Number(t.amount);
    if (t.type === "income") income += amount;
    else expenses += amount;

    const sign = t.type === "income" ? "+" : "-";
    const amountColor = t.type === "income" ? "text-emerald-600" : "text-red-600";
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="py-3 pr-4">${escapeHtml(t.description)}</td>
      <td class="py-3 pr-4">
        <span class="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-600">${escapeHtml(t.category)}</span>
      </td>
      <td class="py-3 pr-4 text-slate-500">${new Date(t.date_created).toLocaleDateString()}</td>
      <td class="py-3 pr-4 text-right font-medium ${amountColor}">${sign}${money(amount)}</td>
      <td class="py-3 text-right">
        <button class="btn-icon" data-id="${t.id}" aria-label="Delete"><i class="bi bi-x-lg"></i></button>
      </td>`;
    listEl.appendChild(row);
  });

  $("income").textContent = money(income);
  $("expenses").textContent = money(expenses);
  $("balance").textContent = money(income - expenses);
  $("balance").classList.toggle("text-red-600", income - expenses < 0);
  $("empty-state").classList.toggle("hidden", transactions.length > 0);
}

$("transaction-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;

  const descriptionInput = $("description");
  const amountInput = $("amount");
  const description = descriptionInput.value.trim();
  const amount = amountInput.value;

  setInvalid(descriptionInput, !description);
  setInvalid(amountInput, !(Number(amount) > 0));
  if (!description || !(Number(amount) > 0)) return;

  try {
    await api("/transactions", {
      method: "POST",
      json: { description, amount, type: $("type").value, category: $("category").value },
    });
    form.reset();
    await loadTransactions();
  } catch (err) {
    if (err.message !== "Unauthorized") showTransactionsError(err.message);
  }
});

$("transaction-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-id]");
  if (!btn) return;
  try {
    await api(`/transactions/${btn.dataset.id}`, { method: "DELETE" });
    await loadTransactions();
  } catch (err) {
    if (err.message !== "Unauthorized") showTransactionsError(err.message);
  }
});

$("clear-all").addEventListener("click", async () => {
  if (!transactions.length || !confirm("Delete all transactions?")) return;
  try {
    await api("/transactions", { method: "DELETE" });
    await loadTransactions();
  } catch (err) {
    if (err.message !== "Unauthorized") showTransactionsError(err.message);
  }
});

/* ------------------------------------------------------------------ */
/* Charts (pie, bar, line). Numbers come from GET /analytics, which    */
/* aggregates and filters on the server.                               */
/* ------------------------------------------------------------------ */

const CHART_COLORS = [
  "#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#64748b",
];

const charts = { pie: null, bar: null, line: null };
let chartsRequestId = 0; // so a slow, older response can't overwrite a newer one

function showChartsError(message) {
  $("charts-error").textContent = message;
  $("charts-error").classList.toggle("hidden", !message);
}

function chartFilterParams() {
  const params = new URLSearchParams({
    type: $("filter-type").value,
    group_by: $("filter-group").value,
    // Minutes east of UTC, so "today" on the server means today for this user.
    tz_offset_minutes: String(-new Date().getTimezoneOffset()),
  });
  if ($("filter-category").value) params.set("category", $("filter-category").value);
  if ($("filter-from").value) params.set("date_from", $("filter-from").value);
  if ($("filter-to").value) params.set("date_to", $("filter-to").value);
  return params;
}

// Keep the category dropdown in sync with the categories the user has actually used.
function fillCategoryFilter(categories) {
  const select = $("filter-category");
  const selected = select.value;
  select.innerHTML =
    `<option value="">All categories</option>` +
    categories.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
  select.value = categories.includes(selected) ? selected : "";
}

function formatPeriod(period) {
  const [y, m, d] = period.split("-").map(Number);
  return d
    ? new Date(y, m - 1, d).toLocaleDateString(undefined, { month: "short", day: "numeric" })
    : new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

// Create the chart on first use, then just swap its data.
function upsertChart(key, canvasId, config) {
  if (!window.Chart) return; // CDN blocked/offline: the rest of the dashboard still works
  if (charts[key]) {
    charts[key].data = config.data;
    charts[key].options = config.options;
    charts[key].update();
  } else {
    charts[key] = new Chart($(canvasId), config);
  }
}

function renderCharts(data) {
  const hasData = data.count > 0;
  $("charts-empty").classList.toggle("hidden", hasData);
  for (const id of ["chart-pie", "chart-bar", "chart-line"]) {
    $(id).parentElement.classList.toggle("invisible", !hasData);
  }

  const typeLabel = { expense: "Expenses", income: "Income", all: "Transactions" }[$("filter-type").value];
  $("line-title").textContent = `${typeLabel} over time (${$("filter-group").value === "month" ? "monthly" : "daily"})`;

  const labels = data.by_category.map((c) => c.category);
  const totals = data.by_category.map((c) => Number(c.total));
  const colors = labels.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);
  const moneyTick = (v) => money(v);

  upsertChart("pie", "chart-pie", {
    type: "pie",
    data: { labels, datasets: [{ data: totals, backgroundColor: colors }] },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right" },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${money(ctx.parsed)} (${data.by_category[ctx.dataIndex].percent}%)`,
          },
        },
      },
    },
  });

  upsertChart("bar", "chart-bar", {
    type: "bar",
    data: { labels, datasets: [{ label: typeLabel, data: totals, backgroundColor: colors }] },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => ` ${money(ctx.parsed.y)}` } },
      },
      scales: { y: { beginAtZero: true, ticks: { callback: moneyTick } } },
    },
  });

  upsertChart("line", "chart-line", {
    type: "line",
    data: {
      labels: data.over_time.map((p) => formatPeriod(p.period)),
      datasets: [
        {
          label: typeLabel,
          data: data.over_time.map((p) => Number(p.total)),
          borderColor: CHART_COLORS[0],
          backgroundColor: "rgba(37, 99, 235, 0.12)",
          fill: true,
          tension: 0.25,
          pointRadius: data.over_time.length > 45 ? 0 : 3,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => ` ${money(ctx.parsed.y)}` } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { callback: moneyTick } },
        x: { ticks: { maxTicksLimit: 12, maxRotation: 0 } },
      },
    },
  });
}

async function loadCharts() {
  const requestId = ++chartsRequestId;
  try {
    const data = await api(`/analytics?${chartFilterParams()}`);
    if (requestId !== chartsRequestId) return;
    showChartsError("");
    fillCategoryFilter(data.categories);
    renderCharts(data);
  } catch (err) {
    if (requestId === chartsRequestId && err.message !== "Unauthorized") showChartsError(err.message);
  }
}

$("chart-filters").addEventListener("change", loadCharts);
$("chart-filters").addEventListener("submit", (e) => e.preventDefault());
$("filter-reset").addEventListener("click", () => {
  $("chart-filters").reset();
  loadCharts();
});

/* ------------------------------------------------------------------ */
/* Budgets + cards (protected API)                                     */
/* ------------------------------------------------------------------ */

function showBudgetsError(message) {
  $("budgets-error").textContent = message;
  $("budgets-error").classList.toggle("hidden", !message);
}

const safeIcon = (icon) => (CARD_ICONS.includes(icon) ? icon : DEFAULT_ICON);

async function loadBudgets() {
  try {
    const [budgets, cards] = await Promise.all([api("/budgets"), api("/cards")]);
    showBudgetsError("");
    renderBudgets(budgets, cards);
  } catch (err) {
    if (err.message !== "Unauthorized") showBudgetsError(err.message);
  }
}

function iconPicker(budgetId) {
  return CARD_ICONS.map(
    (icon, i) => `
      <label class="cursor-pointer" title="${icon}">
        <input type="radio" name="icon" value="${icon}" class="peer sr-only" ${i === 0 ? "checked" : ""} />
        <span class="flex size-9 items-center justify-center rounded-lg border border-slate-300 text-slate-500 peer-checked:border-blue-500 peer-checked:bg-blue-50 peer-checked:text-blue-600 peer-focus-visible:ring-2 peer-focus-visible:ring-blue-300">
          <i class="bi bi-${icon}"></i>
        </span>
      </label>`
  ).join("");
}

// An icon tile for one card. On the dashboard it is read-only and shows its budget's name.
function cardHtml(card, budgetTotal, { readOnly = false, editable = false, budgetName = "" } = {}) {
  const share = budgetTotal > 0 ? Math.round((Number(card.amount) / budgetTotal) * 100) : 0;
  const caption = budgetName ? `${escapeHtml(budgetName)} &middot; ${share}%` : `${share}% of budget`;
  const editBtn = editable
    ? `<button type="button" class="btn-icon" data-edit-card="${card.id}" aria-label="Edit card"><i class="bi bi-pencil"></i></button>`
    : "";
  const actions = readOnly
    ? ""
    : `<div class="absolute right-3 top-3 flex gap-1">
        ${editBtn}
        <button type="button" class="btn-icon" data-delete-card="${card.id}" aria-label="Delete card"><i class="bi bi-x-lg"></i></button>
      </div>`;
  return `
    <li class="relative rounded-2xl border border-slate-200 bg-white p-4">
      ${actions}
      <span class="mb-3 flex size-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
        <i class="bi bi-${safeIcon(card.icon)} text-3xl"></i>
      </span>
      <p class="truncate font-medium">${escapeHtml(card.name)}</p>
      <p class="text-lg font-semibold">${money(card.amount)}</p>
      <p class="truncate text-xs text-slate-500">${caption}</p>
    </li>`;
}

function renderDashboardCards(budgets, cards) {
  const budgetById = new Map(budgets.map((b) => [b.id, b]));
  $("dashboard-cards").innerHTML = cards
    .map((c) => {
      const budget = budgetById.get(c.budget_id);
      return cardHtml(c, budget ? Number(budget.current_amount) : 0, {
        readOnly: true,
        budgetName: budget ? budget.name : "",
      });
    })
    .join("");
  $("dashboard-cards-empty").classList.toggle("hidden", cards.length > 0);
}

async function loadDashboardCards() {
  try {
    const [budgets, cards] = await Promise.all([api("/budgets"), api("/cards")]);
    renderDashboardCards(budgets, cards);
  } catch (err) {
    if (err.message !== "Unauthorized") showTransactionsError(err.message);
  }
}

function budgetHtml(budget, cards) {
  const total = Number(budget.current_amount);
  const allocated = cards.reduce((sum, c) => sum + Number(c.amount), 0);
  const remaining = Math.round((total - allocated) * 100) / 100;
  const pct = total > 0 ? Math.min(100, (allocated / total) * 100) : 0;

  return `
    <article class="panel">
      <div class="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 class="text-lg font-semibold">${escapeHtml(budget.name)}</h3>
          <p class="text-2xl font-semibold text-blue-600">${money(total)}</p>
        </div>
        <button type="button" class="btn-outline-danger" data-delete-budget="${budget.id}">
          <i class="bi bi-trash mr-1"></i>Delete
        </button>
      </div>

      <div class="mb-1 h-2 overflow-hidden rounded-full bg-slate-100">
        <div class="h-full rounded-full bg-blue-500" style="width: ${pct}%"></div>
      </div>
      <p class="mb-3 text-sm text-slate-500">${money(allocated)} split into cards &middot; ${money(remaining)} left</p>

      ${cards.length ? `<ul class="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">${cards.map((c) => cardHtml(c, total)).join("")}</ul>` : ""}

      <form data-budget-id="${budget.id}" novalidate class="rounded-xl bg-slate-50 p-3">
        <p class="mb-2 text-sm font-medium">Split into a card</p>
        <div class="mb-3 flex flex-wrap gap-2">${iconPicker(budget.id)}</div>
        <div class="grid items-end gap-3 sm:grid-cols-[1fr_10rem_auto]">
          <input name="card-name" type="text" maxlength="100" placeholder="Card name" aria-label="Card name" class="input" />
          <input name="card-amount" type="number" min="0.01" step="0.01" placeholder="0.00" aria-label="Card amount" class="input" />
          <button type="submit" class="btn-primary"><i class="bi bi-plus-lg mr-1"></i>Add card</button>
        </div>
      </form>
    </article>`;
}

function renderBudgets(budgets, cards) {
  $("budget-list").innerHTML = budgets
    .map((b) => budgetHtml(b, cards.filter((c) => c.budget_id === b.id)))
    .join("");
  $("budgets-empty").classList.toggle("hidden", budgets.length > 0);
}

$("budget-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = $("budget-name").value.trim();
  const amount = $("budget-amount").value || "0";
  if (!name) return showBudgetsError("Enter a budget name.");
  if (Number(amount) < 0) return showBudgetsError("Amount can't be negative.");

  try {
    await api("/budgets", { method: "POST", json: { name, current_amount: amount } });
    e.target.reset();
    await loadBudgets();
  } catch (err) {
    if (err.message !== "Unauthorized") showBudgetsError(err.message);
  }
});

$("budget-list").addEventListener("submit", async (e) => {
  const form = e.target.closest("form[data-budget-id]");
  if (!form) return;
  e.preventDefault();

  const name = form.elements["card-name"].value.trim();
  const amount = form.elements["card-amount"].value;
  if (!name) return showBudgetsError("Enter a card name.");
  if (!(Number(amount) > 0)) return showBudgetsError("Enter a card amount greater than 0.");

  try {
    await api("/cards", {
      method: "POST",
      json: {
        budget_id: Number(form.dataset.budgetId),
        name,
        amount,
        icon: form.elements.icon.value,
      },
    });
    await loadBudgets();
  } catch (err) {
    if (err.message !== "Unauthorized") showBudgetsError(err.message);
  }
});

$("budget-list").addEventListener("click", async (e) => {
  const budgetBtn = e.target.closest("[data-delete-budget]");
  const cardBtn = e.target.closest("[data-delete-card]");
  if (!budgetBtn && !cardBtn) return;

  if (budgetBtn && !confirm("Delete this budget and all of its cards?")) return;
  const path = budgetBtn
    ? `/budgets/${budgetBtn.dataset.deleteBudget}`
    : `/cards/${cardBtn.dataset.deleteCard}`;

  try {
    await api(path, { method: "DELETE" });
    await loadBudgets();
  } catch (err) {
    if (err.message !== "Unauthorized") showBudgetsError(err.message);
  }
});

/* ------------------------------------------------------------------ */
/* Cards view: create / read / update / delete                         */
/* ------------------------------------------------------------------ */

const cardsState = { budgets: [], cards: [], editingId: null };

function showCardsError(message) {
  $("cards-error").textContent = message;
  $("cards-error").classList.toggle("hidden", !message);
}

function showCardFormError(message) {
  $("card-form-error").textContent = message;
  $("card-form-error").classList.toggle("hidden", !message);
}

function renderCardsView() {
  const { budgets, cards } = cardsState;
  const budgetById = new Map(budgets.map((b) => [b.id, b]));

  $("card-list").innerHTML = cards
    .map((c) => {
      const budget = budgetById.get(c.budget_id);
      return cardHtml(c, budget ? Number(budget.current_amount) : 0, {
        editable: true,
        budgetName: budget ? budget.name : "",
      });
    })
    .join("");

  const empty = $("cards-empty");
  empty.classList.toggle("hidden", cards.length > 0);
  empty.textContent = budgets.length
    ? "No cards yet. Click New card to split one of your budgets."
    : "Create a budget first, then split it into cards.";
  $("new-card-btn").disabled = budgets.length === 0;
  $("new-card-btn").classList.toggle("opacity-50", budgets.length === 0);
}

async function loadCardsView() {
  try {
    const [budgets, cards] = await Promise.all([api("/budgets"), api("/cards")]);
    cardsState.budgets = budgets;
    cardsState.cards = cards;
    showCardsError("");
    renderCardsView();
  } catch (err) {
    if (err.message !== "Unauthorized") showCardsError(err.message);
  }
}

// How much of the selected budget is still unsplit (ignoring the card being edited).
function updateCardBudgetHint() {
  const budgetId = Number($("card-budget").value);
  const budget = cardsState.budgets.find((b) => b.id === budgetId);
  if (!budget) {
    $("card-budget-hint").textContent = "";
    return;
  }
  const allocated = cardsState.cards
    .filter((c) => c.budget_id === budgetId && c.id !== cardsState.editingId)
    .reduce((sum, c) => sum + Number(c.amount), 0);
  const left = Math.round((Number(budget.current_amount) - allocated) * 100) / 100;
  $("card-budget-hint").textContent = `${money(left)} left to split in ${budget.name}.`;
}

function openCardForm(card = null) {
  cardsState.editingId = card ? card.id : null;
  showCardFormError("");

  $("card-form-title").textContent = card ? "Edit card" : "New card";
  $("card-save").textContent = card ? "Save changes" : "Create card";
  $("card-form-icons").innerHTML = iconPicker();

  $("card-budget").innerHTML = cardsState.budgets
    .map((b) => `<option value="${b.id}">${escapeHtml(b.name)}</option>`)
    .join("");
  // The API doesn't move a card between budgets, so the budget is fixed once created.
  $("card-budget").disabled = Boolean(card);

  $("card-form-name").value = card ? card.name : "";
  $("card-form-amount").value = card ? card.amount : "";
  if (card) {
    $("card-budget").value = String(card.budget_id);
    const radio = $("card-form").querySelector(`input[name=icon][value="${safeIcon(card.icon)}"]`);
    if (radio) radio.checked = true;
  }

  updateCardBudgetHint();
  $("card-form").classList.remove("hidden");
  $("card-form-name").focus();
}

function closeCardForm() {
  cardsState.editingId = null;
  $("card-form").classList.add("hidden");
}

$("new-card-btn").addEventListener("click", () => openCardForm());
$("card-cancel").addEventListener("click", closeCardForm);
$("card-budget").addEventListener("change", updateCardBudgetHint);

$("card-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = $("card-form-name").value.trim();
  const amount = $("card-form-amount").value;
  const icon = $("card-form").elements.icon.value;

  if (!name) return showCardFormError("Enter a card name.");
  if (!(Number(amount) > 0)) return showCardFormError("Enter an amount greater than 0.");

  const editing = cardsState.editingId;
  $("card-save").disabled = true;
  try {
    if (editing) {
      await api(`/cards/${editing}`, { method: "PATCH", json: { name, amount, icon } });
    } else {
      await api("/cards", {
        method: "POST",
        json: { budget_id: Number($("card-budget").value), name, amount, icon },
      });
    }
    closeCardForm();
    await loadCardsView();
  } catch (err) {
    // e.g. the 422 "Not enough left in budget to split" message from the server
    if (err.message !== "Unauthorized") showCardFormError(err.message);
  } finally {
    $("card-save").disabled = false;
  }
});

$("card-list").addEventListener("click", async (e) => {
  const editBtn = e.target.closest("[data-edit-card]");
  const deleteBtn = e.target.closest("[data-delete-card]");

  if (editBtn) {
    const card = cardsState.cards.find((c) => c.id === Number(editBtn.dataset.editCard));
    if (card) {
      openCardForm(card);
      $("card-form").scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    return;
  }

  if (deleteBtn && confirm("Delete this card? Its amount goes back to the budget.")) {
    try {
      await api(`/cards/${deleteBtn.dataset.deleteCard}`, { method: "DELETE" });
      await loadCardsView();
    } catch (err) {
      if (err.message !== "Unauthorized") showCardsError(err.message);
    }
  }
});

/* ------------------------------------------------------------------ */
/* Recurring transactions (lazy catch-up: no scheduler)                */
/* ------------------------------------------------------------------ */

// Ask the server to create everything that has come due. It's idempotent, so calling it again
// just returns 0. Throttled so login + opening the dashboard don't fire it twice in a row.
let lastCatchUp = 0;

async function catchUpRecurring() {
  if (Date.now() - lastCatchUp < 5000) return 0;
  lastCatchUp = Date.now();
  try {
    const result = await api("/recurring/process", { method: "POST" });
    return result.created;
  } catch {
    return 0; // never block the app on this; the next visit retries
  }
}

const FREQUENCY_LABELS = { daily: "Daily", weekly: "Weekly", monthly: "Monthly", yearly: "Yearly" };

function showRecurringError(message) {
  $("recurring-error").textContent = message;
  $("recurring-error").classList.toggle("hidden", !message);
}

function showRecurringInfo(message) {
  $("recurring-info").textContent = message;
  $("recurring-info").classList.toggle("hidden", !message);
}

// "2026-07-01" -> a local Date (avoids new Date("2026-07-01") parsing it as UTC midnight)
function isoToDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}
const formatDay = (iso) =>
  isoToDate(iso).toLocaleDateString("en-PH", { year: "numeric", month: "short", day: "numeric" });

function todayIso() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function recurringHtml(rule) {
  const ended = rule.end_date && rule.next_run_date > rule.end_date;
  const status = ended
    ? `<span class="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">Ended</span>`
    : !rule.is_active
      ? `<span class="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">Paused</span>`
      : `<span class="text-xs text-slate-500">Next: ${formatDay(rule.next_run_date)}</span>`;
  const income = rule.type === "income";
  const toggle = ended
    ? ""
    : `<button type="button" class="btn-icon" data-toggle-rule="${rule.id}" data-active="${rule.is_active}"
         aria-label="${rule.is_active ? "Pause" : "Resume"}" title="${rule.is_active ? "Pause" : "Resume"}">
         <i class="bi bi-${rule.is_active ? "pause-fill" : "play-fill"}"></i>
       </button>`;
  const until = rule.end_date ? ` &middot; until ${formatDay(rule.end_date)}` : "";

  return `
    <li class="panel flex items-center gap-4 ${rule.is_active || ended ? "" : "opacity-70"}">
      <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
        <i class="bi bi-arrow-repeat text-xl"></i>
      </span>
      <div class="min-w-0 flex-1">
        <p class="truncate font-medium">${escapeHtml(rule.description)}</p>
        <p class="truncate text-xs text-slate-500">
          ${FREQUENCY_LABELS[rule.frequency]} &middot; ${escapeHtml(rule.category)}${until}
        </p>
      </div>
      <div class="hidden text-right sm:block">${status}</div>
      <p class="font-semibold ${income ? "text-emerald-600" : "text-red-600"}">
        ${income ? "+" : "-"}${money(rule.amount)}
      </p>
      <div class="flex gap-1">
        ${toggle}
        <button type="button" class="btn-icon" data-delete-rule="${rule.id}" aria-label="Delete" title="Delete">
          <i class="bi bi-trash"></i>
        </button>
      </div>
    </li>`;
}

async function loadRecurring() {
  try {
    const rules = await api("/recurring");
    showRecurringError("");
    $("recurring-list").innerHTML = rules.map(recurringHtml).join("");
    $("recurring-empty").classList.toggle("hidden", rules.length > 0);
  } catch (err) {
    if (err.message !== "Unauthorized") showRecurringError(err.message);
  }
}

if (!$("rec-start").value) $("rec-start").value = todayIso();

$("recurring-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const description = $("rec-description").value.trim();
  const amount = $("rec-amount").value;
  const start = $("rec-start").value;
  const end = $("rec-end").value;

  showRecurringInfo("");
  if (!description) return showRecurringError("Enter a description.");
  if (!(Number(amount) > 0)) return showRecurringError("Enter an amount greater than 0.");
  if (!start) return showRecurringError("Pick a start date.");
  if (end && end < start) return showRecurringError("The end date can't be before the start date.");

  try {
    const rule = await api("/recurring", {
      method: "POST",
      json: {
        description,
        amount,
        type: $("rec-type").value,
        category: $("rec-category").value,
        frequency: $("rec-frequency").value,
        start_date: start,
        end_date: end || null,
      },
    });
    e.target.reset();
    $("rec-start").value = todayIso();
    showRecurringError("");
    if (rule.occurrences_generated > 0) {
      const n = rule.occurrences_generated;
      showRecurringInfo(`Added ${n} transaction${n === 1 ? "" : "s"} so far for "${rule.description}".`);
    }
    await loadRecurring();
    loadTransactions(); // any backfilled transactions now exist
  } catch (err) {
    if (err.message !== "Unauthorized") showRecurringError(err.message);
  }
});

$("recurring-list").addEventListener("click", async (e) => {
  const toggleBtn = e.target.closest("[data-toggle-rule]");
  const deleteBtn = e.target.closest("[data-delete-rule]");
  try {
    if (toggleBtn) {
      const resume = toggleBtn.dataset.active !== "true";
      await api(`/recurring/${toggleBtn.dataset.toggleRule}`, {
        method: "PATCH",
        json: { is_active: resume },
      });
      showRecurringInfo(resume ? "Resumed. Anything missed while it was paused is skipped." : "");
      await loadRecurring();
    } else if (
      deleteBtn &&
      confirm("Delete this recurring rule? Transactions it already created are kept.")
    ) {
      await api(`/recurring/${deleteBtn.dataset.deleteRule}`, { method: "DELETE" });
      showRecurringInfo("");
      await loadRecurring();
    }
  } catch (err) {
    if (err.message !== "Unauthorized") showRecurringError(err.message);
  }
});

/* ------------------------------------------------------------------ */
/* Start                                                               */
/* ------------------------------------------------------------------ */

async function boot() {
  setAuthMode("login");
  // Tokens used to live in localStorage; drop any leftover from the older version.
  localStorage.removeItem("budget-tracker-token");

  // Opened from a password-reset email: show the new-password form instead of signing in.
  const resetLink = location.hash.match(/^#reset-password=(.+)$/);
  if (resetLink) {
    resetToken = decodeURIComponent(resetLink[1]);
    clearResetFromUrl();
    setAuthMode("reset");
    return showAuthScreen();
  }

  // No access token survives a page reload (it's memory-only), so try the refresh cookie:
  // if it is still valid the user is silently signed back in.
  const result = await refreshSession();
  if (result === "offline") return showAuthScreen("Can't reach the server. Is the API running?");
  if (result !== "ok") return showAuthScreen();
  try {
    await enterApp();
  } catch (err) {
    // A 401 already went through logout(); anything else (e.g. API down) lands here.
    if (err.message !== "Unauthorized") showAuthScreen(err.message);
  }
}

boot();
