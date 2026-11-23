"""Collect the headline numbers used by the report and the slide deck into
results/key_numbers.json (so no number is typed by hand).

    python experiments/key_numbers.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"


def flat_range(df, s, tol):
    d = df[df.s == s]
    near = d[d.exact <= d.exact.min() + tol]
    return [int(near.big.min()), int(near.big.max())]


def main():
    s = json.loads((R / "summary.json").read_text())
    fin = pd.read_csv(R / "tables" / "final_comparison.csv")
    val = pd.read_csv(R / "tables" / "validation_law_kelton.csv")
    sens = pd.read_csv(R / "tables" / "sensitivity.csv")
    out = {"grid_points_per_policy": s["design"]["grid_sS"], "design": s["design"]}
    for key, row in (("sS", 0), ("sQ", 1), ("baseline", 2)):
        r = fin.iloc[row]
        out[key] = dict(label=r.policy, mean=round(r["mean"], 2), hw=round(r.ci_hw, 2),
                        sd=round(r.sd, 2), ordering=round(r.ordering, 2),
                        holding=round(r.holding, 2), shortage=round(r.shortage, 2),
                        exact=round(r.exact, 2))
    for pol in ("sS", "sQ"):
        out[pol].update(best=s[pol]["best"][1:], exact_optimum=s[pol]["exact_optimum"],
                        exact_optimum_cost=round(s[pol]["exact_optimum_cost"], 3),
                        exact_cost_of_choice=round(s[pol]["exact_cost_of_choice"], 3),
                        optimality_gap=round(s[pol]["optimality_gap"], 4),
                        n_indistinguishable=s[pol]["n_indistinguishable"],
                        corr=s[pol]["sim_vs_exact_corr"])
        df = pd.read_csv(R / "data" / f"screen_{pol}.csv.gz")
        out[pol]["flat_within_1"] = flat_range(df, s[pol]["best"][1], 1.0)
        out[pol]["flat_within_0_25"] = flat_range(df, s[pol]["best"][1], 0.25)
    f = s["final"]
    out["diff"] = dict(mean=round(f["diff_sQ_minus_sS"], 3), lo=round(f["diff_ci"][0], 3),
                       hi=round(f["diff_ci"][1], 3), t=round(f["t_stat"], 1), p=f["p_value"],
                       pct=round(100 * f["diff_sQ_minus_sS"] / out["sS"]["mean"], 2))
    out["crn"] = dict(var_ratio=round(f["crn_variance_ratio"], 3),
                      hw_crn=round(f["crn_ci_half_width"], 3),
                      hw_indep=round(f["independent_ci_half_width"], 3),
                      reps_factor=round(f["reps_needed_without_crn_for_same_precision"]
                                        / s["design"]["n_final"], 1))
    out["baseline_saving"] = round(out["baseline"]["mean"] - out["sS"]["mean"], 2)
    out["baseline_saving_pct"] = round(100 * out["baseline_saving"] / out["baseline"]["mean"], 1)
    out["validation"] = dict(n_in_ci=int(val.exact_in_ci.sum()), n=len(val),
                             max_abs_z=round(float(((val.sim_mean - val.exact) /
                                                    (val.sim_ci_hw / 1.96)).abs().max()), 2),
                             single_run_sd_range=[round(val.single_run_sd.min(), 1),
                                                  round(val.single_run_sd.max(), 1)])
    gaps = []
    for (p, v), g in sens.groupby(["parameter", "value"]):
        a = g.set_index("policy")
        gaps.append(dict(parameter=p, value=v, gap=round(a.loc["sQ", "mean"] - a.loc["sS", "mean"], 2),
                         sS=[int(a.loc["sS", "s"]), int(a.loc["sS", "big"])],
                         sQ=[int(a.loc["sQ", "s"]), int(a.loc["sQ", "big"])]))
    out["sensitivity"] = gaps
    out["sensitivity_min_gap"] = min(g["gap"] for g in gaps)
    out["sensitivity_max_gap"] = max(g["gap"] for g in gaps)
    (R / "key_numbers.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
