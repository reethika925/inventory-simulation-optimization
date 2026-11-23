"""
Simulation-based search for good (s, S) and (s, Q) parameters.

Three stages, each on its own independent random numbers:

1. **Screening** (seed set A): every point of a full integer grid is simulated
   with n_screen CRN replications.  CRN makes the estimated cost surface smooth,
   so differences between neighbouring points are mostly real.
2. **Re-evaluation** (seed set B): the best ``top_k`` points of stage 1 are
   simulated again with fresh, independent replications.  Picking the minimum
   of thousands of noisy estimates is biased low ("optimizer's curse"); fresh
   replications remove that bias.
3. **Selection**: the point with the lowest stage-2 mean is chosen; every other
   candidate is compared with it by a paired-t test with a Bonferroni
   correction.  Candidates that are not significantly worse form the set of
   policies that are statistically indistinguishable from the best.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .model import SystemParams
from .experiment import run_replications, t_ci, paired_t, label


@dataclass
class GridSpec:
    s_values: range = range(0, 81)            # reorder point s
    gap_values: range = range(1, 151)         # S - s for (s,S)
    q_values: range = range(1, 151)           # Q for (s,Q)

    def policies(self, policy: str):
        if policy == "sS":
            return [("sS", s, s + g) for s in self.s_values for g in self.gap_values]
        return [("sQ", s, q) for s in self.s_values for q in self.q_values]


def screen(params: SystemParams, policy: str, grid: GridSpec, n_reps: int,
           base_seed: int) -> pd.DataFrame:
    pols = grid.policies(policy)
    costs = run_replications(params, pols, n_reps, base_seed)
    df = pd.DataFrame(pols, columns=["policy", "s", "big"])
    df["mean"] = costs.mean(axis=0)
    df["se"] = costs.std(axis=0, ddof=1) / np.sqrt(n_reps)
    return df


@dataclass
class Selection:
    policy: str
    table: pd.DataFrame          # stage-2 statistics of the candidates
    best: tuple
    costs: np.ndarray            # stage-2 replications (n_reps, top_k)
    candidates: list = field(default_factory=list)


def reevaluate_and_select(params: SystemParams, screened: pd.DataFrame, top_k: int,
                          n_reps: int, base_seed: int, alpha: float = 0.05) -> Selection:
    top = screened.nsmallest(top_k, "mean").reset_index(drop=True)
    cands = [(r.policy, int(r.s), int(r.big)) for r in top.itertuples()]
    costs = run_replications(params, cands, n_reps, base_seed)
    means = costs.mean(axis=0)
    ib = int(np.argmin(means))
    rows = []
    for j, c in enumerate(cands):
        ci = t_ci(costs[:, j], alpha)
        if j == ib:
            p, lo, hi, worse = np.nan, 0.0, 0.0, False
        else:
            # Bonferroni over the (top_k - 1) comparisons with the best
            pc = paired_t(costs[:, j], costs[:, ib], alpha / (top_k - 1))
            p, lo, hi, worse = pc.p_value, pc.diff.lo, pc.diff.hi, pc.diff.lo > 0
        rows.append(dict(policy=c[0], s=c[1], big=c[2], label=label(c),
                         screen_mean=top.loc[j, "mean"], mean=ci.mean, ci_hw=ci.half_width,
                         diff_vs_best_lo=lo, diff_vs_best_hi=hi, p_vs_best=p,
                         significantly_worse=worse))
    table = pd.DataFrame(rows).sort_values("mean").reset_index(drop=True)
    return Selection(cands[0][0], table, cands[ib], costs, cands)
