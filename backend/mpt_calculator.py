"""
Modern Portfolio Theory (MPT) calculations with covariance matrix.

For each CSP solution:
  - Portfolio expected return = sum(w_i * r_i)
  - Portfolio volatility = sqrt(w^T * Cov * w)
  - Sharpe ratio = (return - risk_free_rate) / volatility

The solution with the highest Sharpe ratio is selected.
"""

import numpy as np

RISK_FREE_RATE = 0.02

ASSET_CLASSES = [
    "Stocks",
    "Bonds",
    "Cash",
    "Real Estate",
    "Commodities",
    "Alternative Investments",
]


def _weights_vector(solution: dict[str, int]) -> np.ndarray:
    """Convert allocation dict (percentages) to weight array (fractions)."""
    return np.array([solution[a] / 100.0 for a in ASSET_CLASSES])


def compute_portfolio_metrics(
    solution: dict[str, int],
    market_data: dict[str, dict[str, float]],
    cov_matrix: np.ndarray,
) -> tuple[float, float, float]:
    """
    Compute (expected_return, volatility, sharpe_ratio) for a single solution.
    """
    w = _weights_vector(solution)
    returns = np.array([market_data[a]["ret"] for a in ASSET_CLASSES])

    port_return = float(np.dot(w, returns))
    port_variance = float(np.dot(w, np.dot(cov_matrix, w)))
    port_vol = float(np.sqrt(max(port_variance, 0.0)))

    if port_vol > 0:
        sharpe = (port_return - RISK_FREE_RATE) / port_vol
    else:
        sharpe = 0.0

    return port_return, port_vol, sharpe


def select_best_portfolio(
    solutions: list[dict[str, int]],
    market_data: dict[str, dict[str, float]],
    cov_matrix: np.ndarray,
) -> tuple[dict[str, int], float, float, float]:
    """
    Evaluate all CSP solutions and return the one with the highest Sharpe ratio.

    Returns
    -------
    (best_solution, expected_return, volatility, sharpe_ratio)
    """
    if not solutions:
        raise ValueError("No CSP solutions provided to evaluate")

    best_solution = None
    best_sharpe = float("-inf")
    best_return = 0.0
    best_vol = 0.0

    for sol in solutions:
        ret, vol, sharpe = compute_portfolio_metrics(sol, market_data, cov_matrix)
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_solution = sol
            best_return = ret
            best_vol = vol

    return best_solution, best_return, best_vol, best_sharpe  # type: ignore[return-value]
