"""
Discrete-event simulation of a single-product inventory system with periodic review.

The system follows the inventory example of Law & Kelton (Simulation Modeling and
Analysis, Sec. 1.5):

* Inventory is reviewed at the start of every month (t = 0, 1, ..., n_months-1).
* Customer demands arrive as a Poisson process (exponential inter-demand times,
  mean 0.1 month) and each demand is for D items, D in {1,2,3,4} with
  probabilities {1/6, 1/3, 1/3, 1/6}.
* Unmet demand is backlogged (inventory level may go negative).
* An order of Z items costs K + i*Z and arrives after a Uniform(0.5, 1) month lag.
  Because the lag is at most one month, an order always arrives before the next
  review, so the inventory level at a review is also the inventory position.
* Holding cost h per item per month on I+(t); shortage cost pi per item per month
  on I-(t). Both are time-integrated (area under the curve).

Two reorder policies are supported:

* ("sS", s, S): if I <= s, order S - I  (order-up-to)
* ("sQ", s, Q): if I <= s, order a fixed Q

Common random numbers (CRN)
---------------------------
Every replication draws three *separate* random streams - inter-demand times,
demand sizes and delivery lags - from a seed that depends only on the replication
index.  Two policies simulated with the same replication index therefore see the
exact same customer demand sequence, and their k-th orders get the same lag.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

try:  # numba makes the grid search ~50x faster; the pure-python path is identical
    from numba import njit
except ImportError:  # pragma: no cover
    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda f: f


POLICY_SS = 0  # (s, S)
POLICY_SQ = 1  # (s, Q)


@dataclass(frozen=True)
class SystemParams:
    """Inventory system parameters (defaults = Law & Kelton example)."""

    initial_inventory: int = 60
    n_months: int = 120
    mean_interdemand: float = 0.1
    demand_sizes: tuple = (1, 2, 3, 4)
    demand_probs: tuple = (1 / 6, 1 / 3, 1 / 3, 1 / 6)
    lag_low: float = 0.5
    lag_high: float = 1.0
    setup_cost: float = 32.0        # K
    incremental_cost: float = 3.0   # i, per item ordered
    holding_cost: float = 1.0       # h, per item per month
    shortage_cost: float = 5.0      # pi, per item per month
    trigger_inclusive: bool = True  # order when I <= s (proposal); False: I < s (Law & Kelton)

    def with_(self, **kw) -> "SystemParams":
        d = self.__dict__.copy()
        d.update(kw)
        return SystemParams(**d)


@dataclass
class Streams:
    """Pre-generated random numbers for one replication (the CRN unit)."""

    demand_times: np.ndarray  # arrival epochs of demands in [0, n_months)
    demand_sizes: np.ndarray  # matching demand sizes
    lags: np.ndarray          # delivery lag for the 1st, 2nd, ... order placed


def make_streams(params: SystemParams, rep: int, base_seed: int = 0) -> Streams:
    """Generate the three independent streams of replication ``rep``.

    ``np.random.SeedSequence((base_seed, rep, stream_id))`` gives statistically
    independent streams across replications and across stream ids, while the
    same (base_seed, rep) always reproduces the same numbers -> CRN.
    """
    g_time = np.random.default_rng(np.random.SeedSequence((base_seed, rep, 1)))
    g_size = np.random.default_rng(np.random.SeedSequence((base_seed, rep, 2)))
    g_lag = np.random.default_rng(np.random.SeedSequence((base_seed, rep, 3)))

    # Draw enough inter-demand times in one shot, extend if needed (rare).
    expected = params.n_months / params.mean_interdemand
    n = int(expected + 10 * np.sqrt(expected) + 50)
    gaps = g_time.exponential(params.mean_interdemand, size=n)
    times = np.cumsum(gaps)
    while times[-1] < params.n_months:
        extra = g_time.exponential(params.mean_interdemand, size=n)
        times = np.concatenate([times, times[-1] + np.cumsum(extra)])
    times = times[times < params.n_months]

    sizes = g_size.choice(np.asarray(params.demand_sizes),
                          p=np.asarray(params.demand_probs), size=len(times))
    lags = g_lag.uniform(params.lag_low, params.lag_high, size=params.n_months + 1)
    return Streams(times, sizes.astype(np.int64), lags)


@njit(cache=True)
def _simulate(demand_times, demand_sizes, lags, policy, s, big, init_inv, n_months,
              K, i_cost, h, pi, inclusive):
    """Event loop.  Returns (order_cost, holding_cost, shortage_cost, n_orders,
    items_ordered, items_demanded) totals over the run (not per month)."""
    inv = init_inv
    t_last = 0.0
    area_plus = 0.0
    area_minus = 0.0
    order_cost = 0.0
    n_orders = 0
    items_ordered = 0
    items_demanded = 0

    pending_amount = 0
    pending_time = 1e18  # no outstanding order

    d = 0
    nd = demand_times.shape[0]
    for month in range(n_months):
        t_review = float(month)
        # process every event strictly before the review, in time order
        while True:
            t_dem = demand_times[d] if d < nd else 1e18
            t_next = min(t_dem, pending_time)
            if t_next >= t_review:
                break
            dt = t_next - t_last
            if inv > 0:
                area_plus += inv * dt
            else:
                area_minus += -inv * dt
            t_last = t_next
            if pending_time <= t_dem:      # order arrival
                inv += pending_amount
                pending_amount = 0
                pending_time = 1e18
            else:                          # demand
                inv -= demand_sizes[d]
                items_demanded += demand_sizes[d]
                d += 1
        # review at t_review
        dt = t_review - t_last
        if inv > 0:
            area_plus += inv * dt
        else:
            area_minus += -inv * dt
        t_last = t_review

        trigger = (inv <= s) if inclusive else (inv < s)
        if trigger:
            if policy == 0:
                z = big - inv
            else:
                z = big
            if z > 0:
                order_cost += K + i_cost * z
                n_orders += 1
                items_ordered += z
                pending_amount = z
                pending_time = t_review + lags[n_orders - 1]

    # events between the last review and the end of the run
    t_end = float(n_months)
    while True:
        t_dem = demand_times[d] if d < nd else 1e18
        t_next = min(t_dem, pending_time)
        if t_next >= t_end:
            break
        dt = t_next - t_last
        if inv > 0:
            area_plus += inv * dt
        else:
            area_minus += -inv * dt
        t_last = t_next
        if pending_time <= t_dem:
            inv += pending_amount
            pending_amount = 0
            pending_time = 1e18
        else:
            inv -= demand_sizes[d]
            items_demanded += demand_sizes[d]
            d += 1
    dt = t_end - t_last
    if inv > 0:
        area_plus += inv * dt
    else:
        area_minus += -inv * dt

    return (order_cost, h * area_plus, pi * area_minus, n_orders, items_ordered,
            items_demanded)


@dataclass
class RunResult:
    ordering: float  # average monthly ordering cost
    holding: float   # average monthly holding cost
    shortage: float  # average monthly shortage (backlog) cost
    n_orders: int
    items_ordered: int
    items_demanded: int

    @property
    def total(self) -> float:
        return self.ordering + self.holding + self.shortage


def policy_code(name: str) -> int:
    if name in ("sS", "(s,S)"):
        return POLICY_SS
    if name in ("sQ", "(s,Q)"):
        return POLICY_SQ
    raise ValueError(f"unknown policy {name!r}")


def simulate(params: SystemParams, policy: str, s: int, big: int,
             streams: Streams) -> RunResult:
    """Run one replication. ``big`` is S for (s,S) and Q for (s,Q)."""
    if policy_code(policy) == POLICY_SS and big <= s:
        raise ValueError("(s,S) needs S > s")
    if policy_code(policy) == POLICY_SQ and big <= 0:
        raise ValueError("(s,Q) needs Q > 0")
    oc, hc, sc, no, io, idm = _simulate(
        streams.demand_times, streams.demand_sizes, streams.lags,
        policy_code(policy), int(s), int(big), int(params.initial_inventory),
        int(params.n_months), float(params.setup_cost), float(params.incremental_cost),
        float(params.holding_cost), float(params.shortage_cost),
        bool(params.trigger_inclusive))
    m = params.n_months
    return RunResult(oc / m, hc / m, sc / m, int(no), int(io), int(idm))


def trajectory(params: SystemParams, policy: str, s: int, big: int,
               streams: Streams):
    """Pure-python event loop that also records the inventory sample path.

    Used for plots and as an independent cross-check of the fast kernel.
    Returns (times, levels, order_times, result).
    """
    inv = params.initial_inventory
    times, levels, order_times = [0.0], [inv], []
    events = [(t, "D", int(z)) for t, z in zip(streams.demand_times, streams.demand_sizes)]
    events += [(float(m), "R", 0) for m in range(params.n_months)]
    events.sort(key=lambda e: (e[0], 0 if e[1] == "D" else 1))
    pending = None  # (time, amount)
    area_p = area_m = 0.0
    t_last = 0.0
    oc = 0.0
    n_orders = io = idm = 0
    code = policy_code(policy)

    def advance(t):
        nonlocal area_p, area_m, t_last
        dt = t - t_last
        area_p += max(inv, 0) * dt
        area_m += max(-inv, 0) * dt
        t_last = t

    k = 0
    while k < len(events) or pending is not None:
        nxt = events[k] if k < len(events) else (float("inf"), "X", 0)
        if pending is not None and pending[0] <= nxt[0] and pending[0] < params.n_months:
            advance(pending[0])
            inv += pending[1]
            times.append(pending[0]); levels.append(inv)
            pending = None
            continue
        if k >= len(events):
            break
        t, kind, z = nxt
        k += 1
        advance(t)
        if kind == "D":
            inv -= z
            idm += z
            times.append(t); levels.append(inv)
        else:
            trig = inv <= s if params.trigger_inclusive else inv < s
            if trig:
                amt = big - inv if code == POLICY_SS else big
                if amt > 0:
                    oc += params.setup_cost + params.incremental_cost * amt
                    pending = (t + streams.lags[n_orders], amt)
                    n_orders += 1
                    io += amt
                    order_times.append(t)
    advance(float(params.n_months))
    times.append(float(params.n_months)); levels.append(inv)
    m = params.n_months
    res = RunResult(oc / m, params.holding_cost * area_p / m,
                    params.shortage_cost * area_m / m, n_orders, io, idm)
    return np.array(times), np.array(levels), np.array(order_times), res
