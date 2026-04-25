const SESSION_KEY = "marketstate_portal_session_v1";

const mockData = {
  portfolioValue: 128430.74,
  portfolioDeltaPct: 1.84,
  cashBalance: 14220.12,
  dayPnl: 758.45,
  holdings: [
    { symbol: "AAPL", name: "Apple Inc.", quantity: 42, price: 196.21, changePct: 0.92 },
    { symbol: "MSFT", name: "Microsoft", quantity: 28, price: 431.05, changePct: 1.22 },
    { symbol: "NVDA", name: "NVIDIA", quantity: 19, price: 967.88, changePct: 2.14 },
    { symbol: "TSLA", name: "Tesla", quantity: 16, price: 183.61, changePct: -0.74 }
  ],
  watchlist: [
    { symbol: "AMZN", price: 184.20, changePct: 0.55 },
    { symbol: "META", price: 503.76, changePct: -1.11 },
    { symbol: "GOOGL", price: 176.82, changePct: 0.27 }
  ],
  recentActivity: [
    { text: "Bought 5 NVDA @ $955.10", time: "Today 09:42" },
    { text: "Sold 3 TSLA @ $188.45", time: "Today 08:17" },
    { text: "Dividend posted: MSFT", time: "Yesterday" }
  ]
};

const loginView = document.getElementById("loginView");
const dashboardView = document.getElementById("dashboardView");
const loginForm = document.getElementById("loginForm");
const emailInput = document.getElementById("emailInput");
const passwordInput = document.getElementById("passwordInput");
const demoLoginButton = document.getElementById("demoLoginButton");
const userEmail = document.getElementById("userEmail");
const logoutButton = document.getElementById("logoutButton");

const portfolioValueEl = document.getElementById("portfolioValue");
const portfolioDeltaEl = document.getElementById("portfolioDelta");
const cashBalanceEl = document.getElementById("cashBalance");
const dayPnlEl = document.getElementById("dayPnl");
const holdingsTableBody = document.getElementById("holdingsTableBody");
const watchlistEl = document.getElementById("watchlist");
const activityListEl = document.getElementById("activityList");

function currency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD"
  }).format(value);
}

function signedPercent(value) {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function signedCurrency(value) {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${currency(Math.abs(value))}`;
}

function signedClass(value) {
  return value >= 0 ? "positive" : "negative";
}

function setSession(email) {
  localStorage.setItem(SESSION_KEY, JSON.stringify({ email }));
}

function getSession() {
  const session = localStorage.getItem(SESSION_KEY);
  return session ? JSON.parse(session) : null;
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

function renderDashboard(email) {
  userEmail.textContent = email;

  portfolioValueEl.textContent = currency(mockData.portfolioValue);
  portfolioDeltaEl.textContent = `${signedPercent(mockData.portfolioDeltaPct)} total return`;
  portfolioDeltaEl.className = `delta ${signedClass(mockData.portfolioDeltaPct)}`;

  cashBalanceEl.textContent = currency(mockData.cashBalance);
  dayPnlEl.textContent = signedCurrency(mockData.dayPnl);
  dayPnlEl.className = `value ${signedClass(mockData.dayPnl)}`;

  holdingsTableBody.innerHTML = "";
  mockData.holdings.forEach((row) => {
    const value = row.quantity * row.price;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.symbol}</td>
      <td>${row.name}</td>
      <td>${row.quantity}</td>
      <td>${currency(row.price)}</td>
      <td class="${signedClass(row.changePct)}">${signedPercent(row.changePct)}</td>
      <td>${currency(value)}</td>
    `;
    holdingsTableBody.appendChild(tr);
  });

  watchlistEl.innerHTML = "";
  mockData.watchlist.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>${item.symbol} ${currency(item.price)}</span>
      <strong class="${signedClass(item.changePct)}">${signedPercent(item.changePct)}</strong>
    `;
    watchlistEl.appendChild(li);
  });

  activityListEl.innerHTML = "";
  mockData.recentActivity.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${item.text}</span><span class="muted">${item.time}</span>`;
    activityListEl.appendChild(li);
  });
}

function showDashboard(email) {
  renderDashboard(email);
  loginView.classList.add("hidden");
  dashboardView.classList.remove("hidden");
}

function showLogin() {
  dashboardView.classList.add("hidden");
  loginView.classList.remove("hidden");
}

function loginWithMockSession(emailCandidate, passwordCandidate) {
  const email = (emailCandidate || "").trim() || "demo@marketstate.ai";
  const password = (passwordCandidate || "").trim() || "demo-password";
  if (!password) return;
  setSession(email);
  showDashboard(email);
}

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loginWithMockSession(emailInput.value, passwordInput.value);
});

demoLoginButton.addEventListener("click", () => {
  loginWithMockSession("demo@marketstate.ai", "demo-password");
});

logoutButton.addEventListener("click", () => {
  clearSession();
  showLogin();
  passwordInput.value = "";
});

const existingSession = getSession();
if (existingSession?.email) {
  showDashboard(existingSession.email);
} else {
  showLogin();
}
