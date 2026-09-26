import os
import time
import json

import pandas as pd

try:
    from .algorithms import ALGORITHMS
    from .objective import calculate_objective_score
    from .evaluation import evaluate_solution
except ImportError:
    from algorithms import ALGORITHMS
    from objective import calculate_objective_score
    from evaluation import evaluate_solution


CONTAINER_FILE = "datasets/generated/containers.csv"
SLOT_FILE = "datasets/generated/slots.csv"
OUTPUT_DIR = "experiments/results"


def run():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print("\n========================================")
    print("AI-ASSISTED CONTAINER STOWAGE EXPERIMENT")
    print("========================================\n")

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------

    if not os.path.exists(CONTAINER_FILE):
        raise FileNotFoundError(
            f"Container file not found: {CONTAINER_FILE}"
        )

    if not os.path.exists(SLOT_FILE):
        raise FileNotFoundError(
            f"Slot file not found: {SLOT_FILE}"
        )

    containers = pd.read_csv(
        CONTAINER_FILE
    )

    slots = pd.read_csv(
        SLOT_FILE
    )

    print(
        f"Containers: {len(containers)}"
    )

    print(
        f"Slots: {len(slots)}"
    )

    print()

    # --------------------------------------------------
    # RESULTS
    # --------------------------------------------------

    all_results = []

    # --------------------------------------------------
    # RUN EVERY ALGORITHM
    # --------------------------------------------------

    for name, algorithm in ALGORITHMS.items():

        print("----------------------------------------")
        print(f"Running: {name}")
        print("----------------------------------------")

        start_time = time.perf_counter()

        try:

            # Every algorithm MUST return a DataFrame.
            solution = algorithm(
                containers,
                slots
            )

            runtime = (
                time.perf_counter()
                - start_time
            )

            # --------------------------------------------------
            # STANDARD OUTPUT CHECK
            # --------------------------------------------------

            if not isinstance(
                solution,
                pd.DataFrame
            ):

                raise TypeError(
                    f"{name} returned "
                    f"{type(solution).__name__} "
                    f"instead of pandas.DataFrame"
                )

            # --------------------------------------------------
            # EVALUATION
            # --------------------------------------------------

            metrics = evaluate_solution(
                solution,
                containers,
                slots
            )

            objective = calculate_objective_score(
                solution
            )

            # --------------------------------------------------
            # SAVE INDIVIDUAL SOLUTION
            # --------------------------------------------------

            output_file = os.path.join(
                OUTPUT_DIR,
                f"{name}_solution.csv"
            )

            solution.to_csv(
                output_file,
                index=False
            )

            # --------------------------------------------------
            # COMPARISON ROW
            # --------------------------------------------------

            row = {

                "algorithm":
                    name,

                "runtime_seconds":
                    round(
                        runtime,
                        6
                    ),

                "assignment_rate":
                    float(
                        metrics[
                            "assignment_rate"
                        ]
                    ),

                "slot_utilization":
                    float(
                        metrics[
                            "slot_utilization"
                        ]
                    ),

                "total_loaded_weight":
                    float(
                        metrics[
                            "total_loaded_weight"
                        ]
                    ),

                "average_container_weight":
                    float(
                        metrics[
                            "average_container_weight"
                        ]
                    ),

                "total_teu":
                    int(
                        metrics[
                            "total_teu"
                        ]
                    ),

                "constraint_violations":
                    int(
                        metrics[
                            "constraint_violations"
                        ]
                    ),

                "rehandling":
                    float(
                        objective[
                            "rehandling"
                        ]
                    ),

                "weight_imbalance_std":
                    float(
                        objective[
                            "weight_imbalance_std"
                        ]
                    ),

                "longitudinal_balance_error":
                    float(
                        objective[
                            "longitudinal_balance_error"
                        ]
                    ),

                "destination_mixing":
                    float(
                        objective[
                            "destination_mixing"
                        ]
                    ),

                "priority_penalty":
                    float(
                        objective[
                            "priority_penalty"
                        ]
                    ),

                "unassigned":
                    int(
                        objective[
                            "unassigned_containers"
                        ]
                    ),

                "objective_score":
                    float(
                        objective[
                            "objective_score"
                        ]
                    )
            }

            all_results.append(
                row
            )

            print(
                f"Assignment Rate: "
                f"{row['assignment_rate']:.2f}%"
            )

            print(
                f"Slot Utilization: "
                f"{row['slot_utilization']:.2f}%"
            )

            print(
                f"Objective Score: "
                f"{row['objective_score']:.2f}"
            )

            print(
                f"Runtime: "
                f"{runtime:.4f} seconds"
            )

            print(
                "Status: SUCCESS"
            )

        except Exception as error:

            runtime = (
                time.perf_counter()
                - start_time
            )

            print(
                f"ERROR: {error}"
            )

            print(
                "Status: FAILED"
            )

        print()

    # --------------------------------------------------
    # CREATE COMPARISON DATAFRAME
    # --------------------------------------------------

    results = pd.DataFrame(
        all_results
    )

    # --------------------------------------------------
    # SAVE CSV
    # --------------------------------------------------

    comparison_csv = os.path.join(
        OUTPUT_DIR,
        "algorithm_comparison.csv"
    )

    results.to_csv(
        comparison_csv,
        index=False
    )

    # --------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------

    comparison_json = os.path.join(
        OUTPUT_DIR,
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

    # --------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------

    print("\n========================================")
    print("FINAL ALGORITHM COMPARISON")
    print("========================================\n")

    if results.empty:

        print(
            "No algorithm completed successfully."
        )

    else:

        print(
            results.to_string(
                index=False
            )
        )

        print("\nFiles saved:")
        print(
            comparison_csv
        )
        print(
            comparison_json
        )


if __name__ == "__main__":

    run()