"""
Scenarios for the Quantum Price Model.  Run:  python demo.py
Writes figures to ./figures and prints a forecast table per scenario.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from qpm import (
    Potential,
    QPMParams,
    QuantumPriceModel,
    black_scholes_density,
    calibrate,
    effective_variance_factor,
    kl_divergence,
    momentum_from_returns,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

S0 = 100.0
T = 30 / 252  # 30 trading days
SIGMA = 0.30  # implied vol
R = 0.04


def show(name: str, f: dict) -> None:
    print(f"\n=== {name} ===")
    print(f"  E[S_T]={f['E[S]']:.2f}  median={f['median_S']:.2f}  std(logret)={f['std_logret']:.4f}")
    print(f"  skew={f['skew']:+.3f}  kurtosis={f['kurtosis']:.3f}  P(S_T>S0)={f['P(S_T > S0)']:.3f}  P(bull)={f['P(bull)']:.3f}")
    print(f"  VaR95={f['VaR_95']:.2f}  VaR99={f['VaR_99']:.2f}  q5={f['quantiles_S'][0.05]:.1f}  q95={f['quantiles_S'][0.95]:.1f}")
    if f["calls"]:
        print("  calls:", {k: round(v, 2) for k, v in f["calls"].items()})


def plot_density(ax, m: QuantumPriceModel, label: str, **kw) -> None:
    ax.plot(S0 * np.exp(m.x), m.density() / S0 / np.exp(m.x), label=label, **kw)


# ---------------------------------------------------------------------------
# A. Sanity: theta = 0 is Black-Scholes; theta in (0,1) with rescaled sigma
# ---------------------------------------------------------------------------
def scenario_A():
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bs = black_scholes_density(np.linspace(-1.5, 1.5, 512, endpoint=False), T, SIGMA, mu=(R - SIGMA**2 / 2), sigma0=0.02)
    xs = np.linspace(-1.5, 1.5, 512, endpoint=False)
    ax.plot(S0 * np.exp(xs), bs / S0 / np.exp(xs), "k--", lw=2, label="Black-Scholes (lognormal)")
    for theta in (0.0, 0.3, 0.6):
        sig = SIGMA / np.sqrt(effective_variance_factor(theta))  # match the variance
        m = QuantumPriceModel(QPMParams(sigma=sig, mu=R - SIGMA**2 / 2, sigma0=0.02, theta=theta), S0=S0).evolve(T)
        plot_density(ax, m, f"QPM theta={theta}  (sigma={sig:.3f})")
        show(f"A: free packet theta={theta}", m.forecast(r=R, strikes=[100, 110]))
    ax.set_xlim(55, 160)
    ax.set_xlabel("S_T")
    ax.set_ylabel("density")
    ax.set_title("A. Free packet: theta=0 reproduces Black-Scholes exactly")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "A_free_packet.png"), dpi=130)


# ---------------------------------------------------------------------------
# B. Mean reversion + support / resistance, with momentum
# ---------------------------------------------------------------------------
def scenario_B():
    recent = np.random.default_rng(1).normal(0.004, 0.018, 20)  # last 20 days: up-trend
    sig = SIGMA / np.sqrt(effective_variance_factor(0.5))
    k0 = momentum_from_returns(recent, sig)
    pot = Potential(
        lam=1500.0,  # lam * (0.1)^2 * T ~ 1.8 : mean reversion is felt within the horizon
        x_f=np.log(108 / 100),  # analysts' fair value 108
        levels=[
            (np.log(90 / 100), 30.0, 0.015),  # support at 90   (h * T ~ 3.6)
            (np.log(120 / 100), 30.0, 0.015),  # resistance at 120
        ],
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ax = axes[0]
    for theta, ls in ((0.0, "--"), (0.5, "-"), (0.85, "-")):
        p = QPMParams(sigma=sig, mu=0.0, sigma0=0.02, k0=k0, theta=theta, potential=pot)
        m = QuantumPriceModel(p, S0=S0).evolve(T)
        plot_density(ax, m, f"theta={theta}", ls=ls)
        show(f"B: mean reversion + levels, theta={theta}, k0={k0:.2f}", m.forecast(r=R, strikes=[100, 110, 120]))
    for lvl in (90, 108, 120):
        ax.axvline(lvl, color="grey", lw=0.8, alpha=0.6)
    ax.set_xlim(60, 150)
    ax.set_xlabel("S_T")
    ax.set_title("B. Mean reversion to 108, support 90, resistance 120, momentum k0>0")
    ax.legend()
    # time evolution heat map for theta=0.5
    p = QPMParams(sigma=sig, sigma0=0.02, k0=k0, theta=0.5, potential=pot)
    m = QuantumPriceModel(p, S0=S0).evolve(T, n_steps=200, record_every=4)
    ts = np.array([t for t, _ in m.history]) * 252
    dens = np.array([d for _, d in m.history])
    ax = axes[1]
    xm = (m.x > np.log(0.6)) & (m.x < np.log(1.5))
    ax.imshow(
        dens[:, xm].T, aspect="auto", origin="lower", cmap="magma",
        extent=[ts[0], ts[-1], S0 * np.exp(m.x[xm][0]), S0 * np.exp(m.x[xm][-1])],
    )
    ax.set_xlabel("trading days")
    ax.set_ylabel("S")
    ax.set_title("|psi(x,t)|^2 over time (theta=0.5)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "B_mean_reversion_levels.png"), dpi=130)


# ---------------------------------------------------------------------------
# C. Earnings: double-well potential -> bimodal, interference, fat tails
# ---------------------------------------------------------------------------
def scenario_C():
    pot = Potential(quartic=(3e5, 1e4))  # minima at +-sqrt(1e4/6e5) = +-13%, depth b^2/4a = 83 (x T ~ 10)
    sig = SIGMA / np.sqrt(effective_variance_factor(0.5))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    xs = np.linspace(-1.5, 1.5, 512, endpoint=False)
    bs = black_scholes_density(xs, T, SIGMA, sigma0=0.02)
    ax.plot(S0 * np.exp(xs), bs / S0 / np.exp(xs), "k--", label="Black-Scholes")
    for theta in (0.0, 0.5, 0.9):
        m = QuantumPriceModel(QPMParams(sigma=sig, sigma0=0.02, theta=theta, potential=pot), S0=S0).evolve(T)
        plot_density(ax, m, f"double well, theta={theta}")
        show(f"C: earnings double well theta={theta}", m.forecast(r=R, strikes=[100]))
    ax.set_xlim(60, 150)
    ax.set_xlabel("S_T")
    ax.set_title("C. Before earnings: double well -> two regimes, interference fringes")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "C_earnings_double_well.png"), dpi=130)


# ---------------------------------------------------------------------------
# D. Decoherence: liquid (high gamma) vs illiquid (low gamma) stock
# ---------------------------------------------------------------------------
def scenario_D():
    pot = Potential(quartic=(3e5, 1e4))
    sig = SIGMA / np.sqrt(effective_variance_factor(0.5))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for gamma, label in ((0.0, "no decoherence (pure)"), (500.0, "illiquid, gamma=500"), (20000.0, "liquid, gamma=20000")):
        p = QPMParams(sigma=sig, sigma0=0.02, theta=0.9, gamma=gamma, potential=pot)
        m = QuantumPriceModel(p, S0=S0, N=192, L=1.2).evolve(T, n_steps=120)
        plot_density(ax, m, label)
        show(f"D: decoherence gamma={gamma}", m.forecast(r=R))
    ax.set_xlim(60, 150)
    ax.set_xlabel("S_T")
    ax.set_title("D. Decoherence (Lindblad, L=x): information flow washes out interference")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "D_decoherence.png"), dpi=130)


# ---------------------------------------------------------------------------
# E. Sentiment qubit coupled to price:  H_int = g sigma_z x + Omega sigma_x
# ---------------------------------------------------------------------------
def scenario_E():
    sig = SIGMA / np.sqrt(effective_variance_factor(0.5))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ax = axes[0]
    for g, omega, pb in ((0.0, 0.0, 0.5), (150.0, 0.0, 0.65), (150.0, 8.0, 0.65)):
        p = QPMParams(sigma=sig, sigma0=0.02, theta=0.6, g=g, omega=omega, p_bull=pb)
        m = QuantumPriceModel(p, S0=S0).evolve(T, record_every=10)
        plot_density(ax, m, f"g={g}, Omega={omega}, P0(bull)={pb}")
        show(f"E: sentiment g={g} Omega={omega}", m.forecast(r=R, strikes=[100]))
        if g:
            pb_t = []
            mm = QuantumPriceModel(p, S0=S0)
            for _ in range(60):
                mm.step(T / 60)
                pb_t.append(mm.prob_bull())
            axes[1].plot(np.linspace(0, 30, 60), pb_t, label=f"g={g}, Omega={omega}")
    ax.set_xlim(60, 150)
    ax.set_xlabel("S_T")
    ax.set_title("E. Bull/bear qubit coupled to price")
    ax.legend(fontsize=8)
    axes[1].set_xlabel("trading days")
    axes[1].set_ylabel("P(bull)")
    axes[1].set_title("Sentiment dynamics (Rabi-like flips when Omega>0)")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "E_sentiment_qubit.png"), dpi=130)


# ---------------------------------------------------------------------------
# F. Measurement: a path of trades = repeated collapses
# ---------------------------------------------------------------------------
def scenario_F():
    rng = np.random.default_rng(7)
    sig = SIGMA / np.sqrt(effective_variance_factor(0.5))
    pot = Potential(lam=800.0, x_f=0.0, levels=[(np.log(0.9), 30.0, 0.015), (np.log(1.15), 30.0, 0.015)])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for path in range(4):
        m = QuantumPriceModel(QPMParams(sigma=sig, sigma0=0.01, theta=0.6, potential=pot), S0=S0)
        xs, ts = [0.0], [0.0]
        for day in range(1, 61):
            m.evolve(1 / 252, n_steps=4, record_every=4)
            x = m.measure(rng, sigma_post=0.01)  # one trade per day collapses the packet
            xs.append(x)
            ts.append(day)
        ax.plot(ts, S0 * np.exp(xs), lw=1.2, label=f"path {path + 1}")
    ax.axhline(90, color="grey", lw=0.8)
    ax.axhline(115, color="grey", lw=0.8)
    ax.set_xlabel("trading days")
    ax.set_ylabel("S")
    ax.set_title("F. Trades as measurements: sample -> collapse -> evolve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "F_measurement_paths.png"), dpi=130)


# ---------------------------------------------------------------------------
# G. Calibration + out-of-sample likelihood vs Black-Scholes on fat-tailed data
# ---------------------------------------------------------------------------
def scenario_G():
    rng = np.random.default_rng(42)
    # synthetic "market": 30-day log-returns with fat tails (Student-t, df=3)
    std_true = SIGMA * np.sqrt(T)
    draws = rng.standard_t(3, size=4000) * std_true / np.sqrt(3)  # unit variance t scaled
    train, test = draws[:2000], draws[2000:]
    xs = np.linspace(-1.5, 1.5, 256, endpoint=False)

    # classical benchmark: Gaussian MLE
    mu_bs, sd_bs = train.mean() / T, train.std() / np.sqrt(T)
    bs_test = black_scholes_density(test, T, sd_bs, mu=mu_bs)
    ll_bs = np.sum(np.log(bs_test))

    # quantum: fit sigma, theta and a mean-reversion well by MLE on train set
    # free parameters: volatility, theta, and an attractive well at the current
    # price (its bound state is Laplace-like -> fat tails without adding them by hand)
    base = QPMParams(sigma=sd_bs, mu=mu_bs, sigma0=0.01, theta=0.3, potential=Potential(magnet_depth=20.0, magnet_width=0.03))
    free = {"sigma": (0.05, 2.5), "theta": (0.0, 0.95), "potential.magnet_depth": (0.0, 3000.0), "potential.magnet_width": (0.005, 0.2)}
    best, loss = calibrate(base, T, free, objective=lambda m: -m.log_likelihood(train), N=256, n_steps=80, maxiter=300)
    m = QuantumPriceModel(best, S0=S0, N=256).evolve(T, n_steps=80)
    ll_q = m.log_likelihood(test)
    print("\n=== G: calibration (MLE on 2000 train returns, scored on 2000 test) ===")
    print(f"  fitted: sigma={best.sigma:.3f}  theta={best.theta:.3f}  magnet depth={best.potential.magnet_depth:.1f} width={best.potential.magnet_width:.3f}")
    print(f"  out-of-sample log-lik  Black-Scholes={ll_bs:.1f}   QPM={ll_q:.1f}   diff={ll_q - ll_bs:+.1f}")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(test, bins=80, density=True, alpha=0.35, label="realised 30d log-returns (test)")
    ax.plot(xs, black_scholes_density(xs, T, sd_bs, mu=mu_bs), "k--", label="Gaussian MLE")
    ax.plot(m.x, m.density(), label=f"QPM MLE (theta={best.theta:.2f}, well depth={best.potential.magnet_depth:.0f})")
    ax.set_xlim(-0.4, 0.4)
    ax.set_yscale("log")
    ax.set_ylim(1e-2, 20)
    ax.set_xlabel("x = ln(S_T/S0)")
    ax.set_title("G. Fat-tailed data: QPM vs Gaussian, log scale")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "G_calibration_fat_tails.png"), dpi=130)


if __name__ == "__main__":
    scenario_A()
    scenario_B()
    scenario_C()
    scenario_D()
    scenario_E()
    scenario_F()
    scenario_G()
    print(f"\nfigures written to {FIG}")
