import os
import shutil
import time
import json

import pandas as pd

from .algorithms import ALGORITHMS
from .evaluation import evaluate_solution
from .objective import calculate_objective_score


BASE_RESULTS_DIR = "experiments/results"


DATASETS = {
    "demo": {
        "containers": "datasets/benchmarks/demo/containers.csv",
        "slots": "datasets/benchmarks/demo/slots.csv"
    },
    "small": {
        "containers": "datasets/benchmarks/small/containers.csv",
        "slots": "datasets/benchmarks/small/slots.csv"
    },
    "medium": {
        "containers": "datasets/benchmarks/medium/containers.csv",
        "slots": "datasets/benchmarks/medium/slots.csv"
    },
    "large": {
        "containers": "datasets/benchmarks/large/containers.csv",
        "slots": "datasets/benchmarks/large/slots.csv"
    }
}


def run_dataset(dataset_name, containers_file, slots_file):

    print()
    print("========================================")
    print(f"DATASET: {dataset_name.upper()}")
    print("========================================")
    print()

    if not os.path.exists(containers_file):
        raise FileNotFoundError(
            f"Containers file not found: {containers_file}"
        )

    if not os.path.exists(slots_file):
        raise FileNotFoundError(
            f"Slots file not found: {slots_file}"
        )

    containers = pd.read_csv(containers_file)
    slots = pd.read_csv(slots_file)

    print(f"Containers: {len(containers)}")
    print(f"Slots: {len(slots)}")
    print()

    output_dir = os.path.join(
        BASE_RESULTS_DIR,
        dataset_name
    )

    os.makedirs(output_dir, exist_ok=True)

    all_results = []

    for name, algorithm in ALGORITHMS.items():

        print("----------------------------------------")
        print(f"Running: {name}")
        print("----------------------------------------")

        start_time = time.perf_counter()

        try:

            solution = algorithm(
                containers,
                slots
            )

            runtime = (
                time.perf_counter()
                - start_time
            )

            if not isinstance(
                solution,
                pd.DataFrame
            ):
                raise TypeError(
                    f"{name} returned "
                    f"{type(solution).__name__} "
                    "instead of pandas.DataFrame"
                )

            metrics = evaluate_solution(
                solution,
                containers,
                slots
            )

            objective = calculate_objective_score(
                solution
            )

            solution_file = os.path.join(
                output_dir,
                f"{name}_solution.csv"
            )

            solution.to_csv(
                solution_file,
                index=False
            )

            row = {
                "dataset": dataset_name,
                "algorithm": name,
                "status": "SUCCESS",
                "runtime_seconds": round(
                    runtime,
                    6
                ),
                "assignment_rate": float(
                    metrics["assignment_rate"]
                ),
                "slot_utilization": float(
                    metrics["slot_utilization"]
                ),
                "total_loaded_weight": float(
                    metrics["total_loaded_weight"]
                ),
                "average_container_weight": float(
                    metrics["average_container_weight"]
                ),
                "total_teu": int(
                    metrics["total_teu"]
                ),
                "constraint_violations": int(
                    metrics["constraint_violations"]
                ),
                "rehandling": float(
                    objective["rehandling"]
                ),
                "weight_imbalance_std": float(
                    objective["weight_imbalance_std"]
                ),
                "longitudinal_balance_error": float(
                    objective[
                        "longitudinal_balance_error"
                    ]
                ),
                "destination_mixing": float(
                    objective["destination_mixing"]
                ),
                "priority_penalty": float(
                    objective["priority_penalty"]
                ),
                "unassigned": int(
                    objective[
                        "unassigned_containers"
                    ]
                ),
                "objective_score": float(
                    objective["objective_score"]
                )
            }

            all_results.append(row)

            print(
                f"Assignment Rate: "
                f"{row['assignment_rate']:.2f}%"
            )

            print(
                f"Objective Score: "
                f"{row['objective_score']:.2f}"
            )

            print(
                f"Runtime: "
                f"{runtime:.4f} seconds"
            )

            print("Status: SUCCESS")

        except Exception as error:

            runtime = (
                time.perf_counter()
                - start_time
            )

            print(
                f"ERROR: {error}"
            )

            all_results.append(
                {
                    "dataset": dataset_name,
                    "algorithm": name,
                    "status": "FAILED",
                    "runtime_seconds": round(
                        runtime,
                        6
                    ),
                    "error": str(error)
                }
            )

            print("Status: FAILED")

        print()

    results = pd.DataFrame(
        all_results
    )

    comparison_csv = os.path.join(
        output_dir,
        "algorithm_comparison.csv"
    )

    results.to_csv(
        comparison_csv,
        index=False
    )

    comparison_json = os.path.join(
        output_dir,
        "algorithm_comparison.json"
    )

    with open(
        comparison_json,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_results,
            file,
            indent=4
        )

    print()
    print("========================================")
    print(
        f"{dataset_name.upper()} COMPLETED"
    )
    print("========================================")
    print()

    if results.empty:

        print("No results generated.")

    else:

        print(
            results[
                [
                    "algorithm",
                    "status",
                    "runtime_seconds"
                ]
            ].to_string(index=False)
        )

    print()
    print(
        f"Results saved to: {output_dir}"
    )
    print()


def main():

    print()
    print("========================================")
    print("FULL BENCHMARK EXPERIMENT")
    print("========================================")
    print()

    for dataset_name, paths in DATASETS.items():

        run_dataset(
            dataset_name,
            paths["containers"],
            paths["slots"]
        )

    print()
    print("========================================")
    print("ALL DATASETS COMPLETED")
    print("========================================")


if __name__ == "__main__":
    main()