"""
engine.py: Marketing budget recommendation engine.

Model
-----
Each platform's daily revenue follows a diminishing-returns response curve

    revenue = a * spend ** beta        (0 < beta < 1: each extra rupee earns less)

fitted on daily spend/revenue history with a log-log regression.

Planning
--------
Curves are anchored at each platform's usual spend: at its historical budget share a
platform earns its usual ROAS. Moving budget share w away from the historical share h
changes its ROAS by the factor (w / h) ** (beta - 1). The optimiser splits a budget to
maximise total expected revenue within business limits (minimum and maximum share).
The recommended split does not depend on the size of the budget.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize


# ----------------------------------------------------------------------------
# Fitting
# ----------------------------------------------------------------------------
def fit_curve(spend, revenue):
    """Log-log least squares. Returns beta, log_a, R^2 (on log scale)."""
    x, y = np.log(spend), np.log(revenue)
    beta, log_a = np.polyfit(x, y, 1)
    resid = y - (log_a + beta * x)
    r2 = 1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return beta, log_a, r2


def fit_all(daily):
    """daily: DataFrame with columns platform, spend, revenue (one row per platform per day)."""
    d = daily[(daily.spend > 0) & (daily.revenue > 0)]
    total = d.spend.sum()
    rows = []
    for p, g in d.groupby("platform", observed=True):
        beta, log_a, r2 = fit_curve(g.spend.values, g.revenue.values)
        usual = g.spend.mean()
        rows.append({"platform": str(p), "beta": beta,
                     "roas_at_usual": np.exp(log_a) * usual ** (beta - 1),
                     "hist_share": g.spend.sum() / total, "r2": r2, "days": len(g),
                     "log_a": log_a, "usual_daily_spend": usual})
    return pd.DataFrame(rows).set_index("platform")


def predict_daily_revenue(params, platform, spend):
    p = params.loc[platform]
    return np.exp(p.log_a) * np.asarray(spend) ** p.beta


# ----------------------------------------------------------------------------
# Planning
# ----------------------------------------------------------------------------
def _arr(shares, params):
    if isinstance(shares, (pd.Series, dict)):
        return pd.Series(shares).reindex(params.index).values.astype(float)
    return np.asarray(shares, dtype=float)


def expected_revenue(shares, params, budget):
    """Expected revenue per platform when `budget` is split by `shares`."""
    w = np.clip(_arr(shares, params), 1e-12, None)
    h, r, b = params.hist_share.values, params.roas_at_usual.values, params.beta.values
    return pd.Series(budget * h * r * (w / h) ** b, index=params.index)


def marginal_roas(shares, params):
    """Revenue from the NEXT rupee on each platform at the given split."""
    w = np.clip(_arr(shares, params), 1e-12, None)
    h, r, b = params.hist_share.values, params.roas_at_usual.values, params.beta.values
    return pd.Series(r * b * (w / h) ** (b - 1), index=params.index)


def optimise(params, min_share=0.0, max_share=1.0):
    """Shares that maximise expected revenue, with sum = 1 and per-platform bounds.
    min_share / max_share can be a number or a dict {platform: value}."""
    idx = params.index
    lo = pd.Series(min_share, index=idx) if np.isscalar(min_share) else pd.Series(min_share).reindex(idx).fillna(0.0)
    hi = pd.Series(max_share, index=idx) if np.isscalar(max_share) else pd.Series(max_share).reindex(idx).fillna(1.0)
    h, r, b = params.hist_share.values, params.roas_at_usual.values, params.beta.values

    def obj(w):
        w = np.clip(w, 1e-12, None)
        return -(h * r * (w / h) ** b).sum()

    def grad(w):
        w = np.clip(w, 1e-12, None)
        return -(r * b * (w / h) ** (b - 1))

    x0 = np.clip(h, lo.values, hi.values)
    x0 = x0 / x0.sum()
    res = minimize(obj, x0, jac=grad, method="SLSQP",
                   bounds=list(zip(lo.values, hi.values)),
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones_like(w)}],
                   options={"ftol": 1e-12, "maxiter": 1000})
    if not res.success:
        raise RuntimeError(f"Optimiser failed: {res.message}")
    return pd.Series(res.x, index=idx)


def round_budget(shares, budget, step=5000):
    """Turn shares into Rs amounts rounded to `step` that still add up exactly to `budget`."""
    units = int(round(budget / step))
    raw = shares.values * units
    base = np.floor(raw).astype(int)
    for i in np.argsort(-(raw - base))[: units - base.sum()]:
        base[i] += 1
    return pd.Series(base * step, index=shares.index)


def bootstrap_shares(daily, n=200, seed=42, **opt_kwargs):
    """Refit and re-optimise on resampled days to measure how stable the recommendation is."""
    S = daily.pivot(index="date", columns="platform", values="spend")
    R = daily.pivot(index="date", columns="platform", values="revenue")
    S, R = S.loc[:, S.columns.astype(str)], R.loc[:, R.columns.astype(str)]
    rng = np.random.default_rng(seed)
    days = len(S)
    out = []
    for _ in range(n):
        i = rng.integers(0, days, days)
        sample = pd.DataFrame({"spend": S.iloc[i].stack(), "revenue": R.iloc[i].stack()}).reset_index()
        out.append(optimise(fit_all(sample), **opt_kwargs))
    return pd.DataFrame(out)
