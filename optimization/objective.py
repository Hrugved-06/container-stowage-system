import pandas as pd
import numpy as np


def calculate_bay_weights(solution):

    assigned = solution[
        solution["slot_id"].notna()
    ]

    if assigned.empty:
        return {}

    return (
        assigned
        .groupby("bay")["container_weight"]
        .sum()
        .to_dict()
    )


def calculate_weight_imbalance(solution):

    bay_weights = calculate_bay_weights(solution)

    if len(bay_weights) <= 1:
        return 0.0

    weights = np.array(
        list(bay_weights.values()),
        dtype=float
    )

    return float(np.std(weights))


def calculate_max_bay_difference(solution):

    bay_weights = calculate_bay_weights(solution)

    if len(bay_weights) <= 1:
        return 0.0

    weights = list(
        bay_weights.values()
    )

    return float(
        max(weights) - min(weights)
    )


def calculate_longitudinal_balance(solution):

    assigned = solution[
        solution["slot_id"].notna()
    ]

    if assigned.empty:
        return 0.0

    bay_weights = (
        assigned
        .groupby("bay")["container_weight"]
        .sum()
    )

    bays = np.array(
        list(bay_weights.index),
        dtype=float
    )

    weights = np.array(
        list(bay_weights.values),
        dtype=float
    )

    total_weight = weights.sum()

    if total_weight == 0:
        return 0.0

    center_of_mass = (
        (bays * weights).sum()
        / total_weight
    )

    target = bays.mean()

    return float(
        abs(center_of_mass - target)
    )


def calculate_rehandling(solution):

    assigned = solution[
        solution["slot_id"].notna()
    ].copy()

    if assigned.empty:
        return 0

    required_columns = {
        "bay",
        "row",
        "tier",
        "destination_order"
    }

    if not required_columns.issubset(
        assigned.columns
    ):
        return 0

    rehandling = 0

    groups = assigned.groupby(
        ["bay", "row"]
    )

    for _, stack in groups:

        stack = stack.sort_values(
            "tier"
        )

        records = stack.to_dict(
            "records"
        )

        for i in range(len(records)):

            lower = records[i]

            for j in range(i + 1, len(records)):

                upper = records[j]

                if (
                    upper["destination_order"]
                    >
                    lower["destination_order"]
                ):
                    rehandling += 1

    return rehandling


def calculate_destination_mixing(solution):

    assigned = solution[
        solution["slot_id"].notna()
    ]

    if assigned.empty:
        return 0.0

    groups = assigned.groupby(
        ["bay", "row"]
    )

    mixing = 0

    for _, stack in groups:

        destinations = (
            stack["destination"]
            .nunique()
        )

        if destinations > 1:
            mixing += destinations - 1

    return float(mixing)


def calculate_unassigned_penalty(solution):

    return int(
        solution["slot_id"].isna().sum()
    )


def calculate_priority_penalty(solution):

    assigned = solution[
        solution["slot_id"].notna()
    ]

    if assigned.empty:
        return 0.0

    return float(
        (
            assigned["priority"]
            .astype(float)
            - 1
        ).sum()
    )


def calculate_objective_score(
    solution,
    rehandling_weight=100.0,
    imbalance_weight=1.0,
    longitudinal_weight=1000.0,
    unassigned_weight=1000000.0,
    destination_weight=20.0,
    priority_weight=5.0
):

    rehandling = calculate_rehandling(
        solution
    )

    imbalance = calculate_weight_imbalance(
        solution
    )

    longitudinal = calculate_longitudinal_balance(
        solution
    )

    unassigned = calculate_unassigned_penalty(
        solution
    )

    destination_mixing = calculate_destination_mixing(
        solution
    )

    priority_penalty = calculate_priority_penalty(
        solution
    )

    score = (
        rehandling_weight * rehandling
        + imbalance_weight * imbalance
        + longitudinal_weight * longitudinal
        + unassigned_weight * unassigned
        + destination_weight * destination_mixing
        + priority_weight * priority_penalty
    )

    return {
        "rehandling": rehandling,
        "weight_imbalance_std": imbalance,
        "longitudinal_balance_error": longitudinal,
        "destination_mixing": destination_mixing,
        "priority_penalty": priority_penalty,
        "unassigned_containers": unassigned,
        "objective_score": score,
    }


if __name__ == "__main__":

    solution = pd.read_csv(
        "experiments/results/greedy_solution.csv"
    )

    metrics = calculate_objective_score(
        solution
    )

    print("\n===== MULTI-OBJECTIVE METRICS =====")

    for key, value in metrics.items():

        if isinstance(value, float):
            print(
                f"{key}: {value:.4f}"
            )
        else:
            print(
                f"{key}: {value}"
            )