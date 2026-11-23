"""Correctness tests for the simulation model.   Run:  python -m pytest -q"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from invsim.model import SystemParams, make_streams, simulate, trajectory  # noqa: E402
from invsim.analytic import exact_cost  # noqa: E402
from invsim.experiment import run_replications, paired_t, t_ci  # noqa: E402

P = SystemParams()
POLICIES = [("sS", 20, 40), ("sS", 40, 100), ("sS", 0, 30), ("sQ", 20, 40), ("sQ", 25, 55)]


@pytest.mark.parametrize("pol", POLICIES)
def test_fast_kernel_matches_reference_event_loop(pol):
    """The compiled kernel and the independent pure-python event loop agree."""
    for rep in range(20):
        st = make_streams(P, rep)
        a = simulate(P, *pol, st)
        *_, b = trajectory(P, *pol, st)
        assert a.n_orders == b.n_orders and a.items_ordered == b.items_ordered
        assert a.total == pytest.approx(b.total, abs=1e-9)
        assert a.holding == pytest.approx(b.holding, abs=1e-9)


def test_crn_streams_are_reproducible_and_shared():
    a, b = make_streams(P, 3, 11), make_streams(P, 3, 11)
    assert np.array_equal(a.demand_times, b.demand_times)
    assert np.array_equal(a.lags, b.lags)
    c = make_streams(P, 4, 11)
    assert not np.array_equal(a.demand_times[:10], c.demand_times[:10])


def test_demand_rate_matches_theory():
    """10 demands/month x mean size 2.5 = 25 items/month."""
    r = [simulate(P, "sS", 20, 40, make_streams(P, k, 99)).items_demanded for k in range(400)]
    rate = np.mean(r) / P.n_months
    assert abs(rate - 25) < 0.15


def test_lags_within_bounds_and_orders_arrive_before_next_review():
    st = make_streams(P, 0)
    assert st.lags.min() >= 0.5 and st.lags.max() <= 1.0


def test_flow_conservation():
    """Final inventory = initial + ordered - demanded (orders all arrive by t=120
    except possibly the very last one)."""
    st = make_streams(P, 5)
    t, lev, orders, res = trajectory(P, "sS", 20, 60, st)
    outstanding = 0
    if len(orders) and orders[-1] + st.lags[res.n_orders - 1] >= P.n_months:
        outstanding = 60 - lev[np.searchsorted(t, orders[-1], side="right") - 1]
    assert lev[-1] == P.initial_inventory + res.items_ordered - outstanding - res.items_demanded


@pytest.mark.parametrize("pol", [("sS", 20, 60), ("sQ", 20, 40), ("sS", 60, 100)])
def test_simulation_is_unbiased_for_exact_cost(pol):
    """Mean of many replications lies within 4 standard errors of the exact value."""
    x = run_replications(P, [pol], 4000, base_seed=123)[:, 0]
    ci = t_ci(x)
    se = ci.std / np.sqrt(ci.n)
    assert abs(ci.mean - exact_cost(P, *pol).total) < 4 * se


def test_paired_t_with_crn_reduces_variance():
    x = run_replications(P, [("sS", 24, 62), ("sQ", 24, 52)], 500, base_seed=7)
    pc = paired_t(x[:, 1], x[:, 0])
    assert pc.var_reduction < 0.5


def test_inclusive_vs_strict_trigger():
    st = make_streams(P, 0)
    a = simulate(P, "sS", 20, 40, st)
    b = simulate(P.with_(trigger_inclusive=False), "sS", 21, 40, st)
    assert a.total == pytest.approx(b.total)   # I <= 20  is the same rule as  I < 21


def test_exact_cost_handles_unstable_policies():
    """Q below mean demand: backlog drifts to ~-2000; the exact grid must widen."""
    x = run_replications(P, [("sQ", 10, 20)], 3000, base_seed=321)[:, 0]
    ci = t_ci(x)
    assert abs(ci.mean - exact_cost(P, "sQ", 10, 20).total) < 4 * ci.std / np.sqrt(ci.n)
