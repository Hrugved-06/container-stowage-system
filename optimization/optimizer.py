import time

import pandas as pd
from ortools.sat.python import cp_model

try:
    from .constraints import check_all_constraints
except ImportError:
    from constraints import check_all_constraints


def optimize_stowage(containers, slots, time_limit=30):
    """
    Solve the container stowage assignment problem
    using Google OR-Tools CP-SAT.

    The current prototype:

    - assigns containers to compatible slots
    - prevents duplicate slot usage
    - penalizes unassigned containers
    - minimizes simplified bay weight imbalance

    This is an academic optimization model,
    not a certified vessel stability system.
    """

    model = cp_model.CpModel()

    num_containers = len(containers)
    num_slots = len(slots)

    # --------------------------------------------------
    # STEP 1: Determine feasible container-slot pairs
    # --------------------------------------------------

    feasible_pairs = []

    for i, container in containers.iterrows():

        for j, slot in slots.iterrows():

            result = check_all_constraints(
                container,
                slot
            )

            if result["valid"]:
                feasible_pairs.append((i, j))

    # --------------------------------------------------
    # STEP 2: Create assignment variables
    # --------------------------------------------------

    x = {}

    for i, j in feasible_pairs:

        x[i, j] = model.new_bool_var(
            f"x_{i}_{j}"
        )

    # --------------------------------------------------
    # STEP 3: Assignment variables
    # --------------------------------------------------

    assigned = {}

    for i in range(num_containers):

        assigned[i] = model.new_bool_var(
            f"assigned_{i}"
        )

    # A container is assigned if exactly one
    # feasible slot is selected.

    for i in range(num_containers):

        possible_slots = [
            x[i, j]
            for ii, j in feasible_pairs
            if ii == i
        ]

        if possible_slots:

            model.add(
                sum(possible_slots) == assigned[i]
            )

        else:

            model.add(
                assigned[i] == 0
            )

    # --------------------------------------------------
    # STEP 4: Each slot can contain at most one container
    # --------------------------------------------------

    for j in range(num_slots):

        possible_containers = [
            x[i, j]
            for i, jj in feasible_pairs
            if jj == j
        ]

        if possible_containers:

            model.add(
                sum(possible_containers) <= 1
            )

    # --------------------------------------------------
    # STEP 5: Calculate bay weights
    # --------------------------------------------------

    bay_values = sorted(
        slots["bay"].unique()
    )

    bay_weights = {}

    total_weight = int(
        containers["weight"].max()
        * num_containers
    )

    for bay in bay_values:

        expressions = []

        for i, j in feasible_pairs:

            slot = slots.iloc[j]

            if slot["bay"] == bay:

                weight = int(
                    containers.iloc[i]["weight"]
                )

                expressions.append(
                    weight * x[i, j]
                )

        if expressions:

            bay_weights[bay] = model.new_int_var(
                0,
                total_weight,
                f"bay_weight_{bay}"
            )

            model.add(
                bay_weights[bay]
                == sum(expressions)
            )

        else:

            bay_weights[bay] = model.new_int_var(
                0,
                total_weight,
                f"bay_weight_{bay}"
            )

            model.add(
                bay_weights[bay] == 0
            )

    # --------------------------------------------------
    # STEP 6: Weight imbalance
    # --------------------------------------------------

    maximum_bay_weight = model.new_int_var(
        0,
        total_weight,
        "maximum_bay_weight"
    )

    minimum_bay_weight = model.new_int_var(
        0,
        total_weight,
        "minimum_bay_weight"
    )

    for bay in bay_values:

        model.add(
            maximum_bay_weight
            >= bay_weights[bay]
        )

        model.add(
            minimum_bay_weight
            <= bay_weights[bay]
        )

    weight_imbalance = model.new_int_var(
        0,
        total_weight,
        "weight_imbalance"
    )

    model.add(
        weight_imbalance
        == maximum_bay_weight
        - minimum_bay_weight
    )

    # --------------------------------------------------
    # STEP 7: Unassigned container penalty
    # --------------------------------------------------

    unassigned = model.new_int_var(
        0,
        num_containers,
        "unassigned"
    )

    model.add(
        unassigned
        == num_containers
        - sum(assigned.values())
    )

    # --------------------------------------------------
    # STEP 8: Objective
    # --------------------------------------------------

    # Large penalty for unassigned containers.
    UNASSIGNED_PENALTY = 100000

    model.minimize(
        weight_imbalance
        + UNASSIGNED_PENALTY * unassigned
    )

    # --------------------------------------------------
    # STEP 9: Solve
    # --------------------------------------------------

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = time_limit

    solver.parameters.num_search_workers = 8

    start_time = time.perf_counter()

    status = solver.solve(model)

    runtime = time.perf_counter() - start_time

    # --------------------------------------------------
    # STEP 10: Read solution
    # --------------------------------------------------

    assignments = []

    if status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):

        for i, container in containers.iterrows():

            selected_slot = None

            for ii, j in feasible_pairs:

                if ii != i:
                    continue

                if solver.value(x[i, j]) == 1:

                    selected_slot = slots.iloc[j]

                    break

            if selected_slot is not None:

                assignments.append(
                    {
                        "container_id":
                            container["container_id"],

                        "slot_id":
                            selected_slot["slot_id"],

                        "bay":
                            selected_slot["bay"],

                        "row":
                            selected_slot["row"],

                        "tier":
                            selected_slot["tier"],

                        "container_size":
                            container["size"],

                        "container_weight":
                            container["weight"],

                        "destination":
                            container["destination"],

                        "priority":
                            container["priority"],
                    }
                )

            else:

                assignments.append(
                    {
                        "container_id":
                            container["container_id"],

                        "slot_id": None,

                        "bay": None,

                        "row": None,

                        "tier": None,

                        "container_size":
                            container["size"],

                        "container_weight":
                            container["weight"],

                        "destination":
                            container["destination"],

                        "priority":
                            container["priority"],
                    }
                )

    else:

        for _, container in containers.iterrows():

            assignments.append(
                {
                    "container_id":
                        container["container_id"],

                    "slot_id": None,

                    "bay": None,

                    "row": None,

                    "tier": None,

                    "container_size":
                        container["size"],

                    "container_weight":
                        container["weight"],

                    "destination":
                        container["destination"],

                    "priority":
                        container["priority"],
                }
            )

    result = pd.DataFrame(
        assignments
    )

    return result, status, runtime


if __name__ == "__main__":

    containers = pd.read_csv(
        "datasets/generated/containers.csv"
    )

    slots = pd.read_csv(
        "datasets/generated/slots.csv"
    )

    print("\n===== CP-SAT OPTIMIZATION =====")

    result, status, runtime = optimize_stowage(
        containers,
        slots
    )

    solver_status = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.UNKNOWN: "UNKNOWN",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
    }

    print(
        "Solver status:",
        solver_status.get(
            status,
            "UNKNOWN"
        )
    )

    print(
        "Runtime:",
        f"{runtime:.4f} seconds"
    )

    print(
        "\n===== OPTIMIZED STOWAGE PLAN =====\n"
    )

    print(
        result.to_string(index=False)
    )

    assigned = result[
        "slot_id"
    ].notna().sum()

    print(
        "\n===== SUMMARY ====="
    )

    print(
        "Total containers:",
        len(containers)
    )

    print(
        "Assigned containers:",
        assigned
    )

    print(
        "Unassigned containers:",
        len(containers) - assigned
    )

    result.to_csv(
        "experiments/results/optimized_solution.csv",
        index=False
    )

    print(
        "\nSaved:"
        " experiments/results/optimized_solution.csv"
    )