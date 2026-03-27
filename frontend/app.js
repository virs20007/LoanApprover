/* ============================================================
   app.js — Investment Planner Agent frontend logic
   ============================================================ */

const API_BASE = "http://localhost:8000";

// Asset colour map (must stay in sync with style.css)
const ASSET_COLORS = {
  "Stocks":                 "#ef4444",
  "Bonds":                  "#22c55e",
  "Cash":                   "#3b82f6",
  "Real Estate":            "#f97316",
  "Commodities":            "#a855f7",
  "Alternative Investments":"#94a3b8",
};

let pieChart = null;   // Chart.js instance — destroyed & recreated on each request
let cachedRequest = null; // cached for report download

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const form            = document.getElementById("investment-form");
const formError       = document.getElementById("form-error");
const submitBtn       = document.getElementById("submit-btn");
const btnText         = submitBtn.querySelector(".btn-text");
const spinner         = document.getElementById("spinner");
const resultsSection  = document.getElementById("results-section");
const downloadBtn     = document.getElementById("download-btn");
const downloadBtnText = downloadBtn.querySelector(".btn-download-text");
const downloadSpinner = document.getElementById("download-spinner");
const downloadError   = document.getElementById("download-error");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function getCurrencySymbol(country) {
  const map = {
    us: "$", canada: "$", india: "₹", uk: "£",
    "new zealand": "NZ$", netherlands: "€",
    germany: "€", france: "€", australia: "A$",
  };
  return map[country] || "$";
}

function fmt(num, decimals = 2) {
  return Number(num).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  spinner.classList.toggle("hidden", !isLoading);
  btnText.textContent = isLoading ? "Calculating…" : "Get My Investment Plan";
}

function setDownloadLoading(isLoading) {
  downloadBtn.disabled = isLoading;
  downloadSpinner.classList.toggle("hidden", !isLoading);
  downloadBtnText.textContent = isLoading ? "Generating PDF…" : "Download PDF Report";
}

function showError(msg) {
  formError.textContent = msg;
  formError.classList.remove("hidden");
  formError.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function hideError() {
  formError.textContent = "";
  formError.classList.add("hidden");
}

function showDownloadError(msg) {
  downloadError.textContent = msg;
  downloadError.classList.remove("hidden");
}

function hideDownloadError() {
  downloadError.textContent = "";
  downloadError.classList.add("hidden");
}

// ---------------------------------------------------------------------------
// Form validation
// ---------------------------------------------------------------------------
function validateForm(data) {
  if (!data.country)        return "Please select your country.";
  if (!data.age || data.age <= 0)
                            return "Please enter a valid age (must be > 0).";
  if (data.monthly_income < 0)
                            return "Monthly income cannot be negative.";
  if (data.monthly_expenses < 0)
                            return "Monthly expenses cannot be negative.";
  if (data.monthly_expenses > data.monthly_income)
                            return "Monthly expenses cannot exceed monthly income.";
  if (!data.risk_level)     return "Please select a risk level.";
  if (!data.financial_goal) return "Please select your financial goal.";
  return null;
}

// ---------------------------------------------------------------------------
// Render results
// ---------------------------------------------------------------------------
function renderResults(data, currency) {
  // Summary cards
  document.getElementById("total-amount").textContent =
    `${currency}${fmt(data.total_investable_amount)}`;
  document.getElementById("exp-return").textContent =
    `${fmt(data.expected_annual_return)}%`;
  document.getElementById("exp-vol").textContent =
    `${fmt(data.expected_annual_volatility)}%`;
  document.getElementById("sharpe").textContent =
    fmt(data.sharpe_ratio, 3);

  // Data source badge
  const badge = document.getElementById("data-source-badge");
  if (data.market_data_source === "live") {
    badge.textContent = "🟢 Live market data";
    badge.className = "data-source-badge badge-live";
  } else {
    badge.textContent = "🟡 Simulated data (fallback)";
    badge.className = "data-source-badge badge-fallback";
  }

  renderPieChart(data.allocation);
  renderAllocationTable(data.allocation, data.investment_amounts, currency);
  renderAIExplanation(data.ai_explanation, data.llm_source);
  renderProducts(data.country_products, data.country);

  resultsSection.classList.remove("hidden");
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------------------
// Pie chart
// ---------------------------------------------------------------------------
function renderPieChart(allocation) {
  if (pieChart) {
    pieChart.destroy();
    pieChart = null;
  }

  const ctx = document.getElementById("pie-chart").getContext("2d");
  const assets = Object.keys(allocation);
  const values = Object.values(allocation);
  const colors = assets.map(a => ASSET_COLORS[a] || "#cbd5e1");

  pieChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: assets,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: "#ffffff",
        borderWidth: 3,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      cutout: "58%",
      plugins: {
        legend: {
          display: false,  // custom legend via table
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.raw}%`,
          },
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// Allocation table
// ---------------------------------------------------------------------------
function renderAllocationTable(allocation, amounts, currency) {
  const tbody = document.getElementById("allocation-tbody");
  tbody.innerHTML = "";

  const sorted = Object.entries(allocation).sort((a, b) => b[1] - a[1]);

  for (const [asset, pct] of sorted) {
    const color = ASSET_COLORS[asset] || "#cbd5e1";
    const amount = amounts[asset] != null
      ? `${currency}${fmt(amounts[asset])}`
      : "—";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <span class="asset-label">
          <span class="asset-dot" style="background:${color}"></span>
          ${asset}
        </span>
      </td>
      <td class="pct-bar-cell">
        <div class="pct-bar-wrapper">
          <div class="pct-bar-bg">
            <div class="pct-bar-fill"
                 style="width:${pct}%;background:${color}"></div>
          </div>
          <strong>${pct}%</strong>
        </div>
      </td>
      <td>${amount}</td>
    `;
    tbody.appendChild(tr);
  }
}

// ---------------------------------------------------------------------------
// AI Explanation
// ---------------------------------------------------------------------------
function renderAIExplanation(explanation, llmSource) {
  const container = document.getElementById("ai-explanation");
  const badge = document.getElementById("llm-badge");
  const card = document.getElementById("explanation-card");

  if (!explanation) {
    card.classList.add("hidden");
    return;
  }

  card.classList.remove("hidden");

  // LLM source badge
  if (llmSource === "openai") {
    badge.textContent = "✨ GPT-4o-mini";
    badge.className = "llm-badge badge-openai";
  } else {
    badge.textContent = "📝 Template";
    badge.className = "llm-badge badge-mock";
  }

  // Render paragraphs
  container.innerHTML = "";
  const paragraphs = explanation.split("\n\n").filter(p => p.trim());
  for (const para of paragraphs) {
    const p = document.createElement("p");
    p.textContent = para.trim();
    container.appendChild(p);
  }
}

// ---------------------------------------------------------------------------
// Country products
// ---------------------------------------------------------------------------
function renderProducts(products, country) {
  const grid = document.getElementById("products-grid");
  const title = document.getElementById("products-title");
  grid.innerHTML = "";

  const countryLabel = {
    us: "United States", canada: "Canada", india: "India",
    uk: "United Kingdom", "new zealand": "New Zealand",
    netherlands: "Netherlands", germany: "Germany",
    france: "France", australia: "Australia",
  }[country] || country;

  title.textContent = `Recommended Products — ${countryLabel}`;

  if (!products || Object.keys(products).length === 0) {
    grid.innerHTML = "<p style='color:var(--color-text-muted)'>No specific products available.</p>";
    return;
  }

  for (const [name, desc] of Object.entries(products)) {
    const div = document.createElement("div");
    div.className = "product-item";
    div.innerHTML = `
      <div class="product-name">${name}</div>
      <div class="product-desc">${desc}</div>
    `;
    grid.appendChild(div);
  }
}

// ---------------------------------------------------------------------------
// Form submit
// ---------------------------------------------------------------------------
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();

  const fd = new FormData(form);
  const data = {
    country:           fd.get("country") || "",
    age:               parseInt(fd.get("age"), 10),
    monthly_income:    parseFloat(fd.get("monthly_income")),
    monthly_expenses:  parseFloat(fd.get("monthly_expenses")),
    risk_level:        fd.get("risk_level") || "",
    financial_goal:    fd.get("financial_goal") || "",
  };

  const err = validateForm(data);
  if (err) { showError(err); return; }

  setLoading(true);

  try {
    const res = await fetch(`${API_BASE}/api/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      let msg = `Server error: ${res.status}`;
      try {
        const body = await res.json();
        msg = body.detail || msg;
      } catch {}
      showError(msg);
      return;
    }

    const result = await res.json();
    cachedRequest = data;   // cache for PDF download
    renderResults(result, getCurrencySymbol(data.country));

  } catch (networkErr) {
    showError(
      "Could not connect to the server. Make sure the backend is running at " +
      API_BASE
    );
  } finally {
    setLoading(false);
  }
});

// ---------------------------------------------------------------------------
// PDF download
// ---------------------------------------------------------------------------
downloadBtn.addEventListener("click", async () => {
  if (!cachedRequest) return;
  hideDownloadError();
  setDownloadLoading(true);

  try {
    const res = await fetch(`${API_BASE}/api/download_report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cachedRequest),
    });

    if (!res.ok) {
      let msg = `Failed to generate report: ${res.status}`;
      try {
        const body = await res.json();
        msg = body.detail || msg;
      } catch {}
      showDownloadError(msg);
      return;
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "investment_report.pdf";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

  } catch (networkErr) {
    showDownloadError(
      "Could not connect to the server. Make sure the backend is running at " +
      API_BASE
    );
  } finally {
    setDownloadLoading(false);
  }
});
