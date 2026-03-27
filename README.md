# AI Investment Planner Agent

A full-stack AI-powered investment portfolio recommendation system that uses **Constraint Satisfaction Problem (CSP)** solving and **Modern Portfolio Theory (MPT)** with a covariance matrix to generate personalised portfolio recommendations.

## Architecture

```
Frontend (HTML/CSS/JS)  <-->  FastAPI Backend  <-->  Investment Agent (CSP + MPT + Covariance)
                                                              |
                                                      Live Market Data (yfinance)
```

## Project Structure

```
/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── agent.py                 # Investment advisor agent logic
│   ├── csp_solver.py            # Constraint Satisfaction Problem logic
│   ├── mpt_calculator.py        # Modern Portfolio Theory + Covariance Matrix
│   ├── market_data.py           # Live market data fetching (yfinance)
│   ├── country_products.py      # Country-specific investment products
│   ├── models.py                # Pydantic models for request/response
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── index.html               # Main webpage
│   ├── style.css                # Styling
│   └── app.js                   # JS to call the API and render results
└── README.md
```

## Supported Countries

United States, Canada, India, United Kingdom, New Zealand, Netherlands, Germany, France, Australia

## Features

- **Live market data** via `yfinance` (S&P 500, bond ETFs, REIT ETFs, commodity ETFs) with automatic fallback to hardcoded values
- **CSP solver** finds all valid portfolio allocations within risk-level bounds (5% step increments)
- **MPT + Covariance Matrix** selects the portfolio with the highest Sharpe ratio
- **Age-based glide path** — stock allocation capped at `max(80 - age, 30)%`
- **Goal-based adjustments** — Savings, Retirement, Investment, Buying House
- **Country-specific products** — localised investment product recommendations for all 9 countries
- **1-hour market data cache** to avoid API rate limits
- **Responsive web UI** with pie chart (Chart.js), allocation table, and product cards

## Setup & Running

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
uvicorn backend.main:app --reload
```

Or from within the `backend/` directory:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 3. Serve the Frontend

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
  "investment_amounts": {"Stocks": 10800.0, ...},
  "total_investable_amount": 24000.0,
  "currency_symbol": "$",
  "expected_annual_return": 6.75,
  "expected_annual_volatility": 7.2,
  "sharpe_ratio": 0.6597,
  "country_products": {"Brokerage Account": "Taxable account for stocks, ETFs...", ...},
  "market_data_source": "live"
}
```

#### `GET /health`

Returns `{"status": "ok"}`.

## Investment Logic

### Risk Preferences
| Level  | Stocks | Bonds | Cash | Real Estate | Commodities | Alt Inv |
|--------|--------|-------|------|-------------|-------------|---------|
| Low    | 30%    | 50%   | 15%  | 5%          | 0%          | 0%      |
| Medium | 50%    | 30%   | 10%  | 5%          | 5%          | 0%      |
| High   | 65%    | 20%   | 5%   | 5%          | 5%          | 0%      |

### Goal Adjustments
- **Buying house**: Stocks −10%, Bonds +5%, Cash +5%
- **Retirement**: Stocks +10%, Bonds −5%, Cash −5%
- **Savings**: Stocks −5%, Cash +10%

### Investable Amount
- Buying house: 70% of (income − expenses) × 12
- Savings: 80% of (income − expenses) × 12
- Retirement / Investment: 100% of (income − expenses) × 12

## Disclaimer

This application is for **educational purposes only** and does not constitute financial advice. Always consult a qualified financial advisor before making investment decisions.
