"""
Run every experiment of the project and write tables to results/.

    python experiments/run_all.py            # full run (~5-10 min on a laptop)
    python experiments/run_all.py --quick    # small smoke-test version

Random-number seed sets (each one an independent experiment):
    1  screening of the full (s,S) and (s,Q) grids          (CRN across all points)
    2  re-evaluation of the top candidates                   (CRN, fresh numbers)
    3  final head-to-head comparison of the two winners      (CRN, fresh numbers)
    4  the same comparison without CRN (s,Q side only)       (shows CRN's value)
    500+j  validation against Law & Kelton's nine (s,S) policies (independent per policy)
    10+ sensitivity analysis
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from invsim.model import SystemParams, make_streams, trajectory  # noqa: E402
from invsim.analytic import exact_cost  # noqa: E402
from invsim.experiment import (run_replications, t_ci, paired_t, welch, label)  # noqa: E402
from invsim.optimize import GridSpec, screen, reevaluate_and_select  # noqa: E402

TABLES = ROOT / "results" / "tables"
DATA = ROOT / "results" / "data"

# Average monthly cost reported by Law & Kelton for one 120-month run of each of
# nine (s,S) policies (their model orders when I < s).  Transcribed from the
# textbook's inventory example (Table 1.x "Results from the nine simulation runs").
LAW_KELTON = {(20, 40): 126.61, (20, 60): 122.74, (20, 80): 123.86, (20, 100): 125.32,
              (40, 60): 126.37, (40, 80): 125.46, (40, 100): 132.34, (60, 80): 150.02,
              (60, 100): 143.20}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def validation(params, n_reps):
    """Nine Law & Kelton policies: simulation CI vs exact value vs textbook.

    Each policy gets its OWN independent seed set here: CRN is the right tool for
    comparing policies, but for checking CI coverage the nine intervals must be
    independent, otherwise they all miss in the same direction together.
    """
    p = params.with_(trigger_inclusive=False)  # textbook rule: order if I < s
    pols = [("sS", s, S) for (s, S) in LAW_KELTON]
    rows = []
    for j, (_, s, S) in enumerate(pols):
        comp = run_replications(p, [pols[j]], n_reps, base_seed=500 + j, components=True)[:, 0]
        tot = comp.sum(axis=1)
        ci = t_ci(tot)
        ex = exact_cost(p, "sS", s, S)
        rows.append(dict(s=s, S=S, sim_mean=ci.mean, sim_ci_hw=ci.half_width,
                         sim_ordering=comp[:, 0].mean(), sim_holding=comp[:, 1].mean(),
                         sim_shortage=comp[:, 2].mean(), exact=ex.total,
                         exact_in_ci=bool(ci.lo <= ex.total <= ci.hi),
                         law_kelton_single_run=LAW_KELTON[(s, S)],
                         single_run_sd=ci.std))
    return pd.DataFrame(rows)


def exact_surface(params, grid: GridSpec, policy):
    rows = []
    for pol in grid.policies(policy):
        rows.append((pol[1], pol[2], exact_cost(params, *pol).total))
    return pd.DataFrame(rows, columns=["s", "big", "exact"])


def optimize_policy(params, policy, grid, n_screen, top_k, n_reeval, seed_screen, seed_reeval):
    scr = screen(params, policy, grid, n_screen, seed_screen)
    sel = reevaluate_and_select(params, scr, top_k, n_reeval, seed_reeval)
    return scr, sel


def main(quick: bool):
    TABLES.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    params = SystemParams()
    if quick:
        grid = GridSpec(range(0, 61, 4), range(4, 121, 4), range(4, 121, 4))
        N_SCREEN, TOP_K, N_REEVAL, N_FINAL, N_VAL = 30, 8, 300, 500, 300
        sens_grid = GridSpec(range(0, 81, 8), range(8, 161, 8), range(8, 161, 8))
        N_SENS_SCREEN, N_SENS_REEVAL = 20, 200
    else:
        grid = GridSpec()  # full integer grid: s 0..80, S-s 1..150, Q 1..150
        N_SCREEN, TOP_K, N_REEVAL, N_FINAL, N_VAL = 200, 20, 5000, 10000, 5000
        sens_grid = GridSpec(range(-20, 101, 2), range(2, 201, 2), range(2, 201, 2))
        N_SENS_SCREEN, N_SENS_REEVAL = 100, 2000
    summary = {"params": params.__dict__, "quick": quick,
               "design": dict(n_screen=N_SCREEN, top_k=TOP_K, n_reeval=N_REEVAL,
                              n_final=N_FINAL, n_validation=N_VAL,
                              grid_sS=len(grid.policies("sS")), grid_sQ=len(grid.policies("sQ")))}

    # ---------------------------------------------------------------- 1. validation
    log("validation against Law & Kelton and the exact Markov-chain cost")
    val = validation(params, N_VAL)
    val.to_csv(TABLES / "validation_law_kelton.csv", index=False)
    summary["validation_exact_in_ci"] = int(val.exact_in_ci.sum())

    # ------------------------------------------------------- 2. screening + selection
    selections = {}
    for policy in ("sS", "sQ"):
        log(f"screening {policy}: {len(grid.policies(policy))} grid points x {N_SCREEN} reps")
        scr, sel = optimize_policy(params, policy, grid, N_SCREEN, TOP_K, N_REEVAL, 1, 2)
        log(f"  exact cost surface for {policy}")
        ex = exact_surface(params, grid, policy)
        scr = scr.merge(ex, on=["s", "big"])
        scr.to_csv(DATA / f"screen_{policy}.csv.gz", index=False)
        sel.table["exact"] = [exact_cost(params, r.policy, r.s, r.big).total
                              for r in sel.table.itertuples()]
        sel.table.to_csv(TABLES / f"top_candidates_{policy}.csv", index=False)
        selections[policy] = sel
        i_ex = scr.exact.idxmin()
        i_scr = scr["mean"].idxmin()
        best_exact_of_choice = exact_cost(params, *sel.best).total
        summary[policy] = dict(
            best=sel.best, best_label=label(sel.best),
            screen_argmin=(int(scr.s[i_scr]), int(scr.big[i_scr])),
            screen_min_mean=float(scr["mean"][i_scr]),
            screen_min_exact=float(scr.exact[i_scr]),
            exact_optimum=(int(scr.s[i_ex]), int(scr.big[i_ex])),
            exact_optimum_cost=float(scr.exact[i_ex]),
            exact_cost_of_choice=best_exact_of_choice,
            optimality_gap=best_exact_of_choice - float(scr.exact[i_ex]),
            n_indistinguishable=int((~sel.table.significantly_worse).sum()),
            sim_vs_exact_corr=float(np.corrcoef(scr["mean"], scr.exact)[0, 1]),
        )
        log(f"  best {label(sel.best)} ; exact optimum {summary[policy]['exact_optimum']}")

    # ------------------------------------------------------- 3. final comparison
    bS, bQ = selections["sS"].best, selections["sQ"].best
    log(f"final CRN comparison {label(bS)} vs {label(bQ)}: {N_FINAL} reps")
    comp = run_replications(params, [bS, bQ], N_FINAL, base_seed=3, components=True)
    tot = comp.sum(axis=2)
    pc = paired_t(tot[:, 1], tot[:, 0])  # (s,Q) minus (s,S)
    indep = run_replications(params, [bQ], N_FINAL, base_seed=4)[:, 0]
    wc = welch(indep, tot[:, 0])
    np.savez_compressed(DATA / "final_comparison.npz", components=comp, indep_sQ=indep)
    rows = []
    for j, pol in enumerate([bS, bQ]):
        ci = t_ci(tot[:, j])
        ex = exact_cost(params, *pol)
        rows.append(dict(policy=label(pol), mean=ci.mean, ci_hw=ci.half_width, sd=ci.std,
                         ordering=comp[:, j, 0].mean(), holding=comp[:, j, 1].mean(),
                         shortage=comp[:, j, 2].mean(), exact=ex.total,
                         exact_ordering=ex.ordering, exact_holding=ex.holding,
                         exact_shortage=ex.shortage))
    # reference: the textbook's starting policy, for context
    ref = ("sS", 20, 40)
    rc = run_replications(params, [ref], N_FINAL, base_seed=3, components=True)[:, 0]
    rci = t_ci(rc.sum(axis=1))
    rows.append(dict(policy=label(ref) + " baseline", mean=rci.mean, ci_hw=rci.half_width,
                     sd=rci.std, ordering=rc[:, 0].mean(), holding=rc[:, 1].mean(),
                     shortage=rc[:, 2].mean(), exact=exact_cost(params, *ref).total))
    pd.DataFrame(rows).to_csv(TABLES / "final_comparison.csv", index=False)
    summary["final"] = dict(
        diff_sQ_minus_sS=pc.diff.mean, diff_ci=(pc.diff.lo, pc.diff.hi), p_value=pc.p_value,
        t_stat=pc.t_stat, significant=pc.significant,
        crn_variance_ratio=pc.var_reduction,
        crn_ci_half_width=pc.diff.half_width, independent_ci_half_width=wc.half_width,
        independent_diff=wc.mean,
        reps_needed_without_crn_for_same_precision=int(np.ceil(
            N_FINAL * (wc.half_width / pc.diff.half_width) ** 2)),
        baseline_saving_vs_20_40=rci.mean - rows[0]["mean"],
    )
    log(f"  diff (s,Q)-(s,S) = {pc.diff}  p={pc.p_value:.2e}")

    # ------------------------------------------------- 4. sample paths for plots
    st = make_streams(params, 0, base_seed=3)
    paths = {}
    for pol in (bS, bQ):
        t, lev, ot, _ = trajectory(params, *pol, st)
        paths[label(pol)] = dict(t=t.tolist(), level=lev.tolist(), orders=ot.tolist())
    (DATA / "sample_paths.json").write_text(json.dumps(paths))

    # ------------------------------------------------- 5. sensitivity analysis
    rows = []
    seed = 10
    scenarios = [("setup_cost", v) for v in (8, 16, 32, 64, 128)] + \
                [("shortage_cost", v) for v in (1, 2, 5, 10, 20)] + \
                [("holding_cost", v) for v in (0.5, 1, 2, 4)]
    if quick:
        scenarios = [("setup_cost", v) for v in (16, 32, 64)] + [("shortage_cost", v) for v in (2, 5, 10)]
    for name, val_ in scenarios:
        p = params.with_(**{name: float(val_)})
        for policy in ("sS", "sQ"):
            log(f"sensitivity {name}={val_} {policy}")
            scr = screen(p, policy, sens_grid, N_SENS_SCREEN, seed)
            sel = reevaluate_and_select(p, scr, 10, N_SENS_REEVAL, seed + 1)
            b = sel.table.iloc[0]
            rows.append(dict(parameter=name, value=val_, policy=policy, s=int(b.s), big=int(b.big),
                             mean=b["mean"], ci_hw=b.ci_hw,
                             exact=exact_cost(p, policy, int(b.s), int(b.big)).total))
            seed += 2
    sens = pd.DataFrame(rows)
    sens.to_csv(TABLES / "sensitivity.csv", index=False)

    # ------------------------------------------------- 6. CI convergence
    conv = run_replications(params, [bS, bQ], N_FINAL, base_seed=3)
    ns = np.unique(np.logspace(1, np.log10(N_FINAL), 25).astype(int))
    crow = []
    for n in ns:
        for j, pol in enumerate((bS, bQ)):
            ci = t_ci(conv[:n, j])
            crow.append(dict(n=int(n), policy=label(pol), mean=ci.mean, ci_hw=ci.half_width))
        d = t_ci(conv[:n, 1] - conv[:n, 0])
        crow.append(dict(n=int(n), policy="difference", mean=d.mean, ci_hw=d.half_width))
    pd.DataFrame(crow).to_csv(TABLES / "ci_convergence.csv", index=False)

    (ROOT / "results" / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    log("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
