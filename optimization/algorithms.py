import random
import math
import time

import pandas as pd

try:
    from .constraints import check_all_constraints
    from .objective import calculate_objective_score
except ImportError:
    from constraints import check_all_constraints
    from objective import calculate_objective_score


def empty_assignment(container):

    return {
        "container_id": container["container_id"],
        "slot_id": None,
        "bay": None,
        "row": None,
        "tier": None,
        "container_size": container["size"],
        "container_weight": container["weight"],
        "destination": container["destination"],
        "destination_order": container.get(
            "destination_order",
            999
        ),
        "priority": container["priority"],
        "hazardous": container["hazardous"],
        "refrigerated": container["refrigerated"],
    }


def make_assignment(container, slot):

    return {
        "container_id": container["container_id"],
        "slot_id": slot["slot_id"],
        "bay": slot["bay"],
        "row": slot["row"],
        "tier": slot["tier"],
        "container_size": container["size"],
        "container_weight": container["weight"],
        "destination": container["destination"],
        "destination_order": container.get(
            "destination_order",
            999
        ),
        "priority": container["priority"],
        "hazardous": container["hazardous"],
        "refrigerated": container["refrigerated"],
    }


def greedy(
    containers,
    slots,
    ordering=None
):

    if ordering is None:
        ordered = containers.copy()
    else:
        ordered = containers.loc[
            ordering
        ]

    assignments = []

    occupied = set()

    for _, container in ordered.iterrows():

        placed = False

        for _, slot in slots.iterrows():

            if slot["slot_id"] in occupied:
                continue

            result = check_all_constraints(
                container,
                slot
            )

            if result["valid"]:

                assignments.append(
                    make_assignment(
                        container,
                        slot
                    )
                )

                occupied.add(
                    slot["slot_id"]
                )

                placed = True

                break

        if not placed:

            assignments.append(
                empty_assignment(
                    container
                )
            )

    return pd.DataFrame(
        assignments
    )


def priority_greedy(
    containers,
    slots
):

    ordering = (
        containers
        .sort_values(
            [
                "priority",
                "destination_order",
                "weight"
            ],
            ascending=[
                True,
                True,
                False
            ]
        )
        .index
    )

    return greedy(
        containers,
        slots,
        ordering
    )


def best_fit(
    containers,
    slots
):

    assignments = []

    occupied = set()

    for _, container in containers.iterrows():

        candidates = []

        for _, slot in slots.iterrows():

            if slot["slot_id"] in occupied:
                continue

            result = check_all_constraints(
                container,
                slot
            )

            if not result["valid"]:
                continue

            remaining_capacity = (
                float(slot["max_weight"])
                - float(container["weight"])
            )

            size_difference = abs(
                int(slot["size"])
                - int(container["size"])
            )

            score = (
                size_difference * 100000
                + remaining_capacity
            )

            candidates.append(
                (
                    score,
                    slot
                )
            )

        if candidates:

            candidates.sort(
                key=lambda x: x[0]
            )

            _, selected = candidates[0]

            assignments.append(
                make_assignment(
                    container,
                    selected
                )
            )

            occupied.add(
                selected["slot_id"]
            )

        else:

            assignments.append(
                empty_assignment(
                    container
                )
            )

    return pd.DataFrame(
        assignments
    )


def randomized_greedy(
    containers,
    slots,
    seed=42
):

    rng = random.Random(
        seed
    )

    ordered = list(
        containers.index
    )

    rng.shuffle(
        ordered
    )

    return greedy(
        containers,
        slots,
        ordered
    )


def random_neighbor(
    solution,
    containers,
    slots,
    rng,
    container_lookup=None,
    slot_lookup=None,
):
    """Create a feasible neighboring stowage plan.

    The original implementation could only move a container into an EMPTY slot.
    That means it became effectively frozen when the vessel was full (for example
    100 uploaded containers competing for 80 slots). This version can also swap
    assigned containers and exchange an assigned container with an unassigned one.
    """
    candidate = solution.copy()

    assigned_rows = candidate[candidate["slot_id"].notna()].index.tolist()
    unassigned_rows = candidate[candidate["slot_id"].isna()].index.tolist()
    if not assigned_rows:
        return candidate

    if container_lookup is None:
        container_lookup = containers.set_index("container_id")
    if slot_lookup is None:
        slot_lookup = slots.set_index("slot_id")

    actions = ["swap"]
    if len(assigned_rows) < len(slots):
        used_slots = set(candidate["slot_id"].dropna().astype(str))
        free_slots = slots[~slots["slot_id"].astype(str).isin(used_slots)]
        if not free_slots.empty:
            actions.append("move")
    else:
        free_slots = slots.iloc[0:0]
    if unassigned_rows:
        actions.extend(["promote", "promote"])

    action = rng.choice(actions)

    if action == "move":
        row_index = rng.choice(assigned_rows)
        cid = candidate.at[row_index, "container_id"]
        container = container_lookup.loc[cid]
        valid = [
            slot for _, slot in free_slots.iterrows()
            if check_all_constraints(container, slot)["valid"]
        ]
        if not valid:
            return candidate
        slot = rng.choice(valid)
        candidate.loc[row_index, ["slot_id", "bay", "row", "tier"]] = [
            slot["slot_id"], slot["bay"], slot["row"], slot["tier"]
        ]
        return candidate

    if action == "promote":
        incoming_row = rng.choice(unassigned_rows)
        outgoing_row = rng.choice(assigned_rows)
        incoming_id = candidate.at[incoming_row, "container_id"]
        outgoing_id = candidate.at[outgoing_row, "container_id"]
        slot_id = candidate.at[outgoing_row, "slot_id"]
        incoming = container_lookup.loc[incoming_id]
        slot = slot_lookup.loc[slot_id]
        if not check_all_constraints(incoming, slot)["valid"]:
            return candidate

        # Put the incoming container in the occupied slot.
        candidate.loc[incoming_row, ["slot_id", "bay", "row", "tier"]] = [
            slot_id,
            candidate.at[outgoing_row, "bay"],
            candidate.at[outgoing_row, "row"],
            candidate.at[outgoing_row, "tier"],
        ]
        # The displaced container becomes unassigned.
        candidate.loc[outgoing_row, ["slot_id", "bay", "row", "tier"]] = [None, None, None, None]
        return candidate

    # Swap two occupied positions. This keeps slot utilization constant while
    # letting the metaheuristics improve destination/rehandling and balance.
    if len(assigned_rows) < 2:
        return candidate
    a, b = rng.sample(assigned_rows, 2)
    cid_a = candidate.at[a, "container_id"]
    cid_b = candidate.at[b, "container_id"]
    slot_a_id = candidate.at[a, "slot_id"]
    slot_b_id = candidate.at[b, "slot_id"]
    container_a = container_lookup.loc[cid_a]
    container_b = container_lookup.loc[cid_b]
    slot_a = slot_lookup.loc[slot_a_id]
    slot_b = slot_lookup.loc[slot_b_id]

    if not check_all_constraints(container_a, slot_b)["valid"]:
        return candidate
    if not check_all_constraints(container_b, slot_a)["valid"]:
        return candidate

    pos_a = [candidate.at[a, c] for c in ["slot_id", "bay", "row", "tier"]]
    pos_b = [candidate.at[b, c] for c in ["slot_id", "bay", "row", "tier"]]
    candidate.loc[a, ["slot_id", "bay", "row", "tier"]] = pos_b
    candidate.loc[b, ["slot_id", "bay", "row", "tier"]] = pos_a
    return candidate


def _interactive_sa_iterations(container_count):
    if container_count <= 30:
        return 260
    if container_count <= 120:
        return 160
    if container_count <= 250:
        return 70
    return 18


def simulated_annealing(
    containers,
    slots,
    iterations=None,
    initial_temperature=1000.0,
    cooling=0.985,
    seed=42
):

    rng = random.Random(seed)
    if iterations is None:
        iterations = _interactive_sa_iterations(len(containers))

    container_lookup = containers.set_index("container_id")
    slot_lookup = slots.set_index("slot_id")

    current = randomized_greedy(
        containers,
        slots,
        seed
    )

    current_score = calculate_objective_score(
        current
    )["objective_score"]

    best = current.copy()

    best_score = current_score

    temperature = initial_temperature

    for _ in range(iterations):

        candidate = random_neighbor(
            current,
            containers,
            slots,
            rng,
            container_lookup=container_lookup,
            slot_lookup=slot_lookup,
        )

        candidate_score = calculate_objective_score(
            candidate
        )["objective_score"]

        delta = (
            candidate_score
            - current_score
        )

        if (
            delta < 0
            or rng.random()
            <
            math.exp(
                -delta
                / max(
                    temperature,
                    1e-9
                )
            )
        ):

            current = candidate
            current_score = candidate_score

        if current_score < best_score:

            best = current.copy()

            best_score = current_score

        temperature *= cooling

    return best


def genetic_algorithm(
    containers,
    slots,
    population_size=None,
    generations=None,
    mutation_rate=0.20,
    seed=42
):

    rng = random.Random(seed)

    n = len(containers)
    if population_size is None:
        population_size = 14 if n <= 120 else (9 if n <= 250 else 5)
    if generations is None:
        generations = 16 if n <= 120 else (8 if n <= 250 else 4)

    container_lookup = containers.set_index("container_id")
    slot_lookup = slots.set_index("slot_id")

    population = []

    for i in range(
        population_size
    ):

        population.append(
            randomized_greedy(
                containers,
                slots,
                seed + i
            )
        )

    def fitness(solution):

        return calculate_objective_score(
            solution
        )["objective_score"]

    for _ in range(
        generations
    ):

        population.sort(
            key=fitness
        )

        elite = population[
            :max(
                2,
                population_size // 5
            )
        ]

        new_population = [
            x.copy()
            for x in elite
        ]

        while len(
            new_population
        ) < population_size:

            parent = rng.choice(
                elite
            )

            child = parent.copy()

            if rng.random() < mutation_rate:

                child = random_neighbor(
                    child,
                    containers,
                    slots,
                    rng,
                    container_lookup=container_lookup,
                    slot_lookup=slot_lookup,
                )

            new_population.append(
                child
            )

        population = new_population

    population.sort(
        key=fitness
    )

    return population[0]


def cp_sat(
    containers,
    slots,
    time_limit=8
):

    from ortools.sat.python import cp_model

    model = cp_model.CpModel()

    variables = {}

    for i, container in containers.iterrows():

        for j, slot in slots.iterrows():

            if check_all_constraints(
                container,
                slot
            )["valid"]:

                variables[
                    (i, j)
                ] = model.NewBoolVar(
                    f"x_{i}_{j}"
                )

    for i in containers.index:

        possible = [
            variables[(i, j)]
            for j in slots.index
            if (i, j) in variables
        ]

        if possible:

            model.Add(
                sum(possible) <= 1
            )

    for j in slots.index:

        possible = [
            variables[(i, j)]
            for i in containers.index
            if (i, j) in variables
        ]

        if possible:

            model.Add(
                sum(possible) <= 1
            )

    objective_terms = []

    for (i, j), variable in variables.items():

        priority = int(
            containers.loc[
                i,
                "priority"
            ]
        )

        objective_terms.append(
            (1000 - priority)
            * variable
        )

    model.Maximize(
        sum(objective_terms)
    )

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = (
        time_limit
    )

    status = solver.Solve(
        model
    )

    assignments = []

    used_containers = set()

    for (i, j), variable in variables.items():

        if solver.Value(
            variable
        ) == 1:

            container = containers.loc[
                i
            ]

            slot = slots.loc[
                j
            ]

            assignments.append(
                make_assignment(
                    container,
                    slot
                )
            )

            used_containers.add(
                i
            )

    for i, container in containers.iterrows():

        if i not in used_containers:

            assignments.append(
                empty_assignment(
                    container
                )
            )

    return pd.DataFrame(
        assignments
    )


ALGORITHMS = {

    "greedy": greedy,

    "priority_greedy":
        priority_greedy,

    "best_fit":
        best_fit,

    "randomized_greedy":
        randomized_greedy,

    "simulated_annealing":
        simulated_annealing,

    "genetic":
        genetic_algorithm,

    "cp_sat":
        cp_sat
}