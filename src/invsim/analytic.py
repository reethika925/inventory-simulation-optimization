"""
Exact (numerical) expected cost of a stationary reorder policy - used only to
*validate* the simulation and to audit the simulation-based optimizer.

Why this is possible: the delivery lag is at most one month, so every order
arrives before the next review.  The inventory level at review epochs,
X_0 = 60, X_1, X_2, ..., is therefore a Markov chain:

    X_{k+1} = X_k + z(X_k) - D_k,

where z(x) is the order quantity the policy places at level x and D_k is the
(compound-Poisson) demand during month k.  The expected cost incurred during
a month that starts at level x with order z is

    K*1{z>0} + i*z + int_0^1 E[ c(x + z*1{L<t} - D(t)) ] dt,

with c(y) = h*y^+ + pi*y^-, D(t) the demand in (0, t] and L ~ U(0.5, 1)
independent of the demand.  Splitting on {L<t}:

    int_0^1 (1-F_L(t)) E c(x - D(t)) dt  +  int_0^1 F_L(t) E c(x + z - D(t)) dt
      =: g0(x) + g1(x + z).

g0 and g1 are tabulated once on an integer grid (Gauss-Legendre in t), and
the distribution of X_k is propagated forward for the 120 months, which gives
the exact expected average monthly cost over the finite horizon - the very
quantity each simulation replication estimates without bias.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.stats import poisson

from .model import SystemParams, policy_code, POLICY_SS

LO, HI = -400, 400          # default inventory-level grid; widened automatically when needed
LOST_MASS_TOL = 1e-12       # probability allowed to fall below the grid before widening it
N_MAX = 60                  # max number of demands in one month (P(N>60) ~ 1e-25)
GL_NODES = 48               # Gauss-Legendre nodes per half-interval


@dataclass
class ExactResult:
    ordering: float
    holding: float
    shortage: float

    @property
    def total(self) -> float:
        return self.ordering + self.holding + self.shortage


def _size_convolutions(params: SystemParams) -> np.ndarray:
    """Row n = pmf of the sum of n i.i.d. demand sizes (support 0..N_MAX*max)."""
    sizes = np.asarray(params.demand_sizes)
    one = np.zeros(sizes.max() + 1)
    one[sizes] = params.demand_probs
    width = N_MAX * sizes.max() + 1
    out = np.zeros((N_MAX + 1, width))
    out[0, 0] = 1.0
    for n in range(1, N_MAX + 1):
        conv = np.convolve(out[n - 1], one)[:width]
        out[n] = conv
    return out


def _demand_pmf(t: float, params: SystemParams, conv: np.ndarray) -> np.ndarray:
    lam = t / params.mean_interdemand
    w = poisson.pmf(np.arange(N_MAX + 1), lam)
    return w @ conv


@lru_cache(maxsize=32)
def _tables(params: SystemParams, LO: int = LO, HI: int = HI):
    """Return y-grid, g0/g1 for holding & shortage, and the one-month demand pmf."""
    conv = _size_convolutions(params)
    y = np.arange(LO, HI + 1)
    a, b = params.lag_low, params.lag_high

    def F_L(t):
        return np.clip((t - a) / (b - a), 0.0, 1.0)

    # quadrature on [0,a] and [a,b] separately (F_L has a kink at a); [b,1] if b<1
    xs, ws = np.polynomial.legendre.leggauss(GL_NODES)
    pieces = [(0.0, a), (a, b)] + ([(b, 1.0)] if b < 1.0 else [])
    nodes, weights = [], []
    for lo, hi in pieces:
        nodes.append(0.5 * (hi - lo) * xs + 0.5 * (hi + lo))
        weights.append(0.5 * (hi - lo) * ws)
    nodes = np.concatenate(nodes)
    weights = np.concatenate(weights)

    g0h = np.zeros_like(y, dtype=float)
    g0s = np.zeros_like(y, dtype=float)
    g1h = np.zeros_like(y, dtype=float)
    g1s = np.zeros_like(y, dtype=float)
    for t, w in zip(nodes, weights):
        pmf = _demand_pmf(t, params, conv)
        d = np.nonzero(pmf > 1e-16)[0]
        p = pmf[d]
        lev = y[:, None] - d[None, :]
        hold = (np.maximum(lev, 0) * p).sum(axis=1)
        short = (np.maximum(-lev, 0) * p).sum(axis=1)
        FL = F_L(t)
        g0h += w * (1 - FL) * hold
        g0s += w * (1 - FL) * short
        g1h += w * FL * hold
        g1s += w * FL * short
    month_pmf = _demand_pmf(1.0, params, conv)
    month_pmf = month_pmf[: np.nonzero(month_pmf > 1e-18)[0].max() + 1]
    return y, g0h, g0s, g1h, g1s, month_pmf


def exact_cost(params: SystemParams, policy: str, s: int, big: int) -> ExactResult:
    """Exact expected average monthly cost over the finite horizon.

    Unstable policies (e.g. an (s,Q) rule with Q below the mean monthly demand of
    25) let the backlog drift far below zero; the grid is then widened until no
    probability mass is lost.
    """
    lo = LO
    while True:
        res = _exact_cost_on_grid(params, policy, s, big, lo)
        if res is not None:
            return res
        lo *= 4


def _exact_cost_on_grid(params, policy, s, big, LO):
    y, g0h, g0s, g1h, g1s, dpmf = _tables(params, LO, HI)
    code = policy_code(policy)
    n = len(y)
    trig = (y <= s) if params.trigger_inclusive else (y < s)
    if code == POLICY_SS:
        z = np.where(trig, big - y, 0)
    else:
        z = np.where(trig, big, 0)
    z = np.maximum(z, 0)
    post = y + z
    if post.max() > HI:
        raise ValueError("order-up-to level outside the analytic grid")
    post_idx = post - LO
    month_order = np.where(z > 0, params.setup_cost + params.incremental_cost * z, 0.0)
    month_hold = params.holding_cost * (g0h + g1h[post_idx])
    month_short = params.shortage_cost * (g0s + g1s[post_idx])

    dist = np.zeros(n)
    dist[params.initial_inventory - LO] = 1.0
    tot_o = tot_h = tot_s = 0.0
    for _ in range(params.n_months):
        tot_o += dist @ month_order
        tot_h += dist @ month_hold
        tot_s += dist @ month_short
        q = np.bincount(post_idx, weights=dist, minlength=n)
        # next level = post - D  ->  shift left by D
        nxt = np.convolve(q, dpmf[::-1])[len(dpmf) - 1:]
        dist = nxt[:n]
        if 1.0 - dist.sum() > LOST_MASS_TOL:
            return None  # mass fell below the grid -> caller widens it
    m = params.n_months
    return ExactResult(tot_o / m, tot_h / m, tot_s / m)
