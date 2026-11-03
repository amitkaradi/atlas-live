"""
How well does QPM forecast the SIZE of next week's move?  Run after real_test.py:
    python swing_test.py

Reuses the yearly fits in results/fits.csv (no re-calibration) and the same
walk-forward forecast dates.  For every forecast and model it records
  * PIT = model CDF at the realised return (uniform if the model is calibrated)
  * predicted typical move  E|y - median|
  * the 5% and 1% downside VaR thresholds
and reports interval coverage, VaR breach rates, whether bigger predicted
swings line up with bigger realised swings, and how the worst weeks were rated.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import special, stats

from qpm import Potential, QPMParams, QuantumPriceModel
from real_test import EWMA_LAMBDA, FIG, H, L, N, OUT, STEPS, TRAIN_DAYS, T, load

MODELS = ["gauss", "student_t", "qpm", "ewma_gauss", "ewma_t", "ewma_qpm"]
LABEL = {"gauss": "Gaussian (BS)", "student_t": "Student-t", "qpm": "QPM",
         "ewma_gauss": "EWMA Gaussian", "ewma_t": "EWMA Student-t", "ewma_qpm": "EWMA QPM"}


def t_abs_mean(df: float) -> float:
    """E|T| for a unit-scale Student-t."""
    return float(2 * np.sqrt(df) * np.exp(special.gammaln((df + 1) / 2) - special.gammaln(df / 2)) / (np.sqrt(np.pi) * (df - 1)))


class Dist:
    """A forecast distribution: cdf, quantile, and typical absolute move, stretched by s around mu."""

    def __init__(self, cdf, ppf, abs_dev, mu, s=1.0):
        self._cdf, self._ppf, self._abs, self.mu, self.s = cdf, ppf, abs_dev, mu, s

    def cdf(self, y):
        return self._cdf(self.mu + (y - self.mu) / self.s)

    def ppf(self, a):
        return self.mu + (self._ppf(a) - self.mu) * self.s

    def abs_dev(self):
        return self._abs * self.s


def year_models(train: np.ndarray, fit: pd.Series) -> dict:
    mu, sd = float(train.mean()), float(train.std())
    df, loc, sc = stats.t.fit(train)
    p = QPMParams(sigma=fit.sigma, mu=mu / T, sigma0=0.003, theta=fit.theta,
                  potential=Potential(magnet_depth=fit.magnet_depth, magnet_width=fit.magnet_width))
    m = QuantumPriceModel(p, S0=1.0, N=N, L=L).evolve(T, n_steps=STEPS, record_every=STEPS)
    x, dens = m.x, m.density()
    cdf = np.cumsum(dens) * m.dx - 0.5 * dens * m.dx
    med = float(np.interp(0.5, cdf, x))
    return dict(
        mu=mu, sd=sd,
        gauss=(lambda y: stats.norm.cdf(y, mu, sd), lambda a: stats.norm.ppf(a, mu, sd), sd * np.sqrt(2 / np.pi)),
        student_t=(lambda y: stats.t.cdf(y, df, loc, sc), lambda a: stats.t.ppf(a, df, loc, sc), sc * t_abs_mean(df)),
        qpm=(lambda y: np.interp(y, x, cdf, left=0.0, right=1.0), lambda a: np.interp(a, cdf, x),
             float(np.sum(np.abs(x - med) * dens) * m.dx)),
    )


def collect() -> pd.DataFrame:
    fits = pd.read_csv(os.path.join(OUT, "fits.csv"))
    rows = []
    for tk, fg in fits.groupby("ticker"):
        px = load(tk)
        dates, lp = px.index, np.log(px.values)
        r1 = np.diff(lp)
        ewvar = pd.Series(r1**2).ewm(alpha=1 - EWMA_LAMBDA, adjust=False).mean().values
        for _, fit in fg.iterrows():
            idx = np.where(dates.year == fit.year)[0]
            t0 = idx[0]
            i0 = t0 - TRAIN_DAYS
            train = lp[i0 + H : t0 + 1] - lp[i0 : t0 + 1 - H]
            ym = year_models(train, fit)
            for t in range(t0, idx[-1] + 1, H):
                if t + H >= len(lp):
                    break
                y = lp[t + H] - lp[t]
                s = np.sqrt(ewvar[t - 1] * H) / ym["sd"]
                row = dict(ticker=tk, date=dates[t], y=y)
                for name in MODELS:
                    base = {"ewma_t": "student_t"}.get(name, name.replace("ewma_", ""))
                    d = Dist(*ym[base], mu=ym["mu"], s=s if name.startswith("ewma_") else 1.0)
                    row[f"pit_{name}"] = float(d.cdf(y))
                    row[f"abs_{name}"] = d.abs_dev()
                    row[f"med_{name}"] = float(d.ppf(0.5))
                    row[f"var5_{name}"] = float(d.ppf(0.05))
                    row[f"var1_{name}"] = float(d.ppf(0.01))
                rows.append(row)
    return pd.DataFrame(rows)


def kupiec_p(breaches: int, n: int, a: float) -> float:
    """Kupiec unconditional-coverage test p-value (low = breach rate inconsistent with a)."""
    if breaches in (0, n):
        return float("nan")
    ph = breaches / n
    lr = -2 * ((n - breaches) * np.log((1 - a) / (1 - ph)) + breaches * np.log(a / ph))
    return float(1 - stats.chi2.cdf(lr, 1))


def main() -> None:
    pd.set_option("display.width", 200)
    r = collect()
    r.to_csv(os.path.join(OUT, "swing_forecasts.csv"), index=False)
    n = len(r)
    print(f"{n} weekly forecasts, {r['ticker'].nunique()} tickers, {r['date'].min():%Y-%m} to {r['date'].max():%Y-%m}\n")

    print("=== A. Interval coverage: % of weeks the realised move fell inside the forecast band ===")
    cov = {}
    for lvl in (50, 80, 90, 95, 98):
        a = (1 - lvl / 100) / 2
        cov[f"{lvl}% band"] = {LABEL[m]: 100 * ((r[f"pit_{m}"] >= a) & (r[f"pit_{m}"] <= 1 - a)).mean() for m in MODELS}
    print(pd.DataFrame(cov).T.round(1).to_string())

    print("\n=== B. Downside VaR: % of weeks the loss was worse than the forecast threshold ===")
    var = {}
    for m in MODELS:
        b5, b1 = int((r["y"] < r[f"var5_{m}"]).sum()), int((r["y"] < r[f"var1_{m}"]).sum())
        var[LABEL[m]] = {"5% VaR breaches %": 100 * b5 / n, "Kupiec p (5%)": kupiec_p(b5, n, 0.05),
                         "1% VaR breaches %": 100 * b1 / n, "Kupiec p (1%)": kupiec_p(b1, n, 0.01)}
    print(pd.DataFrame(var).T.round(3).to_string())

    print("\n=== C. Does a bigger predicted swing mean a bigger actual swing? ===")
    print("Spearman rank correlation of predicted typical move vs realised |move - median|, and the")
    print("ratio of average realised to average predicted move (1.00 = right size on average).")
    sk = {}
    for m in MODELS:
        real = (r["y"] - r[f"med_{m}"]).abs()
        sk[LABEL[m]] = {"rank corr": stats.spearmanr(r[f"abs_{m}"], real).statistic,
                        "realised/predicted": real.mean() / r[f"abs_{m}"].mean(),
                        "mean abs error of size (pct pts)": 100 * (real - r[f"abs_{m}"]).abs().mean()}
    print(pd.DataFrame(sk).T.round(3).to_string())

    print("\n=== D. Calibration by predicted-size quintile (EWMA QPM vs static QPM) ===")
    for m in ("qpm", "ewma_qpm"):
        real = (r["y"] - r[f"med_{m}"]).abs()
        q = pd.qcut(r[f"abs_{m}"].rank(method="first"), 5, labels=["calmest", "2", "3", "4", "wildest"])
        tab = pd.DataFrame({"predicted typical move %": 100 * r[f"abs_{m}"], "actual typical move %": 100 * real,
                            "inside 90% band %": 100 * ((r[f"pit_{m}"] >= 0.05) & (r[f"pit_{m}"] <= 0.95))}).groupby(q, observed=True).mean()
        print(f"\n{LABEL[m]}:")
        print(tab.round(2).to_string())

    print("\n=== E. The 10 worst weeks: what probability did each model give a drop at least that big? ===")
    worst = r.nsmallest(10, "y")
    tab = worst[["ticker", "date", "y"] + [f"pit_{m}" for m in ("gauss", "student_t", "qpm", "ewma_t", "ewma_qpm")]].copy()
    tab["y"] = (np.exp(tab["y"]) - 1) * 100
    tab = tab.rename(columns={"y": "move %"} | {f"pit_{m}": f"1-in-N {LABEL[m]}" for m in MODELS})
    for c in [c for c in tab.columns if c.startswith("1-in-N")]:
        tab[c] = (1 / tab[c].clip(lower=1e-12)).round(0)
    tab["date"] = tab["date"].dt.strftime("%Y-%m-%d")
    print(tab.round(1).to_string(index=False))
    print("  (1-in-N = the model's odds of a week at least this bad; 1e12 = it said essentially impossible)")

    print("\n=== F. Coverage of the 90% band by year (static vs EWMA QPM) ===")
    yr = r.assign(year=r["date"].dt.year)
    print(pd.DataFrame({LABEL[m]: yr.groupby("year").apply(lambda g, m=m: 100 * ((g[f"pit_{m}"] >= 0.05) & (g[f"pit_{m}"] <= 0.95)).mean())
                        for m in ("qpm", "ewma_qpm")}).round(1).T.to_string())

    # figures
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for m, c in (("qpm", "C1"), ("ewma_qpm", "C4"), ("ewma_t", "C3")):
        real = (r["y"] - r[f"med_{m}"]).abs()
        q = pd.qcut(r[f"abs_{m}"].rank(method="first"), 10, labels=False)
        g = pd.DataFrame({"p": r[f"abs_{m}"], "a": real}).groupby(q).mean() * 100
        axes[0].plot(g["p"], g["a"], "o-", color=c, label=LABEL[m])
    lim = axes[0].get_xlim()
    axes[0].plot(lim, lim, "k--", lw=0.8, label="perfect")
    axes[0].set_xlabel("predicted typical weekly move, % (decile average)")
    axes[0].set_ylabel("actual typical weekly move, %")
    axes[0].set_title("Swing size: predicted vs actual")
    axes[0].legend()
    for m, c in (("gauss", "k"), ("qpm", "C1"), ("ewma_qpm", "C4")):
        axes[1].hist(r[f"pit_{m}"], bins=20, range=(0, 1), histtype="step", lw=1.5, color=c, density=True, label=LABEL[m])
    axes[1].axhline(1, color="gray", ls="--", lw=0.8)
    axes[1].set_xlabel("PIT (model CDF at realised return)")
    axes[1].set_title("Calibration: flat = perfect; U-shape = tails too thin")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "R3_swing_size.png"), dpi=130)
    print(f"\nfigure: {os.path.join(FIG, 'R3_swing_size.png')}")


if __name__ == "__main__":
    main()
