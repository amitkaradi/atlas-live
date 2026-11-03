# QPM v2: instructions for running the backtest

This file is for whoever (or whatever agent) runs the v2 walk-forward test on real
prices and reports back. Everything needed is in this folder. Read it fully before running.

## What changed since v1 and why

The v1 test ([`RESULTS.md`](RESULTS.md)) fitted only the "free particle + magnet" corner
of the model and found: beats Black–Scholes, loses to Student-t, no timing value, crash
tails too thin, median biased bearish. v2 fixes the mechanics behind each of those and
turns on the parts of the model that v1 never exercised:

| v1 problem | v2 fix | where |
|---|---|---|
| Tails exponential (Laplace), too thin for crashes | mixed state over the particle's mass: σ² ~ σ²·ν/χ²_ν, ν fitted → power-law-like tails | `qpm.py: QPMEnsemble, mass_mixture_nodes`, config `C_mix` |
| Volatility only as a post-hoc stretch | model fitted on vol-standardised innovations (EWMA or GARCH(1,1)) like GARCH-t does | `features.py: VolModel`, config `B_vol` |
| Median biased bearish (magnet pinned at x=0 while the price drifts) | potential rides with the drift (`comoving=True`) | `qpm.py: _displacement, _shift` |
| Momentum phase k₀ erased within ~1% of the horizon when θ<1, so P(up)>0.5 almost always | momentum is a drift that decays with τ=20d; its scale `k0_scale` is fitted, 0 allowed | `QPMParams.v_mom/tau_mom`, config `D_mom` |
| Degenerate fits (θ→0.94, σ→bound) | θ ∈ [0.2, 0.85], σ bounded relative to the data, 2 starting points | `qpm.calibrate(starts=)` |
| Support/resistance, anchor, earnings never used | pivot barriers (height fitted), SMA-200 well (λ fitted), earnings double well (depth fitted) | `features.py`, configs `E_levels`, `F_anchor`, `G_earn` |
| Returns above the grid got density 1e-300 | closed-form benchmarks; grid densities continued exponentially beyond ±10 sd | `backtest.py: grid_logpdf` |

Still **not** tested, on purpose: the sentiment qubit (needs an external sentiment series),
decoherence (only changes interference fringes, which do not exist at a weekly horizon),
option-implied calibration (needs historical option chains). Say so in the report rather
than improvising substitutes.

## Setup

```bash
cd quantum
pip install -r requirements.txt yfinance pandas
python -c "import qpm, features, backtest; print('ok')"
```

Price CSVs and earnings dates are cached in `data/` (git-ignored). If a `data/<TICKER>.csv`
from the v1 run exists it is reused; delete it to re-download. Earnings dates come from
`yfinance.Ticker(t).get_earnings_dates(limit=120)`; ETFs (SPY, QQQ) get none, which is
expected. If Yahoo returns few or no earnings dates for a stock, note it in the report;
`G_earn` then equals `C_mix` for that ticker.

## Run, in this order

1. Smoke test (about 10 minutes). Confirms the pipeline works on your machine.
   ```bash
   python backtest.py --quick
   ```
   Check that `results/v2_summary_quick.txt` exists and section 5 shows no fit at a bound
   in 100% of cases. Do not report these numbers; they cover 2020 onward only with reduced iterations.

2. Full run with EWMA volatility (the main result, 45–90 minutes on 4 cores; `--workers 8` if you have them).
   ```bash
   python backtest.py
   ```

3. Full run with GARCH(1,1) volatility (same length). This is the robustness check.
   ```bash
   python backtest.py --vol garch
   ```
   It overwrites the same result files, so copy the EWMA outputs first:
   ```bash
   cp results/v2_summary.txt results/v2_summary_ewma.txt
   cp results/v2_forecasts.csv results/v2_forecasts_ewma.csv
   cp results/v2_fits.csv results/v2_fits_ewma.csv
   cp figures/R4_ablation.png figures/R4_ablation_ewma.png
   ```

Do not change the grids, bounds, tickers, train length, horizon or first test year to
improve the numbers. If something looks wrong, report it as found and say what you suspect.
If a run crashes, paste the traceback and the ticker/year it was on (`fit_sec` rows in
`v2_fits.csv` show how far it got).

## What to report (in this order)

Commit `results/v2_*.csv`, `results/v2_summary*.txt`, the figures, and a `RESULTS_v2.md`
with these sections, each answered from the summary file, with the numbers:

1. **Feature ablation (section 1 of the summary).** For each step A→B→C→D/E/F/G→H: the
   mean log-likelihood gain, the paired t-stat and the "better on k/8 tickers" count. The
   key lines are `C_mix vs vol_t`, `H_full vs vol_t`, `G_earn vs vol_t_earn`, and the
   earnings-weeks-only table. State plainly whether any config beats the vol-scaled
   Student-t with |t| > 2.
2. **Calibration (section 2).** 50/90/98 coverage, VaR-5 and VaR-1 breach rates with
   Kupiec p-values, `y>median %` (the v1 bearish bias was 55.4%; target 50 ± 1.5), and
   the swing-size rank correlation. Compare `C_mix` and `H_full` with `vol_t`.
3. **Worst weeks (section 3).** Odds table. Did the mixture fix the 1-in-10¹¹ problem?
4. **Direction (section 4).** Brier vs climatology, hit rate, `mean_pup`, the LF and LS
   strategy rows against buy&hold and the mom20 rule. Note that costs are 0.1% per trade.
5. **Fitted parameters (section 5).** Median θ, ν, magnet depth/width; how often
   `k0_scale`, `lam_anchor`, `level_scale`, `earn_depth` were switched off in-sample;
   fraction of fits at a bound. If a feature is off in most fits, say the data did not
   want it. Compare `A_theta` with v1's 0.69.
6. **EWMA vs GARCH.** Same five points in short form for the GARCH run; say which
   conclusions change.
7. **Runtime and environment.** Minutes per run, CPU count, Python/numpy/scipy versions,
   yfinance data end date, number of earnings dates per ticker.
8. **Verdict in one paragraph**, written for someone who will not read the tables.

Keep the raw outputs; do not round in the CSVs.

## Reading the summary

* All log-likelihood gains in section 1 are relative to `vol_t` (vol-scaled Student-t),
  the best v1 benchmark. A positive `ALL` entry with |t| > 2 is a real improvement.
* `A_static` is the v1 model with the comoving fix, on raw returns; compare it to `gauss`
  and `student_t` (also raw). `B_vol` onwards are on standardised returns; compare them to
  `vol_gauss`, `vol_t`.
* `G_earn` and `vol_t_earn` share the same earnings-week vol multiplier; their difference
  is the double well's shape only.
* `H_full` stacks every feature at its individually fitted value; it is not a joint refit.
* Grid values for the conditional features are in `v2_fits.csv` (`ll_*_grid` columns, the
  in-sample log-likelihood at each grid point) if you want to see how flat the choice was.

## Interpreting a null result

If `C_mix` ≈ `vol_t` and every conditional feature is switched off most of the time, the
honest conclusion is that at a 5-day horizon the quantum structure adds nothing a
Student-t with a volatility model does not already give, and the remaining untested
ideas are option-implied calibration and sentiment data. Report that; do not keep tuning.
