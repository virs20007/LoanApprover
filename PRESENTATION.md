# AI Investment Planner — Presentation

## Slide 0: Title

**AI Investment Planner**
**CSP + MPT + LLM Agent**

*Personalised Portfolio Optimisation with Live Market Data*

---

**Tech Stack:** FastAPI · Python · yfinance · OpenAI · HTML/CSS/JS · Chart.js · ReportLab

---

## Slide 1: Problem & Motivation

### The Problem

- Individual investors struggle to allocate capital across asset classes
- Personal financial advisors are expensive and inaccessible
- Existing robo-advisors lack transparency — "black box" recommendations
- Generic advice ignores age, goals, and country-specific tax/investment products

### Our Solution

An **explainable, AI-powered investment planner** that:

1. 🔒 **Constraint Satisfaction** — only generates *valid* portfolio allocations
2. 📊 **Modern Portfolio Theory** — selects the *mathematically optimal* allocation
3. 🌐 **Live Market Data** — recommendations grounded in *current conditions*
4. 🤖 **LLM Agent** — explains *why* in plain English

### Who is it for?

- First-time investors who need guided, explained recommendations
- People in 9 countries with localised investment product suggestions
- Anyone who wants to understand the *reasoning* behind their portfolio

---

## Slide 2: Techniques Overview

### CSP — Constraint Satisfaction Problem

- **Variables:** 6 asset classes (Stocks, Bonds, Cash, Real Estate, Commodities, Alternatives)
- **Domains:** Multiples of 5% within per-asset bounds
- **Constraints:** Sum = 100%, Stocks ≤ max(80−age, 30)%, risk-level bounds
- **Output:** All valid portfolio combinations (~10–400 solutions)

> *Why CSP?* Exhaustive search guarantees the globally optimal solution within the grid — no local optima risk.

### MPT — Modern Portfolio Theory

```
R_p = Σ w_i × r_i         (expected return)
σ_p = √(w^T Σ w)           (portfolio volatility)
S   = (R_p − 0.02) / σ_p   (Sharpe ratio — objective)
```

Selects the **highest Sharpe ratio** portfolio from all CSP solutions.

### Covariance Matrix

```
σ_p² = w^T Σ w
```

- Computed from **252 days of live ETF data** (SPY, AGG, VNQ, GLD)
- Captures cross-asset correlations — mathematically models diversification
- Annualised: `Σ = daily_returns.cov() × 252`

### LLM Agent (OpenAI GPT-4o-mini)

- Receives portfolio data + user profile as structured prompt
- Generates 2–3 paragraph explanation highlighting key decisions
- Enforced disclaimer: *"not financial advice"*
- Graceful fallback: template-based explanation if no API key

---

## Slide 3: System Architecture & Demo

### Architecture

```
Browser ──POST /api/recommend──▶ FastAPI (port 8000)
                                    │
                           ┌────────┴──────────┐
                           │    agent.py        │
                    ┌──────┴──────┐  ┌─────────┴──────┐
                    │ market_data │  │  csp_solver     │
                    │ (yfinance)  │  │  mpt_calculator │
                    └──────┬──────┘  └─────────┬──────┘
                           │                   │
                    Yahoo Finance           LLM Agent
                                         (OpenAI API)
```

### Demo Walkthrough

**Input Form:**
- User fills: Country, Age, Income, Expenses, Risk Level, Goal
- Clicks "Get My Investment Plan"
- Loading spinner shown while API processes

**Results Panel:**
- 📊 **Doughnut chart** — visual allocation breakdown with asset colours
- 📋 **Allocation table** — asset name, %, dollar amount with progress bars
- 🤖 **AI Explanation** — natural language reasoning (GPT or template)
- 🏦 **Country Products** — localised investment recommendations
- 📄 **PDF Download** — full report with all details

**API Endpoints:**
- `POST /api/recommend` — main recommendation
- `GET /api/market_data?symbols=SPY,BND,GLD` — live market data
- `POST /api/download_report` — PDF generation
- `GET /health` — health check

---

## Slide 4: Results & Performance

### Portfolio Quality

| Metric | Naive Equal-Weight | CSP + MPT Optimised |
|--------|-------------------|---------------------|
| Expected Return | ~5.3% | ~5.8–7.5% |
| Volatility | ~7.2% | ~6.5–10.5% |
| **Sharpe Ratio** | ~0.46 | **~0.55–0.85** |
| Improvement | — | **+20% to +85%** |

### System Performance

| Component | Typical Time |
|-----------|-------------|
| CSP solving (400 solutions) | < 1 second |
| MPT evaluation (all solutions) | < 0.1 second |
| yfinance data fetch | ~2–3 seconds |
| LLM explanation (OpenAI) | ~2–4 seconds |
| PDF generation (ReportLab) | < 0.5 second |
| **Total end-to-end** | **~4–8 seconds** |

### Key Strengths

- ✅ **Exhaustive optimality** — guaranteed best Sharpe within the 5% grid
- ✅ **Live data** — covariance matrix from actual ETF returns, not estimates
- ✅ **Explainable** — every decision traced to age, risk, goal, or market data
- ✅ **Resilient** — dual fallbacks (data + LLM) for graceful degradation
- ✅ **Localised** — 9 countries × 4 goals = 36 sets of specific product recommendations

---

## Slide 5: Engineering Trade-offs & Future Work

### Trade-offs Made

| Decision | Alternative | Why This Choice |
|----------|-------------|-----------------|
| 5% grid increments | Continuous optimisation (scipy) | Interpretability — easy to explain round numbers |
| Sharpe ratio objective | Sortino, CVaR | Industry standard, widely understood |
| python-constraint CSP | Custom backtracking | Battle-tested library, clean API |
| yfinance for data | Alpha Vantage, Quandl | Free, no API key required |
| ReportLab for PDF | Weasyprint, fpdf2 | Rich layout control, pure Python |
| LLM mock fallback | Require API key | Accessibility — works without OpenAI account |

### Limitations

1. **1-year lookback** — short history may not reflect long-term correlations
2. **No transaction costs** — rebalancing costs not modelled
3. **Static risk-free rate** (2%) — should use current T-bill rate
4. **Normal return distribution** assumed in Sharpe ratio

### Future Roadmap

```
Phase 1 (current)     Phase 2                    Phase 3
─────────────────     ──────────────────────      ──────────────────────
CSP + MPT + LLM   ──▶  Monte Carlo simulation  ──▶  Multi-period model
6 asset classes       Fractional weights           Tax-aware allocation
9 countries           Factor risk model            User portfolio history
PDF reports           Mobile responsive UI         Backtesting engine
```

### Key Takeaways

1. **Composability** — CSP + MPT + LLM each handle what they're best at
2. **Transparency** — every recommendation traceable to input parameters
3. **Resilience** — multiple fallback layers (data, LLM)
4. **Accessibility** — works fully offline (mock mode), globally (9 countries)
