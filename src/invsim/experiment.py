"""
Replications, confidence intervals and policy comparison (common random numbers).

Every function takes a ``base_seed``.  Replication k of *every* policy uses the
streams ``make_streams(params, k, base_seed)``, so evaluating several policies
with the same base seed is a CRN experiment, while different base seeds give
statistically independent experiments (used to avoid optimization bias).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from .model import SystemParams, make_streams, simulate, _simulate, policy_code

Policy = tuple  # (policy_name, s, big)


def label(pol: Policy) -> str:
    name, s, big = pol
    return f"(s,S)=({s},{big})" if name == "sS" else f"(s,Q)=({s},{big})"


def run_replications(params: SystemParams, policies: list[Policy], n_reps: int,
                     base_seed: int = 0, components: bool = False) -> np.ndarray:
    """Average monthly cost of each policy in each replication.

    Returns an array of shape (n_reps, n_policies), or (n_reps, n_policies, 3)
    with [ordering, holding, shortage] when ``components`` is True.
    """
    codes = np.array([policy_code(p[0]) for p in policies])
    ss = np.array([int(p[1]) for p in policies])
    bigs = np.array([int(p[2]) for p in policies])
    out = np.empty((n_reps, len(policies), 3) if components else (n_reps, len(policies)))
    m = params.n_months
    args = (int(params.initial_inventory), int(m), float(params.setup_cost),
            float(params.incremental_cost), float(params.holding_cost),
            float(params.shortage_cost), bool(params.trigger_inclusive))
    for k in range(n_reps):
        st = make_streams(params, k, base_seed)
        for j in range(len(policies)):
            oc, hc, sc, *_ = _simulate(st.demand_times, st.demand_sizes, st.lags,
                                       codes[j], ss[j], bigs[j], *args)
            if components:
                out[k, j] = (oc / m, hc / m, sc / m)
            else:
                out[k, j] = (oc + hc + sc) / m
    return out


@dataclass
class CI:
    mean: float
    half_width: float
    std: float
    n: int

    @property
    def lo(self):
        return self.mean - self.half_width

    @property
    def hi(self):
        return self.mean + self.half_width

    def __str__(self):
        return f"{self.mean:.2f} ± {self.half_width:.2f}"


def t_ci(x: np.ndarray, alpha: float = 0.05) -> CI:
    """Student-t confidence interval for the mean of i.i.d. replications."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    sd = x.std(ddof=1)
    hw = stats.t.ppf(1 - alpha / 2, n - 1) * sd / np.sqrt(n)
    return CI(float(x.mean()), float(hw), float(sd), n)


@dataclass
class PairedComparison:
    diff: CI                 # CI for E[cost_A - cost_B]
    t_stat: float
    p_value: float
    var_reduction: float     # Var(A-B) / (Var A + Var B); <1 means CRN helped

    @property
    def significant(self) -> bool:
        return self.diff.lo > 0 or self.diff.hi < 0


def paired_t(a: np.ndarray, b: np.ndarray, alpha: float = 0.05) -> PairedComparison:
    """Paired-t comparison of two policies simulated with common random numbers."""
    d = np.asarray(a) - np.asarray(b)
    ci = t_ci(d, alpha)
    t = ci.mean / (ci.std / np.sqrt(ci.n))
    p = 2 * stats.t.sf(abs(t), ci.n - 1)
    vr = d.var(ddof=1) / (np.var(a, ddof=1) + np.var(b, ddof=1))
    return PairedComparison(ci, float(t), float(p), float(vr))


def welch(a: np.ndarray, b: np.ndarray, alpha: float = 0.05) -> CI:
    """Welch CI for E[A]-E[B] from *independent* samples (no CRN)."""
    a, b = np.asarray(a), np.asarray(b)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    hw = stats.t.ppf(1 - alpha / 2, df) * np.sqrt(va + vb)
    return CI(float(a.mean() - b.mean()), float(hw), float(np.sqrt(va + vb)), len(a))
