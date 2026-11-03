"""
Walk-forward test of the Quantum Price Model on real stock prices.
Run:  python real_test.py [TICKER ...]

Every January the model is re-fitted (MLE, as in demo scenario G) on the
previous 3 years of overlapping 5-day log-returns, then scored on the
following year's non-overlapping 5-day returns it has never seen.

Two questions:
  1. Density: does QPM's forecast distribution fit real returns better than
     Gaussian (Black-Scholes), Student-t, and EWMA-volatility benchmarks?
     Scored by out-of-sample log-likelihood and 90% / 98% interval coverage.
  2. Direction: with momentum k0 from the last 20 days, is P(S_T > S0) a
     useful signal?  Hit rate, Brier score, and a long/flat weekly strategy
     vs buy & hold and a plain 20-day momentum rule.  No costs, no slippage.

Prices: Yahoo Finance via yfinance, cached in ./data.  Not investment advice.
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from qpm import Potential, QPMParams, QuantumPriceModel, calibrate, momentum_from_returns

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "figures")

TICKERS = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "JPM", "XOM", "KO"]
H = 5  # forecast horizon, trading days
T = H / 252
TRAIN_DAYS = 756  # 3 years
FIRST_TEST_YEAR = 2014
MOM_DAYS = 20
EWMA_LAMBDA = 0.94  # RiskMetrics
L, N, STEPS = 0.6, 512, 60  # grid: x in [-0.6, 0.6), dx ~ 0.0023
MODELS = ["gauss", "student_t", "qpm", "ewma_gauss", "ewma_t", "ewma_qpm"]


def load(ticker: str) -> pd.Series:
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, f"{ticker}.csv")
    if not os.path.exists(path):
        import yfinance as yf

        df = yf.download(ticker, start="2010-01-01", auto_adjust=True, progress=False)
        s = df["Close"].squeeze().dropna()
        s.name = ticker
        s.to_csv(path)
    s = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
    return s.dropna()


def fit_year(train: np.ndarray) -> dict:
    """Fit all static models on one training window of H-day log-returns."""
    mu, sd = float(train.mean()), float(train.std())
    df, loc, scale = stats.t.fit(train)
    base = QPMParams(
        sigma=sd / np.sqrt(T), mu=mu / T, sigma0=0.003, theta=0.3,
        potential=Potential(magnet_depth=100.0, magnet_width=sd),
    )
    free = {
        "sigma": (0.03, 3.0),
        "theta": (0.0, 0.95),
        "potential.magnet_depth": (0.0, 20000.0),
        "potential.magnet_width": (0.002, 0.2),
    }
    best, _ = calibrate(base, T, free, objective=lambda m: -m.log_likelihood(train), S0=1.0, N=N, L=L, n_steps=STEPS, maxiter=300)
    m = QuantumPriceModel(best, S0=1.0, N=N, L=L).evolve(T, n_steps=STEPS, record_every=STEPS)
    p = np.maximum(m.density(), 1e-300)
    cdf = np.cumsum(p) * m.dx - 0.5 * p * m.dx
    return dict(mu=mu, sd=sd, t=(df, loc, scale), qpm=best, x=m.x, p=p, cdf=cdf, p_up_clim=float((train > 0).mean()))


def qpm_logpdf(f: dict, y: float, s: float = 1.0) -> float:
    """QPM density, optionally stretched by s around the training mean."""
    z = f["mu"] + (y - f["mu"]) / s
    return float(np.log(max(np.interp(z, f["x"], f["p"], left=1e-300, right=1e-300), 1e-300)) - np.log(s))


def qpm_quantile(f: dict, a: float, s: float = 1.0) -> float:
    q = float(np.interp(a, f["cdf"], f["x"]))
    return f["mu"] + (q - f["mu"]) * s


def run_ticker(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    px = load(ticker)
    dates, lp = px.index, np.log(px.values)
    r1 = np.diff(lp)  # r1[i] = lp[i+1] - lp[i]
    ewvar = pd.Series(r1**2).ewm(alpha=1 - EWMA_LAMBDA, adjust=False).mean().values  # ewvar[i] known at close i+1
    rows, fits = [], []
    for year in range(FIRST_TEST_YEAR, dates[-1].year + 1):
        idx = np.where(dates.year == year)[0]
        t0 = idx[0]
        if t0 < TRAIN_DAYS + MOM_DAYS:
            continue
        i0 = t0 - TRAIN_DAYS
        train = lp[i0 + H : t0 + 1] - lp[i0 : t0 + 1 - H]  # returns ending at or before t0
        tic = time.time()
        f = fit_year(train)
        q = f["qpm"]
        fits.append(dict(ticker=ticker, year=year, n_train=len(train), sd=f["sd"], t_df=f["t"][0], sigma=q.sigma,
                         theta=q.theta, magnet_depth=q.potential.magnet_depth, magnet_width=q.potential.magnet_width,
                         fit_sec=round(time.time() - tic, 1)))
        df_, loc_, sc_ = f["t"]
        for t in range(t0, idx[-1] + 1, H):
            if t + H >= len(lp):
                break
            y = lp[t + H] - lp[t]
            s = np.sqrt(ewvar[t - 1] * H) / f["sd"]  # current vol relative to training vol
            row = dict(ticker=ticker, date=dates[t], y=y, vol_ratio=s)
            row["ll_gauss"] = stats.norm.logpdf(y, f["mu"], f["sd"])
            row["ll_student_t"] = stats.t.logpdf(y, df_, loc_, sc_)
            row["ll_qpm"] = qpm_logpdf(f, y)
            row["ll_ewma_gauss"] = stats.norm.logpdf(y, f["mu"], f["sd"] * s)
            row["ll_ewma_t"] = stats.t.logpdf(y, df_, f["mu"] + (loc_ - f["mu"]) * s, sc_ * s)
            row["ll_ewma_qpm"] = qpm_logpdf(f, y, s)
            for a, tag in ((0.05, "90"), (0.01, "98")):
                bands = {
                    "gauss": stats.norm.ppf([a, 1 - a], f["mu"], f["sd"]),
                    "student_t": stats.t.ppf([a, 1 - a], df_, loc_, sc_),
                    "qpm": [qpm_quantile(f, a), qpm_quantile(f, 1 - a)],
                    "ewma_gauss": stats.norm.ppf([a, 1 - a], f["mu"], f["sd"] * s),
                    "ewma_t": stats.t.ppf([a, 1 - a], df_, f["mu"] + (loc_ - f["mu"]) * s, sc_ * s),
                    "ewma_qpm": [qpm_quantile(f, a, s), qpm_quantile(f, 1 - a, s)],
                }
                for k, (lo, hi) in bands.items():
                    row[f"in{tag}_{k}"] = float(lo <= y <= hi)
            # direction: QPM with momentum phase from the last 20 daily returns
            k0 = momentum_from_returns(r1[t - MOM_DAYS : t], q.sigma)
            mm = QuantumPriceModel(replace(q, k0=k0), S0=1.0, N=N, L=L).evolve(T, n_steps=STEPS, record_every=STEPS)
            row["p_up_qpm"] = mm.forecast()["P(S_T > S0)"]
            row["p_up_clim"] = f["p_up_clim"]
            row["mom20"] = lp[t] - lp[t - MOM_DAYS]
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(fits)


def forecast_now(ticker: str) -> dict:
    """Fit on the latest 3 years and forecast the next H days from the last close."""
    px = load(ticker)
    lp = np.log(px.values)
    t0 = len(lp) - 1
    i0 = t0 - TRAIN_DAYS
    f = fit_year(lp[i0 + H : t0 + 1] - lp[i0 : t0 + 1 - H])
    r1 = np.diff(lp)
    k0 = momentum_from_returns(r1[-MOM_DAYS:], f["qpm"].sigma)
    S0 = float(px.iloc[-1])
    fc = QuantumPriceModel(replace(f["qpm"], k0=k0), S0=S0, N=N, L=L).evolve(T, n_steps=STEPS).forecast()
    return dict(ticker=ticker, as_of=f"{px.index[-1]:%Y-%m-%d}", close=S0, median=fc["median_S"], q05=fc["quantiles_S"][0.05],
                q95=fc["quantiles_S"][0.95], p_up=fc["P(S_T > S0)"], VaR95=fc["VaR_95"], last20d=float(lp[-1] - lp[-1 - MOM_DAYS]))


def strategy_stats(r: np.ndarray) -> dict:
    per_year = 252 / H
    eq = np.cumsum(r)
    return dict(
        total_ret=float(np.exp(eq[-1]) - 1),
        cagr=float(np.exp(eq[-1] * per_year / len(r)) - 1),
        sharpe=float(r.mean() / r.std() * np.sqrt(per_year)) if r.std() > 0 else 0.0,
        max_dd=float(1 - np.exp((eq - np.maximum.accumulate(np.maximum(eq, 0))).min())),
    )


def summarise(rows: pd.DataFrame, fits: pd.DataFrame) -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)

    print("\n================ 1. DENSITY FORECAST (out-of-sample, 5-day returns) ================")
    print("Mean log-likelihood per forecast, minus Gaussian (Black-Scholes).  > 0 = better than BS.\n")
    ll = rows.groupby("ticker")[[f"ll_{m}" for m in MODELS]].mean()
    ll = ll.sub(ll["ll_gauss"], axis=0).drop(columns="ll_gauss")
    ll.columns = [c[3:] for c in ll.columns]
    ll.loc["ALL"] = rows[[f"ll_{m}" for m in MODELS]].mean().sub(rows["ll_gauss"].mean()).drop("ll_gauss").values
    print(ll.round(4).to_string())
    print(f"\n  ({len(rows)} weekly forecasts, {rows['date'].min():%Y-%m} to {rows['date'].max():%Y-%m})")

    print("\nInterval coverage, all tickers (target 90% and 98%):")
    cov = pd.DataFrame({m: [rows[f"in90_{m}"].mean(), rows[f"in98_{m}"].mean()] for m in MODELS}, index=["90% band", "98% band"])
    print((cov * 100).round(1).to_string())

    # paired test: is QPM's per-forecast log-lik gain significant?
    for a, b in (("qpm", "gauss"), ("qpm", "student_t"), ("ewma_qpm", "ewma_t")):
        d = rows[f"ll_{a}"] - rows[f"ll_{b}"]
        tstat = d.mean() / (d.std() / np.sqrt(len(d)))
        print(f"  {a:>9} vs {b:<10} mean gain {d.mean():+.4f}/forecast, t-stat {tstat:+.2f}")

    print("\nFitted QPM parameters (median over yearly fits):")
    print(fits.groupby("ticker")[["sigma", "theta", "magnet_depth", "magnet_width", "t_df", "fit_sec"]].median().round(3).to_string())

    print("\n================ 2. DIRECTION / TRADING (weekly, long or cash) ================")
    out = []
    for tk, g in list(rows.groupby("ticker")) + [("ALL", rows)]:
        up = (g["y"] > 0).astype(float)
        brier_q = float(((g["p_up_qpm"] - up) ** 2).mean())
        brier_c = float(((g["p_up_clim"] - up) ** 2).mean())
        hit = float(((g["p_up_qpm"] > 0.5) == (g["y"] > 0)).mean())
        rec = dict(ticker=tk, hit_rate=hit, brier_qpm=brier_q, brier_clim=brier_c, pct_long=float((g["p_up_qpm"] > 0.5).mean()))
        if tk != "ALL":
            for name, pos in (("bh", np.ones(len(g))), ("qpm", (g["p_up_qpm"] > 0.5).values), ("mom", (g["mom20"] > 0).values)):
                st = strategy_stats(g["y"].values * pos)
                rec[f"{name}_cagr"], rec[f"{name}_sharpe"], rec[f"{name}_maxdd"] = st["cagr"], st["sharpe"], st["max_dd"]
        out.append(rec)
    print(pd.DataFrame(out).set_index("ticker").round(3).to_string())
    print("\n  bh = buy & hold, qpm = long when QPM P(up) > 0.5, mom = long when 20-day return > 0.  No costs.")

    # figures
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ll.drop(index="ALL").plot.bar(ax=ax)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("mean log-lik gain vs Gaussian")
    ax.set_title("Out-of-sample 5-day density forecasts, 2014 onward")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "R1_loglik_vs_gaussian.png"), dpi=130)

    tks = sorted(rows["ticker"].unique())
    fig, axes = plt.subplots(2, (len(tks) + 1) // 2, figsize=(14, 6), sharex=True)
    for ax, tk in zip(axes.flat, tks):
        g = rows[rows["ticker"] == tk].set_index("date")
        ax.plot(np.exp(g["y"].cumsum()), "k", lw=1, label="buy & hold")
        ax.plot(np.exp((g["y"] * (g["p_up_qpm"] > 0.5)).cumsum()), lw=1, label="QPM long/flat")
        ax.plot(np.exp((g["y"] * (g["mom20"] > 0)).cumsum()), lw=1, alpha=0.7, label="20d momentum")
        ax.set_yscale("log")
        ax.set_title(tk)
    axes.flat[0].legend(fontsize=7)
    fig.suptitle("Growth of $1, weekly rebalanced, no costs")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "R2_equity_curves.png"), dpi=130)


def main() -> None:
    tickers = [a.upper() for a in sys.argv[1:]] or TICKERS
    os.makedirs(OUT, exist_ok=True)
    for tk in tickers:  # download sequentially, before the workers start
        s = load(tk)
        print(f"{tk}: {len(s)} days {s.index[0]:%Y-%m-%d} .. {s.index[-1]:%Y-%m-%d}, last close {s.iloc[-1]:.2f}")
    tic = time.time()
    with ProcessPoolExecutor(max_workers=min(len(tickers), os.cpu_count() or 1)) as ex:
        res = list(ex.map(run_ticker, tickers))
    rows = pd.concat([r for r, _ in res], ignore_index=True)
    fits = pd.concat([f for _, f in res], ignore_index=True)
    rows.to_csv(os.path.join(OUT, "forecasts.csv"), index=False)
    fits.to_csv(os.path.join(OUT, "fits.csv"), index=False)
    print(f"\nwalk-forward done in {time.time() - tic:.0f}s")
    summarise(rows, fits)

    print(f"\n================ 3. FORECAST FROM THE LAST CLOSE (next {H} trading days) ================")
    with ProcessPoolExecutor(max_workers=min(len(tickers), os.cpu_count() or 1)) as ex:
        now = pd.DataFrame(list(ex.map(forecast_now, tickers))).set_index("ticker")
    now.to_csv(os.path.join(OUT, "forecast_now.csv"))
    print(now.round(3).to_string())
    print(f"\nresults in {OUT}, figures R1/R2 in {FIG}")


if __name__ == "__main__":
    main()
