"""
Make every figure in results/figures/ from the tables written by run_all.py.

    python experiments/make_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
DATA = ROOT / "results" / "data"
FIG = ROOT / "results" / "figures"

# ---- palette (validated with the dataviz palette checker) --------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
C_SS = "#2a78d6"     # (s,S)  - categorical slot 1
C_SQ = "#eb6834"     # (s,Q)  - categorical slot 2
C_ORDER, C_HOLD, C_SHORT = "#1baf7a", "#eda100", "#6250d6"
C_EXACT = INK
SEQ = LinearSegmentedColormap.from_list(
    "blue", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "legend.frameon": False, "lines.linewidth": 2,
    "font.family": "DejaVu Sans",
})


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def color_of(label):
    return C_SS if label.startswith("(s,S)") else C_SQ


def fig_sample_paths(summary):
    paths = json.loads((DATA / "sample_paths.json").read_text())
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, sharey=True)
    for ax, (lab, d) in zip(axes, paths.items()):
        t, lev = np.array(d["t"]), np.array(d["level"])
        c = color_of(lab)
        ax.step(t, lev, where="post", color=c, lw=1.4)
        ax.fill_between(t, lev, 0, where=lev < 0, step="post", color=C_SHORT, alpha=0.35, lw=0,
                        label="backlog (shortage)")
        ax.axhline(0, color=INK2, lw=0.8)
        s = int(lab.split("(")[2].split(",")[0])
        ax.axhline(s, color=INK2, lw=1, ls="--")
        ax.text(120.5, s, f" s = {s}", va="center", color=INK2, fontsize=9)
        top = max(max(dd["level"]) for dd in paths.values()) + 8
        ax.plot(d["orders"], [top] * len(d["orders"]), marker="v", color=c, ms=5, ls="none")
        ax.set_title(f"{lab}   ({len(d['orders'])} orders, ▼ = order placed)", fontsize=11.5)
        ax.set_ylabel("inventory level I(t)")
        ax.set_xlim(0, 120)
    axes[0].legend(loc="lower right")
    axes[1].set_xlabel("month")
    fig.suptitle("Inventory sample path of the two optimized policies - same demand stream (CRN)",
                 x=0.01, ha="left", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save(fig, "fig01_sample_paths")


def fig_validation():
    v = pd.read_csv(TABLES / "validation_law_kelton.csv")
    labels = [f"({r.s},{r.S})" for r in v.itertuples()]
    y = np.arange(len(v))[::-1]
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    ax.errorbar(v.sim_mean, y, xerr=v.sim_ci_hw, fmt="o", color=C_SS, ms=7, capsize=4,
                label="simulation: mean ± 95% CI")
    ax.plot(v.exact, y, "|", color=C_EXACT, ms=18, mew=2.2, label="exact (Markov chain)")
    ax.plot(v.law_kelton_single_run, y, "x", color=C_SQ, ms=8, mew=2,
            label="Law & Kelton (one 120-month run)")
    # one-run spread: +-1.96 sd of a single replication
    for yi, r in zip(y, v.itertuples()):
        ax.plot([r.sim_mean - 1.96 * r.single_run_sd, r.sim_mean + 1.96 * r.single_run_sd],
                [yi - 0.28, yi - 0.28], color=INK2, lw=1, alpha=0.6)
    ax.plot([], [], color=INK2, lw=1, alpha=0.6, label="range of a single run (±1.96 sd)")
    ax.set_yticks(y, labels)
    ax.set_ylabel("(s, S) policy")
    ax.set_xlabel("average monthly cost ($)")
    ax.set_title("Validation: the model reproduces the Law & Kelton example")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9.5)
    fig.tight_layout()
    save(fig, "fig02_validation")


def fig_heatmaps(summary):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    vmin = min(summary["sS"]["screen_min_mean"], summary["sQ"]["screen_min_mean"])
    vmax = vmin + 40
    for ax, pol, ylab in zip(axes, ("sS", "sQ"), ("order-up-to level S", "order quantity Q")):
        df = pd.read_csv(DATA / f"screen_{pol}.csv.gz")
        piv = df.pivot(index="big", columns="s", values="mean")
        if pol == "sS":
            # show on (s, S) axes; region S<=s is infeasible
            pass
        X, Y = np.meshgrid(piv.columns.values, piv.index.values)
        im = ax.pcolormesh(X, Y, piv.values, cmap=SEQ.reversed(), vmin=vmin, vmax=vmax,
                           shading="nearest", rasterized=True)
        cs = ax.contour(X, Y, piv.values, levels=[vmin + 1, vmin + 3, vmin + 10, vmin + 25],
                        colors=INK, linewidths=0.8)
        ax.clabel(cs, fmt={l: f"+{l - vmin:.0f}" for l in cs.levels}, fontsize=8)
        b = summary[pol]["best"]
        ax.plot(b[1], b[2], marker="*", color="white", ms=17, mec=INK, mew=1.2)
        ax.annotate(f"best ({b[1]}, {b[2]})", (b[1], b[2]), xytext=(10, 12),
                    textcoords="offset points", color=INK, fontsize=10, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))
        ax.set_xlabel("reorder point s")
        ax.set_ylabel(ylab)
        ax.grid(False)
        name = "(s, S)" if pol == "sS" else "(s, Q)"
        ax.set_title(f"{name} policy: estimated cost surface")
    cb = fig.colorbar(im, ax=axes, shrink=0.9, pad=0.02)
    cb.set_label("average monthly cost (\\$), 200 CRN reps")
    fig.text(0.01, -0.02, "Darker = cheaper. Contour labels = \\$ above the best point. "
             "Colour scale capped at best + \\$40; the pale band at Q < 25 is unstable (Q below mean demand).",
             color=INK2, fontsize=9)
    save(fig, "fig03_cost_surfaces")


def fig_slices(summary):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, pol, xl in zip(axes, ("sS", "sQ"), ("order-up-to level S", "order quantity Q")):
        df = pd.read_csv(DATA / f"screen_{pol}.csv.gz")
        b = summary[pol]["best"]
        c = C_SS if pol == "sS" else C_SQ
        for s, a in ((b[1], 1.0),):
            d = df[df.s == s].sort_values("big")
            ax.fill_between(d.big, d["mean"] - 1.96 * d.se, d["mean"] + 1.96 * d.se, color=c,
                            alpha=0.2, lw=0)
            ax.plot(d.big, d["mean"], color=c, lw=2, label=f"simulation, s = {s} (95% band)")
            ax.plot(d.big, d.exact, color=INK, lw=1, ls="--", label="exact")
        ax.axvline(b[2], color=INK2, lw=0.8, ls=":")
        ax.set_xlabel(xl)
        name = "(s, S)" if pol == "sS" else "(s, Q)"
        ax.set_title(f"{name}: cost along the best s")
        ax.legend(loc="upper center")
        lo = min(summary["sS"]["screen_min_mean"], summary["sQ"]["screen_min_mean"])
        ax.set_ylim(lo - 3, lo + 45)
    axes[0].set_ylabel("average monthly cost ($)")
    fig.tight_layout()
    save(fig, "fig04_cost_slices")


def fig_candidates():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    for ax, pol in zip(axes, ("sS", "sQ")):
        t = pd.read_csv(TABLES / f"top_candidates_{pol}.csv").head(12)
        y = np.arange(len(t))[::-1]
        c = C_SS if pol == "sS" else C_SQ
        for yi, r in zip(y, t.itertuples()):
            col = c if not r.significantly_worse else "#b9b8b2"
            ax.errorbar(r.mean, yi, xerr=r.ci_hw, fmt="o", color=col, capsize=3, ms=6)
        ax.plot(t.screen_mean, y, ".", color=INK2, ms=6, label="stage-1 (screening) estimate")
        ax.plot(t.exact, y, "|", color=INK, ms=14, mew=2, label="exact")
        ax.set_yticks(y, [l.split("=")[1] for l in t.label])
        name = "(s, S)" if pol == "sS" else "(s, Q)"
        ax.set_title(f"{name}: top-12 candidates re-evaluated")
        ax.set_xlabel("average monthly cost ($)")
        ax.errorbar([], [], xerr=[], fmt="o", color=c, label="stage-2 mean ± 95% CI (fresh reps)")
        ax.errorbar([], [], xerr=[], fmt="o", color="#b9b8b2",
                    label="significantly worse than best")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=8.5)
    fig.tight_layout()
    save(fig, "fig05_top_candidates")


def fig_breakdown():
    f = pd.read_csv(TABLES / "final_comparison.csv")
    f = f.iloc[[2, 0, 1]].reset_index(drop=True)  # baseline, best sS, best sQ
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_axisbelow(True)
    y = np.arange(len(f))[::-1]
    left = np.zeros(len(f))
    for col, c, name in (("ordering", C_ORDER, "ordering"), ("holding", C_HOLD, "holding"),
                         ("shortage", C_SHORT, "shortage")):
        ax.barh(y, f[col], left=left, color=c, height=0.6, edgecolor=SURFACE, lw=2, label=name)
        for yi, l, v in zip(y, left, f[col]):
            if v > 6:
                ax.text(l + v / 2, yi, f"{v:.1f}", ha="center", va="center", color="white",
                        fontsize=10, fontweight="bold")
        left += f[col].values
    for yi, r in zip(y, f.itertuples()):
        ax.text(r.mean + 1.5, yi, f"${r.mean:.2f}", va="center", fontsize=11, fontweight="bold")
    ax.set_yticks(y, f.policy)
    ax.set_xlabel("average monthly cost ($)")
    ax.set_xlim(0, f["mean"].max() * 1.13)
    ax.grid(axis="y", visible=False)
    ax.set_title("Where the money goes: cost components of each policy")
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.15))
    fig.tight_layout()
    save(fig, "fig06_cost_breakdown")


def fig_crn(summary):
    z = np.load(DATA / "final_comparison.npz")
    tot = z["components"].sum(axis=2)
    d_crn = tot[:, 1] - tot[:, 0]
    d_ind = z["indep_sQ"] - tot[:, 0]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    ax = axes[0]
    bins = np.linspace(min(d_ind.min(), d_crn.min()), max(d_ind.max(), d_crn.max()), 80)
    ax.hist(d_ind, bins=bins, color="#b9b8b2", alpha=0.9, label="independent streams")
    ax.hist(d_crn, bins=bins, color=C_SS, alpha=0.85, label="common random numbers")
    ax.axvline(0, color=INK, lw=1)
    ax.set_xlabel("cost(s,Q) − cost(s,S) in one replication ($/month)")
    ax.set_ylabel("replications")
    ax.set_title("CRN makes the per-replication difference far less noisy")
    ax.legend()
    ax = axes[1]
    fin = summary["final"]
    labels_ = ["independent", "CRN (paired)"]
    vals = [fin["independent_ci_half_width"], fin["crn_ci_half_width"]]
    bars = ax.bar(labels_, vals, color=["#b9b8b2", C_SS], width=0.5)
    for b_, v in zip(bars, vals):
        ax.text(b_.get_x() + b_.get_width() / 2, v, f"±{v:.3f}", ha="center", va="bottom",
                fontsize=11, fontweight="bold")
    ax.set_ylabel("95% CI half-width of the difference ($)")
    ax.set_title(f"Same {len(d_crn):,} reps: CRN ≈ {fin['reps_needed_without_crn_for_same_precision'] / len(d_crn):.0f}× fewer reps needed")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "fig07_crn_variance_reduction")


def fig_convergence():
    c = pd.read_csv(TABLES / "ci_convergence.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    ax = axes[0]
    for lab, g in c.groupby("policy", sort=False):
        if lab == "difference":
            continue
        col = color_of(lab)
        ax.fill_between(g.n, g["mean"] - g.ci_hw, g["mean"] + g.ci_hw, color=col, alpha=0.2, lw=0)
        ax.plot(g.n, g["mean"], color=col, label=lab)
    ax.set_xscale("log")
    ax.set_xlabel("number of replications")
    ax.set_ylabel("running mean ± 95% CI ($)")
    ax.set_title("Running estimates separate after ~100 replications")
    ax.legend()
    ax = axes[1]
    for lab, g in c.groupby("policy", sort=False):
        col = INK if lab == "difference" else color_of(lab)
        ax.plot(g.n, g.ci_hw, color=col, ls="--" if lab == "difference" else "-",
                label=lab if lab != "difference" else "difference (CRN)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("number of replications")
    ax.set_ylabel("95% CI half-width ($)")
    ax.set_title("Precision improves as 1/√n")
    ax.legend()
    fig.tight_layout()
    save(fig, "fig08_ci_convergence")


def fig_sensitivity():
    s = pd.read_csv(TABLES / "sensitivity.csv")
    params = [p for p in ("setup_cost", "shortage_cost", "holding_cost") if p in set(s.parameter)]
    names = {"setup_cost": "setup cost K ($/order)", "shortage_cost": "shortage cost π ($/item/month)",
             "holding_cost": "holding cost h ($/item/month)"}
    fig, axes = plt.subplots(2, len(params), figsize=(4.6 * len(params), 7.4), squeeze=False)
    for j, p in enumerate(params):
        g = s[s.parameter == p]
        ax = axes[0, j]
        for pol, col, lab in (("sS", C_SS, "(s,S)"), ("sQ", C_SQ, "(s,Q)")):
            h = g[g.policy == pol].sort_values("value")
            ax.plot(h.value, h["mean"], "o-", color=col, label=lab, ms=5)
        ax.set_xscale("log")
        ax.set_xticks(sorted(g.value.unique()), [f"{v:g}" for v in sorted(g.value.unique())])
        ax.minorticks_off()
        ax.set_title(names[p].split(" (")[0], fontsize=12)
        if j == 0:
            ax.set_ylabel("optimized monthly cost ($)")
        ax.legend()
        ax = axes[1, j]
        sS = g[g.policy == "sS"].set_index("value")["mean"]
        sQ = g[g.policy == "sQ"].set_index("value")["mean"]
        gap = (sQ - sS).sort_index()
        bars = ax.bar(range(len(gap)), gap.values, color=C_SQ, width=0.6)
        for b_, v in zip(bars, gap.values):
            ax.text(b_.get_x() + b_.get_width() / 2, v, f"{v:.2f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=9)
        ax.set_xticks(range(len(gap)), [f"{v:g}" for v in gap.index])
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_xlabel(names[p])
        ax.grid(axis="x", visible=False)
        if j == 0:
            ax.set_ylabel("extra cost of (s,Q) over (s,S) ($)")
    fig.suptitle("Sensitivity: each policy re-optimized under different cost parameters",
                 x=0.01, ha="left", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save(fig, "fig09_sensitivity")


def fig_parity(summary):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for ax, pol in zip(axes, ("sS", "sQ")):
        df = pd.read_csv(DATA / f"screen_{pol}.csv.gz")
        df = df[df.exact < df.exact.min() + 150]
        c = C_SS if pol == "sS" else C_SQ
        ax.plot(df.exact, df["mean"], ".", color=c, ms=2, alpha=0.4, rasterized=True)
        lo, hi = df.exact.min(), df.exact.max()
        ax.plot([lo, hi], [lo, hi], color=INK, lw=1)
        r = summary[pol]["sim_vs_exact_corr"]
        name = "(s, S)" if pol == "sS" else "(s, Q)"
        ax.set_title(f"{name}: {len(df):,} grid points, r = {r:.6f}")
        ax.set_xlabel("exact expected cost ($)")
        ax.set_ylabel("simulated mean, 200 reps ($)")
    fig.text(0.01, -0.03, "Points within \\$150 of the optimum. All grid points share the same 200 CRN "
             "streams, so their errors are correlated and can bend together slightly; an independent "
             "20,000-rep re-check of the worst-looking points agrees with the exact values.",
             color=INK2, fontsize=8.5, wrap=True)
    fig.tight_layout()
    save(fig, "fig10_sim_vs_exact")


def fig_optimal_params():
    s = pd.read_csv(TABLES / "sensitivity.csv")
    params = [p for p in ("setup_cost", "shortage_cost", "holding_cost") if p in set(s.parameter)]
    fig, axes = plt.subplots(1, len(params), figsize=(4.6 * len(params), 4.2), squeeze=False)
    for j, p in enumerate(params):
        ax = axes[0, j]
        g = s[s.parameter == p]
        h = g[g.policy == "sS"].sort_values("value")
        q = g[g.policy == "sQ"].sort_values("value")
        ax.plot(h.value, h.s, "o-", color=C_SS, label="s  (s,S)")
        ax.plot(h.value, h.big, "s--", color=C_SS, label="S  (s,S)", mfc=SURFACE)
        ax.plot(q.value, q.s, "o-", color=C_SQ, label="s  (s,Q)")
        ax.plot(q.value, q.big, "s--", color=C_SQ, label="Q  (s,Q)", mfc=SURFACE)
        ax.set_xscale("log")
        ax.set_xticks(sorted(g.value.unique()), [f"{v:g}" for v in sorted(g.value.unique())])
        ax.minorticks_off()
        ax.set_xlabel(p.replace("_", " "))
        if j == 0:
            ax.set_ylabel("optimal parameter value")
            ax.legend(fontsize=9)
    fig.suptitle("How the optimal s, S and Q move with the cost parameters", x=0.01, ha="left",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    save(fig, "fig11_optimal_parameters")


def main():
    summary = json.loads((ROOT / "results" / "summary.json").read_text())
    fig_sample_paths(summary)
    fig_validation()
    fig_heatmaps(summary)
    fig_slices(summary)
    fig_candidates()
    fig_breakdown()
    fig_crn(summary)
    fig_convergence()
    fig_sensitivity()
    fig_parity(summary)
    fig_optimal_params()


if __name__ == "__main__":
    main()
