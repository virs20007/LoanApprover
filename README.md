# AI Investment Planner Agent

A full-stack AI-powered investment portfolio recommendation system that combines **Constraint Satisfaction Problem (CSP)** solving, **Modern Portfolio Theory (MPT)** with a live covariance matrix, an **LLM agent** for natural-language explanations, and **downloadable PDF reports**.

## Architecture

```
Frontend (HTML/CSS/JS)  <-->  FastAPI Backend  <-->  Investment Agent (CSP + MPT + Covariance)
                                                              |                    |
                                                    Live Market Data (yfinance)  LLM (OpenAI)
```

## Project Structure

```
/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── agent.py                 # Investment advisor agent + LLM integration
│   ├── csp_solver.py            # Constraint Satisfaction Problem logic
│   ├── mpt_calculator.py        # Modern Portfolio Theory + Covariance Matrix
│   ├── market_data.py           # Live market data fetching (yfinance)
│   ├── country_products.py      # Country-specific investment products (Python)
│   ├── country_specific_info.json  # Country-specific products (JSON)
│   ├── report_generator.py      # PDF report generation (ReportLab)
│   ├── models.py                # Pydantic models for request/response
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── index.html               # Main webpage
│   ├── style.css                # Styling
│   └── app.js                   # JS to call the API and render results
├── .env.example                 # Environment variable template
├── REPORT.md                    # Comprehensive technical report
├── PRESENTATION.md              # 5-slide presentation
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Uvicorn |
| Portfolio Optimisation | python-constraint (CSP) + NumPy (MPT) |
| Market Data | yfinance (Yahoo Finance) |
| LLM Agent | OpenAI GPT-4o-mini (with mock fallback) |
| PDF Generation | ReportLab |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Charts | Chart.js |

## Supported Countries

United States, Canada, India, United Kingdom, New Zealand, Netherlands, Germany, France, Australia

## Features

- **Live market data** via `yfinance` (SPY, AGG, VNQ, GLD) with automatic fallback to hardcoded values
- **CSP solver** finds all valid portfolio allocations within risk-level bounds (5% step increments)
- **MPT + Covariance Matrix** selects the portfolio with the highest Sharpe ratio
- **Age-based glide path** — stock allocation capped at `max(80 - age, 30)%`
- **Goal-based adjustments** — Savings, Retirement, Investment, Buying House
- **LLM explanation** — OpenAI GPT-4o-mini generates a 2–3 paragraph narrative (mock template if no API key)
- **PDF report** — downloadable report with allocation table, AI explanation, and country products
- **Country-specific products** — localised investment product recommendations for all 9 countries
- **1-hour market data cache** to avoid API rate limits
- **Responsive web UI** with pie chart (Chart.js), allocation table, AI explanation, and product cards

## Setup & Running

### 1. Environment Variables (Optional)

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY if you want LLM explanations
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the Backend

From the `backend/` directory:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. Serve the Frontend

Open `frontend/index.html` directly in your browser, or use a simple HTTP server:

```bash
cd frontend
python -m http.server 3000
```

Then open `http://localhost:3000` in your browser.

> **Note:** The frontend calls `http://localhost:8000` by default. Make sure the backend is running before submitting the form.

## API Documentation

Interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints

#### `POST /api/recommend`

Generate a personalised investment portfolio recommendation.

Request body:

```json
{
  "country": "us",
  "age": 35,
  "monthly_income": 5000,
  "monthly_expenses": 3000,
  "risk_level": "Medium",
  "financial_goal": "Investment"
}
```

Response:

```json
{
  "allocation": {"Stocks": 45.0, "Bonds": 30.0, "Cash": 10.0, "Real Estate": 10.0, "Commodities": 5.0},
  "investment_amounts": {"Stocks": 10800.0, "Bonds": 7200.0, "Cash": 2400.0, "Real Estate": 2400.0, "Commodities": 1200.0},
  "total_investable_amount": 24000.0,
  "currency_symbol": "$",
  "expected_annual_return": 6.75,
  "expected_annual_volatility": 7.2,
  "sharpe_ratio": 0.6597,
  "country_products": {"Brokerage Account": "Taxable account for stocks, ETFs...", ...},
  "market_data_source": "live",
  "ai_explanation": "Based on your medium risk tolerance...",
  "llm_source": "openai"
}
```

#### `GET /api/market_data?symbols=SPY,BND,GLD`

Returns live price/volatility data for requested symbols.

```json
{
  "data": {
    "SPY": {"asset_class": "Stocks", "annualised_return": 12.5, "annualised_volatility": 15.2},
    "BND": {"asset_class": "Bonds", "annualised_return": 4.1, "annualised_volatility": 5.3},
    "GLD": {"asset_class": "Commodities", "annualised_return": 8.2, "annualised_volatility": 13.1}
  },
  "source": "live"
}
```

#### `POST /api/download_report`

Generates and returns a downloadable PDF report. Accepts the same request body as `/api/recommend`. Returns `application/pdf`.

#### `GET /health`

Returns `{"status": "ok"}`.

## Investment Logic

### Risk Preferences (Base Allocations)

| Level  | Stocks | Bonds | Cash | Real Estate | Commodities | Alt Inv |
|--------|--------|-------|------|-------------|-------------|---------|
| Low    | 30%    | 50%   | 15%  | 5%          | 0%          | 0%      |
| Medium | 50%    | 30%   | 10%  | 5%          | 5%          | 0%      |
| High   | 65%    | 20%   | 5%   | 5%          | 5%          | 0%      |

### Goal Adjustments (Applied on top of base)

- **Buying house**: Stocks −10%, Bonds +5%, Cash +5%
- **Retirement**: Stocks +10%, Bonds −5%, Cash −5%
- **Savings**: Stocks −5%, Cash +10%

### Age-Based Glide Path

- Maximum stock allocation = `max(80 − age, 30)%`
- Excess stock allocation is redistributed to Bonds then Cash

### Investable Amount

- Buying house: 70% of (income − expenses) × 12
- Savings: 80% of (income − expenses) × 12
- Retirement / Investment: 100% of (income − expenses) × 12

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | OpenAI API key for LLM explanations (uses mock template if not set) |
| `ALPHA_VANTAGE_API_KEY` | No | Not currently used (reserved for future use) |

## Disclaimer

This application is for **educational purposes only** and does not constitute financial advice. Always consult a qualified financial advisor before making investment decisions.
