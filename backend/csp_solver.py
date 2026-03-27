"""
CSP (Constraint Satisfaction Problem) solver for portfolio allocation.

Asset classes and their min/max allocation bounds (in whole percentages):
  Stocks:                 0 – 80 %
  Bonds:                  0 – 60 %
  Cash:                   0 – 50 %
  Real Estate:            0 – 15 %
  Commodities:            0 – 10 %
  Alternative Investments:0 – 10 %

Constraints applied:
  1. All allocations sum to 100 %
  2. Stocks ≤ max(80 – age, 30)

Allocations are explored at 5 % step increments for performance.
"""

from constraint import Problem

ASSET_CLASSES = [
    "Stocks",
    "Bonds",
    "Cash",
    "Real Estate",
    "Commodities",
    "Alternative Investments",
]

BASE_BOUNDS: dict[str, tuple[int, int]] = {
    "Stocks": (0, 80),
    "Bonds": (0, 60),
    "Cash": (0, 50),
    "Real Estate": (0, 15),
    "Commodities": (0, 10),
    "Alternative Investments": (0, 10),
}

STEP = 5  # percent step increment


def _make_domain(low: int, high: int, step: int = STEP) -> list[int]:
    """Return a list of multiples-of-step within [low, high]."""
    values = []
    v = 0
    while v <= high:
        if v >= low:
            values.append(v)
        v += step
    return values or [low]


def solve_csp(age: int, risk_bounds: dict[str, tuple[int, int]] | None = None) -> list[dict[str, int]]:
    """
    Run CSP and return all valid allocation solutions (list of dicts).

    Parameters
    ----------
    age : int
        Investor age, used to cap the maximum stock allocation.
    risk_bounds : dict or None
        Optional override of per-asset (min, max) bounds, e.g., from risk preferences.
        When provided, the effective bounds are the intersection of these and BASE_BOUNDS.

    Returns
    -------
    list[dict[str, int]]
        Each solution maps asset name → allocation percentage (0–100).
    """
    stocks_max = max(80 - age, 30)
    effective_bounds = dict(BASE_BOUNDS)
    effective_bounds["Stocks"] = (
        effective_bounds["Stocks"][0],
        min(effective_bounds["Stocks"][1], stocks_max),
    )

    if risk_bounds:
        for asset, (lo, hi) in risk_bounds.items():
            if asset in effective_bounds:
                cur_lo, cur_hi = effective_bounds[asset]
                effective_bounds[asset] = (max(cur_lo, lo), min(cur_hi, hi))

    problem = Problem()

    for asset in ASSET_CLASSES:
        lo, hi = effective_bounds[asset]
        domain = _make_domain(lo, hi, STEP)
        problem.addVariable(asset, domain)

    def total_is_100(*values: int) -> bool:
        return sum(values) == 100

    problem.addConstraint(total_is_100, ASSET_CLASSES)

    solutions = problem.getSolutions()
    return solutions
