"""
QPM v2 walk-forward ablation on real stock prices.

    python backtest.py                       # 8 default tickers, EWMA vol, full run (~1-2 h on 4 cores)
    python backtest.py --quick               # smoke test: 2 tickers, 2020 onward, fewer iterations (~10 min)
    python backtest.py --vol garch           # GARCH(1,1) volatility instead of EWMA
    python backtest.py SPY AAPL --workers 2  # any tickers

Every January the model is fitted on the previous 3 years and scored on the
following year, which it never saw.  Features are switched on one at a time
(an ablation) so each one's value is measured separately:

    A_static   v1 model (sigma, theta, magnet) on raw returns, now with the comoving potential
    B_vol      same, fitted on vol-standardised returns  (volatility inside the model)
    C_mix      + mixed state over the mass (nu)          (power-law tails)
    D_mom      C + momentum as a decaying drift, scale fitted
    E_levels   C + support / resistance barriers from pivots, height fitted
    F_anchor   C + mean reversion to the 200-day average, strength fitted
    G_earn     C + earnings weeks: same vol multiplier as the benchmark + a double well, depth fitted
    H_full     C + every fitted feature together

Benchmarks: Gaussian, Student-t, vol-scaled Gaussian / Student-t, and vol-scaled
Student-t with an earnings-week multiplier (the fair rival for G_earn).

Outputs: results/v2_forecasts.csv, results/v2_fits.csv, results/v2_summary.txt,
figures/R4_ablation.png, figures/R5_pit_v2.png.  Not investment advice.
"""

from __future__ import annotations

import argparse
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

from features import VolModel, anchor_z, earnings_in_window, levels_in_z, load_earnings_dates, momentum_velocity, pivot_levels
from qpm import Potential, QPMParams, build_model, calibrate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "figures")

TICKERS = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "JPM", "XOM", "KO"]
H = 5
T = H / 252
TRAIN_DAYS = 756
FIRST_TEST_YEAR = 2014
MOM_DAYS = 20
COST = 0.001  # per side, for the trading test

# grids.  Raw-return grid for A_static; standardised grid (units of forecast sd) for everything else
L_RAW, L_Z = 0.6, 10.0
N, STEPS = 320, 40
K_MIX = 7

CONFIGS = ["A_static", "B_vol", "C_mix", "D_mom", "E_levels", "F_anchor", "G_earn", "H_full"]
BENCH = ["gauss", "student_t", "vol_gauss", "vol_t", "vol_t_earn"]
MODELS = BENCH + CONFIGS

GRID_MOM = [0.0, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0]  # k0_scale: fraction of the 20-day velocity that persists
GRID_LEVEL = [0.0, 10.0, 25.0, 50.0, 100.0, 200.0]  # barrier height (energy units, 1/T ~ 50)
GRID_ANCHOR = [0.0, 2.0, 5.0, 10.0, 20.0, 50.0]  # lam of the harmonic well around the 200d average
GRID_EARN = [0.0, 5.0, 15.0, 40.0, 100.0]  # double-well depth in earnings weeks


# ----------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------


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


# ----------------------------------------------------------------------------
# fitting
# ----------------------------------------------------------------------------


def evolve(params: QPMParams, L: float):
    return build_model(params, S0=1.0, N=N, L=L).evolve(T, n_steps=STEPS, record_every=STEPS)


def grid_logpdf(x: np.ndarray, p: np.ndarray, z: float) -> float:
    """log p(z) from a grid density; beyond the grid the log-density is continued
    linearly from the slope over the outer 10% of points (exponential tail)."""
    if x[0] <= z <= x[-1]:
        return float(np.log(max(np.interp(z, x, p), 1e-300)))
    k = max(len(x) // 10, 2)
    lp = np.log(np.maximum(p, 1e-300))
    if z > x[-1]:
        slope = (lp[-1] - lp[-k]) / (x[-1] - x[-k])
        return float(lp[-1] + min(slope, 0.0) * (z - x[-1]))
    slope = (lp[k - 1] - lp[0]) / (x[k - 1] - x[0])
    return float(lp[0] - max(slope, 0.0) * (x[0] - z))


def density_fn(params: QPMParams, L: float):
    """Returns (x, p, cdf) of the evolved model."""
    m = evolve(params, L)
    p = np.maximum(m.density(), 1e-300)
    return m.x, p, np.cumsum(p) * m.dx - 0.5 * p * m.dx


def fit_static(train: np.ndarray, L: float, with_mix: bool, maxiter: int) -> QPMParams:
    """Unconditional MLE of (sigma, theta, [nu], magnet) on a set of returns on grid [-L, L)."""
    sd = float(train.std())
    scale = 1.0 / np.sqrt(T)
    base = QPMParams(sigma=sd * scale, mu=0.0, sigma0=0.1 * sd, theta=0.5, nu=6.0 if with_mix else np.inf, n_mix=K_MIX,
                     potential=Potential(magnet_depth=50.0 / T * 0.5, magnet_width=sd))
    free = {
        "sigma": (0.3 * sd * scale, 3.0 * sd * scale),
        "theta": (0.2, 0.85),
        "potential.magnet_depth": (0.0, 100.0 / T),
        "potential.magnet_width": (0.1 * sd, 3.0 * sd),
    }
    if with_mix:
        free["nu"] = (2.5, 60.0)
    best, _ = calibrate(base, T, free, objective=lambda m: -m.log_likelihood(train), S0=1.0, N=N, L=L, n_steps=STEPS,
                        maxiter=maxiter, starts=[{"theta": 0.7, "potential.magnet_depth": 10.0 / T}])
    return best


def grid_fit(base: QPMParams, groups: list[tuple[np.ndarray, "callable"]], grid: list[float]) -> tuple[float, list[float]]:
    """Pick the grid value maximising the summed log-likelihood over groups.
    Each group is (returns, make_params(value) -> QPMParams).  Returns (best value, ll per grid value)."""
    lls = []
    for g in grid:
        ll = 0.0
        for z, make in groups:
            x, p, _ = density_fn(make(g), L_Z)
            ll += float(np.sum(np.log(np.interp(z, x, p, left=1e-300, right=1e-300))))
        lls.append(ll)
    return grid[int(np.argmax(lls))], lls


def bin_groups(z: np.ndarray, feature: np.ndarray, nbins: int = 5) -> list[tuple[np.ndarray, float]]:
    """Split training returns into quantile bins of a feature; each bin uses the bin-mean feature."""
    q = pd.qcut(pd.Series(feature).rank(method="first"), nbins, labels=False).values
    return [(z[q == b], float(feature[q == b].mean())) for b in range(nbins) if (q == b).any()]


# ----------------------------------------------------------------------------
# one ticker, walk-forward
# ----------------------------------------------------------------------------


def run_ticker(args: tuple) -> tuple[pd.DataFrame, pd.DataFrame]:
    ticker, vol_mode, first_year, maxiter, n_sub = args
    px = load(ticker)
    dates, lp = px.index, np.log(px.values)
    n = len(lp)
    r1 = np.diff(lp)
    earn = load_earnings_dates(ticker, DATA)
    has_earn = len(earn) > 0
    rows, fits = [], []
    rng = np.random.default_rng(0)

    for year in range(first_year, dates[-1].year + 1):
        idx = np.where(dates.year == year)[0]
        if len(idx) == 0:
            continue
        t0 = idx[0]
        if t0 < TRAIN_DAYS + 200:
            continue
        i0 = t0 - TRAIN_DAYS
        tic = time.time()

        # volatility model: fitted (GARCH) on the training window only, filtered forward through the test year
        vm = VolModel(r1[: idx[-1] + 1], H, mode=vol_mode, fit_slice=slice(i0, t0))
        s = vm.s  # s[t] = forecast sd of lp[t+H]-lp[t] at close t

        # training set: overlapping H-day returns ending at or before t0 (start index i -> return lp[i+H]-lp[i])
        starts = np.arange(i0, t0 + 1 - H)
        y_tr = lp[starts + H] - lp[starts]
        mu = float(y_tr.mean())
        sd = float(y_tr.std())
        z_tr = (y_tr - mu) / s[starts]
        df_, loc_, sc_ = stats.t.fit(y_tr)
        zdf, zloc, zsc = stats.t.fit(z_tr)

        # earnings-week vol multiplier (benchmark) and earnings-week z's
        if has_earn:
            is_earn_tr = np.array([earnings_in_window(earn, dates[i], dates[i + H]) for i in starts])
        else:
            is_earn_tr = np.zeros(len(starts), bool)
        if is_earn_tr.sum() >= 4:
            earn_mult = float(np.sqrt(np.mean(z_tr[is_earn_tr] ** 2) / np.mean(z_tr[~is_earn_tr] ** 2)))
            earn_xmin = float(np.median(np.abs(z_tr[is_earn_tr])))
        else:
            earn_mult, earn_xmin = 1.0, 0.0

        # --- stage 1: unconditional fits ---------------------------------------
        pA = fit_static(y_tr - mu, L_RAW, with_mix=False, maxiter=maxiter)  # raw returns, centred (A_static)
        pB = fit_static(z_tr, L_Z, with_mix=False, maxiter=maxiter)  # standardised (B_vol)
        pC = fit_static(z_tr, L_Z, with_mix=True, maxiter=maxiter)  # standardised + mixture (C_mix)

        # --- stage 2: conditional features on top of C, each by grid search --------
        # momentum: v in standardised units = k0_scale * velocity / s
        vel_tr = np.array([momentum_velocity(lp, i, MOM_DAYS) for i in starts]) / s[starts]
        groups = [(zb, (lambda g, v=vb: replace(pC, v_mom=g * v))) for zb, vb in bin_groups(z_tr, vel_tr)]
        k0_scale, ll_mom = grid_fit(pC, groups, GRID_MOM)

        # anchor: harmonic well centred on the 200-day average (in z units)
        anc_tr = np.array([anchor_z(lp, i, s[i]) for i in starts])
        groups = [(zb, (lambda g, a=ab: replace(pC, potential=replace(pC.potential, lam=g, x_f=a)))) for zb, ab in bin_groups(z_tr, anc_tr)]
        lam_anchor, ll_anc = grid_fit(pC, groups, GRID_ANCHOR)

        # levels: each training sample has its own barriers -> subsample
        sub = rng.choice(len(starts), size=min(n_sub, len(starts)), replace=False)
        groups = []
        for j in sub:
            i = starts[j]
            lv = levels_in_z(pivot_levels(lp, i), lp[i], s[i])
            groups.append((z_tr[j : j + 1], (lambda g, lv=lv: replace(pC, potential=replace(pC.potential, levels=lv, level_scale=g)))))
        level_scale, ll_lev = grid_fit(pC, groups, GRID_LEVEL)

        # earnings: double well on earnings weeks only
        # G_earn = C_mix with the same earnings-week vol multiplier as the benchmark, plus a
        # double well (depth fitted, 0 allowed) so that G_earn vs vol_t_earn tests the SHAPE
        if earn_xmin > 0:
            xm = earn_xmin / earn_mult  # well minima in multiplier-scaled units
            groups = [(z_tr[is_earn_tr] / earn_mult, (lambda g: replace(pC, potential=replace(pC.potential, quartic=Potential.double_well(g, xm)))))]
            earn_depth, ll_earn = grid_fit(pC, groups, GRID_EARN)
        else:
            earn_depth, ll_earn = 0.0, []

        fits.append(dict(
            ticker=ticker, year=year, n_train=len(z_tr), sd=sd, t_df=df_, zt_df=zdf, vol_mode=vol_mode,
            A_sigma=pA.sigma, A_theta=pA.theta, A_depth=pA.potential.magnet_depth, A_width=pA.potential.magnet_width,
            B_sigma=pB.sigma, B_theta=pB.theta, B_depth=pB.potential.magnet_depth, B_width=pB.potential.magnet_width,
            C_sigma=pC.sigma, C_theta=pC.theta, C_nu=pC.nu, C_depth=pC.potential.magnet_depth, C_width=pC.potential.magnet_width,
            k0_scale=k0_scale, lam_anchor=lam_anchor, level_scale=level_scale, earn_depth=earn_depth, earn_xmin=earn_xmin,
            earn_mult=earn_mult, n_earn_train=int(is_earn_tr.sum()),
            ll_mom_grid=" ".join(f"{v:.1f}" for v in ll_mom), ll_anchor_grid=" ".join(f"{v:.1f}" for v in ll_anc),
            ll_level_grid=" ".join(f"{v:.1f}" for v in ll_lev), ll_earn_grid=" ".join(f"{v:.1f}" for v in ll_earn),
            fit_sec=round(time.time() - tic, 1),
        ))

        # static densities (one per year)
        dA = density_fn(pA, L_RAW)
        dB = density_fn(pB, L_Z)
        dC = density_fn(pC, L_Z)

        # --- scoring: non-overlapping weeks of the test year --------------------
        for t in range(t0, idx[-1] + 1, H):
            if t + H >= n:
                break
            y = lp[t + H] - lp[t]
            st = s[t]
            z = (y - mu) / st
            is_earn = has_earn and earnings_in_window(earn, dates[t], dates[t + H])
            row = dict(ticker=ticker, date=dates[t], y=y, s=st, mu=mu, z=z, is_earn=int(is_earn),
                       vel=momentum_velocity(lp, t, MOM_DAYS), anchor=anchor_z(lp, t, st))

            def score(name: str, x: np.ndarray, p: np.ndarray, cdf: np.ndarray, scale: float, centre: float, logpdf=None, cdf_fn=None) -> None:
                """Record ll, PIT, VaR, typical move and P(up) for a density in units (y - centre)/scale.
                Grid densities are extrapolated exponentially beyond the grid (log-linear tail)."""
                zz = (y - centre) / scale
                if logpdf is not None:
                    row[f"ll_{name}"] = float(logpdf(zz) - np.log(scale))
                    row[f"pit_{name}"] = float(cdf_fn(zz))
                else:
                    row[f"ll_{name}"] = float(grid_logpdf(x, p, zz) - np.log(scale))
                    row[f"pit_{name}"] = float(np.interp(zz, x, cdf, left=0.0, right=1.0))
                q = lambda a: centre + scale * float(np.interp(a, cdf, x))
                row[f"var5_{name}"], row[f"var1_{name}"], row[f"med_{name}"] = q(0.05), q(0.01), q(0.5)
                med = float(np.interp(0.5, cdf, x))
                row[f"abs_{name}"] = scale * float(np.sum(np.abs(x - med) * p) * (x[1] - x[0]))
                row[f"pup_{name}"] = float(1.0 - np.interp((0.0 - centre) / scale, x, cdf, left=0.0, right=1.0))

            # benchmarks (closed form)
            xg = np.linspace(-L_Z, L_Z, 2001)
            for name, dist, sc in (("gauss", stats.norm(0, sd), sd), ("student_t", stats.t(df_, loc_ - mu, sc_), sd)):
                score(name, xg * sc, dist.pdf(xg * sc), dist.cdf(xg * sc), 1.0, mu, dist.logpdf, dist.cdf)
            tz = stats.t(zdf, zloc, zsc)
            score("vol_gauss", xg, stats.norm.pdf(xg), stats.norm.cdf(xg), st, mu, stats.norm.logpdf, stats.norm.cdf)
            score("vol_t", xg, tz.pdf(xg), tz.cdf(xg), st, mu, tz.logpdf, tz.cdf)
            em = earn_mult if is_earn else 1.0
            score("vol_t_earn", xg, tz.pdf(xg), tz.cdf(xg), st * em, mu, tz.logpdf, tz.cdf)

            # QPM configs
            score("A_static", *dA, 1.0, mu)
            score("B_vol", *dB, st, mu)
            score("C_mix", *dC, st, mu)
            v = k0_scale * row["vel"] / st
            score("D_mom", *density_fn(replace(pC, v_mom=v), L_Z), st, mu)
            lv = levels_in_z(pivot_levels(lp, t), lp[t], st)
            score("E_levels", *density_fn(replace(pC, potential=replace(pC.potential, levels=lv, level_scale=level_scale)), L_Z), st, mu)
            score("F_anchor", *density_fn(replace(pC, potential=replace(pC.potential, lam=lam_anchor, x_f=row["anchor"])), L_Z), st, mu)
            qw = Potential.double_well(earn_depth, earn_xmin / earn_mult) if (is_earn and earn_xmin > 0) else (0.0, 0.0)
            score("G_earn", *density_fn(replace(pC, potential=replace(pC.potential, quartic=qw)), L_Z), st * em, mu)
            # full: every feature, in the earnings-scaled frame on earnings weeks
            lv_e = [(zj / em, hj, wj) for zj, hj, wj in lv]
            pot = replace(pC.potential, levels=lv_e, level_scale=level_scale, lam=lam_anchor * em**2, x_f=row["anchor"] / em, quartic=qw)
            score("H_full", *density_fn(replace(pC, v_mom=v / em, potential=pot), L_Z), st * em, mu)
            row["n_levels"] = len(lv)
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(fits)


# ----------------------------------------------------------------------------
# summary
# ----------------------------------------------------------------------------


def kupiec_p(breaches: int, n: int, a: float) -> float:
    if breaches in (0, n):
        return float("nan")
    ph = breaches / n
    lr = -2 * ((n - breaches) * np.log((1 - a) / (1 - ph)) + breaches * np.log(a / ph))
    return float(1 - stats.chi2.cdf(lr, 1))


def strategy(r: np.ndarray, pos: np.ndarray, cost: float = COST) -> dict:
    trades = np.abs(np.diff(np.concatenate([[0.0], pos])))
    net = r * pos - cost * trades
    eq = np.cumsum(net)
    per_year = 252 / H
    return dict(cagr=float(np.exp(eq[-1] * per_year / len(r)) - 1), sharpe=float(net.mean() / net.std() * np.sqrt(per_year)) if net.std() > 0 else 0.0,
                maxdd=float(1 - np.exp((eq - np.maximum.accumulate(np.maximum(eq, 0))).min())), pct_long=float((pos > 0).mean()), pct_short=float((pos < 0).mean()))


def summarise(rows: pd.DataFrame, fits: pd.DataFrame, vol_mode: str, elapsed: float) -> str:
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 40)
    out = []
    P = out.append
    n = len(rows)
    P(f"QPM v2 ablation.  {n} weekly forecasts, {rows['ticker'].nunique()} tickers, {rows['date'].min():%Y-%m} to {rows['date'].max():%Y-%m}, vol={vol_mode}, {elapsed/60:.0f} min")

    P("\n=== 1. Density: mean out-of-sample log-likelihood per forecast, relative to vol-scaled Student-t (vol_t) ===")
    P("    > 0 means better than the best v1 benchmark.")
    ll = rows.groupby("ticker")[[f"ll_{m}" for m in MODELS]].mean()
    ll = ll.sub(ll["ll_vol_t"], axis=0)
    ll.columns = [c[3:] for c in ll.columns]
    ll.loc["ALL"] = rows[[f"ll_{m}" for m in MODELS]].mean().sub(rows["ll_vol_t"].mean()).values
    P(ll.round(4).to_string())

    P("\nPaired t-stats of per-forecast log-likelihood differences (|t| > 2 is significant):")
    pairs = [("A_static", "gauss"), ("B_vol", "A_static"), ("C_mix", "B_vol"), ("C_mix", "vol_t"), ("D_mom", "C_mix"), ("E_levels", "C_mix"),
             ("F_anchor", "C_mix"), ("G_earn", "C_mix"), ("G_earn", "vol_t_earn"), ("H_full", "C_mix"), ("H_full", "vol_t"), ("H_full", "vol_t_earn")]
    for a, b in pairs:
        d = rows[f"ll_{a}"] - rows[f"ll_{b}"]
        tstat = d.mean() / (d.std() / np.sqrt(len(d))) if d.std() > 0 else float("nan")
        P(f"  {a:>9} vs {b:<11} mean {d.mean():+.4f}  t = {tstat:+.2f}   better on {int((d.groupby(rows['ticker']).mean() > 0).sum())}/{rows['ticker'].nunique()} tickers")
    if rows["is_earn"].sum() > 0:
        e = rows[rows["is_earn"] == 1]
        P(f"\nEarnings weeks only ({len(e)} forecasts): mean ll relative to vol_t")
        P(e[[f"ll_{m}" for m in ("vol_t", "vol_t_earn", "C_mix", "G_earn", "H_full")]].mean().sub(e["ll_vol_t"].mean()).round(4).to_string())

    P("\n=== 2. Calibration: interval coverage % (target in header) and downside VaR breaches % ===")
    tab = {}
    for m in MODELS:
        pit = rows[f"pit_{m}"]
        rec = {f"{lvl}%": 100 * ((pit >= (1 - lvl / 100) / 2) & (pit <= 1 - (1 - lvl / 100) / 2)).mean() for lvl in (50, 90, 98)}
        b5, b1 = int((rows["y"] < rows[f"var5_{m}"]).sum()), int((rows["y"] < rows[f"var1_{m}"]).sum())
        rec["VaR5 breach%"], rec["Kupiec p5"] = 100 * b5 / n, kupiec_p(b5, n, 0.05)
        rec["VaR1 breach%"], rec["Kupiec p1"] = 100 * b1 / n, kupiec_p(b1, n, 0.01)
        real = (rows["y"] - rows[f"med_{m}"]).abs()
        rec["size rank corr"] = stats.spearmanr(rows[f"abs_{m}"], real).statistic
        rec["realised/pred size"] = real.mean() / rows[f"abs_{m}"].mean()
        rec["y>median %"] = 100 * (rows["y"] > rows[f"med_{m}"]).mean()
        tab[m] = rec
    P(pd.DataFrame(tab).T.round(3).to_string())

    P("\n=== 3. The 10 worst weeks: 1-in-N odds each model gave a drop at least that bad ===")
    worst = rows.nsmallest(10, "y")
    t = worst[["ticker", "date", "y"]].copy()
    t["move %"] = ((np.exp(t.pop("y")) - 1) * 100).round(1)
    for m in ("gauss", "vol_t", "A_static", "C_mix", "H_full"):
        t[m] = (1 / worst[f"pit_{m}"].clip(lower=1e-12)).round(0).values
    t["date"] = t["date"].dt.strftime("%Y-%m-%d")
    P(t.to_string(index=False))

    P("\n=== 4. Direction (weekly).  Brier vs the training up-rate; long/flat and long/short strategies, 0.1% per trade ===")
    up = (rows["y"] > 0).astype(float)
    clim = rows.groupby("ticker")["y"].transform(lambda g: (g > 0).mean())  # in-sample, generous to the benchmark
    recs = []
    for m in ("vol_t", "C_mix", "D_mom", "F_anchor", "H_full"):
        p = rows[f"pup_{m}"]
        rec = dict(model=m, brier=float(((p - up) ** 2).mean()), brier_clim=float(((clim - up) ** 2).mean()),
                   hit=float(((p > 0.5) == (rows["y"] > 0)).mean()), mean_pup=float(p.mean()))
        lf = [strategy(g["y"].values, (g[f"pup_{m}"] > 0.5).values.astype(float)) for _, g in rows.groupby("ticker")]
        ls = [strategy(g["y"].values, np.sign(g[f"pup_{m}"].values - 0.5)) for _, g in rows.groupby("ticker")]
        rec |= {f"LF {k}": float(np.mean([d[k] for d in lf])) for k in ("cagr", "sharpe", "maxdd", "pct_long")}
        rec |= {f"LS {k}": float(np.mean([d[k] for d in ls])) for k in ("cagr", "sharpe", "maxdd")}
        recs.append(rec)
    bh = [strategy(g["y"].values, np.ones(len(g)), cost=0) for _, g in rows.groupby("ticker")]
    mom = [strategy(g["y"].values, (g["vel"] > 0).values.astype(float)) for _, g in rows.groupby("ticker")]
    recs.append(dict(model="buy&hold", **{f"LF {k}": float(np.mean([d[k] for d in bh])) for k in ("cagr", "sharpe", "maxdd", "pct_long")}))
    recs.append(dict(model="mom20 rule", **{f"LF {k}": float(np.mean([d[k] for d in mom])) for k in ("cagr", "sharpe", "maxdd", "pct_long")}))
    P(pd.DataFrame(recs).set_index("model").round(3).to_string())
    P("  (strategy numbers are averages over tickers; CAGR per ticker, equal weights)")

    P("\n=== 5. Fitted parameters ===")
    cols = ["A_theta", "B_theta", "C_theta", "C_nu", "C_depth", "C_width", "zt_df", "k0_scale", "lam_anchor", "level_scale", "earn_depth", "earn_mult", "fit_sec"]
    P("median over yearly fits:")
    P(fits.groupby("ticker")[cols].median().round(3).to_string())
    P("\nhow often each grid-fitted feature was switched OFF (value 0) in-sample:")
    for c in ("k0_scale", "lam_anchor", "level_scale"):
        P(f"  {c:<12} off in {100 * (fits[c] == 0).mean():.0f}% of fits;  values: {np.sort(fits[c].unique())}")
    fe = fits[fits["earn_xmin"] > 0]
    if len(fe):
        P(f"  earn_depth   off in {100 * (fe['earn_depth'] == 0).mean():.0f}% of {len(fe)} fits with earnings data")
    P(f"  theta at a bound (0.2 or 0.85) in {100 * ((fits['C_theta'] < 0.21) | (fits['C_theta'] > 0.84)).mean():.0f}% of C fits;  nu at 60 in {100 * (fits['C_nu'] > 59).mean():.0f}%")
    P(f"\nmean yearly 'A_static' vs v1: theta median {fits['A_theta'].median():.3f} (v1 was 0.69), depth median {fits['A_depth'].median():.0f}")

    # figures
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ll.drop(index="ALL")[CONFIGS + ["vol_t_earn"]].plot.bar(ax=ax)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("mean log-lik gain vs vol-scaled Student-t")
    ax.set_title(f"QPM v2 ablation, out-of-sample 5-day density forecasts ({vol_mode} vol)")
    ax.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "R4_ablation.png"), dpi=130)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for m, c in (("vol_t", "k"), ("A_static", "C1"), ("C_mix", "C2"), ("H_full", "C4")):
        ax.hist(rows[f"pit_{m}"], bins=20, range=(0, 1), histtype="step", lw=1.5, color=c, density=True, label=m)
    ax.axhline(1, color="gray", ls="--", lw=0.8)
    ax.set_xlabel("PIT")
    ax.set_title("Calibration: flat = perfect; U = tails too thin; hump = too wide")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "R5_pit_v2.png"), dpi=130)
    return "\n".join(out)


# ----------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--vol", choices=["ewma", "garch"], default="ewma")
    ap.add_argument("--quick", action="store_true", help="2 tickers, 2020 onward, fewer iterations")
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--first-year", type=int, default=FIRST_TEST_YEAR)
    ap.add_argument("--maxiter", type=int, default=120)
    ap.add_argument("--n-sub", type=int, default=60, help="training subsample size for the level-height grid fit")
    a = ap.parse_args()
    tickers = [t.upper() for t in a.tickers] or (["SPY", "AAPL"] if a.quick else TICKERS)
    first_year, maxiter, n_sub = (2020, 50, 25) if a.quick else (a.first_year, a.maxiter, a.n_sub)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    for tk in tickers:
        s = load(tk)
        e = load_earnings_dates(tk, DATA)
        print(f"{tk}: {len(s)} days {s.index[0]:%Y-%m-%d} .. {s.index[-1]:%Y-%m-%d}, last close {s.iloc[-1]:.2f}, {len(e)} earnings dates"
              + (f" ({e.min():%Y-%m} .. {e.max():%Y-%m})" if len(e) else ""))
    tic = time.time()
    jobs = [(tk, a.vol, first_year, maxiter, n_sub) for tk in tickers]
    with ProcessPoolExecutor(max_workers=min(len(tickers), a.workers)) as ex:
        res = list(ex.map(run_ticker, jobs))
    rows = pd.concat([r for r, _ in res], ignore_index=True)
    fits = pd.concat([f for _, f in res], ignore_index=True)
    tag = "_quick" if a.quick else ""
    rows.to_csv(os.path.join(OUT, f"v2_forecasts{tag}.csv"), index=False)
    fits.to_csv(os.path.join(OUT, f"v2_fits{tag}.csv"), index=False)
    text = summarise(rows, fits, a.vol, time.time() - tic)
    print(text)
    with open(os.path.join(OUT, f"v2_summary{tag}.txt"), "w") as f:
        f.write(text + "\n")
    print(f"\nwritten: results/v2_forecasts{tag}.csv, results/v2_fits{tag}.csv, results/v2_summary{tag}.txt, figures/R4_ablation.png, figures/R5_pit_v2.png")


if __name__ == "__main__":
    main()
