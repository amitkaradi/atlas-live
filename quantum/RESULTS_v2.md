# QPM v2: backtest results

Run of [`backtest.py`](backtest.py) at commit `ec474f6`, following [`BACKTEST.md`](BACKTEST.md).
Raw outputs:
* EWMA (main): [`results/v2_summary_ewma.txt`](results/v2_summary_ewma.txt), `v2_forecasts_ewma.csv`, `v2_fits_ewma.csv`, [`figures/R4_ablation_ewma.png`](figures/R4_ablation_ewma.png), [`figures/R5_pit_v2_ewma.png`](figures/R5_pit_v2_ewma.png)
* GARCH (robustness): the same files with `_garch`. (`backtest.py` writes unsuffixed `v2_*` names; each run's outputs were renamed with its vol mode.)

Grids, bounds, tickers, train length, horizon and first test year are as shipped. The one code change is below.

> Not investment advice.

## 0. Bug found and fixed before the full runs

`features.load_earnings_dates` called `get_earnings_dates(limit=120)`. yfinance 1.7.0 raises `ValueError: Yahoo caps limit at 100`. The `except` turned that into an empty list and **cached it**, so every stock would have had zero earnings dates. `G_earn` would then have silently equalled `C_mix`, and `vol_t_earn` would have equalled `vol_t`.

Changed to `limit=100` (one line in `features.py`, included in this commit). It returns dates back to 2002, which covers every training window. The `--quick` smoke test ran before the fix (AAPL showed 0 earnings dates). Its caches were deleted before the full runs.

## 1. Feature ablation (EWMA)

Mean out-of-sample log-likelihood per forecast. Paired t-stats; "k/8" = number of tickers where the first model is better.

| Step | Mean gain | t | Better on |
|---|---|---|---|
| A_static vs gauss | +0.0918 | +5.27 | 8/8 |
| B_vol vs A_static | +0.0586 | +6.21 | 8/8 |
| C_mix vs B_vol | +0.0024 | +3.20 | 8/8 |
| **C_mix vs vol_t** | **−0.0020** | **−1.78** | **1/8** |
| D_mom vs C_mix | −0.0006 | −1.02 | 3/8 |
| E_levels vs C_mix | −0.0085 | −5.10 | 0/8 |
| F_anchor vs C_mix | −0.0043 | −2.90 | 2/8 |
| G_earn vs C_mix | +0.0083 | +3.18 | 5/8 |
| **G_earn vs vol_t_earn** | **−0.0025** | **−1.86** | **0/8** |
| H_full vs C_mix | −0.0059 | −1.74 | 1/8 |
| **H_full vs vol_t** | **−0.0079** | **−2.27** | **1/8** |
| H_full vs vol_t_earn | −0.0167 | −6.23 | 0/8 |

Earnings weeks only (364 forecasts), mean log-likelihood relative to vol_t:

| | Gain |
|---|---|
| vol_t_earn | +0.125 |
| G_earn | +0.108 |
| H_full | +0.076 |
| C_mix | −0.010 |

**No configuration beats the vol-scaled Student-t with |t| > 2.** The only significantly different result versus vol_t is H_full, and it is worse (t = −2.27).

* Vol-standardising (B) and the mass mixture (C) are real improvements over v1. C_mix ends up statistically tied with vol_t: slightly worse, better on 1/8 tickers.
* Barriers (E) and the 200-day anchor (F) hurt out of sample.
* Momentum (D) does nothing.
* G_earn's gain over C_mix is the earnings-week vol multiplier, not the double well. G_earn loses to vol_t_earn, which has the same multiplier, on every earnings ticker.
* The best model overall is **vol_t_earn** (+0.0088 vs vol_t), which is not a QPM.

## 2. Calibration (EWMA)

| Model | 50% | 90% | 98% | VaR5 breach % (p) | VaR1 breach % (p) | y > median % | Size rank corr |
|---|---|---|---|---|---|---|---|
| vol_t | 49.3 | 89.1 | 97.7 | 6.83 (0.000) | 1.55 (0.000) | 51.3 | 0.443 |
| vol_t_earn | 50.6 | 90.3 | 98.2 | 6.38 (0.000) | 1.34 (0.020) | 51.3 | 0.454 |
| A_static | 49.1 | 87.9 | 97.0 | 6.67 (0.000) | 1.75 (0.000) | 52.9 | 0.371 |
| C_mix | 49.2 | 89.2 | 97.8 | 6.63 (0.000) | 1.45 (0.002) | 52.9 | 0.443 |
| G_earn | 50.5 | 90.2 | 98.3 | 6.21 (0.000) | **1.26 (0.071)** | 52.9 | 0.454 |
| H_full | 48.8 | 89.6 | 98.0 | 6.17 (0.000) | **1.28 (0.053)** | 53.1 | **0.465** |

* Coverage is good for every vol-aware model.
* 5% VaR is breached too often by every model, benchmarks included (6.2–6.8%).
* 1% VaR passes Kupiec at 5% only for G_earn and H_full (EWMA only; see section 6).
* H_full has the best swing-size rank correlation, 0.465 vs 0.443 for vol_t. That is small, and it does not translate into likelihood.
* **Median bias: 52.9% vs v1's 55.4%, still outside the 50 ± 1.5 target.** For A, B and C it equals the Gaussian's 52.880% exactly: the densities are symmetric around the training mean `mu`, so median = mean. The comoving fix removed the magnet's own bias. What remains comes from centring on the mean when weekly returns are negatively skewed (median > mean). The Student-t, which fits its own location, gets 51.2–51.5%. Possible fix: centre on a fitted location or the training median, not the mean.

## 3. Worst weeks

1-in-N odds of a drop at least this bad:

| Week | Move | v1 static QPM | vol_t (EWMA) | C_mix (EWMA) | C_mix (GARCH) |
|---|---|---|---|---|---|
| AAPL 2025-04-01 | −22.7% | ~10¹¹ | 31,182 | **9,564** | 10,978,477 |
| JPM 2020-03-02 | −23.1% | "impossible" (10¹²) | 1,515 | **1,860** | 1,482,857 |
| TSLA 2020-03-09 | −26.8% | 6,446 | 31 | 27 | 3,836 |
| NVDA 2018-11-14 | −26.6% | 37,335 | 81 | 73 | 1,152 |

**Yes, with EWMA, the mixture fixes the 1-in-10¹¹ problem.** Worst-week odds are on par with or better than vol_t. With GARCH it is only partly fixed: GARCH reacts more slowly to a sudden vol spike, and every GARCH model (vol_t included) gives these weeks 10–1,000× longer odds.

## 4. Direction (EWMA, 0.1% per trade)

| Model | Brier | Brier clim | Hit | mean P(up) | LF CAGR | LF Sharpe | LS CAGR | LS Sharpe |
|---|---|---|---|---|---|---|---|---|
| vol_t | 0.247 | 0.244 | 0.573 | 0.566 | 23.4% | 0.70 | 22.5% | 0.67 |
| C_mix | 0.248 | 0.244 | 0.574 | 0.551 | 23.8% | 0.70 | 23.4% | 0.68 |
| D_mom | 0.248 | 0.244 | 0.567 | 0.554 | 21.2% | 0.66 | 18.3% | 0.56 |
| F_anchor | 0.249 | 0.244 | 0.559 | 0.540 | 20.9% | 0.62 | 17.7% | 0.50 |
| H_full | 0.251 | 0.244 | 0.545 | 0.544 | 17.6% | 0.56 | 11.4% | 0.29 |
| buy & hold | | | | | 24.2% | 0.71 | | |
| mom20 rule | | | | | 13.1% | 0.53 | | |

(LF = long/flat, LS = long/short.)

* Every model's Brier score is worse than climatology. Note that `brier_clim` uses the test-period up-rate, which is generous to the benchmark.
* No strategy beats buy & hold. The more conditional features are added, the worse direction gets: momentum, anchor and full all lower CAGR and Sharpe.
* v2 did fix v1's "P(up) > 0.5 almost always": mean P(up) is 0.55, long 95% (C_mix) down to 82% (H_full). The extra signal it now produces is noise.

## 5. Fitted parameters (EWMA; GARCH in brackets)

| Parameter | Value |
|---|---|
| Median C_theta | 0.701 (0.688) |
| Median nu | 9.5 (13.1) |
| Median magnet depth | 242 (193) |
| Median magnet width | 1.25 (1.14) sd units |
| A_theta | 0.698, vs v1's 0.69 (same corner of parameter space) |

Per ticker, nu ranges from 3.4 (SPY) to 16.7 (KO). The index ETFs want the heaviest tails.

Switched off in-sample:

| Feature | EWMA | GARCH |
|---|---|---|
| k0_scale (momentum) | 66% | 71% |
| lam_anchor | 69% | 68% |
| level_scale | 51% | 56% |
| earn_depth | **95%** | 90% |

* When momentum and the anchor are on, they take the smallest grid values (k0_scale ≤ 0.35, lam ≤ 5).
* **The data did not want the earnings double well, momentum or the anchor.**
* Levels are a coin flip in-sample and lose out of sample.
* Fits at a bound: theta 0% (GARCH 1.9%); nu at 60 in 9% (7%). No degenerate fits.

## 6. EWMA vs GARCH

| | EWMA | GARCH |
|---|---|---|
| C_mix vs vol_t | −0.0020, t −1.78 (1/8) | **−0.0030, t −2.22 (0/8)**, now significantly worse |
| G_earn vs vol_t_earn | −0.0025, t −1.86 | **−0.0038, t −2.46**, significantly worse |
| H_full vs vol_t | −0.0079, t −2.27 | −0.0136, t −3.72 |
| E_levels / F_anchor vs C_mix | t −5.1 / −2.9 | t −6.0 / −3.9 |
| Best model | vol_t_earn (+0.0088) | vol_t_earn (+0.0095) |
| VaR1 breach, G_earn / H_full | 1.26% / 1.28% (pass) | 1.40% / 1.61% (**fail**) |
| y > median, C_mix | 52.9% | 52.9% |
| Worst weeks | fixed | partly fixed |
| Direction | no skill | no skill (H_full LS CAGR 7.6%) |

Conclusions that change under GARCH:
* QPM goes from "tied with" to "significantly worse than" the vol-scaled Student-t.
* The 1% VaR pass disappears.
* The crash-odds fix weakens.

Nothing improves for QPM under GARCH.

## 7. Runtime and environment

| | |
|---|---|
| Machine | Windows 10, 12 logical CPUs, 8 workers (one per ticker) |
| Runtime | `--quick` 7 min; EWMA 32 min; GARCH 28 min. Per yearly fit: about 117 s (EWMA), 99 s (GARCH) |
| Software | Python 3.12.3, numpy 2.5.1, scipy 1.18.1, pandas 3.1.0, yfinance 1.7.0 |
| Prices | Yahoo, adjusted, through 2026-11-02 close; 5,157 weekly forecasts, 2014-01 to 2026-10 |
| Earnings dates | AAPL 99, NVDA 98, TSLA 66, JPM 100, XOM 100, KO 100, SPY 0, QQQ 0 (ETFs, expected). 77 yearly fits had earnings data |

## 8. Verdict

v2 fixed the mechanics that v1 got wrong:
* Building volatility into the model and mixing over the "mass" turned an unusable crash model (AAPL's April 2025 drop at 1 in 100 billion) into one that rates it about 1 in 10,000, on par with standard practice.
* The magnet no longer drags the forecast down.

But once volatility is handled properly, the quantum model only ties a plain Student-t scaled by volatility, and loses to it under GARCH. None of the features that are distinctively the model's own adds value at a one-week horizon:
* support/resistance barriers
* momentum phase
* 200-day anchor
* earnings double well

The data switches most of them off, and the ones it keeps make out-of-sample forecasts worse. The single most useful addition was a simple "earnings weeks are about 1.25–2× more volatile" multiplier (median `earn_mult` per ticker), and that works just as well, or better, on the ordinary Student-t. There is still no directional or trading value.

By BACKTEST.md's own criterion this is a null result. The ideas left untested are option-implied calibration and sentiment data, and they are where any remaining edge would have to come from.
