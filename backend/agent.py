"""
Investment advisor agent.

Orchestrates the full recommendation flow:
1. Fetch live market data (with fallback)
2. Apply risk preferences
3. Apply age-based stock glide path
4. Apply financial goal adjustments
5. Run CSP to get valid allocations
6. Run MPT to select the best portfolio
7. Query LLM for a natural-language explanation
8. Return InvestmentResponse
"""

import logging
import os

from models import InvestmentRequest, InvestmentResponse
from market_data import get_market_data, ASSET_CLASSES
from csp_solver import solve_csp
from mpt_calculator import select_best_portfolio
from country_products import COUNTRY_SPECIFIC_INFO, CURRENCY_SYMBOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk preference targets (from notebook)
# ---------------------------------------------------------------------------
RISK_PREFERENCES: dict[str, dict[str, int]] = {
    "Low": {
        "Stocks": 30, "Bonds": 50, "Cash": 15,
        "Real Estate": 5, "Commodities": 0, "Alternative Investments": 0,
    },
    "Medium": {
        "Stocks": 50, "Bonds": 30, "Cash": 10,
        "Real Estate": 5, "Commodities": 5, "Alternative Investments": 0,
    },
    "High": {
        "Stocks": 65, "Bonds": 20, "Cash": 5,
        "Real Estate": 5, "Commodities": 5, "Alternative Investments": 0,
    },
}

# ---------------------------------------------------------------------------
# Goal adjustments (from notebook)
# ---------------------------------------------------------------------------
GOAL_ADJUSTMENTS: dict[str, dict[str, int]] = {
    "Buying house": {"Stocks": -10, "Bonds": 5, "Cash": 5},
    "Retirement":   {"Stocks": 10,  "Bonds": -5, "Cash": -5},
    "Savings":      {"Stocks": -5,  "Cash": 10},
    "Investment":   {},
}

# ---------------------------------------------------------------------------
# Investable-income fraction per goal
# ---------------------------------------------------------------------------
INVESTABLE_FRACTION: dict[str, float] = {
    "Buying house": 0.70,
    "Savings":      0.80,
    "Retirement":   1.00,
    "Investment":   1.00,
}

STEP = 5  # percentage step — must match csp_solver

LLM_SYSTEM_PROMPT = (
    "You are an AI financial advisor for educational purposes. "
    "Explain investment portfolio allocations clearly and concisely. "
    "Always include a disclaimer that this is not real financial advice."
)


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def _snap_to_step(value: int, step: int = STEP) -> int:
    """Round to nearest multiple of step."""
    return round(value / step) * step


def _build_target_allocation(
    risk_level: str,
    age: int,
    goal: str,
) -> dict[str, int]:
    """
    Build a target (seed) allocation by combining:
    - base risk preferences
    - age-based stock glide path
    - goal adjustments
    All values are snapped to STEP multiples and normalised to 100.
    """
    target = dict(RISK_PREFERENCES[risk_level])

    # Age-based stock glide path
    stocks_max = max(80 - age, 30)
    if target["Stocks"] > stocks_max:
        excess = target["Stocks"] - stocks_max
        target["Stocks"] = stocks_max
        # Redistribute excess to Bonds then Cash
        for asset in ("Bonds", "Cash"):
            addition = min(excess, 60 - target[asset])  # rough cap
            target[asset] = target.get(asset, 0) + addition
            excess -= addition
            if excess <= 0:
                break

    # Goal adjustments
    for asset, delta in GOAL_ADJUSTMENTS.get(goal, {}).items():
        target[asset] = target.get(asset, 0) + delta

    # Ensure non-negative
    for asset in list(target.keys()):
        target[asset] = max(0, target[asset])

    # Snap to step
    for asset in list(target.keys()):
        target[asset] = _snap_to_step(target[asset])

    # Normalise to 100
    total = sum(target.values())
    if total != 100:
        diff = 100 - total
        # Adjust the largest asset
        largest = max(target, key=lambda a: target[a])
        target[largest] += diff
        target[largest] = _snap_to_step(max(0, target[largest]))

    return target


def _target_to_bounds(
    target: dict[str, int],
    window: int = 20,
) -> dict[str, tuple[int, int]]:
    """
    Convert a target allocation into +-window% bounds for the CSP.
    """
    bounds: dict[str, tuple[int, int]] = {}
    for asset, pct in target.items():
        lo = _snap_to_step(max(0, pct - window))
        hi = _snap_to_step(min(100, pct + window))
        bounds[asset] = (lo, hi)
    return bounds


def _mock_explanation(
    request: InvestmentRequest,
    allocation: dict[str, float],
    expected_return: float,
    volatility: float,
    sharpe: float,
) -> str:
    """Generate a template-based explanation when no LLM is available."""
    top_asset = max(allocation, key=lambda a: allocation[a])
    top_pct = allocation[top_asset]
    stocks_pct = allocation.get("Stocks", 0)
    bonds_pct = allocation.get("Bonds", 0)

    age_note = ""
    if request.age >= 50:
        age_note = (
            f" Given your age of {request.age}, the stock allocation has been "
            f"moderated to reduce exposure to market volatility as you approach "
            f"or are in your peak earning years."
        )
    elif request.age <= 30:
        age_note = (
            f" At {request.age} years old, you have a longer investment horizon, "
            f"allowing the portfolio to take on slightly more risk for potentially "
            f"higher long-term returns."
        )

    goal_note = {
        "Buying house": (
            "The portfolio is structured conservatively with higher cash and bond "
            "allocations to preserve capital for your home purchase goal."
        ),
        "Retirement": (
            "For retirement planning, the portfolio balances growth assets (stocks) "
            "with stability (bonds) to build wealth over time while managing risk."
        ),
        "Savings": (
            "With a savings goal, the portfolio emphasises capital preservation "
            "through higher bond and cash allocations while maintaining some growth "
            "potential."
        ),
        "Investment": (
            "For a general investment goal, the portfolio is optimised for the "
            "best risk-adjusted return based on your risk tolerance."
        ),
    }.get(request.financial_goal, "")

    explanation = (
        f"Based on your {request.risk_level.lower()} risk tolerance and "
        f"{request.financial_goal.lower()} goal, the CSP + Modern Portfolio Theory "
        f"optimiser recommends a portfolio led by {top_asset} ({top_pct:.0f}%), "
        f"with Stocks at {stocks_pct:.0f}% and Bonds at {bonds_pct:.0f}%.{age_note} "
        f"This allocation achieved a Sharpe Ratio of {sharpe:.4f}, representing "
        f"an expected annual return of {expected_return:.2f}% with "
        f"{volatility:.2f}% volatility — the highest risk-adjusted return "
        f"among all valid portfolio combinations.\n\n"
        f"{goal_note} "
        f"The covariance matrix computed from live market data ensures that "
        f"correlations between asset classes are properly accounted for, leading "
        f"to more accurate volatility estimates than simple variance calculations.\n\n"
        f"Disclaimer: This analysis is for educational purposes only and does "
        f"not constitute professional financial advice. Past performance is not "
        f"indicative of future results. Please consult a qualified financial "
        f"advisor before making any investment decisions."
    )
    return explanation


def _generate_llm_explanation(
    request: InvestmentRequest,
    allocation: dict[str, float],
    expected_return: float,
    volatility: float,
    sharpe: float,
    currency: str,
    total_investable: float,
) -> tuple[str, str]:
    """
    Generate a natural-language explanation of the portfolio recommendation.
    Returns (explanation_text, source) where source is 'openai' or 'mock'.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return _mock_explanation(request, allocation, expected_return, volatility, sharpe), "mock"

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        alloc_lines = "\n".join(
            f"  - {asset}: {pct:.0f}%"
            for asset, pct in sorted(allocation.items(), key=lambda x: -x[1])
        )
        user_msg = (
            f"User Profile:\n"
            f"  Country: {request.country}\n"
            f"  Age: {request.age}\n"
            f"  Monthly Income: {currency}{request.monthly_income:,.0f}\n"
            f"  Monthly Expenses: {currency}{request.monthly_expenses:,.0f}\n"
            f"  Risk Level: {request.risk_level}\n"
            f"  Financial Goal: {request.financial_goal}\n\n"
            f"Recommended Portfolio:\n{alloc_lines}\n\n"
            f"Portfolio Metrics:\n"
            f"  Expected Annual Return: {expected_return:.2f}%\n"
            f"  Expected Annual Volatility: {volatility:.2f}%\n"
            f"  Sharpe Ratio: {sharpe:.4f}\n"
            f"  Annual Investable Amount: {currency}{total_investable:,.0f}\n\n"
            f"Please provide a 2-3 paragraph explanation of why this portfolio was "
            f"recommended, highlighting key decisions such as how age, risk level, "
            f"and financial goal influenced the allocation. Include a brief disclaimer."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=600,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip(), "openai"
    except Exception as exc:
        logger.warning("OpenAI call failed (%s). Using mock explanation.", exc)
        return _mock_explanation(request, allocation, expected_return, volatility, sharpe), "mock"


def get_investment_recommendation(request: InvestmentRequest) -> InvestmentResponse:
    """Main agent entry point."""
    # 1. Live market data
    md_result = get_market_data()
    market_data = md_result["market_data"]
    cov_matrix = md_result["cov_matrix"]
    data_source: str = md_result["source"]

    # 2. Compute monthly surplus & investable amount
    monthly_surplus = request.monthly_income - request.monthly_expenses
    fraction = INVESTABLE_FRACTION.get(request.financial_goal, 1.0)
    monthly_investable = monthly_surplus * fraction
    # Annualise to give a meaningful "total investable" figure shown in UI
    total_investable = monthly_investable * 12

    # 3. Build target allocation
    target = _build_target_allocation(
        request.risk_level, request.age, request.financial_goal
    )

    # 4. Build risk bounds from target for CSP
    risk_bounds = _target_to_bounds(target, window=20)

    # 5. Run CSP
    solutions = solve_csp(age=request.age, risk_bounds=risk_bounds)

    if not solutions:
        # Widen window and retry without custom bounds
        logger.warning("CSP returned no solutions with tight bounds, retrying with base bounds")
        solutions = solve_csp(age=request.age)

    if not solutions:
        raise RuntimeError("CSP could not find any valid portfolio solution")

    # 6. Run MPT — select portfolio with highest Sharpe Ratio
    best_sol, exp_return, exp_vol, sharpe = select_best_portfolio(
        solutions, market_data, cov_matrix
    )

    # 7. Build allocation & investment amounts
    allocation: dict[str, float] = {a: float(best_sol[a]) for a in ASSET_CLASSES}
    currency = CURRENCY_SYMBOLS.get(request.country, "$")

    investment_amounts: dict[str, float] = {
        a: round(total_investable * (pct / 100.0), 2)
        for a, pct in allocation.items()
        if pct > 0
    }
    allocation = {a: pct for a, pct in allocation.items() if pct > 0}

    # 8. Country-specific products
    country_info = COUNTRY_SPECIFIC_INFO.get(request.country, {})
    products = country_info.get(request.financial_goal, {})

    # 9. LLM explanation
    ai_explanation, llm_source = _generate_llm_explanation(
        request=request,
        allocation=allocation,
        expected_return=round(exp_return * 100, 2),
        volatility=round(exp_vol * 100, 2),
        sharpe=round(sharpe, 4),
        currency=currency,
        total_investable=total_investable,
    )

    return InvestmentResponse(
        allocation=allocation,
        investment_amounts=investment_amounts,
        total_investable_amount=round(total_investable, 2),
        currency_symbol=currency,
        expected_annual_return=round(exp_return * 100, 2),
        expected_annual_volatility=round(exp_vol * 100, 2),
        sharpe_ratio=round(sharpe, 4),
        country_products=products,
        market_data_source=data_source,
        ai_explanation=ai_explanation,
        llm_source=llm_source,
    )
