"""
Market features that feed the Quantum Price Model's potential and initial state,
all computed from price history alone (no look-ahead: a feature for a forecast
made at close t uses prices up to and including t).

  * volatility: EWMA (RiskMetrics) or GARCH(1,1), used to standardise returns
  * pivots:     support / resistance levels from recent local highs and lows
  * anchor:     distance to a long moving average (mean-reversion target)
  * momentum:   recent trend, as an annualised velocity
  * earnings:   whether an earnings date falls inside the forecast horizon
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# volatility
# ----------------------------------------------------------------------------


def ewma_variance(r1: np.ndarray, lam: float = 0.94) -> np.ndarray:
    """Daily EWMA variance.  v[i] uses r1[0..i], i.e. it is known at the close
    that ends return r1[i]."""
    return pd.Series(r1**2).ewm(alpha=1 - lam, adjust=False).mean().values


def garch11_fit(r1: np.ndarray) -> tuple[float, float, float]:
    """GARCH(1,1) by MLE on demeaned daily returns.  Returns (omega, alpha, beta)."""
    from scipy.optimize import minimize

    r = r1 - r1.mean()
    v0 = float(r.var())

    def nll(u: np.ndarray) -> float:
        a = 0.3 / (1 + np.exp(-u[0]))  # alpha in (0, 0.3)
        b = 0.999 / (1 + np.exp(-u[1]))  # beta in (0, 0.999)
        if a + b >= 0.999:
            return 1e30
        w = v0 * (1 - a - b)
        v = np.empty(len(r))
        v[0] = v0
        for i in range(1, len(r)):
            v[i] = w + a * r[i - 1] ** 2 + b * v[i - 1]
        return float(0.5 * np.sum(np.log(v) + r**2 / v))

    best = None
    for u0 in ([np.log(0.08 / 0.22), np.log(0.9 / 0.099)], [np.log(0.05 / 0.25), np.log(0.8 / 0.199)]):
        res = minimize(nll, u0, method="Nelder-Mead", options={"maxiter": 400, "xatol": 1e-4, "fatol": 1e-6})
        if best is None or res.fun < best.fun:
            best = res
    a = 0.3 / (1 + np.exp(-best.x[0]))
    b = 0.999 / (1 + np.exp(-best.x[1]))
    return float(v0 * (1 - a - b)), float(a), float(b)


def garch11_filter(r1: np.ndarray, omega: float, alpha: float, beta: float, v0: float | None = None) -> np.ndarray:
    """Conditional variance path.  v[i] is the variance of r1[i] given r1[:i]."""
    r = r1 - r1.mean()
    v = np.empty(len(r))
    v[0] = v0 if v0 is not None else omega / max(1 - alpha - beta, 1e-6)
    for i in range(1, len(r)):
        v[i] = omega + alpha * r[i - 1] ** 2 + beta * v[i - 1]
    return v


def garch11_horizon_variance(v_next: float, omega: float, alpha: float, beta: float, H: int) -> float:
    """Sum of expected daily variances over the next H days, given tomorrow's variance."""
    vl = omega / max(1 - alpha - beta, 1e-6)
    phi = alpha + beta
    return float(sum(vl + phi**h * (v_next - vl) for h in range(H)))


class VolModel:
    """Forecast of the H-day return standard deviation at every close.

    s[t] = std of (lp[t+H] - lp[t]) as seen at close t.  Only r1[:t] is used,
    where r1[i] = lp[i+1] - lp[i], so r1[t-1] is the last return known at close t."""

    def __init__(self, r1: np.ndarray, H: int, mode: str = "ewma", fit_slice: slice | None = None, lam: float = 0.94):
        self.mode, self.H = mode, H
        if mode == "ewma":
            v = ewma_variance(r1, lam)  # v[i] uses r1[..i], known at close i+1
            self.s = np.sqrt(np.maximum(v * H, 1e-12))  # after the final shift below: s[t] = sqrt(H v[t-1])
            self.params = (lam,)
        elif mode == "garch":
            sl = fit_slice if fit_slice is not None else slice(0, len(r1))
            w, a, b = garch11_fit(r1[sl])
            v = garch11_filter(r1, w, a, b)  # v[i] = var of r1[i]; var of r1[t] is known at close t
            vnext = np.concatenate([[v[0]], w + a * (r1[:-1] - r1.mean()) ** 2 + b * v[:-1]])  # var of r1[t] given r1[:t]
            self.s = np.sqrt(np.maximum(np.array([garch11_horizon_variance(x, w, a, b, H) for x in vnext]), 1e-12))
            self.params = (w, a, b)
        else:
            raise ValueError(mode)
        # s is indexed like lp: s[t] is the forecast std at close t (len = len(r1) + 1)
        self.s = np.concatenate([[self.s[0]], self.s])


# ----------------------------------------------------------------------------
# potential features
# ----------------------------------------------------------------------------


def pivot_levels(lp: np.ndarray, t: int, lookback: int = 120, order: int = 8, max_levels: int = 6) -> list[float]:
    """Log-price levels of recent local highs / lows (support & resistance),
    most recent first, using prices up to and including index t."""
    from scipy.signal import argrelextrema

    w = lp[max(0, t - lookback) : t + 1]
    if len(w) < 2 * order + 5:
        return []
    hi = argrelextrema(w, np.greater_equal, order=order)[0]
    lo = argrelextrema(w, np.less_equal, order=order)[0]
    idx = sorted(set(hi.tolist()) | set(lo.tolist()), reverse=True)
    idx = [i for i in idx if i < len(w) - order]  # an extreme needs `order` bars on both sides
    return [float(w[i]) for i in idx[:max_levels]]


def levels_in_z(levels: list[float], lp_t: float, s_t: float, zmin: float = 0.3, zmax: float = 5.0, width: float = 0.25):
    """Barriers for Potential.levels in standardised units (height 1, scaled by level_scale)."""
    out = []
    for lv in levels:
        z = (lv - lp_t) / s_t
        if zmin <= abs(z) <= zmax:
            out.append((float(z), 1.0, width))
    return out


def anchor_z(lp: np.ndarray, t: int, s_t: float, window: int = 200) -> float:
    """Distance to the long moving average of log price, in standardised units."""
    if t < window:
        return 0.0
    return float((lp[t - window + 1 : t + 1].mean() - lp[t]) / s_t)


def momentum_velocity(lp: np.ndarray, t: int, days: int = 20) -> float:
    """Annualised log-return velocity over the last `days` days (known at close t)."""
    if t < days:
        return 0.0
    return float((lp[t] - lp[t - days]) * 252.0 / days)


# ----------------------------------------------------------------------------
# earnings dates
# ----------------------------------------------------------------------------


def load_earnings_dates(ticker: str, data_dir: str) -> pd.DatetimeIndex:
    """Earnings announcement dates from Yahoo (cached).  Empty for ETFs or on failure."""
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"{ticker}_earnings.csv")
    if not os.path.exists(path):
        dates: list = []
        try:
            import yfinance as yf

            ed = yf.Ticker(ticker).get_earnings_dates(limit=120)
            if ed is not None and len(ed):
                dates = sorted(set(pd.to_datetime(ed.index).tz_localize(None).normalize()))
        except Exception:
            dates = []
        pd.Series(dates, name="date").to_csv(path, index=False)
    s = pd.read_csv(path)
    if "date" not in s or s.empty:
        return pd.DatetimeIndex([])
    return pd.DatetimeIndex(pd.to_datetime(s["date"])).normalize()


def earnings_in_window(dates: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    """True if an earnings date falls in (start, end]  (announcement after close `start` or later, up to `end`)."""
    if len(dates) == 0:
        return False
    return bool(((dates > start.normalize()) & (dates <= end.normalize())).any()) or bool((dates == start.normalize()).any())
