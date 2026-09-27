"""Reproducible benchmark runner for the RCSPPSuite-derived datasets.

Examples:
    python research/run_rcspp_benchmark.py --dataset rcspp_small --repeats 5
    python research/run_rcspp_benchmark.py --dataset all --repeats 5

The three stochastic algorithms are repeated with explicit seeds. Deterministic
heuristics and CP-SAT are executed once per dataset. Raw and aggregate CSV files
are written to research/results/.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optimization.algorithms import (
    greedy,
    priority_greedy,
    best_fit,
    randomized_greedy,
    simulated_annealing,
    genetic_algorithm,
    cp_sat,
)
from optimization.evaluation import evaluate_solution
from optimization.objective import calculate_objective_score

DATASETS = {
    "rcspp_small": ROOT / "datasets" / "rcspp" / "generated" / "rcspp_small",
    "rcspp_medium": ROOT / "datasets" / "rcspp" / "generated" / "rcspp_medium",
    "rcspp_large": ROOT / "datasets" / "rcspp" / "generated" / "rcspp_large",
}

DETERMINISTIC = {
    "greedy": lambda c, s, seed: greedy(c, s),
    "priority_greedy": lambda c, s, seed: priority_greedy(c, s),
    "best_fit": lambda c, s, seed: best_fit(c, s),
    "cp_sat": lambda c, s, seed: cp_sat(c, s),
}
STOCHASTIC = {
    "randomized_greedy": lambda c, s, seed: randomized_greedy(c, s, seed=seed),
    "simulated_annealing": lambda c, s, seed: simulated_annealing(c, s, seed=seed),
    "genetic": lambda c, s, seed: genetic_algorithm(c, s, seed=seed),
}


def run_one(dataset_name: str, repeats: int, seeds: list[int]):
    folder = DATASETS[dataset_name]
    containers = pd.read_csv(folder / "containers.csv")
    slots = pd.read_csv(folder / "slots.csv")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))

    rows = []
    algorithms = {**DETERMINISTIC, **STOCHASTIC}
    for name, fn in algorithms.items():
        run_seeds = [seeds[0]] if name in DETERMINISTIC else seeds[:repeats]
        for repeat_index, seed in enumerate(run_seeds, start=1):
            started = time.perf_counter()
            status = "SUCCESS"
            error = ""
            try:
                solution = fn(containers, slots, seed)
                runtime = time.perf_counter() - started
                metrics = evaluate_solution(solution, containers, slots)
                objective = calculate_objective_score(solution)
                row = {
                    "dataset": dataset_name,
                    "source_instance": manifest["source_instance"],
                    "algorithm": name,
                    "repeat": repeat_index,
                    "seed": seed,
                    "runtime_seconds": runtime,
                    **metrics,
                    **objective,
                }
            except Exception as exc:
                runtime = time.perf_counter() - started
                status = "FAILED"
                error = str(exc)
                row = {
                    "dataset": dataset_name,
                    "source_instance": manifest["source_instance"],
                    "algorithm": name,
                    "repeat": repeat_index,
                    "seed": seed,
                    "runtime_seconds": runtime,
                }
            row["status"] = status
            row["error"] = error
            rows.append(row)
            print(dataset_name, name, repeat_index, status, f"{runtime:.3f}s")
    return pd.DataFrame(rows)


def aggregate(raw: pd.DataFrame):
    successful = raw[raw["status"] == "SUCCESS"].copy()
    numeric = [
        "runtime_seconds", "assignment_rate", "slot_utilization",
        "constraint_violations", "rehandling", "weight_imbalance_std",
        "longitudinal_balance_error", "destination_mixing",
        "unassigned_containers", "objective_score",
    ]
    numeric = [c for c in numeric if c in successful.columns]
    if successful.empty:
        return pd.DataFrame()
    agg = successful.groupby(["dataset", "source_instance", "algorithm"])[numeric].agg(["mean", "std", "min", "max"])
    agg.columns = [f"{a}_{b}" for a, b in agg.columns]
    return agg.reset_index()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["all", *DATASETS.keys()], default="rcspp_small")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    repeats = max(1, args.repeats)
    seeds = [42, 142, 242, 342, 442, 542, 642, 742, 842, 942]
    chosen = list(DATASETS) if args.dataset == "all" else [args.dataset]

    frames = [run_one(ds, repeats, seeds) for ds in chosen]
    raw = pd.concat(frames, ignore_index=True)
    summary = aggregate(raw)

    out = ROOT / "research" / "results"
    out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out / "rcspp_benchmark_raw.csv", index=False)
    summary.to_csv(out / "rcspp_benchmark_summary.csv", index=False)
    print(f"Saved: {out / 'rcspp_benchmark_raw.csv'}")
    print(f"Saved: {out / 'rcspp_benchmark_summary.csv'}")


if __name__ == "__main__":
    main()
