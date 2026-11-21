const API_URL = "http://localhost:8000";
const TOKEN_KEY = "budget-tracker-token";
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

let token = localStorage.getItem(TOKEN_KEY);
let currentUser = null;

function errorMessage(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return "Something went wrong.";
}

async function api(path, { method = "GET", json, form, auth = true } = {}) {
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
    res = await fetch(API_URL + path, { method, headers, body });
  } catch {
    throw new Error("Can't reach the server. Is the API running?");
  }

  // A protected endpoint rejected our token: send the user back to the login screen.
  if (res.status === 401 && auth) {
    logout("Your session expired. Please log in again.");
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

let authMode = "login";

function setAuthMode(mode) {
  authMode = mode;
  const register = mode === "register";
  $("register-fields").classList.toggle("hidden", !register);
  $("register-fields").classList.toggle("grid", register);
  $("password-hint").classList.toggle("hidden", !register);
  $("auth-submit").textContent = register ? "Create account" : "Log in";
  $("password").autocomplete = register ? "new-password" : "current-password";
  for (const [id, active] of [["tab-login", !register], ["tab-register", register]]) {
    $(id).classList.toggle("bg-white", active);
    $(id).classList.toggle("text-slate-900", active);
    $(id).classList.toggle("text-slate-500", !active);
  }
  showAuthError("");
}

function showAuthError(message) {
  $("auth-error").textContent = message;
  $("auth-error").classList.toggle("hidden", !message);
}

function showAuthScreen(message = "") {
  $("app-view").classList.add("hidden");
  $("auth-view").classList.remove("hidden");
  $("password").value = "";
  showAuthError(message);
}

function logout(message = "") {
  token = null;
  currentUser = null;
  localStorage.removeItem(TOKEN_KEY);
  setAuthMode("login");
  showAuthScreen(message);
}

$("tab-login").addEventListener("click", () => setAuthMode("login"));
$("tab-register").addEventListener("click", () => setAuthMode("register"));
$("logout").addEventListener("click", () => logout());

$("auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("email").value.trim();
  const password = $("password").value;
  const register = authMode === "register";

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
    token = result.access_token;
    localStorage.setItem(TOKEN_KEY, token);
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
  if (name === "dashboard") loadDashboardCards();
  if (name === "cards") loadCardsView();
}

document.querySelectorAll("[data-view]").forEach((btn) =>
  btn.addEventListener("click", () => showView(btn.dataset.view))
);

async function enterApp() {
  currentUser = await api("/users/me");
  $("user-name").textContent = `${currentUser.first_name} ${currentUser.last_name}`;
  loadTransactions(); // fire and forget: renders when the API responds

  const stored = localStorage.getItem(SIDEBAR_KEY);
  setSidebarCollapsed(stored === null ? window.innerWidth < 768 : stored === "true");

  $("auth-view").classList.add("hidden");
  $("app-view").classList.remove("hidden");
  const view = localStorage.getItem(VIEW_KEY);
  showView(["dashboard", "cards", "budgets"].includes(view) ? view : "dashboard");
}

/* ------------------------------------------------------------------ */
/* Dashboard (transactions live in the database, via the API)         */
/* ------------------------------------------------------------------ */

let transactions = [];

function showTransactionsError(message) {
  $("transactions-error").textContent = message;
  $("transactions-error").classList.toggle("hidden", !message);
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
/* Start                                                               */
/* ------------------------------------------------------------------ */

async function boot() {
  setAuthMode("login");
  if (!token) return showAuthScreen();
  try {
    await enterApp();
  } catch (err) {
    // A 401 already went through logout(); anything else (e.g. API down) lands here.
    if (err.message !== "Unauthorized") showAuthScreen(err.message);
  }
}

boot();
