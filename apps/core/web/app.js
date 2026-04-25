const SESSION_KEY = "marketstate_portal_session_v1";
const DEMO_EMAIL = "demo@marketstate.ai";
const supabaseClient = window.marketstateSupabase ?? null;

const mockData = {
  userId: "11111111-1111-1111-1111-111111111111",
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
    { symbol: "AMZN", price: 184.2, changePct: 0.55 },
    { symbol: "META", price: 503.76, changePct: -1.11 },
    { symbol: "GOOGL", price: 176.82, changePct: 0.27 }
  ],
  recentActivity: [
    { text: "Bought 5 NVDA @ $955.10", time: "Today 09:42" },
    { text: "Sold 3 TSLA @ $188.45", time: "Today 08:17" },
    { text: "Dividend posted: MSFT", time: "Yesterday" }
  ]
};

const state = {
  activeEmail: null,
  activeUserId: mockData.userId,
  dataSource: "mock"
};

const loginView = document.getElementById("loginView");
const dashboardView = document.getElementById("dashboardView");
const loginForm = document.getElementById("loginForm");
const loginHint = document.getElementById("loginHint");
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
const dataSourceBadge = document.getElementById("dataSourceBadge");
const watchlistForm = document.getElementById("watchlistForm");
const watchlistSymbolInput = document.getElementById("watchlistSymbolInput");
const watchlistPriceInput = document.getElementById("watchlistPriceInput");
const watchlistChangeInput = document.getElementById("watchlistChangeInput");
const watchlistSaveButton = document.getElementById("watchlistSaveButton");
const watchlistMessage = document.getElementById("watchlistMessage");

if (loginHint) {
  loginHint.textContent = supabaseClient
    ? "Supabase is connected. Login then use Watchlist Save to test live writes."
    : "Temporary mock login for GitHub Pages. Any email/password works.";
}

function setWatchlistMessage(message, type = "") {
  if (!watchlistMessage) return;
  watchlistMessage.textContent = message || "";
  watchlistMessage.className = `muted form-message ${type}`.trim();
}

function setDataSourceBadge(source) {
  if (!dataSourceBadge) return;
  const isLive = source === "supabase";
  dataSourceBadge.textContent = isLive ? "Supabase Live" : "Mock Fallback";
  dataSourceBadge.className = `source-badge ${isLive ? "live" : "mock"}`;
}

function formatActivityTime(isoString) {
  if (!isoString) return "";
  const value = new Date(isoString);
  if (Number.isNaN(value.getTime())) return "";
  return value.toLocaleString("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function mapSupabasePayloadToDashboardShape(payload) {
  if (!payload || typeof payload !== "object") return null;
  const profile = payload.profile || {};
  const snapshot = payload.snapshot || {};
  const holdings = Array.isArray(payload.holdings) ? payload.holdings : [];
  const watchlist = Array.isArray(payload.watchlist) ? payload.watchlist : [];
  const activity = Array.isArray(payload.activity) ? payload.activity : [];

  return {
    userId: profile.id || null,
    portfolioValue: Number(snapshot.total_value ?? 0),
    portfolioDeltaPct: Number(snapshot.total_return_pct ?? 0),
    cashBalance: Number(snapshot.cash_balance ?? 0),
    dayPnl: Number(snapshot.day_pnl ?? 0),
    holdings: holdings.map((row) => ({
      symbol: row.symbol,
      name: row.company_name,
      quantity: Number(row.quantity ?? 0),
      price: Number(row.price ?? 0),
      changePct: Number(row.change_pct ?? 0)
    })),
    watchlist: watchlist.map((row) => ({
      symbol: row.symbol,
      price: Number(row.price ?? 0),
      changePct: Number(row.change_pct ?? 0)
    })),
    recentActivity: activity.map((row) => ({
      text: row.activity_text,
      time: formatActivityTime(row.activity_time)
    }))
  };
}

async function fetchDashboardPayloadByEmail(email) {
  const { data, error } = await supabaseClient.rpc("ms_get_portal_payload", {
    p_email: email
  });

  if (error) {
    return { data: null, error };
  }

  const mapped = mapSupabasePayloadToDashboardShape(data);
  if (!mapped) {
    return { data: null, error: new Error("Invalid dashboard payload") };
  }

  return { data: mapped, error: null };
}

async function loadDashboardData(email) {
  if (!supabaseClient) {
    return {
      data: mockData,
      source: "mock",
      resolvedEmail: DEMO_EMAIL,
      note: "Supabase client unavailable. Showing local mock data."
    };
  }

  const primaryResult = await fetchDashboardPayloadByEmail(email);
  if (!primaryResult.error && primaryResult.data) {
    return {
      data: primaryResult.data,
      source: "supabase",
      resolvedEmail: email,
      note: ""
    };
  }

  if (email !== DEMO_EMAIL) {
    const fallbackResult = await fetchDashboardPayloadByEmail(DEMO_EMAIL);
    if (!fallbackResult.error && fallbackResult.data) {
      return {
        data: fallbackResult.data,
        source: "supabase",
        resolvedEmail: DEMO_EMAIL,
        note: `No backend profile for ${email}. Showing demo account data.`
      };
    }
  }

  const reason = primaryResult.error?.message || "RPC unavailable";
  console.warn("Supabase RPC failed. Falling back to mock data:", reason);
  return {
    data: mockData,
    source: "mock",
    resolvedEmail: DEMO_EMAIL,
    note: `Supabase unavailable (${reason}). Showing mock data.`
  };
}

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
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (_error) {
    return null;
  }
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

function renderDashboard(email, dashboardData, source) {
  const sourceData = dashboardData || mockData;
  userEmail.textContent = email;
  state.activeEmail = email;
  state.activeUserId = sourceData.userId || mockData.userId;
  state.dataSource = source;

  setDataSourceBadge(source);

  portfolioValueEl.textContent = currency(sourceData.portfolioValue);
  portfolioDeltaEl.textContent = `${signedPercent(sourceData.portfolioDeltaPct)} total return`;
  portfolioDeltaEl.className = `delta ${signedClass(sourceData.portfolioDeltaPct)}`;

  cashBalanceEl.textContent = currency(sourceData.cashBalance);
  dayPnlEl.textContent = signedCurrency(sourceData.dayPnl);
  dayPnlEl.className = `value ${signedClass(sourceData.dayPnl)}`;

  holdingsTableBody.innerHTML = "";
  sourceData.holdings.forEach((row) => {
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
  sourceData.watchlist.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>${item.symbol} ${currency(item.price)}</span>
      <strong class="${signedClass(item.changePct)}">${signedPercent(item.changePct)}</strong>
    `;
    watchlistEl.appendChild(li);
  });

  activityListEl.innerHTML = "";
  sourceData.recentActivity.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${item.text}</span><span class="muted">${item.time}</span>`;
    activityListEl.appendChild(li);
  });
}

async function showDashboard(email) {
  const { data, source, resolvedEmail, note } = await loadDashboardData(email);
  renderDashboard(email, data, source);
  loginView.classList.add("hidden");
  dashboardView.classList.remove("hidden");
  setWatchlistMessage(note, note ? "" : "");

  if (resolvedEmail && resolvedEmail !== email) {
    state.activeUserId = data.userId || mockData.userId;
  }
}

function showLogin() {
  dashboardView.classList.add("hidden");
  loginView.classList.remove("hidden");
  setWatchlistMessage("");
}

function loginWithMockSession(emailCandidate, passwordCandidate) {
  const email = (emailCandidate || "").trim() || DEMO_EMAIL;
  const password = (passwordCandidate || "").trim() || "demo-password";
  if (!password) return;
  setSession(email);
  void showDashboard(email);
}

async function saveWatchlistEntry(symbol, price, changePct) {
  const payload = {
    user_id: state.activeUserId || mockData.userId,
    symbol,
    price,
    change_pct: changePct
  };

  const { error } = await supabaseClient
    .from("ms_watchlist")
    .upsert(payload, { onConflict: "user_id,symbol" });

  if (error) {
    throw error;
  }
}

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loginWithMockSession(emailInput.value, passwordInput.value);
});

demoLoginButton.addEventListener("click", () => {
  loginWithMockSession(DEMO_EMAIL, "demo-password");
});

logoutButton.addEventListener("click", () => {
  clearSession();
  showLogin();
  passwordInput.value = "";
});

if (watchlistForm) {
  watchlistForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const symbol = (watchlistSymbolInput?.value || "").trim().toUpperCase();
    const price = Number(watchlistPriceInput?.value);
    const changePct = Number(watchlistChangeInput?.value);

    if (!symbol || Number.isNaN(price) || Number.isNaN(changePct)) {
      setWatchlistMessage("Enter symbol, price and change %.", "error");
      return;
    }

    if (!supabaseClient) {
      setWatchlistMessage("Supabase client is not configured in this build.", "error");
      return;
    }

    watchlistSaveButton.disabled = true;
    watchlistSaveButton.textContent = "Saving...";
    setWatchlistMessage("");

    try {
      await saveWatchlistEntry(symbol, price, changePct);
      await showDashboard(state.activeEmail || DEMO_EMAIL);
      setWatchlistMessage(`Saved ${symbol} to Supabase watchlist.`, "success");
      watchlistSymbolInput.value = "";
      watchlistPriceInput.value = "";
      watchlistChangeInput.value = "";
    } catch (error) {
      setWatchlistMessage(`Save failed: ${error.message}`, "error");
    } finally {
      watchlistSaveButton.disabled = false;
      watchlistSaveButton.textContent = "Save";
    }
  });
}

const existingSession = getSession();
if (existingSession?.email) {
  void showDashboard(existingSession.email);
} else {
  showLogin();
}
