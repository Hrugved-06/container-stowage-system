"""Quick self-check for the publication benchmark extension."""
from pathlib import Path
import json
import pandas as pd

from backend.validator import validate_dataset
from optimization.algorithms import greedy, priority_greedy, best_fit
from optimization.evaluation import evaluate_solution

ROOT = Path(__file__).resolve().parent


def main():
    failed = False
    for ds in ["rcspp_small", "rcspp_medium", "rcspp_large"]:
        folder = ROOT / "datasets" / "rcspp" / "generated" / ds
        containers = pd.read_csv(folder / "containers.csv")
        slots = pd.read_csv(folder / "slots.csv")
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        validation = validate_dataset(containers, slots)
        if not validation["valid"]:
            failed = True
            print(f"[FAIL] {ds}: {validation}")
            continue
        print(f"[PASS] {ds}: {len(containers)} containers / {len(slots)} slots from {manifest['source_instance']}")

    # Fast smoke test on the smallest public-benchmark-derived dataset.
    folder = ROOT / "datasets" / "rcspp" / "generated" / "rcspp_small"
    containers = pd.read_csv(folder / "containers.csv")
    slots = pd.read_csv(folder / "slots.csv")
    for name, fn in [("greedy", greedy), ("priority_greedy", priority_greedy), ("best_fit", best_fit)]:
        solution = fn(containers, slots)
        metrics = evaluate_solution(solution, containers, slots)
        if metrics["constraint_violations"] != 0 or metrics["slot_utilization"] > 100.000001:
            failed = True
            print(f"[FAIL] {name}: {metrics}")
        else:
            print(
                f"[PASS] {name}: assignment={metrics['assignment_rate']:.2f}% "
                f"utilization={metrics['slot_utilization']:.2f}% violations=0"
            )

    if failed:
        raise SystemExit(1)
    print("\nPublication benchmark smoke test passed.")


if __name__ == "__main__":
    main()
