# QPM on real stocks: walk-forward results (v1)

> Superseded by the v2 ablation in [`backtest.py`](backtest.py); run instructions in [`BACKTEST.md`](BACKTEST.md). This file stays as the v1 record.

Out-of-sample test of the Quantum Price Model ([`qpm.py`](qpm.py)) on real daily prices.
Scripts: [`real_test.py`](real_test.py) (density, direction, trading) and [`swing_test.py`](swing_test.py) (swing-size accuracy).
Raw outputs: [`results/`](results/). Run date: 2026-11-03, prices through 2026-11-02 close (Yahoo Finance, adjusted).

> Not investment advice. No transaction costs, slippage or taxes unless stated.

## Setup

| | |
|---|---|
| Tickers | SPY, QQQ, AAPL, NVDA, TSLA, JPM, XOM, KO |
| Forecast | next 5 trading days' log-return |
| Fitting | every January, MLE on the previous 3 years of overlapping 5-day returns (same free parameters as demo scenario G: `sigma`, `theta`, `magnet_depth`, `magnet_width`) |
| Scoring | the following year's non-overlapping weekly returns, never seen in fitting |
| Sample | 5,208 weekly forecasts, 2014-01 to 2026-10, 104 yearly fits |
| Benchmarks | Gaussian (= Black-Scholes), Student-t MLE, and EWMA-volatility versions (RiskMetrics λ=0.94) of Gaussian, Student-t and QPM |

"EWMA QPM" is the fitted QPM shape stretched each week by current EWMA volatility / training volatility, so it can react to volatility regimes the yearly fit can't see.

## Bug fixed in `qpm.py`

`forecast()` built the CDF as `cumsum(p) * dx`, which counts the whole grid bin at x = 0 (today's price) as "down". P(S_T > S0) came out 1–3 points too low even for an exactly symmetric distribution (0.4725 instead of 0.5000 with the magnet on). The magnet piles mass exactly at x = 0, so the error is largest where the model is used. Fixed with the midpoint rule (`- 0.5 * p * dx`). Quantiles and VaR shift by half a bin.

Before the fix, the long/flat test sat in cash most weeks (long only 42% of the time, 47.6% hit rate). All numbers below are after the fix.

## 1. Distribution fit (log-likelihood)

Mean out-of-sample log-likelihood per forecast, relative to Gaussian (higher is better):

| Model | Gain vs Gaussian |
|---|---|
| Student-t | +0.104 |
| **QPM** | **+0.082** |
| EWMA Gaussian | +0.116 |
| EWMA QPM | +0.133 |
| EWMA Student-t | **+0.144** |

* QPM beats Black-Scholes on all 8 tickers (paired t-stat +4.9). The magnet's Laplace-like fat tails are real.
* A plain Student-t beats QPM (t-stat −3.9, QPM worse on 7/8 tickers). With EWMA scaling it still loses (t-stat −3.9).

## 2. Swing size (`swing_test.py`)

**Average size: correct.** Realised typical move / predicted typical move = 1.03 (static), 1.04 (EWMA).

**Bigger forecast → bigger move: moderately.** Spearman rank correlation between predicted and realised move size: 0.38 (static QPM), 0.45 (EWMA QPM). This is the same as the benchmarks (Student-t 0.38, EWMA Student-t 0.45).

**Single-week error: large.** The mean absolute error of the size forecast is 2.0 percentage points per week (EWMA QPM 1.9), when a typical week moves about 2.5%.

By predicted-size quintile (EWMA QPM):

| Quintile | Predicted typical move | Actual typical move | Inside 90% band |
|---|---|---|---|
| calmest | 1.15% | 1.37% | 85.2% |
| 2 | 1.73% | 1.97% | 85.9% |
| 3 | 2.32% | 2.54% | 87.6% |
| 4 | 3.27% | 3.43% | 88.6% |
| wildest | 6.01% | 5.78% | 90.4% |

Calm weeks are under-predicted by about 20%.

**Interval coverage** (target in brackets):

| | 50% | 80% | 90% | 95% | 98% |
|---|---|---|---|---|---|
| QPM | 49.3 | 78.6 | 88.3 | 93.5 | 96.9 |
| EWMA QPM | 45.5 | 77.0 | 87.5 | 93.5 | 97.2 |
| Gaussian | 56.8 | 81.8 | 89.3 | 92.9 | 95.6 |
| Student-t | 49.4 | 78.1 | 87.9 | 93.3 | 97.0 |

**Downside VaR: too optimistic about crashes.** The 5% VaR was breached 5.9% of weeks, and the 1% VaR 1.8% of weeks (nearly double). Kupiec p < 0.01 for both, so the tails are still too thin on the downside. Every model fails this test.

**Static fits break in volatility regimes.** Static QPM 90%-band coverage by year: 65.7% in 2020, 81.6% in 2022, 98.2% in 2023. EWMA QPM stays between 84.6% and 90.9% in every year. The yearly fit alone cannot be used for risk.

**Worst weeks.** Static QPM odds for the biggest drops:

| Week | Drop | Static QPM odds | EWMA QPM odds |
|---|---|---|---|
| AAPL Apr 2025 | −22.7% | about 1 in 10^11 | about 1 in 10^10 |
| JPM Mar 2020 | −23.1% | "impossible" | 1 in 549,000 |

A Student-t gave AAPL's drop 1 in 74 million. The quantum tails decay faster than a power law, which is too thin for real crashes.

**Median biased bearish.** The realised return finished above the QPM median in 55.4% of weeks (Gaussian 52.8%). The magnet is centred on today's price (`x_f = 0`), so it pulls the median toward "no change" while stocks drift up.

Figure: [`figures/R3_swing_size.png`](figures/R3_swing_size.png).

## 3. Direction and trading

Strategy: weekly, long when QPM P(up) > 0.5 (momentum `k0` from the last 20 days), else cash.

* Brier score is worse than the stock's own historical up-rate on 6/8 tickers and tied on 2 (overall 0.249 vs 0.246). There is no directional information.
* The strategy was long 94% of weeks, so it is close to buy & hold. It was also never short.
* $10k in each ticker, 2014-01 to 2026-10: buy & hold $870k per $10k split equally; QPM $766k ($758k after 0.1% per trade).
* QPM beat buy & hold on 1 ticker (AAPL, +$15k), tied on JPM (never sold), and lost on the other 6. TSLA lost $199k and NVDA lost $630k.
* The large dollar totals come from hindsight ticker choice (NVDA, TSLA), not from the model.

Figure: [`figures/R2_equity_curves.png`](figures/R2_equity_curves.png), log-likelihood by ticker: [`figures/R1_loglik_vs_gaussian.png`](figures/R1_loglik_vs_gaussian.png).

## Conclusions

1. QPM is a legitimate fat-tailed distribution and beats Black-Scholes, but it does not beat a Student-t. Any advantage would have to come from features this test didn't fit: barriers, the double well, sentiment, or decoherence.
2. For swing size it is only as good as its volatility input. With EWMA scaling it ties the best benchmark on ranking and size. Without it, coverage collapses in volatile years.
3. Tails are too thin for crashes, at 1% VaR and beyond.
4. No market-timing value.

### Ideas worth testing next

* Fit `sigma` dynamically (GARCH/EWMA inside the model), not by post-hoc stretching.
* Let `x_f` drift with `mu` (or fit it) to remove the bearish median.
* Add a power-law tail component, or fit `magnet_width` per regime, to fix 1% VaR.
* Calibrate to option prices (MODEL.md §10.1) and compare the model's distribution with the market's implied one. That is where a distribution-only model could pay.
* Compare to GARCH-t and Heston, as MODEL.md §11 requires.

## Reproduce

```bash
pip install -r requirements.txt yfinance pandas
python real_test.py          # ~5 min, writes results/forecasts.csv, fits.csv, forecast_now.csv, figures R1-R2
python swing_test.py         # ~1 min, reuses results/fits.csv, writes swing_forecasts.csv, figure R3
python real_test.py MSFT AMZN   # any tickers
```

Price CSVs are cached in `data/` (git-ignored, re-downloaded on first run).
