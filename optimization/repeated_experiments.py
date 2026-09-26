import time
import pandas as pd

from algorithms import ALGORITHMS
from evaluation import evaluate_solution
from objective import calculate_objective_score


CONTAINER_FILE = (
    "datasets/generated/containers.csv"
)

SLOT_FILE = (
    "datasets/generated/slots.csv"
)


STOCHASTIC = [
    "randomized_greedy",
    "simulated_annealing",
    "genetic",
]


def run():

    containers = pd.read_csv(
        CONTAINER_FILE
    )

    slots = pd.read_csv(
        SLOT_FILE
    )

    records = []

    for algorithm_name in STOCHASTIC:

        algorithm = ALGORITHMS[
            algorithm_name
        ]

        for seed in range(10):

            start = time.perf_counter()

            solution = algorithm(
                containers,
                slots,
                seed=seed
            )

            runtime = (
                time.perf_counter()
                - start
            )

            metrics = evaluate_solution(
                solution,
                containers,
                slots
            )

            objective = (
                calculate_objective_score(
                    solution
                )
            )

            records.append({
                "algorithm":
                    algorithm_name,

                "seed":
                    seed,

                "runtime_seconds":
                    runtime,

                "assignment_rate":
                    metrics[
                        "assignment_rate"
                    ],

                "objective_score":
                    objective[
                        "objective_score"
                    ],

                "weight_imbalance_std":
                    objective[
                        "weight_imbalance_std"
                    ],
            })

            print(
                algorithm_name,
                "seed",
                seed,
                "completed."
            )


    df = pd.DataFrame(
        records
    )

    df.to_csv(
        "experiments/results/"
        "repeated_stochastic_results.csv",
        index=False
    )


    summary = (
        df.groupby("algorithm")
        .agg({
            "runtime_seconds":
                ["mean", "std", "min", "max"],

            "assignment_rate":
                ["mean", "std", "min", "max"],

            "objective_score":
                ["mean", "std", "min", "max"],

            "weight_imbalance_std":
                ["mean", "std", "min", "max"],
        })
    )

    summary.to_csv(
        "experiments/results/"
        "stochastic_summary.csv"
    )

    print(
        "\nRepeated experiment completed."
    )


if __name__ == "__main__":
    run()