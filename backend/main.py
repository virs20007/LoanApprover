import os

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from dotenv import load_dotenv

load_dotenv()

from models import InvestmentRequest, InvestmentResponse
from agent import get_investment_recommendation
from market_data import get_market_data, ASSET_TICKERS, ASSET_CLASSES
from report_generator import generate_pdf_report

app = FastAPI(
    title="Investment Planner Agent",
    description="AI-powered investment portfolio recommendation using CSP + MPT + Covariance Matrix",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.post("/api/recommend", response_model=InvestmentResponse)
async def recommend(request: InvestmentRequest) -> InvestmentResponse:
    """
    Generate a personalised investment portfolio recommendation.
    """
    try:
        return get_investment_recommendation(request)
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/market_data")
async def market_data_endpoint(
    symbols: str = Query(
        default="SPY,BND,GLD",
        description="Comma-separated list of ETF symbols (e.g. SPY,BND,GLD)",
    )
) -> dict:
    """
    Return live price, annualised return, and annualised volatility
    for the requested symbols (or all asset ETFs if none specified).
    """
    try:
        md_result = get_market_data()
        market_data = md_result["market_data"]
        data_source = md_result["source"]

        requested = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        # Build reverse map: ticker -> asset class
        ticker_to_asset = {v: k for k, v in ASSET_TICKERS.items() if v is not None}

        result: dict[str, dict] = {}
        for ticker in requested:
            asset = ticker_to_asset.get(ticker)
            if asset and asset in market_data:
                result[ticker] = {
                    "asset_class": asset,
                    "annualised_return": round(market_data[asset]["ret"] * 100, 2),
                    "annualised_volatility": round(market_data[asset]["vol"] * 100, 2),
                }
            else:
                result[ticker] = {"error": "Symbol not tracked or data unavailable"}

        return {"data": result, "source": data_source}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/download_report")
async def download_report(request: InvestmentRequest) -> Response:
    """
    Generate a PDF report for the portfolio and return it as a file download.
    """
    try:
        recommendation = get_investment_recommendation(request)
        pdf_bytes = generate_pdf_report(
            country=request.country,
            age=request.age,
            monthly_income=request.monthly_income,
            monthly_expenses=request.monthly_expenses,
            risk_level=request.risk_level,
            financial_goal=request.financial_goal,
            currency_symbol=recommendation.currency_symbol,
            allocation=recommendation.allocation,
            investment_amounts=recommendation.investment_amounts,
            total_investable=recommendation.total_investable_amount,
            expected_return=recommendation.expected_annual_return,
            volatility=recommendation.expected_annual_volatility,
            sharpe_ratio=recommendation.sharpe_ratio,
            ai_explanation=recommendation.ai_explanation,
            country_products=recommendation.country_products,
            market_data_source=recommendation.market_data_source,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=investment_report.pdf",
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
