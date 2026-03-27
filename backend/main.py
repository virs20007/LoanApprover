from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import InvestmentRequest, InvestmentResponse
from agent import get_investment_recommendation

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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
